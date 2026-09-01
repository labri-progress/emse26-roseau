## Fetch the top-100 libraries on Maven Central

```
$ cd 1_libs_selection
$ python parse_mvn_top_repo.py
```

The resulting libraries are stored in [2_libs_download/libs_to_download.csv](2_libs_download/libs_to_download.csv).

## Download the libraries

```
$ cd 2_libs_download
$ python download_lib_and_generate_benchmark_conf.py
```

## Download the JDK

```
$ cd 3_jdk_download
$ python download_jdk.py
```
