package com.github.alien.bench.performance.state;

import org.openjdk.jmh.annotations.Level;
import org.openjdk.jmh.annotations.Setup;

import java.nio.file.Path;
import java.util.List;

public class JarJdkState extends JdkState {
	public List<Path> jarModulePaths;

	@Setup(Level.Trial)
	public void doSetup() {
		jarModulePaths = modules.stream()
				.map(module -> jdkPath.resolve(module).resolve("lib.jar"))
				.toList();
	}
}
