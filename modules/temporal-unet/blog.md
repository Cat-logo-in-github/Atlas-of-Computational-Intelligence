# BioHub Cell Tracking — Understanding the Temporal U-Net + Transformer Pipeline

This README explains how the current BioHub cell-tracking pipeline works from **raw Zarr images to a final tracking graph**.

The goal is not just to describe which functions are called, but to explain **what the model is trying to do at each stage and why each stage exists**.

The pipeline can be thought of as:

```text
Raw microscopy video
        │
        ▼
   Zarr dataset
        │
        ▼
Read metadata + image statistics
        │
        ▼
Quantile normalization
        │
        ▼
Spatial downsampling
        │
        ▼
Temporal windows of frames
        │
        ▼
┌──────────────────────────────┐
│      Temporal U-Net 3D       │
│                              │
│  image → spatial features    │
│       + detection logits     │
└──────────────────────────────┘
        │
        ├──────────────► Cell detection
        │                    │
        │                    ▼
        │              cell coordinates
        │
        ▼
U-Net feature maps
        │
        ▼
Extract features at detected cells
        │
        ▼
Positional / temporal features
        │
        ▼
┌──────────────────────────────┐
│      Node Transformer        │
│                              │
│ source-cell ↔ target-cell    │
│                              │
│        edge probability      │
└──────────────────────────────┘
        │
        ▼
Edge filtering / constraints
        │
        ▼
Tracking graph
        │
        ├────────► optional ILP optimization
        │
        ▼
       .geff
        │
        ▼
    Evaluation
```

The important idea is that this is **not one model doing tracking directly**.

Instead, the system separates the problem into two related tasks:

1. **Where are the cells?**
2. **Which cell in one frame corresponds to which cell in the next frame?**

The Temporal U-Net primarily provides the visual representation and cell-detection signal. The transformer then uses those representations, together with cell positions, to predict links between cells.

---

# 1. Dataset

The input is a microscopy time-lapse stored as a Zarr dataset.

Conceptually, the image has four dimensions:

```text
(T, Z, Y, X)
```

where:

* `T` = time / frame
* `Z` = depth
* `Y` = image height
* `X` = image width

A single frame is therefore a 3D volume:

```text
(Z, Y, X)
```

and the complete video is a sequence of these volumes:

```text
frame 0
frame 1
frame 2
...
frame T-1
```

The current datasets use anisotropic voxel sizes. The default physical scale is:

```text
Z = 1.625 µm
Y = 0.40625 µm
X = 0.40625 µm
```

This matters because a voxel step in `Z` does not represent the same physical distance as a voxel step in `Y` or `X`.

The dataset also stores image statistics in the Zarr attributes. In particular, the prediction pipeline expects the `0.001` and `0.999` quantiles.

These statistics allow inference to use the same intensity normalization convention that was used during training.

---

# 2. Opening the Dataset

The main dataset entry point is:

```python
open_dataset(...)
```

from:

```text
biohub_tracking/io.py
```

The function handles the dataset as a combination of:

```text
Zarr image
   +
metadata
   +
voxel scale
   +
optional tracking graph
   +
image statistics
```

The important distinction is that opening a dataset does **not necessarily mean loading the entire image into memory**.

During prediction we use:

```python
load_image=False
```

because the prediction code reads individual frames directly from Zarr.

This is useful for large microscopy videos where loading the entire volume into RAM would be unnecessary.

The returned `Dataset` object still contains:

```text
image_shape
zarr_path
scale
quantiles
```

so the prediction code knows how the data is structured.

---

# 3. Intensity Normalization

Microscopy images can have very different raw intensity ranges.

The model should not have to learn:

```text
"this dataset uses values around 3000"
```

versus:

```text
"this dataset uses values around 50000"
```

when those differences are caused mainly by acquisition conditions.

Instead, the image is normalized using quantiles.

The basic operation is:

```python
normalized = (image - q_low) / (q_high - q_low + 1e-6)
```

followed by clipping at zero.

For prediction, the stored:

```text
0.1% quantile
0.999% quantile
```

statistics are used.

In other words, the pipeline approximately treats:

```text
very dark pixels  → 0
low/high useful range → 0..1
very bright pixels → >1
```

and then clips the result.

The important conceptual point is:

