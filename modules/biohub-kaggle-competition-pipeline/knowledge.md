# Biohub Kaggle competition pipeline

### Challenge Overview:

Your goal is to develop algorithms to detect, track and link cells across time in 3D microscopy data, including accurate identification of cell divisions and lineage reconstruction. You will work with real microscopy datasets to build robust methods that can handle dense cell populations, noise and complex biological structures.

Your work will eliminate a massive manual bottleneck in biological research and help scientists quantify the building blocks of life.

[Check out the official competition page](https://www.kaggle.com/competitions/biohub-cell-tracking-during-development/overview)

### Exploring the Dataset

train/ - Training samples. Each sample has a paired .zarr (image volume) and .geff (ground-truth tracking graph).
test/ - Example test samples (copies from train). Contains .zarr image volumes only — no ground truth is provided. When a notebook is submitted for rerun, a new hidden test set is swapped in. The size of the hidden test set is approximately the same size as the training dataset.
sample_submission.csv - A valid submission file demonstrating the correct format.

To learn from basics about the .zarr and .geff files check out my introductory notebook here:
[Notebook Link](https://www.kaggle.com/code/catingithublogo/bio-hub-guide-to-exploring-the-dataset)

### Leading Pipeline Analysis

As of making this deep-dive, the competition has no winning pipeline. The analysis is based on a public notebook I found from:

[Yusuke Togashi](https://www.kaggle.com/code/yusuketogashi/clean-approach-lightweight-local-cv-no-hack/notebook)

and offers a deep dive into the fundamentals behind the working of the current pipeline. The notebook is itself well documented for someone familiar with the prerequisite knowledge and wanting to getinto the competition.

Most notebook run their model based on the repo:

[Support Pack](https://www.kaggle.com/datasets/pilkwang/biohub-tracking-support-pack-50ep-v1)

Which is where the notebook above loads it's model from.

So our first foray will be into the same lane. We will look at the working of this repository.

### Files to Explore the repository

* [Image Preprocessing]()
* [Temporal Unet]()
* [Simple Node Transformer]()
* [Graph Construction]()
* [Complete Pipeline Analysis]()



## Quiz

# Biohub Kaggle competition pipeline

# Quiz: Biohub Kaggle Competition Pipeline Understanding

## Question 1

What does a .zarr file contain?

**Answer:**
It contains image volumes.

**Explanation:**

A .zarr file stores multi-dimensional arrays in a way that is efficient and supports distributed access, which is ideal for large datasets like microscopy images.

## Question 2

In the pipeline, what do frame windows represent?

**Answer:**
They represent consecutive time frames of an image volume.

**Explanation:**

Frame windows are used to extract temporal information from the sequence of zarr files, allowing for the analysis of changes in cell positions over time.

## Question 3

What does a Transformer model add to the pipeline compared to traditional models?

**Answer:**
It adds positional embeddings and cross-attention mechanisms.

**Explanation:**

The Transformer model introduces attention layers that allow it to focus on specific parts of the input, particularly useful for understanding sequences like cell tracks in microscopy data.

## Question 4

What is the main purpose of adding positional embeddings in a Transformer model?

**Answer:**
To provide information about relative positions between source and target nodes.

**Explanation:**

Positional embeddings encode the spatial position or order of elements within sequences, which helps the Transformer understand dependencies and relations across different time steps.

## Question 5

Where are edge scores calculated in the pipeline?

**Answer:**
They are calculated based on the output of the Edge prediction module.

**Explanation:**

Edge scores represent the likelihood that there is a connection between two nodes (cells) at adjacent time frames. They are computed by comparing the features extracted from source and target cells.

## Question 6

In what way does backpropagation work in this context?

**Answer:**
It propagates gradients through the Transformer, Edge prediction, Feature maps creation, Indexing, Positional Embeddings addition, etc., to update model parameters.

**Explanation:**

Backpropagation adjusts the weights of the network based on the loss function calculated at each step. In complex pipelines like this one, it involves propagating errors backward from the output layer through all layers in reverse order of processing.

## Question 7

What is the role of Dense voxel feature maps?

**Answer:**
They provide dense, high-resolution features that capture the spatial distribution of cells across the image volume.

**Explanation:**

Dense voxel feature maps aggregate information about cell locations and their properties at every voxel (3D pixel), offering a rich context for further analysis within and between frames.
