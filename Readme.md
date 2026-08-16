# Atlas of Computational Intelligence

> **What is intelligence?**

This is a long-term attempt to answer that question.

Not by defining intelligence once, but by approaching it from many directions:

**Machine Learning. · Reinforcement Learning. · Mathematics. · Neuroscience. · Cognitive Psychology. · Computation. · Experiments.**

The central idea is simple:

> **Intelligence is not one thing.**

It may emerge from the interaction of **representation, learning, memory, optimization, uncertainty, prediction, decision-making, and interaction with the world**.

This repository is an attempt to understand those pieces individually—and, more importantly, understand **how they fit together**.

---

# The Question

Most discussions of intelligence eventually become philosophical.

This project tries to make the question computational.

```text
                         INTELLIGENCE
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
   Representation         Learning        Decision Making
          │                   │                   │
       Memory            Optimization          Planning
          │                   │                   │
     Prediction        Generalization       Exploration
          │                   │                   │
     Neural Nets             RL             Neuroscience
          │                   │                   │
          └───────────────────┼───────────────────┘
                              │
                       Open Problems
```

The goal isn't to prove that one of these is *the* explanation for intelligence.

It is to investigate whether intelligence can be better understood as the **interaction of these mechanisms**.

---

# The Questions

The Atlas will gradually work through questions such as:

1. **What is intelligence?**
2. **What information does an intelligent system perceive?**
3. **How is that information represented?**
4. **How is it remembered?**
5. **How does it learn?**
6. **How does it decide?**
7. **How does it improve?**
8. **How does it generalize?**
9. **How do biological and artificial intelligence compare?**
10. **What remains unsolved?**

And then the questions become less tidy:

* How do we learn?
* Why do we forget?
* How do we recognize faces?
* How do we decide?
* Can machines imagine?
* Why do humans make mistakes?
* Can intelligence exist without memory?
* What is curiosity?
* What is consciousness?
* Why do we explore?
* How do we know what is true?
* Can intelligence emerge from randomness?

There may not be clean answers.

That's part of the point.

---

# How I Want to Explore These Questions

A question should not stop at a paragraph of explanation.

The ideal path is:

```text
                    Question
                       ↓
                 Short intuition
                       ↓
                   Mathematics
                       ↓
                     Code
                       ↓
              Interactive simulation
                       ↓
                  Visualization
                       ↓
                      Blog
                       ↓
              10-minute YouTube video
                       ↓
                 Further reading
                       ↓
                   Connections
```

Different questions will reach different stages.

Some may remain a notebook.

Some may become an experiment.

Some may eventually become a full research-style exploration.

---

# From Seed to Forest

Not every idea needs to become a giant project.

I want the repository to grow organically.

### 🌱 Seed

A question, a short explanation, and a notebook.

```text
question
   +
intuition
   +
experiment
```

### 🌿 Sapling

Add a visualization and a cleaned-up explanation.

```text
question
   +
math
   +
code
   +
visualization
   +
write-up
```

### 🌳 Tree

Turn the idea into a complete exploration.

```text
question
   ↓
mathematics
   ↓
implementation
   ↓
simulation
   ↓
visual explanation
   ↓
blog
```

### 🌲 Forest

Connect the idea to the larger map.

```text
research papers
      +
YouTube explanation
      +
related modules
      +
experiments
      +
biological connections
      +
open questions
```

A module doesn't need to become a Forest.

**The goal is depth where depth is warranted.**

---

# The Areas

The Atlas is organized around several recurring ideas rather than treating ML, neuroscience, and psychology as completely separate subjects.

## Representation

How does an intelligent system represent the world?

Topics might include:

* Linear algebra
* PCA
* Feature engineering
* Embeddings
* Neural representations
* Neuroscience
* Symbolic representations

```text
Representation
│
├── PCA
├── Linear Algebra
├── Neuroscience
└── Feature Engineering
```

---

## Learning

How does a system change when it encounters experience?

Topics might include:

* Regression
* Statistics
* Decision trees
* Neural networks
* Gradient-based learning
* Hebbian learning
* Plasticity

```text
Learning
│
├── Regression
├── Decision Trees
├── Neural Networks
└── Statistics
```

---

## Optimization

How does an intelligent system improve?

Topics might include:

* Multivariable calculus
* Gradient descent
* Loss functions
* Optimization landscapes
* Evolutionary optimization
* Credit assignment

```text
Optimization
│
└── Multivariable Calculus
    └── Gradient Descent
```

---

## Decision Making

How does an agent choose what to do?

Topics might include:

* Markov chains
* Markov decision processes
* Dynamic programming
* Q-learning
* Planning
* Exploration
* Exploitation

