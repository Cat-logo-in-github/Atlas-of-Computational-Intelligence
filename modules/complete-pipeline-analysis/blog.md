# From Microscopy Pixels to a Map of Cell Life

A tracking pipeline can look intimidating when you first open the repository.

There are image loaders, normalization functions, a 3D U-Net, detection code, positional encodings, a transformer, graph utilities, coordinate transformations, thresholds, and even an optional optimization solver.

It is easy to look at all of that and wonder:

**What is the system actually doing?**

I found it much easier to understand once I stopped looking at the individual files and followed the information itself.

At the beginning, the system knows almost nothing except:

```text
there is a microscopy image
```

At the end, it has produced:

```text
these cells were observed
+
these cells are probably related
+
these relationships form this tracking graph
```

The interesting part is everything that happens in between.

---

# Start with the microscope

The source data is stored as a Zarr image.

Conceptually, the dataset is a four-dimensional array:

```text id="q5g3z7"
(T, Z, Y, X)
```

These dimensions represent:

```text id="h29q89"
T → time
Z → depth
Y → image height
X → image width
```

So instead of thinking about the input as one giant image, think of it as a sequence of 3D volumes:

```text id="4wwvav"
Time 0       Time 1       Time 2

┌────────┐   ┌────────┐   ┌────────┐
│        │   │        │   │        │
│  3D    │   │  3D    │   │  3D    │
│ volume │   │ volume │   │ volume │
│        │   │        │   │        │
└────────┘   └────────┘   └────────┘
```

This is already important.

The pipeline isn't tracking cells in a flat photograph.

It is working with **3D objects observed repeatedly over time**.

That means the final problem is simultaneously spatial and temporal.

---

# The data has physical scale

The voxels aren't necessarily physically equal in every direction.

For this dataset, the scale is approximately:

```text id="9u2x0f"
Z = 1.625 µm
Y = 0.40625 µm
X = 0.40625 µm
```

So moving one voxel in Z represents a much larger physical distance than moving one voxel in X.

This is called anisotropy.

You can imagine the image grid as having stretched spacing:

```text id="c9kt7w"
Z
↑

│
│
│
└────────────→ X
```

The spacing between layers in Z is physically different from the spacing between pixels in X/Y.

That matters later when the pipeline asks questions involving distance.

The system therefore has to keep the physical geometry in mind instead of blindly treating every voxel as equivalent.

---

# Before the model sees the image

Raw microscopy intensities can vary substantially.

Two datasets might contain visually similar cells but have very different numerical intensity ranges.

The pipeline therefore applies quantile-based normalization.

Conceptually:

```text id="8x7e92"
raw intensity
      ↓
find low/high reference quantiles
      ↓
scale
      ↓
clip
      ↓
normalized image
```

The production inference path uses precomputed dataset statistics, including approximately:

```text id="4z2x6w"
0.001
0.999
```

So very low and very high intensity values define the useful range.

The important point isn't the exact formula.

It's consistency.

The model was trained to see images under a particular normalization convention.

If inference uses a completely different intensity scale, the network is effectively being shown a different kind of input from what it learned during training.

---

# The image is also reduced spatially

The model configuration uses:

```text id="gq0m69"
downsample = (1, 4, 4)
```

This means:

```text id="u6ifcm"
Z → ×1
Y → ×4
X → ×4
```

The model keeps the original Z sampling while reducing the XY resolution.

Why?

Because 3D microscopy data can be enormous.

Reducing the XY resolution makes the neural network substantially cheaper to run.

Conceptually:

```text id="1rpgxm"
Large microscopy volume
          ↓
      downsample
          ↓
Smaller model representation
```

The important part is that the pipeline remembers this transformation.

It cannot detect something on a reduced grid and then forget that the grid was reduced.

The coordinates eventually need to be mapped back.

---

# The video isn't processed all at once

Another practical decision is the temporal window.

The supplied model uses:

```text id="u7p5m4"
window_size = 2
```

So rather than sending an entire movie through the network:

```text id="t8v0eu"
0 1 2 3 4 5 6 7 ...
```

it processes:

```text id="j7z1ip"
[0,1]
   [1,2]
      [2,3]
         [3,4]
            ...
```

This is a sliding temporal window.

It gives the model temporal context without requiring the entire experiment to fit into one enormous computation.

But the final graph still needs to represent the whole movie.