> **Normalization changes the intensity scale, not the biological structure of the image.**

It gives the neural network a more consistent numerical input.

---

# 4. Spatial Downsampling

The current model uses:

```python
downsample = (1, 4, 4)
```

This means:

```text
Z → keep every voxel
Y → keep every 4th voxel
X → keep every 4th voxel
```

So the image becomes approximately:

```text
(T, Z, Y/4, X/4)
```

The reason this is useful is that the original XY resolution is much finer than the Z resolution.

Keeping the full XY resolution would make the 3D convolutional network considerably more expensive.

Notice that Z is **not** downsampled:

```text
(1, 4, 4)
 ↑  ↑  ↑
 Z  Y  X
```

This preserves the already-coarse depth information while reducing the much larger XY computational cost.

The prediction code keeps track of this transformation so that detected coordinates can later be converted back to the original image coordinate system.

---

# 5. Temporal Windows

The model does not necessarily process the entire video at once.

Instead, it processes small temporal windows.

The checkpoint configuration currently contains:

```python
window_size = 2
```

Therefore the model normally sees:

```text
frame t
frame t+1
```

together.

This is important because the model is called a **Temporal U-Net**.

A purely spatial model would look at one 3D volume:

```text
frame t
```

A temporal model can instead look at:

```text
frame t ─────► frame t+1
```

and learn representations that contain information about how structures change across time.

The prediction code uses sliding windows.

With `W = 2`, the windows are conceptually:

```text
[0, 1]
[1, 2]
[2, 3]
[3, 4]
...
```

Every consecutive frame pair is therefore covered.

---

# 6. TemporalUNet3D

The main visual model is:

```python
TemporalUNet3D
```

with the current configuration:

```python
{
    "unet_out_channels": 32,
    "unet_layers": [32, 64, 128],
    "downsample": [1, 4, 4],
    "window_size": 2,
    "pool_kernel_um": 5.0
}
```

The important distinction is between:

```text
input image
```

and:

```text
learned feature representation
```

The image contains raw intensity values.

The U-Net transforms those values through a sequence of convolutional operations into feature maps.

These feature maps can encode things such as:

```text
local brightness
cell-like structures
boundaries
texture
spatial context
3D shape
temporal context
```

We should not think of each feature channel as one simple human-interpretable property. Instead, the network learns a distributed representation useful for the downstream tasks.

---

# 7. Why a U-Net?

A U-Net has two broad sides:

```text
Encoder
   ↓
compressed / contextual representation
   ↓
Decoder
```

The encoder progressively builds higher-level features.

The decoder brings information back toward the spatial resolution needed for prediction.

Skip connections allow information from earlier, higher-resolution layers to be combined with deeper features.

Conceptually:

```text
high-resolution details
       │
       ├──────────────┐
       ▼              │
     Encoder          │
       │              │
       ▼              │
  deep features       │
       │              │
       ▼              │
     Decoder ◄────────┘
       │
       ▼
spatial prediction
```

For this tracking system, the U-Net output is valuable for **more than just producing a segmentation-like prediction**.

Its feature maps become the visual representation used by the transformer.

---

# 8. U-Net Output

The model's encoder is called through:

```python
unet_out, det_logits = model.encode(imgs)
```

There are two important outputs.

## `unet_out`

This is the learned feature representation.

Conceptually:

```text
image
  ↓
Temporal U-Net
  ↓
feature maps
```

The current model produces:

```text
32 feature channels
```

at the relevant output resolution.

These features are later sampled at detected cell locations.

## `det_logits`

These are the raw detection scores.

They are not probabilities yet.

They are logits, which are converted using:

```python
torch.sigmoid(...)
```

so that each location receives a value between:

```text
0 and 1
```

interpreted as the detector's confidence that a cell center exists there.

---

# 9. Detection Is a Peak-Finding Problem

The detector does not simply threshold every voxel.

If every voxel with:

```text
probability > threshold
```

were considered a cell, one cell could generate hundreds of nearby detections.

Instead, the prediction code performs local-max detection using:

```python
F.max_pool3d(...)
```

The basic idea is:

```text
                 high score
                    ●
                  / | \
                 /  |  \
                low values
```

A point is accepted when:

1. its detector logit is the maximum within the local neighborhood, and
2. its sigmoid probability is above the detection threshold.