```text
Decision Making
│
├── Markov Chains
├── MDPs
└── Q Learning
```

---

## Generalization

How does an intelligent system go beyond what it has seen?

Topics might include:

* PAC learning
* Bias and variance
* Inductive biases
* Distribution shift
* Research methodology
* Transfer learning

```text
Generalization
│
├── PAC Learning
├── Bias / Variance
└── Research Methods
```

---

## Biological Intelligence

What can biology teach us about intelligence?

Topics might include:

* Hippocampus
* Memory
* Plasticity
* Emotion
* Attention
* Prediction
* Decision making
* Neural circuits

```text
Biological Intelligence
│
├── Hippocampus
├── Plasticity
├── Emotion
└── Memory
```

The goal isn't to assume that brains are simply biological neural networks.

The interesting question is where the analogy **breaks**.

---

# Questions I Want to Investigate

The repository will be driven by questions rather than a fixed curriculum.

Some early examples:

| #   | Question                                      |
| --- | --------------------------------------------- |
| 001 | Why does gradient descent work?               |
| 002 | Can Hebbian learning replace backpropagation? |
| 003 | Why does PCA preserve variance?               |
| 004 | Why is dopamine similar to TD learning?       |
| 005 | Why are transformers not recurrent?           |

More questions will emerge as the project develops.

The questions are intentionally broad.

A question like **"Why does gradient descent work?"** can lead from calculus → optimization → learning → neural networks → biological learning → credit assignment.

That is exactly the kind of connection this Atlas is interested in.

---

# The Map

The eventual structure should look less like a textbook and more like a network.

```text
                         INTELLIGENCE
                              │
              ┌───────────────┼───────────────┐
              │               │               │
        REPRESENTATION      LEARNING      DECISION MAKING
              │               │               │
              │               │               │
           Memory        Optimization       Planning
              │               │               │
              │               │               │
        Prediction      Generalization     Exploration
              │               │               │
              └───────────────┼───────────────┘
                              │
                       Neural Networks
                              │
                              RL
                              │
                       Neuroscience
                              │
                              ↓
                       OPEN PROBLEMS
```

But this isn't meant to be a hierarchy.

It's a **graph**.

Representation affects learning.

Learning changes representations.

Memory affects decision-making.

Optimization drives learning.

Uncertainty affects exploration.

Neuroscience challenges assumptions made by artificial systems.

Reinforcement learning connects learning, prediction, reward, and action.

And new connections will appear as the Atlas grows.

> **Click anything. Everything is connected.**

---

# The Computational Approach

Whenever possible, I want ideas to be explored at multiple levels.

```text
THE BIG QUESTION
       ↓
   Mental Model
       ↓
 Real-world Example
       ↓
      Math
       ↓
   Algorithm
       ↓
   Simulation
       ↓
 Neuroscience
       ↓
   Research
       ↓
Implementation
```

For example:

**Why does gradient descent work?**

could become:

```text
What does "learning" mean?
        ↓
What is an objective function?
        ↓
Why does the gradient point somewhere useful?
        ↓
What happens on different loss landscapes?
        ↓
Implement gradient descent
        ↓
Visualize the optimization path
        ↓
Connect it to neural networks
        ↓
Compare with biological learning
        ↓
Ask what gradient descent does NOT explain
```

The mathematics is not decoration.

The code is not decoration.

The neuroscience is not decoration.

Each is another lens on the same question.

---

# Research Notes

Some explorations will begin as rough notes.

That is intentional.

A research notebook might contain:

```text
Today I learned...

I don't understand...

This reminds me of...

Possible project...

Paper to read...

Connection to another idea...
```

Not everything needs to be polished immediately.

The Atlas is allowed to contain unfinished thoughts.

In fact, some of the most interesting questions will probably begin there.

---

# Weekly Journal

The `weekly-journal/` directory is where the learning process itself can be recorded.

The format is deliberately simple:

```text
Today I learned...

I don't understand...

This reminds me of...

Possible project...

Paper to read...
```

The journal isn't the finished product.

It is the **raw material from which modules emerge**.

---

# Repository Structure

The structure will evolve as the project does.

The current intended organization is:

```text
Atlas-of-Computational-Intelligence/

├── README.md
│
├── 00_foundations/
├── 01_learning/
├── 02_memory/
├── 03_decision-making/
├── 04_representation/
├── 05_optimization/
├── 06_uncertainty/
├── 07_neural-networks/
├── 08_reinforcement-learning/
├── 09_brain/
├── 10_research-notes/
│
├── questions/
│   ├── 001.md
│   ├── 002.md
│   └── ...
│
├── simulations/
├── papers/
├── videos/
├── blog/
├── assets/
└── weekly-journal/
```

