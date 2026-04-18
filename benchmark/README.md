This benchmark uses multiple datasets to assess the accuracy of Java breaking-change detection tools.

Each dataset consists of a set of cases. Each case includes: a baseline API (`v1`), an updated version of that API (`v2`), and a `main()` method that uses symbols from the baseline API (`client`).
The ground truth is built by systematically compiling the baseline API, the updated API, and the client code.
The client is then recompiled and relinked against the updated API.
If the compiler reports an error, the case is marked as _source-incompatible_. If the linker reports an error, the case is marked as _binary-incompatible_.

Each tool is given the two API versions and must identify source- or binary-breaking changes. Tool results are compared against the ground truth to compute accuracy metrics.
The tools do not have access to the clients.

## Evaluated tools

  - [Roseau](https://github.com/alien-tools/roseau)
  - [japicmp](https://siom79.github.io/japicmp/)
  - [Revapi](https://revapi.org)
  - GPT-5.2, prompted to identify source- and binary-breaking changes
  - GPT-4.1, prompted to identify source- and binary-breaking changes

## Datasets

  - Jezek (310 cases): presented in [API Evolution and Compatibility: A Data Corpus and Tool Evaluation](https://www.jot.fm/issues/issue_2017_04/article2.pdf) by Jezek and Dietrich
  - Roseau (311 cases): automatically extracted from [Roseau's test suite](https://github.com/alien-tools/roseau/tree/main/core/src/test/java/io/github/alien/roseau/diff)

## Design choices

- The benchmark uses the Java 25 compiler and linker (OpenJDK).
- The benchmark strictly focuses on source- and binary-breaking changes; behavioral/semantic breaking changes are not evaluated.
- When client code breaks, it is guaranteed that the case is indeed breaking. When client code doesn't break, however, it might be that the benchmark does not contain the right client that would break as a result of moving from the baseline to the updated API.
- The baseline API and client code are located in different Java packages. Therefore, the benchmark assumes that package-private symbols are not part of the API.

## Results

<table>
  <thead>
    <tr>
      <th>Dataset</th>
      <th>Category</th>
      <th>Metric</th>
      <th>Roseau 0.5.0</th>
      <th>japicmp 0.23.1</th>
      <th>Revapi 0.28.1</th>
      <th>GPT-5.2</th>
      <th>GPT4.1</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td rowspan="9">Jezek</td>
      <td rowspan="3">Breaking</td>
      <td>Precision</td>
      <td><strong>0.98</strong></td>
      <td>0.83</td>
      <td>0.82</td>
      <td>0.81</td>
      <td>0.83</td>
    </tr>
    <tr>
      <td>Recall</td>
      <td><strong>1.00</strong></td>
      <td>0.91</td>
      <td>0.90</td>
      <td>0.92</td>
      <td>0.91</td>
    </tr>
    <tr>
      <td>F1</td>
      <td><strong>0.99</strong></td>
      <td>0.87</td>
      <td>0.86</td>
      <td>0.86</td>
      <td>0.87</td>
    </tr>
    <tr>
      <td rowspan="3">Source</td>
      <td>Precision</td>
      <td><strong>0.91</strong></td>
      <td>0.76</td>
      <td>0.77</td>
      <td>0.82</td>
      <td>0.78</td>
    </tr>
    <tr>
      <td>Recall</td>
      <td><strong>0.99</strong></td>
      <td>0.90</td>
      <td>0.89</td>
      <td>0.77</td>
      <td>0.85</td>
    </tr>
    <tr>
      <td>F1</td>
      <td><strong>0.95</strong></td>
      <td>0.83</td>
      <td>0.82</td>
      <td>0.79</td>
      <td>0.81</td>
    </tr>
    <tr>
      <td rowspan="3">Binary</td>
      <td>Precision</td>
      <td><strong>0.70</strong></td>
      <td>0.70</td>
      <td>0.65</td>
      <td>0.44</td>
      <td>0.52</td>
    </tr>
    <tr>
      <td>Recall</td>
      <td><strong>0.98</strong></td>
      <td>0.97</td>
      <td>0.91</td>
      <td>0.96</td>
      <td>0.90</td>
    </tr>
    <tr>
      <td>F1</td>
      <td><strong>0.82</strong></td>
      <td>0.81</td>
      <td>0.76</td>
      <td>0.61</td>
      <td>0.66</td>
    </tr>
    <tr>
      <td rowspan="9">Roseau</td>
      <td rowspan="3">Breaking</td>
      <td>Precision</td>
      <td><strong>0.95</strong></td>
      <td>0.85</td>
      <td>0.79</td>
      <td>0.82</td>
      <td>0.86</td>
    </tr>
    <tr>
      <td>Recall</td>
      <td><strong>0.99</strong></td>
      <td>0.82</td>
      <td>0.97</td>
      <td>0.90</td>
      <td>0.90</td>
    </tr>
    <tr>
      <td>F1</td>
      <td><strong>0.97</strong></td>
      <td>0.84</td>
      <td>0.87</td>
      <td>0.86</td>
      <td>0.88</td>
    </tr>
    <tr>
      <td rowspan="3">Source</td>
      <td>Precision</td>
      <td><strong>0.86</strong></td>
      <td>0.74</td>
      <td>0.71</td>
      <td>0.78</td>
      <td>0.77</td>
    </tr>
    <tr>
      <td>Recall</td>
      <td><strong>1.00</strong></td>
      <td>0.81</td>
      <td>0.96</td>
      <td>0.84</td>
      <td>0.90</td>
    </tr>
    <tr>
      <td>F1</td>
      <td><strong>0.92</strong></td>
      <td>0.77</td>
      <td>0.82</td>
      <td>0.81</td>
      <td>0.83</td>
    </tr>
    <tr>
      <td rowspan="3">Binary</td>
      <td>Precision</td>
      <td><strong>0.88</strong></td>
      <td>0.84</td>
      <td>0.86</td>
      <td>0.52</td>
      <td>0.61</td>
    </tr>
    <tr>
      <td>Recall</td>
      <td>0.99</td>
      <td>0.99</td>
      <td>0.96</td>
      <td><strong>1.00</strong></td>
      <td>0.91</td>
    </tr>
    <tr>
      <td>F1</td>
      <td><strong>0.93</strong></td>
      <td>0.91</td>
      <td>0.90</td>
      <td>0.69</td>
      <td>0.73</td>
    </tr>
  </tbody>
</table>

## Running the benchmark

First, package the project:

```
$ mvn clean package
```

### Accuracy benchmark

Set the environment variable `OPENAI_API_KEY` to interact with OpenAI's APIs and run the accuracy benchmark:

```
$ OPENAI_API_KEY=sk-proj-[...] mvn exec:java -Dexec.mainClass="com.github.alien.bench.accuracy.JezekDietrichBenchmark"
```

Results are stored in `working-dir/results-by-{case,tool}.csv`.

### Performance benchmark

We use JMH to measure the performance of each tool. To run the performance benchmark:

```
$ java -jar target/benchmarks.jar -rf json
```

Results are stored in `jmh-result.json`. This JSON file is analyzed in the accompanying notebooks.
