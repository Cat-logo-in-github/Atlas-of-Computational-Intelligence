# When Predictions Become a Tracking Graph

A cell tracker can make two kinds of mistakes.

It can fail to find a cell.

Or it can find the cell perfectly and then connect it to the wrong cell in the next frame.

The first problem happens during detection.

The second happens during temporal linking.

But there is a third problem that is easy to overlook:

**Even good individual predictions can produce a bad tracking graph if they are assembled without considering the structure of the whole system.**

That is what makes the graph-construction stage interesting.

At this point, the pipeline has already found candidate cells and the transformer has produced scores describing how likely pairs of cells are to be connected.

Now those predictions have to become something more concrete:

```text
nodes + edges = tracking graph
```

---

## We already have the pieces

Suppose the detector has found these cells:

```text
Frame 0          Frame 1          Frame 2

   A                B                D
   C                E                F
```

The transformer might predict relationships such as:

```text
A → B
A → E
C → E
B → D
E → F
```

But these predictions are not automatically the final tracking graph.

They first have to pass through several decisions.

Conceptually:

```text
Transformer predictions
        │
        ▼
edge probabilities
        │
        ▼
thresholding
        │
        ▼
graph constraints
        │
        ▼
accepted edges
        │
        ▼
tracking graph
```

This is where the pipeline changes from a machine-learning problem into a graph-building problem.

---

# The nodes are the detected cells

The simplest part of the graph is the node.

Every accepted cell detection becomes a node containing its location:

```text
(t, z, y, x)
```

For example:

```text
Node 1
t = 0
z = 4
y = 31
x = 82
```

The time coordinate tells us **when** the cell was observed.

The spatial coordinates tell us **where** it was observed.

![](../temporal-unet/assets/video2_frame1_detection_heatmap_3d_compatible.mp4)

So a node isn't simply:

```text
Cell
```

It is more accurately:

```text
Cell detection at a particular time and location
```

This distinction matters because the same biological cell can appear as multiple nodes across different frames.

For example:

```text
Frame 0       Frame 1       Frame 2

   A             B             C
```

could represent one biological cell moving through time.

The graph would contain:

```text
A → B → C
```

as three nodes connected by two temporal edges.

---

# The edges describe relationships

An edge connects a detection in one frame to a detection in the next.

Conceptually:

```text
Frame t                 Frame t+1

   A ───────────────────→ B
```

The edge stores information about that relationship.

In this pipeline, an edge contains information such as:

```text
source
target
edge probability
edge distance
```

So an edge might conceptually look like:

```text
A → B

probability = 0.91
distance    = 4.7
```

These two values answer different questions.

The probability comes from the learned model.

The distance comes from the coordinates.

![](../simple-node-transformer/assets/video2_frame7_64d_nodes_candidate_pairs.mp4)

Together, they give us a more complete description of the predicted connection.

---

# Probability does not mean "keep the edge"

This is one of the easiest assumptions to make incorrectly.

Suppose the transformer produces:

```text
A → B = 0.92
A → C = 0.81
A → D = 0.21
```

It might seem reasonable to keep everything above some probability.

The pipeline does something along those lines, but there is another layer of reasoning.

An edge can have a high probability and still create a graph that doesn't make biological sense.

For that reason, graph construction happens in stages.

---

# Step 1: Threshold the predictions

The default edge threshold is:

```text
0.5
```

So candidate edges below this value are discarded.

For example:

```text
A → B = 0.87   ✓
A → C = 0.63   ✓
A → D = 0.24   ✗
```

The third candidate disappears.

The threshold is essentially saying:

> "Only keep relationships that have enough support from the model."

But this is only the first filter.

---

# Step 2: Respect biological structure

Now imagine that after thresholding we have:

```text
        B
       ↗
      /
A ───
      \
       ↘
        C
```

This is perfectly reasonable.

It could represent cell division:

```text
        A
       / \
      B   C
```

But imagine instead that we get:

```text
        B
       ↗ ↑ ↖
      /  │  \
     A   C   D
          │
          ↓
          E
```

Now the graph is becoming difficult to interpret biologically.

A normal cell shouldn't suddenly have five children.

Likewise, a cell normally shouldn't have several unrelated parents.

The graph builder therefore applies constraints.

The default configuration includes:

```text
max_parents_per_node = 1
max_children_per_node = 2
```

These are simple rules, but they encode an important biological assumption.