Therefore, detection becomes:

```text
detector heatmap
      ↓
local maximum filtering
      ↓
confidence threshold
      ↓
one coordinate per detected cell
```

The resulting coordinates have the form:

```text
[t, z, y, x]
```

---

# 10. Physical-Size-Aware Detection

The pooling kernel is not simply chosen as an arbitrary number of voxels.

The code converts a physical suppression distance in microns into a per-axis voxel kernel:

```python
pool_kernel_from_um(...)
```

For example, because:

```text
Z = 1.625 µm
Y = 0.40625 µm
X = 0.40625 µm
```

a fixed physical distance corresponds to very different numbers of voxels in Z and XY.

This produces an anisotropic kernel.

That is important because a cell that is separated by a certain physical distance should not be treated differently merely because the voxel spacing differs between axes.

---

# 11. Detection Test-Time Augmentation

The detector can also use test-time augmentation.

The current prediction code performs:

```text
original
flip X
flip Y
flip X + Y
```

The Z axis is intentionally not flipped.

This is because the data is strongly anisotropic and the Z direction has substantially different resolution.

For each flipped version:

```text
image
  ↓
U-Net
  ↓
detection logits
  ↓
flip prediction back
```

The logits are then averaged.

Conceptually:

```text
              original ─────┐
              flip X ───────┤
              flip Y ───────┼──► average logits
              flip XY ──────┘
```

This gives the detector several slightly different views of the same image.

![](assets/tta_flips.png)

---

# 12. From Detection Heatmap to Cell Nodes

After peak extraction, we no longer have a dense image.

We have a list of detected cells:

```text
frame 0:
    cell A → (z, y, x)
    cell B → (z, y, x)
    cell C → (z, y, x)

frame 1:
    cell D → (z, y, x)
    cell E → (z, y, x)
    cell F → (z, y, x)
```

These detections become **nodes**.

This is the first major conceptual transition in the pipeline:

```text
image space
     ↓
cell coordinates
     ↓
graph nodes
```

The model has answered:

> "Where do I think cells are?"

It has not yet answered:

> "Which cell belongs to which track?"

That is the next stage.

---

# 13. The Node Registry

During sliding-window prediction, the same frame may appear in multiple windows.

For example:

```text
window 0: [0, 1]
window 1: [1, 2]
window 2: [2, 3]
```

Frame `1` appears twice.

The code therefore keeps:

```python
seen_frames
coord_offset
```

to make sure detections for a frame are only registered once.

Conceptually:

```text
window [0,1] → detect frame 0 + frame 1
window [1,2] → frame 1 already exists
                 ↓
              reuse it
```

This prevents duplicate nodes from being created for the same biological cell simply because the frame appeared in more than one inference window.

---

# 14. Returning Coordinates to Original Resolution

The U-Net operates on the downsampled image.

Therefore its detected coordinates initially live in:

```text
downsampled coordinate space
```

For:

```python
downsample = (1, 4, 4)
```

a detected:

```text
(z, y, x)
```

corresponds approximately to:

```text
(z, 4y, 4x)
```

in the original image.

At the end of prediction:

```python
coords[:, 1:] *= ds_arr
```

converts spatial coordinates back to the original resolution.

Time is not scaled.

Therefore:

```text
[t, z, y, x]
```

becomes:

```text
[t, original_z, original_y, original_x]
```

---

# 15. Why We Need Another Model

At this point we have detected cells.

Suppose we have:

```text
Frame t

A    B    C
```

and in the next frame:

```text
Frame t+1

D    E    F
```

We need to determine something like:

```text
A → D
B → F
C → E
```

This is a matching problem.

The nearest cell is not always the correct cell.

Two cells may be physically close.

Cells may move.

Cells may change appearance.

Cells may divide.

A robust tracker therefore needs information beyond simple Euclidean distance.

This is where the transformer-based edge predictor enters.

---

# 16. Extracting Features at Cell Locations

The U-Net has produced a dense feature map:

```text
Z × Y × X × C
```

but the tracker does not need every voxel.

We already know the approximate cell coordinates.

The method:

```python
model._index_features(...)
```

samples the U-Net feature map at those coordinates.

So instead of representing the entire image, we obtain:

```text
cell A → feature vector
cell B → feature vector
cell C → feature vector
```