So the pipeline maintains global bookkeeping while the model works locally.

This is one of the recurring themes in the system:

> **Local computation, global structure.**

---

# The Temporal U-Net sees the image

Now the neural network enters.

The central image-processing model is:

```text id="fkj8yu"
TemporalUNet3D
```

Its configuration includes:

```text id="1ndbq4"
input channels: 1
U-Net output channels: 32
U-Net layers: [32, 64, 128]
temporal window: 2
downsample: [1, 4, 4]
```

The U-Net takes the image sequence and produces two important outputs:

```text id="7j3rll"
U-Net feature maps
+
detection logits
```

This is a major conceptual point.

The network isn't simply answering:

```text id="xqf9de"
cell / no cell
```

at the beginning.

It creates dense spatial representations.

Think of the output as two maps covering the image.

One map represents learned visual information.

The other indicates where the network thinks cell centers may exist.

---

# Dense information becomes discrete cells

The detection logits are still dense.

For every spatial position, there is a value.

But a tracking graph needs individual objects.

So the pipeline has to convert:

```text id="u7f4ly"
dense detection field
```

into:

```text id="r2w0be"
individual cell detections
```

This happens using local maxima.

The detection probability is obtained through a sigmoid, and the system looks for spatial peaks.

Conceptually:

```text id="q5w8ne"
dense detection field
        ↓
find local peaks
        ↓
remove weak peaks
        ↓
cell coordinates
```

A detection might become:

```text id="n5d7yx"
(t, z, y, x)
```

At this point, something fundamental has happened.

The system has moved from **image space** to **object space**.

It is no longer reasoning about every voxel equally.

It now has a list of candidate cells.

---

# Detection is the first major bottleneck

This gives us a useful way to think about the whole system.

If a cell never becomes a node, the later stages cannot magically reconstruct it.

The transformer cannot link a cell that was never detected.

The graph builder cannot add a node that doesn't exist.

Therefore:

```text id="4p5m31"
missed detection
      ↓
no node
      ↓
no temporal links
      ↓
no track
```

This is why detection quality has such a strong effect on tracking quality.

A later stage can choose the wrong relationship between two detected cells.

But it cannot connect to a cell that isn't there.

---

# The pipeline now asks a different question

Suppose we have:

```text id="wkjk4w"
Frame t:

A
B
C
```

and:

```text id="e0kg48"
Frame t+1:

D
E
F
```

The detection stage has succeeded.

But tracking still hasn't.

We need to know:

```text id="x5x4cy"
A → ?
B → ?
C → ?
```

This is where the representation of each cell becomes important.

---

# Every cell gets two descriptions

For every detected cell, the pipeline combines:

```text id="g4x6ch"
1. learned U-Net feature
2. positional encoding
```

The U-Net feature has 32 dimensions.

It represents learned image information around the cell.

The positional encoding also has 32 dimensions.

It represents where the cell is.

Together:

```text id="3r7gdy"
32-D appearance/context
+
32-D position
        ↓
64-D node representation
```

This is one of the clearest examples of the system combining learned and known information.

The network learns:

```text
what visual patterns matter
```

The pipeline provides:

```text
where the object is
```

---

# Why encode position instead of using four numbers?

The detected cell has only four basic coordinates:

```text id="m1u9n4"
(t, z, y, x)
```

But these are transformed into a 32-dimensional positional representation.

Each coordinate is normalized and represented using multiple sinusoidal frequencies.

For each coordinate:

```text id="i0i9br"
4 frequencies
×
sin + cos
=
8 values
```

There are four coordinates:

```text id="qjv7fy"
t
z
y
x
```

Therefore:

```text id="4bq0f6"
4 × 8 = 32
```

The important thing is that the system hasn't invented 28 new physical dimensions.

It has created a richer numerical representation of the same four coordinates.

---

# The transformer compares cells

Now every detected cell has a 64-dimensional representation.

The transformer can compare cells across consecutive frames.

For example:

```text id="v5t5sd"
A ↔ D
A ↔ E
A ↔ F

B ↔ D
B ↔ E
B ↔ F

C ↔ D
C ↔ E
C ↔ F
```

The model produces a matrix of scores:

```text id="dqu8a4"
             Target

             D       E       F

Source A     2.1    -1.2     0.4

       B    -0.8     3.7     0.1

       C     0.2    -0.4     4.2
```