---

# One parent, up to two children

The first rule is:

```text
maximum parents = 1
```

That means a node cannot normally be connected from multiple parents.

Conceptually:

```text
A ──→ B
```

is allowed.

But:

```text
A ──→ B ←── C
```

would violate the parent constraint.

The second rule is:

```text
maximum children = 2
```

This allows:

```text
      A
     / \
    B   C
```

which represents a possible division event.

So the graph rules are not arbitrary software restrictions.

They are an attempt to make the resulting graph compatible with the biological process being modeled.

![](./assets/asset_8A_real_edge_filtering_one_parent.mp4)

---

# Why the order of edges matters

When ILP optimization is disabled, the pipeline uses a greedy strategy.

Candidate edges are sorted by probability.

Imagine we have:

```text
A → B = 0.94
A → C = 0.88
A → D = 0.76
```

The pipeline considers the strongest candidate first.

```text
A → B
```

is accepted.

Then:

```text
A → C
```

is considered.

Since A can have up to two children, it can also be accepted.

Then:

```text
A → D
```

is considered.

But now A already has two children.

So D is rejected.

The result becomes:

```text
      B
     ↗
    A
     ↘
      C
```

This is an important detail because it means that the graph isn't simply:

```text
all probabilities > 0.5
```

It is:

```text
high-probability predictions
+
structural constraints
```

---

# Greedy graph construction

The process can be thought of as:

```text
1. Collect candidate edges
        ↓
2. Convert scores to probabilities
        ↓
3. Remove low-probability edges
        ↓
4. Sort remaining edges
        ↓
5. Consider strongest edge first
        ↓
6. Keep it if constraints allow
        ↓
7. Continue until candidates are exhausted
```

This approach is attractive because it is simple and fast.

But it has a weakness.

The decision made for one edge can affect later decisions.

---

# The problem with local decisions

Consider this situation:

```text
A → B = 0.95
A → C = 0.90
D → B = 0.89
```

Suppose B can only have one parent.

A greedy strategy might accept:

```text
A → B
```

because it has the highest probability.

Then:

```text
D → B
```

has to be rejected.

But perhaps, when considering the complete graph, choosing:

```text
D → B
```

would produce a much better overall set of tracks.

The greedy algorithm doesn't naturally reason about that larger picture.

It makes a strong local choice and moves on.

This is where the optional ILP stage becomes important.

---

# Before ILP: the graph is already useful

It is worth emphasizing that ILP isn't required for the pipeline to produce a graph.

Without ILP, the system can still produce:

```text
nodes
+
accepted temporal edges
=
tracking graph
```

That graph can be saved as:

```text
.geff
```

The ILP stage is an optional optimization layer that can operate on the graph afterward.

So there are really two possible paths:

```text
Transformer
    │
    ▼
edge probabilities
    │
    ▼
greedy filtering
    │
    ▼
tracking graph
```

or:

```text
Transformer
    │
    ▼
edge probabilities
    │
    ▼
candidate graph
    │
    ▼
ILP optimization
    │
    ▼
globally optimized graph
```

The neural network hasn't changed.

The difference is how the predicted relationships are selected.

![](./assets/asset_8C_real_greedy_vs_global_ILP.mp4)
---

# Why spatial distance is stored separately

The graph also keeps track of the distance between connected cells.

Suppose:

```text
A → B
```

The coordinates might be:

```text
A = (0, 20, 30, 40)
B = (1, 21, 31, 42)
```

The pipeline can calculate the spatial separation between them.

That gives us:

```text
edge_dist
```

It is useful to keep this separate from probability.

Consider:

```text
Edge 1:
probability = 0.93
distance    = 3.2

Edge 2:
probability = 0.93
distance    = 17.4
```

The model gives both relationships the same confidence.

But their spatial relationships are very different.

Keeping both values in the graph means downstream analysis can examine these properties independently.

---

# The coordinate problem

There is another issue hiding underneath graph construction:

**Which coordinate system are we using?**

This pipeline works with more than one.

The original microscopy image has coordinates:

```text
(T, Z, Y, X)
```

But the model uses spatial downsampling:

```text
downsample = (1, 4, 4)
```

So the model sees:

```text
Z → unchanged
Y → reduced
X → reduced
```

![](../image-preprocessing/assets/03_spatial_downsampling_3d.mp4)

That means a detected coordinate initially belongs to the model's lower-resolution coordinate system.

