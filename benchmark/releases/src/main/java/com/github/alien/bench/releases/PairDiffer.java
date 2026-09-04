package com.github.alien.bench.releases;

import com.google.common.base.Stopwatch;
import com.google.common.collect.Iterables;
import io.github.alien.roseau.Library;
import io.github.alien.roseau.Roseau;
import io.github.alien.roseau.api.model.API;
import io.github.alien.roseau.api.model.AccessModifier;
import io.github.alien.roseau.api.model.FieldDecl;
import io.github.alien.roseau.api.model.MethodDecl;
import io.github.alien.roseau.api.model.Symbol;
import io.github.alien.roseau.api.model.TypeDecl;
import io.github.alien.roseau.api.model.TypeMemberDecl;
import io.github.alien.roseau.diff.RoseauReport;
import io.github.alien.roseau.diff.changes.BreakingChange;
import io.github.alien.roseau.diff.changes.BreakingChangeKind;
import io.github.alien.roseau.diff.changes.BreakingChangeNature;
import io.github.alien.roseau.options.RoseauOptions;

import java.io.BufferedWriter;
import java.io.IOException;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collection;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.stream.Collectors;

/**
 * Diffs a list of version pairs with Roseau and reports the breaking changes in the same shape as
 * the commit-level walk's {@code <lib>-bcs.csv}.
 * <p>
 * The pairs are supplied as a CSV so that the same runner serves both halves of the release study:
 * pairs of released JARs downloaded from Maven Central, and pairs of source trees checked out at
 * the commits the releases were cut from. Exclusion rules come from the walk's {@code walk.yaml},
 * so a symbol is inside or outside the public API here exactly as it was during the walk.
 *
 * <pre>
 * PairDiffer &lt;walk.yaml&gt; &lt;pairs.csv&gt; &lt;output-dir&gt; &lt;prefix&gt; [threads]
 * </pre>
 * <p>
 * {@code pairs.csv} declares: {@code library,pair_id,v1_label,v1_location,v2_label,v2_location}.
 */
public final class PairDiffer {
	private static final List<String> PAIRS_HEADER = List.of(
		"library", "pair_id", "v1_label", "v2_label",
		"v1_all_types_count", "v1_exported_types_count", "v1_exported_symbols_count",
		"v2_all_types_count", "v2_exported_types_count", "v2_exported_symbols_count",
		"v2_deprecated_count", "v2_internal_count",
		"all_breaking_changes_count", "api_breaking_changes_count", "excluded_breaking_changes_count",
		"binary_breaking_changes_count", "source_breaking_changes_count",
		"v1_unresolved_types_count", "v2_unresolved_types_count", "v2_incomplete_hierarchy_types_count",
		"api_time_ms", "diff_time_ms", "error");

	private static final List<String> BCS_HEADER = List.of(
		"library", "pair_id", "v1_label", "v2_label", "kind", "nature", "details", "compatibility",
		"impacted_package_fqn", "impacted_type_fqn", "impacted_symbol_fqn", "symbol_visibility",
		"is_excluded_symbol", "is_deprecated_removal", "is_internal_removal", "matched_exclusion_rule",
		"impacted_type_hierarchy_incomplete");

	private PairDiffer() {
	}

	record Pair(String library, String pairId, String v1Label, Path v1, String v2Label, Path v2) {
	}

	public static void main(String[] args) throws IOException, InterruptedException {
		if (args.length < 4) {
			System.err.println("Usage: PairDiffer <walk.yaml> <pairs.csv> <output-dir> <prefix> [threads]");
			System.exit(2);
		}
		Path walkYaml = Path.of(args[0]);
		Path pairsCsv = Path.of(args[1]);
		Path outputDir = Path.of(args[2]);
		String prefix = args[3];
		int threads = args.length > 4 ? Integer.parseInt(args[4]) : Runtime.getRuntime().availableProcessors();

		Map<String, RoseauOptions.Exclude> exclusions = WalkConfig.exclusionsByLibrary(walkYaml);
		List<Pair> pairs = readPairs(pairsCsv);
		Files.createDirectories(outputDir);

		System.err.printf("Diffing %d pairs with %d threads%n", pairs.size(), threads);
		AtomicInteger done = new AtomicInteger();

		try (BufferedWriter pairsOut = writer(outputDir.resolve(prefix + "-pairs.csv"));
		     BufferedWriter bcsOut = writer(outputDir.resolve(prefix + "-bcs.csv"))) {
			writeRow(pairsOut, PAIRS_HEADER);
			writeRow(bcsOut, BCS_HEADER);

			// Roseau's own diff parallelises internally, so pairs are dispatched one per thread and
			// the two writers are the only shared state.
			try (ExecutorService pool = Executors.newFixedThreadPool(threads)) {
				for (Pair pair : pairs) {
					pool.execute(() -> {
						Result result = diff(pair, exclusions.getOrDefault(pair.library(),
							new RoseauOptions.Exclude(List.of(), List.of())));
						synchronized (PairDiffer.class) {
							try {
								writeRow(pairsOut, result.pairRow());
								for (List<Object> row : result.bcRows()) {
									writeRow(bcsOut, row);
								}
							} catch (IOException e) {
								System.err.println("Failed to write " + pair.pairId() + ": " + e);
							}
						}
						int n = done.incrementAndGet();
						if (n % 25 == 0) {
							System.err.printf("  %d/%d pairs%n", n, pairs.size());
						}
					});
				}
			}
		}
		System.err.println("Done");
	}

