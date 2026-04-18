package com.github.alien.tool;

import org.revapi.API;
import org.revapi.AnalysisContext;
import org.revapi.CompatibilityType;
import org.revapi.DifferenceSeverity;
import org.revapi.Revapi;
import org.revapi.base.CollectingReporter;
import org.revapi.base.FileArchive;
import org.revapi.java.JavaApiAnalyzer;

import java.nio.file.Path;
import java.util.EnumSet;
import java.util.stream.Collectors;

public class RevapiTool extends Tool {
	@Override public String getName() {
		return "revapi";
	}

	@Override
	public BreakingVerdict analyze(Path v1, Path v2) {
		var revapi = Revapi.builder()
			.withAnalyzers(JavaApiAnalyzer.class)
			.withReporters(CollectingReporter.class)
			.build();

		var v1Api = API.of(new FileArchive(v1.toFile())).build();
		var v2Api = API.of(new FileArchive(v2.toFile())).build();

		var analysisContext = AnalysisContext.builder()
			.withOldAPI(v1Api)
			.withNewAPI(v2Api)
			.build();

		try (var results = revapi.analyze(analysisContext)) {
			var collectingReporters = results.getExtensions()
				.getReporters().keySet().stream()
				.filter(r -> r.getInstance() instanceof CollectingReporter)
				.map(r -> (CollectingReporter) r.getInstance())
				.toList();
			var differences = collectingReporters.stream()
				.flatMap(r -> r.getReports().stream())
				.flatMap(report -> report.getDifferences().stream())
				.toList();
			var breaking = EnumSet.of(DifferenceSeverity.BREAKING,
				DifferenceSeverity.POTENTIALLY_BREAKING);
			var isBinaryBreaking = differences.stream().anyMatch(diff ->
				breaking.contains(diff.classification.get(CompatibilityType.BINARY)));
			var isSourceBreaking = differences.stream().anyMatch(diff ->
				breaking.contains(diff.classification.get(CompatibilityType.SOURCE)));

			return new BreakingVerdict(isBinaryBreaking, isSourceBreaking, 0, 0, 0,
				differences.stream().map(d -> d.name).collect(Collectors.joining(", ")));
		} catch (Exception e) {
			throw new IllegalStateException("Revapi analysis failed for " + v1 + " and " + v2, e);
		}
	}
}
