package com.github.alien.bench.performance.state;

import org.openjdk.jmh.annotations.Level;
import org.openjdk.jmh.annotations.Setup;

import java.nio.file.Path;
import java.util.List;

public class SourcesJdkState extends JdkState {
	public List<Path> sourceModulePaths;

	@Setup(Level.Trial)
	public void doSetup() {
		sourceModulePaths = modules.stream()
				.map(module -> jdkPath.resolve(module).resolve("src"))
				.toList();
	}
}