The values indicate compatibility.

But they aren't graph edges yet.

They are evidence for possible edges.

That distinction is important.

---

# From scores to probabilities

The current configuration uses softmax:

```text id="g8o9j1"
edge_activation = "softmax"
```

The raw scores are converted into probabilities relative to the possible targets.

So the model effectively answers questions like:

```text id="x1c6f8"
For this source cell,
which target is the strongest candidate?
```

The resulting probabilities can then be filtered.

The default edge threshold is:

```text id="g0d9t4"
0.5
```

So weak candidates can be removed before graph construction.

---

# But biology adds another layer

Imagine the model gives these predictions:

```text id="j3s2qx"
A → B = 0.91
A → C = 0.87
A → D = 0.82
```

A purely mathematical system might happily keep all three.

But if A is a normal cell, having three children might not make biological sense.

The pipeline therefore applies structural constraints:

```text id="n5w3l0"
maximum parents = 1
maximum children = 2
```

Now the graph can represent:

```text id="h7l3jp"
       A
      / \
     B   C
```

which could represent division.

But it avoids arbitrary many-to-many relationships.

This is an important theme in biological machine learning:

**The neural network provides learned evidence, while domain knowledge helps structure the result.**

---

# Now the predictions become a graph

Once the candidate edges survive thresholding and graph constraints, the system has something that looks like:

```text id="j9z9kp"
Frame 0          Frame 1          Frame 2

   A ───────────── B ───────────── D
    \
     └──────────── C ───────────── E
```

Now the pipeline has crossed another conceptual boundary.

It started with independent observations:

```text id="8e8zib"
A
B
C
D
E
```

and produced relationships:

```text id="q4qf14"
A → B
A → C
B → D
C → E
```

Those relationships form a graph.

The graph is now a representation of a possible biological history.

---

# What does one edge mean?

An edge such as:

```text id="l8v4yq"
A → B
```

doesn't merely mean:

```text
A is close to B
```

It means that the model and graph-building process consider B a plausible temporal continuation of A.

The edge stores both:

```text id="mb7bq3"
edge probability
+
spatial distance
```

So we can distinguish:

```text id="7bq2o4"
How confident was the prediction?
```

from:

```text id="18x0dj"
How far apart are the detections?
```

Those are related but not identical properties.

---

# Coordinate systems quietly hold everything together

One of the easiest things to miss is that the coordinates don't stay in exactly the same representation throughout the pipeline.

We start with:

```text id="c6gl1h"
original image coordinates
```

Then spatial downsampling changes the model grid:

```text id="8p0r6n"
original
   ↓
downsampled
```

Detections are initially made on that model grid.

At the end, the pipeline rescales the spatial coordinates:

```text id="6l1z09"
model coordinates
      ↓
multiply by downsample factor
      ↓
original-resolution coordinates
```

So the graph's coordinates correspond to the original image system.

This matters whenever we want to overlay predictions on the microscopy data or calculate meaningful spatial distances.

---

# Why anisotropy matters again

Remember the voxel scale:

```text id="h0p3c6"
Z = 1.625 µm
Y = 0.40625 µm
X = 0.40625 µm
```

Suppose two cells differ by:

```text id="2p2l5b"
1 voxel in Z
```

and another pair differs by:

```text id="g8a5e5"
1 voxel in X
```

Those aren't the same physical movement.

The first is roughly four times larger in physical distance.

So the pipeline can't safely assume that:

```text id="8r7m5q"
distance = √(ΔZ² + ΔY² + ΔX²)
```

using raw voxel units means physical distance.

The scale of each axis matters.

This is why physical metadata follows the image through the pipeline.

---

# Sliding windows become one global result

There is another seemingly contradictory part of the system.

The model only sees two frames at a time:

```text id="2j6a0j"
[0,1]
[1,2]
[2,3]
...
```

Yet the final `.geff` file represents the whole sequence.

The solution is bookkeeping.

The prediction process keeps track of frames and frame pairs that have already been processed.

This allows local inference windows to contribute to one global collection of nodes and edges.

So:

```text id="o7b0af"
small model windows
        ↓
global node registry
        +
global edge registry
        ↓
whole-video graph
```

This is another place where the software architecture supports the biological interpretation.

A cell does not become a different biological object just because the computer processed it in another window.

---

# Optional global optimization

