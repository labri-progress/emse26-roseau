package com.github.alien.bench.performance.state;

import org.openjdk.jmh.annotations.Level;
import org.openjdk.jmh.annotations.Setup;

import java.nio.file.Path;

public class JarLibrariesState extends LibrariesState {
	public Path jarPath;

	@Setup(Level.Trial)
	public void doSetup() {
		this.jarPath = this.librariesPath.resolve(Path.of(library, "lib.jar"));
	}
}