This converts the dense visual representation into a collection of **node features**.

Conceptually:

```text
U-Net feature map

████████████████
██████●█████████
████████████████
████████●███████
████████████████

        ↓ sample at detections

cell 1 → [feature vector]
cell 2 → [feature vector]
```

The transformer can then reason about cells rather than every voxel in the image.

---

# 17. Positional Features

Visual features alone are not enough.

The tracker also needs to know where the cells are.

The code therefore creates positional features using:

```python
extract_pos_features(...)
```

The features encode spatial and temporal position.

The transformer consequently receives information of the general form:

```text
cell appearance
+
cell position
+
cell time
```

This is important because two cells can look similar while being in completely different parts of the image.

Likewise, a candidate correspondence between two cells is more plausible when their spatial relationship is reasonable.

---

# 18. Source Cells and Target Cells

For each consecutive pair of frames we create two node sets:

```text
source frame
     │
     ▼
source cells

target frame
     │
     ▼
target cells
```

For example:

```text
Frame t                         Frame t+1

A ─────────────── candidate ───► D
A ─────────────── candidate ───► E
A ─────────────── candidate ───► F

B ─────────────── candidate ───► D
B ─────────────── candidate ───► E
B ─────────────── candidate ───► F
```

The transformer effectively evaluates these possible relationships.

---

# 19. Transformer Edge Prediction

The relevant model call is:

```python
model.predict_edges(...)
```

The output is approximately:

```text
(number of source cells,
 number of target cells)
```

For example, with:

```text
3 source cells
4 target cells
```

the model produces:

```text
3 × 4
```

edge logits.

Each entry represents the model's score for:

```text
source cell i → target cell j
```

Conceptually:

```text
             Target
             D    E    F
          ┌───────────────┐
Source A  │ .8  .1  .2    │
Source B  │ .1  .9  .3    │
Source C  │ .2  .2  .7    │
          └───────────────┘
```

This is the second major transition:

```text
cell nodes
   ↓
candidate relationships
   ↓
edge scores
```

---

# 20. What the Transformer Is Actually Predicting

It is useful to distinguish between:

```text
logit
```

and:

```text
probability
```

The transformer produces raw edge logits.

These are converted into probabilities using either:

```python
softmax
```

or:

```python
sigmoid
```

The current default is:

```python
edge_activation = "softmax"
```

With softmax, the scores are normalized across the candidate target dimension.

This makes the model's output behave more like a competition between possible target cells.

Conceptually:

```text
Source A

A → D : 0.80
A → E : 0.15
A → F : 0.05
```

rather than treating every edge as an entirely independent yes/no decision.

---

# 21. Why Edge Probability Is Not Enough

Even if the model predicts:

```text
A → D = 0.91
```

we still need to decide whether the edge should actually be placed in the tracking graph.

There are biological and graph constraints.

For example, a normal cell generally has:

```text
at most one parent
```

and usually:

```text
one child
```

while a dividing cell may have:

```text
two children
```

The prediction pipeline therefore performs a second stage:

```text
raw edge scores
       ↓
probabilities
       ↓
thresholding
       ↓
graph constraints
       ↓
accepted edges
```

---

# 22. Edge Thresholding

The configuration contains:

```python
threshold = 0.5
```

Only candidates satisfying:

```python
probability > threshold
```

are considered.

This is not the same thing as saying that the model is always "50% certain."

The threshold is a **post-processing decision**.

Changing it changes the precision/recall trade-off.

A lower threshold may produce:

```text
more candidate links
```

but also:

```text
more false links
```

A higher threshold may produce:

```text
fewer links
```

but potentially miss real links.

---

# 23. Parent and Child Constraints

When ILP is disabled, the code applies greedy constraints.

The defaults are:

```python
max_parents_per_node = 1
max_children_per_node = 2
```

Therefore:

```text
one target cell
    ← at most one parent
```

and:

```text
one source cell
    → at most two children
```

The second rule allows divisions.

The edges are sorted from highest probability to lowest probability.

Then the code accepts an edge if the corresponding parent/child constraints have not already been filled.

Conceptually:

```text
candidate edges

A → D   0.95
B → D   0.91
A → E   0.88
A → F   0.83

        ↓

take A → D
        ↓
D already has a parent

take B → D?
        ↓
reject

take A → E
        ↓
accept

take A → F
        ↓
accept if division is allowed
```

