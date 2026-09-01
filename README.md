# EMSE'26: Roseau reproduction artifacts

This repository contains the source code, data, and scripts supporting our EMSE'26 submission "_Scaling Syntactic Breaking Change Analysis in Java with Roseau_".
Should the submission be accepted, we will finalize this repository and archive it on Zenodo.

The paper evaluates [Roseau](https://github.com/alien-tools/roseau) **v0.6.0** against japicmp 0.25.4 and Revapi 0.28.4.

## Organization

This repository is organized as follows. Subdirectories contain specific instructions for running the different tools and scripts.

  - [jezek-dataset](jezek-dataset/): This directory contains our refined and extended version of Jezek and Dietrich's benchmark (310 cases)
  - [libraries-dataset](libraries-dataset/): This directory contains the scripts we used to collect popular Java libraries from Maven Central
  - [results](results/): This directory contains the pre-computed accuracy, performance, and longitudinal results together with Jupyter notebooks presenting the analyses and plots we use in the paper
  - [benchmark](benchmark/): This directory contains the analysis pipeline, including:
    - Running Roseau, Japicmp, and Revapi on the improved accuracy dataset and collecting their accuracy
    - Running the JMH benchmarks to measure their runtime performance
    - [benchmark/walk](benchmark/walk/): the configuration of the longitudinal study (RQ3)

## Reproducing each research question

| | What | Where |
| --- | --- | --- |
| **RQ1** Accuracy | `mvn exec:java -Dexec.mainClass=com.github.alien.bench.accuracy.JezekStaticBenchmark` in [benchmark](benchmark/) | data: [benchmark/analysis/data](benchmark/analysis/data/) |
| **RQ2** Performance | `java -jar target/benchmarks.jar -rf json` in [benchmark](benchmark/) | data + notebook: [results/bench](results/bench/) |
| **RQ3** Longitudinal | `BatchGitWalker` on the `git-walk` branch of [alien-tools/roseau](https://github.com/alien-tools/roseau), driven by [benchmark/walk/walk.yaml](benchmark/walk/walk.yaml) | data + notebooks: [results/longitudinal/walk/notebooks](results/longitudinal/walk/notebooks/) |

## Requirements

JDK 25, Maven 3.9+, and [uv](https://docs.astral.sh/uv/) for the notebooks (`uv sync && uv run jupyter lab` in each notebook directory).