If we simply wrote those coordinates into the final graph, the locations would no longer correspond to the original image.

So the pipeline rescales them.

Conceptually:

```text
original image
      │
      ▼
downsample
      │
      ▼
model coordinates
      │
      ▼
detection
      │
      ▼
rescale coordinates
      │
      ▼
original-resolution coordinates
```

The final graph therefore represents positions in the original image coordinate system.

This sounds like a small implementation detail.

It isn't.

A coordinate mistake here could make an otherwise correct tracking graph appear spatially wrong.

---

# Why Z needs special attention

Microscopy data is often anisotropic.

In this dataset, the physical voxel scale is approximately:

```text
Z = 1.625 µm
Y = 0.40625 µm
X = 0.40625 µm
```

So one voxel in Z does not represent the same physical distance as one voxel in X or Y.

Imagine walking:

```text
1 step in Z
```

versus:

```text
1 step in X
```

Those two steps are not physically equivalent.

This matters when calculating distances.

The pipeline therefore keeps track of the physical scale rather than assuming:

```text
1 Z voxel = 1 Y voxel = 1 X voxel
```

That is particularly important for 3D microscopy.

---

# Native anisotropy versus isotropic resampling

The repository also contains utilities for converting anisotropic volumes into isotropic space.

In an isotropic representation:

```text
Z ≈ Y ≈ X
```

in physical scale.

This can make certain geometric operations easier to reason about.

But there is an important distinction:

**The default Temporal U-Net prediction path does not need to resample the entire dataset into isotropic space.**

Instead, it works with the native image representation and accounts for physical scale where necessary.

That means the pipeline can preserve the original data while still reasoning correctly about distances.

This is a good example of an implementation decision that can easily be missed when looking only at the neural network architecture.

---

# Sliding windows create another graph problem

The video is not processed as one enormous tensor.

The model uses temporal windows.

With:

```text
window_size = 2
```

the sequence looks like:

```text
[0, 1]
   [1, 2]
      [2, 3]
         [3, 4]
```

This is useful because the model only needs to process a small temporal context.

But it introduces a bookkeeping problem.

The pipeline needs to make sure that:

```text
Frame 1
```

doesn't accidentally become two unrelated sets of detections simply because it appeared in two different windows.

Likewise, the pair:

```text
Frame 1 → Frame 2
```

should not accidentally be treated as two different temporal relationships.

The inference code therefore maintains registries such as:

```text
seen_frames
seen_pairs
coord_offset
```

![](./assets/sliding_window_tracking.gif)

These help keep the graph global even though inference happens in smaller windows.

---

# Local windows, global graph

This is an elegant part of the design.

The model sees:

```text
small temporal window
```

but the output is:

```text
one graph covering the video
```

So we can think of the pipeline as having two different scales.

### Model scale

```text
few consecutive frames
```

### Graph scale

```text
entire video
```

The sliding-window system bridges those two.

Conceptually:

```text
Video
─────────────────────────────────────

[0,1]
   [1,2]
      [2,3]
         [3,4]
            [4,5]

        ↓

Global node registry
        +
Global edge registry
        ↓

Complete tracking graph
```

That separation allows the neural network to remain computationally manageable without limiting the final graph to a tiny section of the experiment.

---

# What does the final graph actually represent?

Once graph construction is complete, we have something much more meaningful than a collection of predictions.

We have a network describing how detected cells relate through time.

For example:

```text
Frame 0          Frame 1          Frame 2

   A ───────────── B ───────────── D
    \
     └──────────── C ───────────── E
```

This can be interpreted as:

```text
A
├── B → D
└── C → E
```

The first relationship represents continuation.

The second branch could represent division.

The graph has now transformed a sequence of independent observations into a temporal structure.

![](./assets/asset_8B_graph_lineage_explanation.mp4)

That is the real purpose of tracking.

---

# From graph to `.geff`

Once the nodes and edges have been assembled, the graph is saved as a:

```text
.geff
```

file.

Conceptually, it contains:

```text
Nodes
------
time
z
y
x


Edges
------
source
target
edge probability
spatial distance
```

The `.geff` file is therefore the final structured representation of the prediction.

Instead of looking at the original microscopy frames, a downstream program can now inspect the relationships directly.

For example:

```text
Which cells were detected?

Which cells were connected?

How confident were those connections?

How far apart were connected cells?

Where did divisions occur?
```

