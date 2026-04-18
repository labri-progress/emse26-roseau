package com.github.alien.bench.performance.state;

import org.openjdk.jmh.annotations.Scope;
import org.openjdk.jmh.annotations.State;

import java.io.File;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Objects;

@State(Scope.Benchmark)
public abstract class JdkState {
	protected Path jdkPath = Path.of("../libraries-dataset/3_jdk_download/output/jdk");

	protected List<String> modules = new ArrayList<>();

	public JdkState() {
		var jdkPathFile = jdkPath.toFile();
		if (!jdkPathFile.exists() || !jdkPathFile.isDirectory()) {
			throw new IllegalStateException("JDK path does not exist: " + jdkPath);
		}

		var jdkPathFiles = jdkPathFile.listFiles();
		if (Objects.isNull(jdkPathFiles)) {
			throw new IllegalStateException("JDK path is empty: " + jdkPath);
		}

		modules.addAll(Arrays.stream(jdkPathFiles)
				.filter(File::isDirectory)
				.map(File::getName)
				.toList()
		);
	}
}
