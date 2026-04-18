# EMSE'26: Roseau reproduction artifacts

This repository contains the source code, data, and scripts supporting our EMSE'26 submission "_Scaling Syntactic Breaking Change Analysis in Java with Roseau_".
Should the submission be accepted, we will finalize this repository and archive it on Zenodo.

## Organization

This repository is organized as follows. Subdirectories contain specific instructions for running the different tools and scripts.

  - [jezek-dataset](jezek-dataset/): This directory contains our refined and extend version of Jezek and Dietrich's benchmark
  - [libraries-dataset](libraries-dataset/): This directory contains the scripts we used to collect popular Java libraries from Maven Central
  - [results](results/): This directory contains the pre-computed accuracy, performance, and longitudinal results together with Jupyter notebooks presenting the analyses and plots we use in the paper
  - [benchmark](benchmark/): This directory contains the analysis pipeline, including:
    - Running Roseau, Japicmp, and Revapi on the improved accuracy dataset and collecting their accuracy
    - Running the JMH benchmarks to measure their runtime performance