The graph makes these questions much easier to ask.

---

# The graph is where different assumptions meet

This stage is interesting because it combines information from several earlier parts of the pipeline.

The graph depends on:

```text
Detection
   │
   ├── Did we find the cell?
   │
   ▼
Node representation
   │
   ├── What does it look like?
   ├── Where is it?
   │
   ▼
Transformer
   │
   ├── Which relationships are plausible?
   │
   ▼
Probability
   │
   ├── How confident is the model?
   │
   ▼
Graph constraints
   │
   ├── Does the relationship fit?
   │
   ▼
Tracking graph
```

This is why tracking errors can be difficult to diagnose.

A wrong edge doesn't necessarily mean the transformer itself is bad.

The problem could have started with:

```text
wrong detection
```

or:

```text
wrong coordinate conversion
```

or:

```text
poor edge threshold
```

or:

```text
graph constraint
```

or, when enabled:

```text
global optimization
```

The graph is the point where all these decisions become visible together.

---

# Greedy versus global optimization

This leads naturally to the optional ILP stage.

The greedy approach asks:

> "Is this edge good enough, and can I add it without breaking the rules?"

The ILP approach asks something closer to:

> "What combination of edges gives the best overall graph under the allowed constraints?"

That is a major conceptual difference.

Greedy:

```text
edge 1 looks best
      ↓
accept

edge 2 looks best among remaining
      ↓
accept

edge 3 conflicts
      ↓
reject
```

Global optimization:

```text
many candidate edges
        │
        ▼
consider combinations
        │
        ▼
optimize the overall graph
        │
        ▼
consistent solution
```

The second approach can make a different decision because it isn't evaluating every edge in isolation.

![](./assets/asset_8C_real_greedy_vs_global_ILP.mp4)

---

# The biological interpretation

At this point, the entire tracking problem starts looking less like image processing and more like reconstructing a biological history.

The microscope gives us observations:

```text
cell seen here
cell seen there
cell seen somewhere else
```

The graph proposes a history:

```text
this observation
      ↓
is related to this one
      ↓
which is related to this one
```

And when a division occurs:

```text
       parent
       /    \
      /      \
daughter   daughter
```

the graph can represent that branching event explicitly.

So the output isn't simply a list of detected cells.

It is a proposed explanation of how those cells are related through time.

---

# The complete graph-building picture

The whole stage can now be summarized as:

```text
Detected cells
      │
      ▼
(t, z, y, x) nodes
      │
      ▼
Transformer edge scores
      │
      ▼
probabilities
      │
      ▼
threshold
      │
      ▼
sort candidate edges
      │
      ▼
parent/child constraints
      │
      ▼
accepted temporal edges
      │
      ▼
tracking graph
      │
      ├───────────────┐
      │               │
      ▼               ▼
   save .geff     optional ILP
                      │
                      ▼
              globally optimized graph
```

The important conceptual shift is this:

**A neural network prediction is not yet a track.**

The neural network supplies evidence.

The graph-building system turns that evidence into structure.

---

# What I found most useful about this stage

The most useful way I found to think about graph construction was to separate three questions.

### Question 1: Did we see a cell?

That's the detection problem.

```text
image → cell node
```

### Question 2: Which cells might be related?

That's the transformer problem.

```text
node + node → edge score
```

### Question 3: Which relationships should actually exist?

That's the graph-construction problem.

```text
edge scores → constrained graph
```

Keeping those questions separate makes the pipeline much easier to understand.

It also makes debugging easier.

If a cell is missing entirely, look earlier.

If the cell exists but is connected to the wrong neighbor, look at temporal linking.

If the individual predictions look reasonable but the resulting graph is biologically strange, look at graph construction and optimization.

---

# The final transformation

The pipeline has now gone through a remarkable sequence of representations:

```text
3D microscopy
      ↓
dense neural representation
      ↓
cell detections
      ↓
64-D cell representations
      ↓
pairwise temporal scores
      ↓
candidate edges
      ↓
constrained graph
      ↓
tracking structure
```

At the beginning, we had an image.

At the end, we have something that represents a hypothesis about how cells relate through time.

And that raises the final question:

**What happens when we step back and look at the entire pipeline as one system?**

The answer is more interesting than simply saying "image goes in, graph comes out."

The important story is how the representation changes at every stage — from pixels, to features, to cells, to relationships, and finally to a global biological structure.
