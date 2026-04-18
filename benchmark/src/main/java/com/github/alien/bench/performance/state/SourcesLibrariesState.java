package com.github.alien.bench.performance.state;

import org.openjdk.jmh.annotations.Level;
import org.openjdk.jmh.annotations.Setup;

import java.nio.file.Path;

public class SourcesLibrariesState extends LibrariesState {
	public Path sourcesPath;

	@Setup(Level.Trial)
	public void doSetup() {
		this.sourcesPath = this.librariesPath.resolve(Path.of(library, "src"));
	}
}