This is a **greedy local solution**.

It is simple and fast, but it does not necessarily produce the globally best tracking graph.

---

# 24. Optional ILP Post-Processing

The pipeline also contains an optional global optimization stage.

ILP means:

```text
Integer Linear Programming
```

The tracking problem is represented as an optimization problem where candidate edges are selected subject to constraints.

Instead of deciding:

```text
"Is this individual edge good?"
```

the solver can reason about:

```text
"What collection of edges produces the best globally consistent tracking solution?"
```

The solver includes terms for:

```text
edge selection
appearance
disappearance
division
```

The main edge contribution is based on:

```python
edge_prob
```

The ILP can therefore replace the greedy edge assignment with a globally optimized graph.

The current default configuration does not enable ILP:

```python
use_ilp = False
```

So the normal prediction path is:

```text
edge probabilities
       ↓
greedy filtering
       ↓
graph
```

while the optional path is:

```text
edge probabilities
       ↓
ILP solver
       ↓
globally optimized graph
```

---

# 25. Building the Tracking Graph

Once nodes and accepted edges are available, the pipeline constructs a `tracksdata` graph.

Nodes contain:

```text
t
z
y
x
```

Edges contain:

```text
source
target
edge_prob
edge_dist
```

So the final structure looks conceptually like:

```text
             Frame t

        ┌── Cell A
        │
        │
        ▼
        Cell D ─────► Cell G
        │
        └───────────► Cell H
             Frame t+1       Frame t+2
```

The graph is no longer an image.

It is a mathematical representation of the inferred cell trajectories.

---

# 26. Edge Distance

The graph also stores:

```python
edge_dist
```

which is the Euclidean distance between the source and target coordinates.

This is calculated from the detected coordinates.

It provides useful information for later analysis, even though the current greedy edge selection primarily uses the predicted edge probability.

Therefore each accepted edge has two useful pieces of information:

```text
edge_prob
    How strongly the model supports the connection

edge_dist
    How far the cells are from one another
```

---

# 27. Saving the Result

The final graph is saved using:

```python
save_graph(...)
```

as:

```text
.geff
```

The `.geff` file is the graph representation of the prediction.

At this point the pipeline has transformed:

```text
microscopy video
```

into:

```text
tracking graph
```

The graph can then be loaded by downstream tracking/evaluation tools.

---

# 28. Evaluation

When evaluation is enabled, the generated graphs are compared with the available ground truth.

The pipeline reports quantities such as:

```text
score
edge_jaccard
adj_edge_jaccard
division_jaccard
node_recall
```

These measure different parts of the tracking problem.

## Node recall

This asks approximately:

> How many of the expected cell detections were recovered?

A detector that misses many cells will have poor node recall even if its links are very accurate.

## Edge Jaccard

This compares predicted and ground-truth edges.

It measures whether the tracker connected the correct cells.

## Adjacent-edge Jaccard

This focuses on edges between adjacent time points.

This is especially relevant because the current model predicts consecutive-frame links.

## Division Jaccard

This evaluates cell division events.

This is particularly important because division introduces a branching structure:

```text
        parent
          │
       ┌──┴──┐
       ▼     ▼
    child  child
```

A tracking system can therefore have good node detection while still performing poorly on divisions.

---

# 29. The Complete Mental Model

The easiest way to understand the entire system is to divide it into four layers.

## Layer 1 — Image understanding

```text
Raw Zarr image
      ↓
normalization
      ↓
downsampling
      ↓
Temporal U-Net
      ↓
feature maps + detection logits
```

The question here is:

> **What is in the image?**

---

## Layer 2 — Cell detection

```text
detection logits
      ↓
sigmoid
      ↓
local-max pooling
      ↓
threshold
      ↓
cell coordinates
```

The question here is:

> **Where are the cells?**

---

## Layer 3 — Cell-to-cell matching

```text
cell coordinates
      +
U-Net features
      +
positional features
      ↓
transformer
      ↓
edge logits
      ↓
edge probabilities
```

The question here is:

> **Which cell corresponds to which cell in the next frame?**

---

## Layer 4 — Graph construction

