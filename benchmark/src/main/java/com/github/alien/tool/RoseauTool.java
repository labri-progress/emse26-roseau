package com.github.alien.tool;

import io.github.alien.roseau.Library;
import io.github.alien.roseau.Roseau;

import java.nio.file.Path;
import java.util.stream.Collectors;

public class RoseauTool extends Tool {
	@Override
	public String getName() {
		return "roseau";
	}

	@Override
	public BreakingVerdict analyze(Path v1, Path v2) {
		var lib1 = Library.of(v1);
		var lib2 = Library.of(v2);
		var report = Roseau.diff(lib1, lib2);

		return new BreakingVerdict(report.isBinaryBreaking(), report.isSourceBreaking(), 0, 0, 0,
			report.getBreakingChanges().stream().map(bc -> bc.kind().name()).collect(Collectors.joining(", ")));
	}
}