The numbered directories provide a rough map.

They are **not prerequisites** and they are not meant to become a rigid course.

A question can jump across several areas.

---

# The Knowledge Object

The smallest useful unit in the Atlas is not a chapter.

It's a **question**.

For example:

```text
questions/
└── 001-why-does-gradient-descent-work/
```

A mature question might eventually contain:

```text
001-why-does-gradient-descent-work/

├── question.md
├── notes.md
├── mathematics.md
├── notebook.ipynb
├── simulation/
├── assets/
├── references.bib
├── blog.md
└── video.md
```

But it doesn't have to start that way.

It can begin as:

```text
question.md
notebook.ipynb
```

and grow naturally.

---

# The Atlas as a Knowledge Graph

Eventually, I want the connections between ideas to be as important as the ideas themselves.

For example:

```text
Gradient Descent
       │
       ├── Calculus
       │
       ├── Optimization
       │
       ├── Neural Networks
       │
       ├── Learning
       │
       └── Credit Assignment
               │
               ├── Reinforcement Learning
               └── Neuroscience
```

And:

```text
Memory
 │
 ├── Hippocampus
 │
 ├── Representation
 │
 ├── Learning
 │
 ├── Generalization
 │
 └── Decision Making
```

The interesting discoveries may happen **between modules**.

---

# The Long-Term Vision

I don't know exactly what this repository will look like at the end of the next semester.

That's intentional.

This is not a project where the entire destination is known beforehand.

The semester may produce:

* notebooks
* mathematical derivations
* simulations
* failed experiments
* research notes
* literature reviews
* blog posts
* videos
* small implementations
* unexpected connections
* questions that turn out to be much harder than expected

Some ideas will die.

Some will become small notes.

Some might become months-long investigations.

The Atlas should accommodate all of them.

---

# The Engine vs. The Atlas

There is also a second problem hiding underneath this project:

**How do you build a system that makes it easy to turn learning into durable knowledge?**

Eventually, I may build tooling around the Atlas so that a new knowledge object can follow something like:

```text
New Knowledge Object
        ↓
    template.md
        ↓
   notebook.ipynb
        ↓
      images/
        ↓
      publish
        ↓
  ┌─────┼─────────┐
  ↓     ↓         ↓
Website Blog   Video
```

The idea is to separate:

**the knowledge I create**

from

**the machinery used to publish it.**

But the tooling is secondary.

The first priority is answering interesting questions.

If the publishing engine becomes useful, it can grow alongside the Atlas.

---

# A Possible Future

The ideal future state looks something like this:

```text
                         QUESTION
                            │
                            ↓
                       EXPLORATION
                            │
            ┌───────────────┼───────────────┐
            ↓               ↓               ↓
           MATH            CODE         RESEARCH
            │               │               │
            └───────────────┼───────────────┘
                            ↓
                       EXPERIMENT
                            │
                            ↓
                       SIMULATION
                            │
                            ↓
                       EXPLANATION
                            │
             ┌──────────────┼──────────────┐
             ↓              ↓              ↓
           WEBSITE          BLOG         VIDEO
             │              │              │
             └──────────────┼──────────────┘
                            ↓
                       CONNECTIONS
                            │
                            ↓
                      NEW QUESTIONS
                            │
                            └──────────────→
```

One question generates another.

One experiment connects two fields.

One paper changes the mental model.

One failed implementation exposes an assumption.

And gradually, the map becomes larger.

---

# What This Is Not

This is not intended to be:

* a textbook
* a complete ML curriculum
* a neuroscience encyclopedia
* a collection of random notes
* a collection of AI-generated summaries
* a claim that we already understand intelligence

It is an **ongoing investigation**.

The objective is understanding, not completeness.

---

# Status

🚧 **Beginning / long-term project**

The repository is currently mostly a foundation for future work.

The substantive content will be developed gradually over the coming academic semester.

The structure will probably change.

The questions will change.

Some modules will disappear.

New ones will appear.

That's expected.

> **The Atlas is being built while the territory is being explored.**

---

# The Big Question

Everything eventually comes back here:

> **What is intelligence?**

Maybe intelligence is a collection of mechanisms.

Maybe it is an emergent property of interacting systems.

Maybe biological intelligence and artificial intelligence share deeper principles.

Maybe they don't.

Maybe memory is essential.

Maybe prediction is fundamental.

Maybe intelligence is inseparable from interaction with an environment.

Maybe we're asking the wrong question entirely.

I don't know yet.

**That's what this project is for.**

---

## One Question at a Time.

**Mathematics → Computation → Experiment → Neuroscience → Research → Connection**

And eventually:

**a map of what we know, what we think we know, and what we still don't understand.**