```text
candidate edges
      ↓
threshold
      ↓
parent/child constraints
      ↓
optional ILP
      ↓
tracking graph
      ↓
.geff
```

The question here is:

> **Which predicted relationships form a valid tracking solution?**

---

# 30. The Most Important Concept

The most important thing to remember is that **tracking is not performed directly on pixels**.

The pipeline gradually changes representation:

```text
pixels
  ↓
features
  ↓
detections
  ↓
nodes
  ↓
candidate edges
  ↓
tracking graph
```

Each representation solves a different part of the problem.

The Temporal U-Net gives us a learned representation of the image.

The detector converts that representation into candidate cell locations.

The transformer converts pairs of cells into candidate relationships.

The graph stage turns those relationships into trajectories.

This separation is useful because we can inspect each stage independently.

For example:

```text
If detections are wrong:
    investigate the U-Net detector.

If detections are good but links are wrong:
    investigate feature extraction / transformer / edge filtering.

If links look good but divisions are wrong:
    investigate graph constraints / ILP.

If everything looks correct but coordinates are shifted:
    investigate downsampling / physical scaling.
```

This gives us a practical debugging strategy rather than treating the entire pipeline as one opaque neural network.

---

# 31. Current Model Configuration

The checkpoint used by the current support pack contains:

```python
{
    "unet_out_channels": 32,
    "unet_layers": [32, 64, 128],
    "downsample": [1, 4, 4],
    "window_size": 2,
    "pool_kernel_um": 5.0
}
```

The checkpoint itself contains:

```text
epoch
best_score
model_state_dict
optimizer_state_dict
model_config
method
fold
metrics
```

The important distinction is that:

```text
model_state_dict
```

contains the learned parameters, while:

```text
model_config
```

describes how the model should be reconstructed.

Prediction therefore does not simply load arbitrary weights into an arbitrary network.

It reconstructs the expected architecture and then loads the saved parameters.

---

# 32. Prediction Pipeline in Code

The main prediction entry point is:

```text
scripts/predict_unet_transformer.py
```

The important sequence is:

```python
predict(...)
    ↓
load_model(...)
    ↓
predict_video(...)
    ↓
model.encode(...)
    ↓
_detect_cells_pooled(...)
    ↓
_index_features(...)
    ↓
predict_edges(...)
    ↓
edge filtering
    ↓
build_graph(...)
    ↓
optional ILP
    ↓
save_graph(...)
```

This sequence is the practical implementation of the conceptual pipeline described above.

---

# 33. A Single Frame Pair

It is useful to zoom all the way in and follow just two frames.

Suppose we start with:

```text
Frame 10
Frame 11
```

The pipeline does:

```text
1. Read both frames
        ↓
2. Normalize intensity
        ↓
3. Downsample XY
        ↓
4. Stack them into a temporal window
        ↓
5. Run TemporalUNet3D
        ↓
6. Obtain feature maps
        +
   detection logits
        ↓
7. Find local maxima
        ↓
8. Obtain cell coordinates
        ↓
9. Sample U-Net features at those coordinates
        ↓
10. Create positional features
        ↓
11. Send source/target node features to transformer
        ↓
12. Obtain edge logits
        ↓
13. Convert logits to probabilities
        ↓
14. Threshold candidate edges
        ↓
15. Apply parent/child constraints
        ↓
16. Add accepted edges to graph
```

This is the smallest useful unit of the tracking system.

Once this works correctly for one frame pair, the sliding-window code simply repeats the same idea across the video.

---

# 34. Sliding Through the Full Video

For a video:

```text
0 1 2 3 4 5 6
```

with:

```text
window_size = 2
```

the model processes:

```text
[0,1]
[1,2]
[2,3]
[3,4]
[4,5]
[5,6]
```

The detections are registered once per frame.

The edges are predicted once per consecutive pair.

Therefore the final graph combines:

```text
nodes from all frames
+
edges between consecutive frames
```

into one graph.

![](assets/global_graph_accumulation.mp4)

---

# 35. Coordinate Systems

There are several coordinate systems in this pipeline, and keeping them separate prevents many bugs.

### Original image coordinates

The coordinates in the original Zarr volume:

```text
(t, z, y, x)
```

### Downsampled coordinates

After:

```text
(1, 4, 4)
```

the spatial coordinates are approximately:

```text
(t, z, y/4, x/4)
```

### Physical coordinates

A voxel coordinate can be converted into a physical distance using:

```text
(z × scale_z,
 y × scale_y,
 x × scale_x)
```

For the current dataset:

```text
scale = (1.625, 0.40625, 0.40625) µm
```

These coordinate systems should not be mixed.

For example, a Euclidean distance calculated directly in anisotropic voxel units is not the same as a physical distance in microns.

The prediction code is careful about this when physical scaling is relevant.

---

# 36. Why Z Is Special

The image is highly anisotropic:

```text
Z resolution ≈ 4 × coarser than XY
```

This affects several decisions in the pipeline.

### Downsampling

We use:

```text
(1, 4, 4)
```

rather than reducing Z in the same way.

### Test-time augmentation

We flip:

```text
X
Y
X + Y
```

but not Z.

### Detection pooling

The detection kernel is calculated independently for each axis from physical voxel size.

The general principle is:

> **The network and post-processing should respect the physical geometry of the microscope rather than treating every voxel as identical.**

---

# 37. What the Model Does Not Do

It is also useful to be explicit about what is **not** happening.

The current pipeline does not simply:

```text
detect cells
    ↓
connect every nearest neighbor
```

It also does not directly output:

```text
track ID = 17
track ID = 18
...
```

Instead, it builds a graph.

A track is represented implicitly by a connected sequence of graph nodes and edges.

For example:

```text
A ──► B ──► C ──► D
```

represents a trajectory.

A division can be represented as:

```text
        B
       ↙ ↘
A ───► C   D
```

The graph representation is therefore more flexible than assigning a single independent ID to every detection.

---

# 38. Why the Architecture Is Split This Way

The architecture reflects the structure of the biological problem.

A cell-tracking system needs both:

```text
appearance information
```

and:

```text
relationship information
```

The U-Net is good at learning spatial/visual representations from image data.

The transformer is then given a much smaller set of objects:

```text
cell 1
cell 2
cell 3
...
```

and can reason about relationships between those objects.

This is computationally attractive because the transformer does not need to process every voxel in the entire microscopy volume.

Instead:

```text
large image
    ↓
U-Net
    ↓
small set of detected cells
    ↓
transformer
```

The expensive relational reasoning happens on the detected nodes rather than on the full 3D image.

---

# 39. What We Should Inspect Experimentally

The pipeline gives us several natural points for experiments.

### Image → U-Net

Inspect:

```text
normalized input
feature maps
detection logits
```

### U-Net → detections

Inspect:

```text
heatmap
local maxima
threshold
pooling kernel
```

### Detections → node features

Inspect:

```text
cell coordinates
sampled feature vectors
positional features
```

### Nodes → edges

Inspect:

```text
edge logits
edge probabilities
candidate edges
```

### Edges → graph

Inspect:

```text
accepted edges
parent/child constraints
division events
ILP changes
```

This makes the next notebook experiment particularly useful: rather than only looking at the final `.geff`, we can expose the intermediate tensors and visualize what each stage is actually doing.

---

# 40. Final Mental Picture

The whole system can be reduced to one diagram:

```text
                         IMAGE
                           │
                           ▼
                 ┌─────────────────┐
                 │  Normalization  │
                 │ + Downsampling  │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ Temporal U-Net  │
                 └───────┬─┬───────┘
                         │ │
              features ──┘ └── detection logits
                  │                 │
                  │                 ▼
                  │          local-max detection
                  │                 │
                  │                 ▼
                  │          CELL COORDINATES
                  │                 │
                  └────────┬────────┘
                           ▼
                  NODE REPRESENTATIONS
                           │
                           ▼
                 ┌─────────────────┐
                 │ Node Transformer│
                 └────────┬────────┘
                          │
                          ▼
                    EDGE SCORES
                          │
                          ▼
                 threshold + constraints
                          │
                          ▼
                    TRACKING GRAPH
                          │
                    optional ILP
                          │
                          ▼
                       .GEFF
```

![](assets/Pipeline-overview.jpg)

The key idea is therefore:

> **The Temporal U-Net understands the image; the detector turns that understanding into cell candidates; the transformer evaluates relationships between those cells; and the graph stage turns those relationships into tracks.**

That is the working mental model we will use for the next stage of exploration.



---