At this stage, the pipeline already has a graph.

But it can optionally perform another step:

```text id="j3kz1h"
ILP optimization
```

ILP stands for Integer Linear Programming.

The important idea isn't the mathematics behind the solver.

The useful intuition is:

```text
greedy approach:
make the best local decision available

ILP:
look at many decisions together
and optimize the overall solution
```

Suppose several possible edges compete with one another.

A greedy algorithm might choose:

```text id="h2txq5"
best edge
↓
best remaining edge
↓
best remaining edge
```

An ILP solver can instead evaluate combinations of decisions and search for a globally consistent solution.

The optimization can consider things such as:

```text id="w9c3d2"
edge selection
appearance
disappearance
division
```

So ILP isn't another neural network.

It is a graph-level optimization stage.

---

# This gives us a useful division of labor

At the end, the entire pipeline can be understood as several different systems working together.

### Image processing

```text id="x9p0a1"
normalization
downsampling
coordinate handling
```

prepares the data.

### Temporal U-Net

```text id="9w7f8u"
image
  ↓
features + detection field
```

finds candidate cells and learns useful visual representations.

### Detection

```text id="5z1r6v"
dense detection field
  ↓
cell nodes
```

turns continuous predictions into discrete objects.

### Node Transformer

```text id="z2x0x6"
cell A + cell B
      ↓
compatibility score
```

predicts possible temporal relationships.

### Graph construction

```text id="y1u4m8"
scores
  ↓
probabilities
  ↓
constraints
  ↓
edges
```

turns those predictions into a structured graph.

### Optional ILP

```text id="m4n6k2"
candidate graph
      ↓
global optimization
      ↓
consistent graph
```

tries to improve the overall structure.

---

# What is learned and what isn't?

This distinction becomes especially clear when looking at the entire system.

The neural network learns:

```text id="3w1h9d"
image patterns
+
cell representations
+
temporal compatibility
```

But many other decisions are fixed by the pipeline:

```text id="6e4k1x"
quantile normalization
downsampling
detection threshold
edge threshold
local-max detection
parent/child limits
coordinate conversion
graph construction
optional optimization
```

These aren't all things the model learned from the images.

They are design choices around the model.

This is extremely useful when trying to understand a failure.

---

# What if the detector is bad?

Suppose evaluation shows:

```text id="1k0f9v"
low node recall
```

The first place to investigate is the detection side.

Possible causes include:

```text id="6k1d4f"
normalization
detection threshold
local-max suppression
U-Net predictions
```

There isn't much value in tuning the transformer if the required nodes don't exist.

---

# What if detections are good but tracks are bad?

Now imagine:

```text id="9u8v1a"
high node recall
+
poor edge quality
```

That tells a different story.

The system is finding the cells, but it isn't connecting them correctly.

Now the investigation moves downstream:

```text id="3y4s6q"
node features
+
positional encoding
+
transformer
+
edge probabilities
+
edge threshold
+
graph constraints
```

This separation is one of the most useful things about the architecture.

The pipeline naturally divides different types of failure.

---

# Why the output is more than a prediction

The final `.geff` file is a graph.

It contains:

```text id="h4z5v6"
Nodes:
    time
    z
    y
    x

Edges:
    source
    target
    probability
    distance
```

This makes the output useful beyond simply asking:

```text
"Did the model get the image right?"
```

We can ask biological questions about the predicted structure:

```text id="k6z7s8"
Which cells persisted?

Where did divisions occur?

Which detections disappeared?

How many temporal relationships were predicted?

Where are tracking errors concentrated?
```

The image has been transformed into a structure that can be queried.

---

# Evaluation closes the loop

The repository also includes tracking evaluation.

Metrics include things such as:

```text id="j9h0k1"
node recall
edge Jaccard
adjusted edge Jaccard
division Jaccard
```

These measure different aspects of the final result.

For example:

```text id="n2m3o4"
high node recall
+
low edge Jaccard
```

could mean:

```text
cells are being detected
but their temporal relationships are poor
```

Whereas:

```text id="p5q6r7"
low node recall
```

suggests that the problem occurs earlier.

This gives the pipeline a feedback loop:

```text id="s8t9u0"
prediction
    ↓
graph
    ↓
evaluation
    ↓
identify failure
    ↓
inspect relevant stage
```

---

# The complete journey

At this point, the whole pipeline can be seen as one transformation:

```text id="v1w2x3"
MICROSCOPY VIDEO
       │
       ▼
Zarr + metadata
       │
       ▼
normalization
       │
       ▼
spatial downsampling
       │
       ▼
temporal windows
       │
       ▼
Temporal U-Net
       │
       ├───────────────┐
       │               │
       ▼               ▼
detection logits    U-Net features
       │               │
       ▼               │
local maxima           │
       │               │
       ▼               │
cell coordinates       │
(t,z,y,x)              │
       │               │
       ├───────────────┘
       │
       ▼
32-D U-Net feature
+
32-D positional encoding
       │
       ▼
64-D node representation
       │
       ▼
Simple Node Transformer
       │
       ▼
pairwise edge scores
       │
       ▼
probabilities
       │
       ▼
thresholding
       │
       ▼
biological graph constraints
       │
       ▼
tracking graph
       │
       ├──────────────► optional ILP
       │                    │
       │                    ▼
       │              optimized graph
       │
       ▼
     .geff
```

What started as a four-dimensional image has become a graph.

That is the central transformation.

---

# Three representations tell the whole story

If I had to reduce the entire pipeline to three moments, they would be these.

## First: the image

```text id="y4z5a6"
continuous microscopy information
```

At this point, we haven't identified individual cells.

---

## Second: the node

```text id="b7c8d9"
(t,z,y,x)
+
U-Net feature
+
positional representation
```

Now the system has discrete objects.

Each node represents a detected cell at a particular moment and location.

---

## Third: the graph

```text id="e0f1g2"
nodes
+
temporal edges
```

Now the system has relationships between those observations.

This is where a collection of cell detections becomes a tracking hypothesis.

---

# The most important insight

The architecture becomes much less mysterious when you stop thinking of it as one giant "cell tracker."

It is actually a sequence of increasingly structured problems.

First:

> **Where are the cells?**

Then:

> **What does each detected cell look like, and where is it?**

Then:

> **Which cells could be related across time?**

Then:

> **Which of those relationships should become graph edges?**

Finally:

> **Does the resulting graph make sense as a whole?**

Each stage has a different responsibility.

And that is probably the most useful discovery I took away from examining the pipeline.

The system doesn't jump directly from pixels to tracks.

It gradually transforms the representation:

```text id="h3i4j5"
pixels
  ↓
features
  ↓
detections
  ↓
nodes
  ↓
relationships
  ↓
edges
  ↓
graph
```

Each transformation throws away some unnecessary complexity while preserving information needed by the next stage.

---

# A biological way to think about the pipeline

Imagine watching a time-lapse movie of cells.

A human observer might naturally do something like this:

1. Notice where the cells are.
2. Recognize what each cell looks like.
3. Look at the next frame.
4. Guess which cell corresponds to which.
5. Notice when one cell divides.
6. Continue following those relationships.
7. Build a mental history of the population.

The pipeline performs a computational version of the same broad process.

Not because the computer literally "thinks like a human," but because the problem itself naturally decomposes this way.

```text id="k6l7m8"
SEE
 ↓
REPRESENT
 ↓
COMPARE
 ↓
CONNECT
 ↓
OPTIMIZE
```

That is what makes the architecture easier to understand.

---

# The final mental model

The simplest description I can give is:

**The U-Net turns microscopy images into candidate cells.**

**The node representation describes each cell using both learned appearance and position.**

**The transformer scores possible relationships between cells in neighboring frames.**

**The graph builder turns those relationships into a constrained tracking graph.**

**The optional ILP stage can then optimize that graph globally.**

So the pipeline isn't really just:

```text id="n9o0p1"
IMAGE → TRACKS
```

It is:

```text id="q2r3s4"
IMAGE
  ↓
DENSE REPRESENTATION
  ↓
CELL DETECTIONS
  ↓
CELL REPRESENTATIONS
  ↓
TEMPORAL RELATIONSHIPS
  ↓
GRAPH
  ↓
OPTIONAL GLOBAL OPTIMIZATION
```

And the final `.geff` file is the point where all of those decisions become a single structured representation of the observed cell dynamics.

That, ultimately, is what makes this pipeline interesting to me.

It doesn't try to understand an entire biological movie in one step.

It progressively turns a complicated visual problem into a sequence of simpler representations — until what began as microscopy data becomes a map of how cells are connected through time.