	private record Result(List<Object> pairRow, List<List<Object>> bcRows) {
	}

	private static Result diff(Pair pair, RoseauOptions.Exclude exclude) {
		Stopwatch apiSw = Stopwatch.createStarted();
		try {
			API v1 = Roseau.buildAPI(Library.builder().location(pair.v1()).classpath(List.of()).build());
			API v2 = Roseau.buildAPI(Library.builder().location(pair.v2()).classpath(List.of()).build());
			long apiMs = apiSw.elapsed().toMillis();

			Stopwatch diffSw = Stopwatch.createStarted();
			RoseauReport report = Roseau.diff(v1, v2);
			long diffMs = diffSw.elapsed().toMillis();

			List<BreakingChange> bcs = report.getAllBreakingChanges();
			Exclusions matcher = Exclusions.of(exclude);
			// One exclusion decision per breaking change, shared by the pair row and the BC rows
			Map<BreakingChange, String> matchedRules = new IdentityHashMap<>();
			for (BreakingChange bc : bcs) {
				matcher.matchedRule(bc.impactedSymbol(), v2)
					.or(() -> matcher.matchedRule(bc.impactedType(), v2))
					.ifPresent(rule -> matchedRules.put(bc, rule));
			}

			Stats s1 = stats(v1, matcher);
			Stats s2 = stats(v2, matcher);
			long binary = bcs.stream().filter(bc -> bc.kind().isBinaryBreaking()).count();
			long source = bcs.stream().filter(bc -> bc.kind().isSourceBreaking()).count();

			List<Object> pairRow = new ArrayList<>(List.of(
				pair.library(), pair.pairId(), pair.v1Label(), pair.v2Label(),
				s1.allTypes(), s1.exportedTypes(), s1.exportedSymbols(),
				s2.allTypes(), s2.exportedTypes(), s2.exportedSymbols(),
				s2.deprecated(), s2.internal(),
				bcs.size(), bcs.size() - matchedRules.size(), matchedRules.size(), binary, source,
				s1.unresolvedTypes(), s2.unresolvedTypes(), s2.incompleteHierarchies(),
				apiMs, diffMs, ""));

			List<List<Object>> bcRows = new ArrayList<>();
			for (BreakingChange bc : bcs) {
				bcRows.add(bcRow(pair, bc, v2, matchedRules.getOrDefault(bc, "")));
			}
			return new Result(pairRow, bcRows);
		} catch (Exception e) {
			System.err.printf("Pair %s/%s failed: %s%n", pair.library(), pair.pairId(), e);
			List<Object> row = new ArrayList<>();
			row.addAll(List.of(pair.library(), pair.pairId(), pair.v1Label(), pair.v2Label()));
			for (int i = 4; i < PAIRS_HEADER.size() - 1; i++) {
				row.add("");
			}
			row.add(e.getClass().getSimpleName() + ": " + e.getMessage());
			return new Result(row, List.of());
		}
	}

	private static List<Object> bcRow(Pair pair, BreakingChange bc, API v2, String matchedRule) {
		BreakingChangeKind kind = bc.kind();
		Symbol impacted = bc.impactedSymbol();
		boolean excluded = !matchedRule.isEmpty();
		boolean removal = kind.getNature() == BreakingChangeNature.DELETION;
		return List.of(
			pair.library(), pair.pairId(), pair.v1Label(), pair.v2Label(),
			kind.name(), kind.getNature().name().toLowerCase(Locale.ROOT), bc.details().toString(),
			compatibility(kind),
			bc.impactedType().getPackageName(), bc.impactedType().getQualifiedName(),
			impacted.getQualifiedName(), visibility(impacted.getVisibility()),
			excluded, removal && isDeprecated(impacted), removal && excluded, matchedRule,
			v2.analyzer().hasIncompleteHierarchy(bc.impactedType()));
	}

