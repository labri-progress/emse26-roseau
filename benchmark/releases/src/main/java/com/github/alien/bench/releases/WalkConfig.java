package com.github.alien.bench.releases;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.dataformat.yaml.YAMLFactory;
import io.github.alien.roseau.options.RoseauOptions;

import java.io.IOException;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;

/**
 * Reads the per-library exclusion rules out of the longitudinal study's {@code walk.yaml}, merging
 * the {@code defaults} block into each repository exactly like {@code BatchGitWalker} does.
 */
final class WalkConfig {
	private static final RoseauOptions.Exclude EMPTY = new RoseauOptions.Exclude(List.of(), List.of());
	private static final ObjectMapper MAPPER = new ObjectMapper(new YAMLFactory()).findAndRegisterModules();

	private WalkConfig() {
	}

	static Map<String, RoseauOptions.Exclude> exclusionsByLibrary(Path yaml) throws IOException {
		JsonNode root = MAPPER.readTree(yaml.toFile());
		RoseauOptions.Exclude defaults = readExclusions(root.path("defaults").path("exclusions"));

		Map<String, RoseauOptions.Exclude> byLibrary = new HashMap<>();
		for (JsonNode repo : root.path("repositories")) {
			RoseauOptions.Exclude own = readExclusions(repo.path("exclusions"));
			byLibrary.put(repo.path("libraryId").asText(), merge(defaults, own));
		}
		return byLibrary;
	}

	private static RoseauOptions.Exclude readExclusions(JsonNode node) {
		if (node == null || node.isMissingNode() || node.isNull()) {
			return EMPTY;
		}
		RoseauOptions.Exclude parsed = MAPPER.convertValue(node, RoseauOptions.Exclude.class);
		return new RoseauOptions.Exclude(
			parsed.names() == null ? List.of() : parsed.names(),
			parsed.annotations() == null ? List.of() : parsed.annotations());
	}

	private static RoseauOptions.Exclude merge(RoseauOptions.Exclude defaults, RoseauOptions.Exclude own) {
		return new RoseauOptions.Exclude(
			Stream.concat(defaults.names().stream(), own.names().stream()).toList(),
			Stream.concat(defaults.annotations().stream(), own.annotations().stream()).toList());
	}
}
