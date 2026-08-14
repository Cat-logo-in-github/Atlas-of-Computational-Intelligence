# Image Preprocessing

## Overview

The first stage of the cell-tracking pipeline converts raw microscopy data into a representation that can be consumed reliably by the neural network.

The preprocessing stage is responsible for:

1. Opening the source **Zarr** dataset.
2. Reading image metadata and physical voxel scale.
3. Selecting temporal windows from the video.
4. Loading the corresponding 3D image volumes.
5. Applying quantile-based intensity normalization.
6. Applying spatial downsampling.
7. Optionally applying test-time augmentation (TTA).
8. Maintaining the correct coordinate system and physical scale.

The goal is not to detect cells yet.

Instead, preprocessing ensures that the image entering the [Temporal U-Net](../temporal-unet/knowledge.md#4.-Temporal-U-Net-Architecture) has the same spatial, intensity, and temporal conventions expected by the trained model.

The high-level transformation is:

```text
Raw microscopy video
        │
        ▼
      Zarr
        │
        ▼
 Dataset metadata
        │
        ├──────────────► voxel scale
        │
        └──────────────► intensity statistics
        │
        ▼
 Temporal window
        │
        ▼
 Image loading
        │
        ▼
 Quantile normalization
        │
        ▼
 Spatial downsampling
        │
        ▼
 Optional TTA
        │
        ▼
 Model-ready image
        │
        ▼
```
[Temporal U-Net](../temporal-unet/knowledge.md#4.-Temporal-U-Net-Architecture)

---

# 1. Input Dataset

The source microscopy data is stored as a **Zarr** image dataset.

![](./assets/01_input_timelapse.gif)

Conceptually, the image is a four-dimensional array:

```text
(T, Z, Y, X)
```

where:

| Dimension | Meaning      |
| --------- | ------------ |
| `T`       | Time / frame |
| `Z`       | Depth        |
| `Y`       | Image height |
| `X`       | Image width  |

A short section of the video can therefore be visualized as:

```text
Frame 0              Frame 1              Frame 2
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│              │     │              │     │              │
│   3D volume  │     │   3D volume  │     │   3D volume  │
│              │     │              │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                             ▼
                    Temporal processing
```
![](./assets/01_input_3d_timelapse.mp4)

The model does **not** load the entire video into the network simultaneously.

Instead, inference operates on short temporal windows.

For example, with:

```python
window_size = 2
```

the video is processed as:

```text
(frame 0, frame 1)
(frame 1, frame 2)
(frame 2, frame 3)
(frame 3, frame 4)
...
```

For a temporal window of `W` frames, the prediction process uses a stride of:

```text
W - 1
```

This allows consecutive frame pairs to be covered while still providing the temporal context required by the model.

The details of how these windows are consumed by the neural network are described in [Temporal U-Net](../temporal-unet/knowledge.md#2.)

---

# 2. Dataset Parsing

The main dataset entry point is:

```python
open_dataset(...)
```

located in:

```text
biohub_tracking/io.py
```

The loader understands the dataset as a collection of associated files.

Conceptually:

```text
dataset_name.zarr
        │
        ├── microscopy image
        └── metadata

dataset_name.geff
        │
        └── tracking graph, when available
```

The `.zarr` file contains the image data.

The `.geff` file can contain ground-truth or previously generated tracking information.

For inference, the important object is the Zarr image together with its metadata.

---

# 3. Metadata and Physical Voxel Scale

One of the most important pieces of metadata is the physical voxel scale.

The repository uses a default scale of:

```python
DEFAULT_SCALE = (1.625, 0.40625, 0.40625)
```

corresponding to:

```text
(Z, Y, X)

Z = 1.625 µm
Y = 0.40625 µm
X = 0.40625 µm
```

Therefore:

```text
Z voxel
    ↓
1.625 µm


Y voxel
    ↓
0.40625 µm


X voxel
    ↓
0.40625 µm
```

The data is consequently **anisotropic**.

A voxel in the Z direction represents substantially more physical distance than a voxel in Y or X.

This matters whenever an operation is supposed to represent a physical distance.

For example, the following assumption would be incorrect:

```text
1 Z voxel = 1 Y voxel = 1 X voxel
```

because these voxels do not correspond to the same physical distance.

Instead:

```text
1 Z voxel = 1.625 µm

1 Y voxel = 0.40625 µm

1 X voxel = 0.40625 µm
```

The pipeline therefore keeps track of physical scale when converting physical distances into image-space operations.

This becomes particularly important for detection suppression and edge distances, which are discussed in [Temporal U-Net](../temporal-unet/knowledge.md#15-physical-detection-suppression) and [Graph Construction](../graph-construction/knowledge.md#14-edge-distance).

---

# 4. Intensity Normalization

Raw microscopy intensities are not necessarily comparable between datasets.

One image may have a substantially different intensity distribution from another because of differences in:

* acquisition settings,
* illumination,
* staining,
* microscope configuration,
* background intensity,
* dynamic range.

The model was trained using a particular normalization convention.

Therefore inference must reproduce that convention.

The basic transformation is:

```text
normalized =
    (image - q_low)
    /
    (q_high - q_low + ε)
```

followed by clipping.

The production inference code uses precomputed dataset statistics stored in:

```text
image_statistics.quantiles
```

and specifically checks for:

```text
0.001
0.999
```

Therefore the effective normalization is approximately:

```text
Raw image
    │
    ▼
0.1th percentile ───────────► lower intensity reference
    │
    │ linear scaling
    ▼
99.9th percentile ──────────► upper intensity reference
    │
    ▼
clipping
    │
    ▼
normalized image
```

In simplified form:

```text
                 q_low                 q_high
                   │                      │
                   ▼                      ▼
───────────────┬────┴──────────────────────┬───────────────
               │                           │
               │      linear scaling       │
               └───────────────────────────┘
                           │
                           ▼
                       normalized
```

The important point is that normalization is **not learned at inference time**.

The statistics used by the prediction pipeline are provided by the dataset/model configuration.

---

# 5. Why Quantile Normalization Matters

Suppose the model was trained on images whose useful intensity range was approximately:

```text
q_0.001 → q_0.999
```

and an inference image is instead passed into the network using raw intensity values.

The network then sees a distribution that can be very different from the one used during training.

Conceptually:

```text
Training

raw image
    │
    ▼
quantile normalization
    │
    ▼
model input distribution
    │
    ▼
trained model
```

Whereas incorrect inference might look like:

```text
raw image
    │
    │  no matching normalization
    ▼
different input distribution
    │
    ▼
trained model
```

This can affect both:

* cell detection,
* learned U-Net features.

Since the [Simple Node Transformer](../simple-node-transformer/knowledge.md#u-net-feature) later uses U-Net features extracted from these images, preprocessing differences can propagate beyond detection.

---

# 6. Spatial Downsampling

The prediction configuration contains:

```python
downsample = (1, 4, 4)
```

This means:

```text
Z → ×1
Y → ×4
X → ×4
```

In other words:

```text
Z:
keep the original sampling


Y:
reduce spatial resolution by 4×


X:
reduce spatial resolution by 4×
```

The model therefore operates on a lower-resolution XY representation while retaining the original Z sampling.

![](./assets/03_spatial_downsampling_3d.mp4)
---

## 6.1 Visualizing Downsampling

Conceptually, an original XY image:

```text
Original XY

████████████████████
████████████████████
████████████████████
████████████████████
████████████████████
████████████████████
████████████████████
████████████████████
```

is reduced to a smaller representation:

```text
Model XY

█    █    █    █    █
                     
█    █    █    █    █
                     
█    █    █    █    █
                     
█    █    █    █    █
```

The exact implementation depends on the image-processing utilities, but conceptually the important point is:

```text
native image
      │
      ▼
reduce Y/X resolution
      │
      ▼
model-space image
```

This substantially reduces the spatial computational cost of the 3D neural network.

---

# 7. Why Downsampling Is Asymmetric

The downsampling is:

```text
(1, 4, 4)
```

rather than:

```text
(4, 4, 4)
```

because the source microscopy data is anisotropic.

The Z axis has substantially different physical sampling from X and Y.

The pipeline therefore does not simply reduce every axis by the same amount.

Instead:

```text
            Z        Y        X
            │        │        │
sampling    1        4        4
            │        │        │
            ▼        ▼        ▼
          native   reduced  reduced
```

This preserves the Z sampling while reducing the computationally expensive XY dimensions.

---

# 8. Coordinate Systems

Preprocessing introduces an important distinction between several coordinate systems.

The same detected cell can be represented in different spaces during inference.

## Original Image Coordinates

The source image uses:

```text
(T, Z, Y, X)
```

These coordinates refer to the original Zarr image.

---

## Model Coordinates

After:

```python
downsample = (1, 4, 4)
```

the Y and X dimensions are reduced.

Therefore a detection generated by the model initially exists in model-space coordinates.

Conceptually:

```text
Original image coordinate
        │
        ▼
downsampling
        │
        ▼
model coordinate
```

For Y and X:

```text
model_y ≈ original_y / 4

model_x ≈ original_x / 4
```

while Z remains at the original sampling.

---

## Output Coordinates

Before the tracking graph is saved, the prediction pipeline restores the spatial coordinates:

```python
coords[:, 1:] *= ds_arr
```

Conceptually:

```text
model coordinates
       │
       ▼
multiply by downsampling factors
       │
       ▼
original-resolution coordinates
```

Thus the final graph represents positions in the original image coordinate system.

The graph structure itself is covered in [Graph Construction](../graph-construction/knowledge.md#17-why-coordinate-conversion-matters).

---

# 9. Temporal Window Preparation

The preprocessing stage also determines which frames are presented together.

For:

```text
window_size = 2
```

the sequence is:

```text
Video:

0 ─── 1 ─── 2 ─── 3 ─── 4
     │     │     │
     ▼     ▼     ▼
   [0,1] [1,2] [2,3] [3,4]
```

For a larger window:

```text
window_size = W
```

the model receives:

```text
[0 ... W-1]
[W-1 ... 2W-2]
...
```

according to the prediction stride logic.

The key idea is that preprocessing prepares **short temporal image sequences**, rather than treating the entire movie as one tensor.

The neural-network interpretation of this temporal context is discussed in [Temporal U-Net](../temporal-unet/knowledge.md#2-temporal-input).

---

# 10. Test-Time Augmentation

The inference pipeline can optionally use **test-time augmentation (TTA)**.

TTA makes multiple predictions from transformed versions of the same input and combines those predictions.

The important distinction is:

> TTA is an inference-time technique. The model does not need to be retrained every time TTA is enabled.

For this pipeline, the relevant augmentations are flips in the XY plane.

The transformations are:

```text
Original
Flip X
Flip Y
Flip X + Y
```

Conceptually:

```text
                       Input image
                            │
             ┌──────────────┼──────────────┐
             │              │              │
             ▼              ▼              ▼
         Original         Flip X         Flip Y
             │              │              │
             │              │              │
             │              └──────┐       │
             │                     │       │
             │                     ▼       │
             │                  Flip XY    │
             │                     │       │
             └──────────┬──────────┴───────┘
                        ▼
                     Model
                        │
                        ▼
                  detection logits
```

![](../temporal-unet/assets/tta_flips.png)

The important detail is that the pipeline does **not** average the transformed images.

It:

1. transforms the input,
2. runs the model,
3. transforms the resulting logits back into the original coordinate system,
4. averages the aligned logits.

The conceptual operation is:

```text
Original image
      │
      ├──────────────► model ──────────────► logits
      │
      ├── flip X ────► model ──────────────► flip logits back
      │
      ├── flip Y ────► model ──────────────► flip logits back
      │
      └── flip XY ───► model ──────────────► flip logits back
                                               │
                                               ▼
                                      average logits
                                               │
                                               ▼
                                      final logits
```

The final detection logits are then passed to the detection procedure described in [Temporal U-Net](../temporal-unet/knowledge.md#10-detection-logits).

---

# 11. Why Flip X and Y?

The TTA configuration uses:

```python
tta_flips = [
    (-1,),
    (-2,),
    (-2, -1)
]
```

These correspond to spatial flips in the relevant XY dimensions.

The pipeline does not treat Z as another interchangeable image axis.

This is reasonable given the strongly anisotropic nature of the microscopy data:

```text
Z = 1.625 µm

Y = 0.40625 µm

X = 0.40625 µm
```

The XY plane therefore has substantially finer physical sampling than Z.

The TTA strategy assumes that the detection task remains semantically meaningful under XY reflection.

---

# 12. TTA and Detection Thresholding

TTA happens **before** final cell detection.

The order is approximately:

```text
input image
     │
     ▼
preprocessing
     │
     ▼
TTA model evaluations
     │
     ▼
aligned detection logits
     │
     ▼
average logits
     │
     ▼
sigmoid
     │
     ▼
local-max detection
     │
     ▼
detection threshold
     │
     ▼
cell coordinates
```

This distinction is important.

The pipeline does not independently threshold every augmented prediction and then merge four sets of detected cells.

Instead, the logits are aligned and combined first.

The final detection stage then operates on the combined prediction.

---

# 13. Physical-Scale Detection Suppression

Cell detection uses a local-maximum operation.

The suppression distance is not necessarily interpreted purely in raw voxel units.

The configuration contains a physical pooling scale:

```python
pool_kernel_um = 5.0
```

The image-processing code converts this physical distance into a per-axis voxel kernel using the actual voxel scale.

For example:

```text
Physical distance
      │
      │ 5.0 µm
      ▼
┌─────────────────────┐
│ voxel-scale convert │
└──────────┬──────────┘
           │
           ▼
      per-axis kernel
           │
      ┌────┼────┐
      ▼    ▼    ▼
      Z    Y    X
```

Because:

```text
Z = 1.625 µm / voxel

Y = 0.40625 µm / voxel

X = 0.40625 µm / voxel
```

the same physical distance corresponds to different numbers of voxels along each axis.

For example, approximately:

```text
5.0 µm / 1.625 µm ≈ 3.08 Z voxels

5.0 µm / 0.40625 µm ≈ 12.31 Y voxels

5.0 µm / 0.40625 µm ≈ 12.31 X voxels
```

The exact pooling implementation determines the final integer kernel.

The important concept is:

> A physical suppression radius should not be treated as the same number of voxels on every axis when the data is anisotropic.

This physical-scale reasoning becomes relevant again when spatial distances are stored on graph edges in [Graph Construction](../graph-construction/knowledge.md#edge-distance).

---

# 14. Native Anisotropic Data vs. Isotropic Resampling

The repository also provides utilities for explicitly resampling images into isotropic voxel space.

For example:

```python
resample_image_to_isotropic(...)
```

can transform an anisotropic image:

```text
Z = 1.625 µm
Y = 0.40625 µm
X = 0.40625 µm
```

into a representation where:

```text
Z ≈ Y ≈ X
```

in physical scale.

The repository also provides coordinate transformations:

```python
rescale_coords_to_isotropic(...)
rescale_coords_from_isotropic(...)
```

These allow coordinates to be moved between the native and isotropic coordinate systems.

---

## 14.1 Isotropic Resampling Is Not the Default Prediction Path

An important distinction is that the current Temporal U-Net prediction path does **not** require the entire microscopy volume to be resampled isotropically.

Instead, it operates on the native anisotropic image while explicitly accounting for physical scale where necessary.

Therefore:

```text
Default prediction:

native anisotropic image
          │
          ├── quantile normalization
          │
          ├── XY downsampling
          │
          └── physical-scale operations
                     │
                     ▼
                 model input
```

rather than:

```text
native image
     │
     ▼
full isotropic resampling
     │
     ▼
model input
```

The isotropic utilities are useful when another experiment or model specifically requires isotropic geometry.

---

# 15. Preprocessing Data Flow

The entire preprocessing stage can be summarized as:

```text
                 Zarr dataset
                      │
                      ▼
              Read dataset metadata
                      │
          ┌───────────┴────────────┐
          │                        │
          ▼                        ▼
     voxel scale              quantiles
          │                        │
          └───────────┬────────────┘
                      ▼
              Select temporal window
                      │
                      ▼
                 Load frames
                      │
                      ▼
             Quantile normalization
                      │
                      ▼
              Spatial downsampling
                      │
                      ▼
              Optional X/Y TTA
                      │
                      ▼
            model-ready image tensor
                      │
                      ▼
```
              [Temporal UNet](../temporal-unet/knowledge.md#2-temporal-input)

---

# 16. Preprocessing and Coordinate Tracking

One of the most important responsibilities of preprocessing is ensuring that transformations applied to the image can later be reversed or accounted for when interpreting model predictions.

The pipeline can be viewed as maintaining a mapping:

```text
Original image space
        │
        │ downsample
        ▼
Model image space
        │
        │ model prediction
        ▼
Detected coordinates
        │
        │ rescale
        ▼
Original-resolution coordinates
```

This matters because the neural network operates on the transformed image, but the final tracking graph should describe cells in the original image coordinate system.

Therefore a coordinate should never be interpreted without asking:

> Which image coordinate system does this value belong to?

This distinction becomes especially important when constructing nodes in [Simple Node Transformer](../simple-node-transformer/knowledge.md#10-the-complete-32-d-positional-vector).

---

# 17. What Preprocessing Learns vs. What It Does

Preprocessing itself is largely deterministic.

It does not learn cell representations.

Instead, it applies predefined transformations:

```text
Dataset parsing
        │
        ├── deterministic

Metadata extraction
        │
        ├── deterministic

Quantile normalization
        │
        ├── deterministic

Downsampling
        │
        ├── deterministic

Coordinate scaling
        │
        ├── deterministic

TTA transformations
        │
        └── deterministic
```

The learned component begins when the model processes the prepared image.

```text
Prepared image
      │
      ▼
Temporal U-Net
      │
      ├── learned image features
      │
      └── learned detection signal
```

See [Temporal U-Net](../temporal-unet/knowledge.md#27-learned-vs-deterministic-components) for the distinction between learned and deterministic stages.

---

# 18. Preprocessing Failure Modes

Because preprocessing occurs before detection, errors here can propagate through the entire tracking pipeline.

## Incorrect normalization

```text
Wrong intensity distribution
          │
          ▼
Different model input
          │
          ▼
Poor detection/features
          │
          ▼
Poor tracking
```

## Incorrect downsampling

```text
Wrong coordinate scaling
          │
          ▼
Incorrect cell positions
          │
          ▼
Incorrect node features
          │
          ▼
Incorrect temporal associations
```

## Ignoring anisotropy

```text
Treat Z = Y = X
        │
        ▼
Incorrect physical distances
        │
        ▼
Incorrect detection suppression
and/or graph distances
```

## Incorrect TTA alignment

If a flipped prediction is not flipped back before averaging:

```text
prediction A → original coordinates
prediction B → flipped coordinates

        │
        ▼
average incompatible coordinate systems

        │
        ▼
incorrect logits
```

Therefore every TTA prediction must be transformed back before aggregation.

---

# 19. Practical Mental Model

The easiest way to understand preprocessing is:

> **Preprocessing makes the raw microscopy video look like the kind of data the trained model expects, while preserving enough information to map predictions back to the original image.**

The transformation is:

```text
RAW MICROSCOPY
      │
      ▼
   ZARR DATA
      │
      ▼
 METADATA + SCALE
      │
      ▼
TEMPORAL WINDOW
      │
      ▼
NORMALIZATION
      │
      ▼
DOWNSAMPLING
      │
      ▼
 OPTIONAL TTA
      │
      ▼
MODEL-READY IMAGE
      │
      ▼
┌──────────────────────┐
│    TEMPORAL U-NET    │
└──────────────────────┘
      │
      ├──────────────► Detection logits
      │
      └──────────────► U-Net feature maps
```

The next stage converts these dense outputs into discrete cell detections.

See [Temporal U-Net — Detection](../temporal-unet/knowledge.md#20-from-detection-coordinates-to-node-features).

---

# 20. Key Configuration

The most relevant preprocessing/model-input settings are:

```text
Temporal window:
    2 frames

Spatial downsample:
    [1, 4, 4]

Quantile normalization:
    0.001 → 0.999

Physical pooling scale:
    5.0 µm

Voxel scale:
    Z = 1.625 µm
    Y = 0.40625 µm
    X = 0.40625 µm

TTA:
    X flip
    Y flip
    X + Y flip
```

These values are not arbitrary implementation details.

They define the input distribution and geometry expected by the trained pipeline.

---

# 21. Repository Responsibilities

The preprocessing-related functionality is distributed primarily across:

```text
src/
└── biohub_tracking/
    ├── io.py
    └── img_proc.py
```

Their conceptual responsibilities are:

| File          | Responsibility                                                                  |
| ------------- | ------------------------------------------------------------------------------- |
| `io.py`       | Dataset loading, metadata, normalization, coordinate transformations, graph I/O |
| `img_proc.py` | Image normalization, isotropic resampling, NMS, coordinate utilities            |

The model itself is implemented separately:

```text
src/
└── biohub_tracking/
    └── models/
        └── temporal_unet.py
```

and is described in [Temporal U-Net](../temporal-unet/knowledge.md).

---

# 22. Summary

The preprocessing stage transforms:

```text
Raw Zarr microscopy
```

into:

```text
normalized,
spatially downsampled,
temporally organized,
model-compatible image tensors
```

while maintaining the information needed to interpret predictions in the original image coordinate system.

The complete transformation is:

```text
                 RAW DATA
                    │
                    ▼
             ┌─────────────┐
             │    Zarr     │
             └──────┬──────┘
                    │
                    ▼
          dataset + metadata
                    │
          ┌─────────┴─────────┐
          │                   │
          ▼                   ▼
     voxel scale          quantiles
          │                   │
          └─────────┬─────────┘
                    ▼
             temporal window
                    │
                    ▼
           quantile normalize
                    │
                    ▼
            downsample [1,4,4]
                    │
                    ▼
              optional TTA
                    │
                    ▼
             model-ready data
                    │
                    ▼
        ┌──────────────────────┐
        │    Temporal U-Net    │
        └──────────────────────┘
                    │
             ┌──────┴──────┐
             ▼             ▼
       detection logits   features
             │             │
             ▼             │
       cell detections     │
             │             │
             └──────┬──────┘
                    ▼
          Simple Node Transformer
                    │
                    ▼
          Graph Construction
```

## Core takeaway

The preprocessing stage has three fundamental responsibilities:

```text
1. Make the image numerically compatible with the trained model.

2. Make the image computationally manageable.

3. Preserve the relationship between model coordinates
   and physical/original image coordinates.
```

It does **not** decide which cells are connected.

That responsibility begins after the image has passed through the [Temporal U-Net](../temporal-unet/knowledge.md), where dense detection fields and learned feature maps are converted into cell nodes.