	private record Stats(int allTypes, int exportedTypes, int exportedSymbols, long deprecated, long internal,
	                     int unresolvedTypes, int incompleteHierarchies) {
	}

	private static Stats stats(API api, Exclusions matcher) {
		Collection<TypeDecl> allTypes = api.getLibraryTypes().getAllTypes();
		int exportedTypes = 0;
		int exportedSymbols = 0;
		int incompleteHierarchies = 0;
		long deprecated = 0;
		long internal = 0;
		for (TypeDecl type : api.getExportedTypes()) {
			Set<MethodDecl> methods = api.analyzer().getDeclaredExportedMethods(type);
			Set<FieldDecl> fields = api.analyzer().getDeclaredExportedFields(type);
			exportedTypes++;
			exportedSymbols += 1 + methods.size() + fields.size();
			if (api.analyzer().hasIncompleteHierarchy(type)) {
				incompleteHierarchies++;
			}
			if (isDeprecated(type)) {
				deprecated++;
			}
			if (matcher.matchedRule(type, api).isPresent()) {
				internal++;
			}
			for (TypeMemberDecl member : Iterables.concat(methods, fields)) {
				if (isDeprecated(member)) {
					deprecated++;
				}
				if (matcher.matchedRule(member, api).isPresent()) {
					internal++;
				}
			}
		}
		return new Stats(allTypes.size(), exportedTypes, exportedSymbols, deprecated, internal,
			api.analyzer().resolver().unresolvedTypes().size(), incompleteHierarchies);
	}

	private static boolean isDeprecated(Symbol symbol) {
		return symbol.getAnnotations().stream()
			.anyMatch(a -> a.actualAnnotation().getQualifiedName().equals(Deprecated.class.getCanonicalName()));
	}

	private static String compatibility(BreakingChangeKind kind) {
		if (kind.isBinaryBreaking() && kind.isSourceBreaking()) {
			return "both";
		}
		return kind.isBinaryBreaking() ? "binary" : "source";
	}

	private static String visibility(AccessModifier visibility) {
		return visibility == null ? "" : visibility.toString();
	}

	private static List<Pair> readPairs(Path csv) throws IOException {
		List<String> lines = Files.readAllLines(csv, StandardCharsets.UTF_8);
		List<String> header = splitCsv(lines.getFirst());
		List<Pair> pairs = new ArrayList<>();
		for (String line : lines.subList(1, lines.size())) {
			if (line.isBlank()) {
				continue;
			}
			List<String> cells = splitCsv(line);
			pairs.add(new Pair(cell(header, cells, "library"), cell(header, cells, "pair_id"),
				cell(header, cells, "v1_label"), Path.of(cell(header, cells, "v1_location")),
				cell(header, cells, "v2_label"), Path.of(cell(header, cells, "v2_location"))));
		}
		return pairs;
	}

	private static String cell(List<String> header, List<String> cells, String name) {
		int i = header.indexOf(name);
		if (i < 0) {
			throw new IllegalArgumentException("Missing column " + name);
		}
		return cells.get(i);
	}

	/** Minimal RFC-4180 split; the pair files this reads contain no embedded newlines. */
	private static List<String> splitCsv(String line) {
		List<String> cells = new ArrayList<>();
		StringBuilder current = new StringBuilder();
		boolean quoted = false;
		for (int i = 0; i < line.length(); i++) {
			char c = line.charAt(i);
			if (quoted) {
				if (c == '"' && i + 1 < line.length() && line.charAt(i + 1) == '"') {
					current.append('"');
					i++;
				} else if (c == '"') {
					quoted = false;
				} else {
					current.append(c);
				}
			} else if (c == '"') {
				quoted = true;
			} else if (c == ',') {
				cells.add(current.toString());
				current.setLength(0);
			} else {
				current.append(c);
			}
		}
		cells.add(current.toString());
		return cells;
	}

	private static BufferedWriter writer(Path file) throws IOException {
		return Files.newBufferedWriter(file, StandardCharsets.UTF_8);
	}

	private static void writeRow(Writer writer, List<?> values) throws IOException {
		writer.write(values.stream().map(PairDiffer::csvCell).collect(Collectors.joining(",")));
		writer.write(System.lineSeparator());
	}

	private static String csvCell(Object value) {
		String raw = value == null ? "" : String.valueOf(value);
		boolean needsQuoting = raw.contains(",") || raw.contains("\"") || raw.contains("\n") || raw.contains("\r");
		return needsQuoting ? "\"" + raw.replace("\"", "\"\"") + "\"" : raw;
	}
}
