package com.github.alien.bench.accuracy;

import com.github.alien.compiler.JavaCompiler;
import com.github.alien.tool.BreakingChangesCount;
import com.github.alien.tool.BreakingVerdict;
import com.github.alien.tool.Tool;
import com.google.common.io.MoreFiles;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Function;
import java.util.jar.JarOutputStream;
import java.util.stream.Collectors;
import java.util.stream.Stream;

public class Benchmark {
	private static final String CASES_CSV = "results-by-case.csv";
	private static final String TOOLS_CSV = "results-by-tool.csv";

	public static void runBenchmark(Path v1Path, Path v2Path, Path clientPath, Path workingPath, Path v1Jars,
	                                 Path v2Jars, Path clientJars, List<Tool> jarTools, List<Tool> sourceTools)
		throws IOException {
		JavaCompiler.ensureJavaVersion(25);
		cleanWorkingDir(workingPath);

		// Compile V1 into JARs
		packageLibraryCases(v1Path, v1Jars);
		// Compile V2 into JARs
		packageLibraryCases(v2Path, v2Jars);
		// Compile client against V1
		packageClientCases(clientPath, v1Jars, clientJars);

		// Build ground truth
		var groundTruth = buildGroundTruth(clientPath, clientJars, v2Jars);

		// Benchmark tools
		var toolsWithPaths = Stream.concat(
			jarTools.stream().map(tool -> jarTool(tool, v1Jars, v2Jars)),
			sourceTools.stream().map(tool -> sourceTool(tool, v1Path, v2Path))
		).toList();
		benchmarkTools(groundTruth, toolsWithPaths, workingPath);
	}

	private static void cleanWorkingDir(Path workingPath) throws IOException {
		var casesCsv = workingPath.resolve(CASES_CSV);
		var toolsCsv = workingPath.resolve(TOOLS_CSV);
		var casesCsvBackup = Files.exists(casesCsv) ? Files.readAllBytes(casesCsv) : null;
		var toolsCsvBackup = Files.exists(toolsCsv) ? Files.readAllBytes(toolsCsv) : null;

		if (Files.isDirectory(workingPath)) {
			MoreFiles.deleteRecursively(workingPath);
		}
		Files.createDirectories(workingPath);

		if (casesCsvBackup != null) {
			Files.write(casesCsv, casesCsvBackup);
		}
		if (toolsCsvBackup != null) {
			Files.write(toolsCsv, toolsCsvBackup);
		}
	}

	public record ToolWithPaths(Tool tool, Function<String, Path> v1PathResolver, Function<String, Path> v2PathResolver) {
		public Path v1Path(String caseName) {
			return v1PathResolver.apply(caseName);
		}

		public Path v2Path(String caseName) {
			return v2PathResolver.apply(caseName);
		}
	}

	public static ToolWithPaths jarTool(Tool tool, Path v1JarsPath, Path v2JarsPath) {
		return new ToolWithPaths(
			tool,
			caseName -> v1JarsPath.resolve("%s.jar".formatted(caseName)),
			caseName -> v2JarsPath.resolve("%s.jar".formatted(caseName))
		);
	}

	public static ToolWithPaths sourceTool(Tool tool, Path v1SourcePath, Path v2SourcePath) {
		return new ToolWithPaths(
			tool,
			v1SourcePath::resolve,
			v2SourcePath::resolve
		);
	}

	public static void packageLibraryCases(Path sourcesPath, Path jarsPath) {
		System.out.printf("Packaging %s to %s...%n", sourcesPath, jarsPath);

		try (var cases = Files.list(sourcesPath)) {
			cases.filter(Files::isDirectory)
				.parallel()
				.forEach(caseDir -> {
					var caseName = caseDir.getFileName();
					var classesPath = jarsPath.resolve("%s-classes".formatted(caseName));
					var jarPath = jarsPath.resolve("%s.jar".formatted(caseName));
					System.out.printf("\tCompiling %s into %s%n".formatted(caseDir, jarPath));

					try {
						JavaCompiler.packageSources(caseDir, classesPath, jarPath, List.of(), true);
						MoreFiles.deleteRecursively(classesPath);
					} catch (Exception e) {
						// Erroneous case
						throw new RuntimeException("Couldn't compile library case %s".formatted(caseDir), e);
					}
				});
		} catch (IOException e) {
			throw new RuntimeException("Couldn't list library cases from %s".formatted(sourcesPath), e);
		}
	}

	public static void packageClientCases(Path clientPath, Path v1JarsPath, Path clientJarPath) {
		System.out.printf("Packaging %s against %s...%n", clientPath, v1JarsPath);

		try (var cases = Files.list(clientPath)) {
			cases.filter(Files::isDirectory)
				.parallel()
				.forEach(caseDir -> {
					var caseName = caseDir.getFileName().toString();
					var clientClasses = clientJarPath.resolve("%s-classes".formatted(caseName));
					var clientJar = clientJarPath.resolve("%s.jar".formatted(caseName));
					var v1Jar = v1JarsPath.resolve("%s.jar".formatted(caseName));
					System.out.printf("\tCompiling %s against %s to %s%n".formatted(caseDir, v1Jar, clientJar));

					try {
						ensureJarExists(v1Jar);
						JavaCompiler.packageSources(caseDir, clientClasses, clientJar, List.of(v1Jar), true);
						MoreFiles.deleteRecursively(clientClasses);
					} catch (Exception e) {
						// Erroneous case
						throw new RuntimeException("Couldn't compile client case %s".formatted(caseDir), e);
					}
				});
		} catch (IOException e) {
			throw new RuntimeException("Couldn't list client cases from %s".formatted(clientPath), e);
		}
	}

	public static Map<String, BreakingVerdict> buildGroundTruth(Path clientsPath, Path clientJarsPath, Path v2JarsPath) {
		System.out.println("Building ground truth...");

		Map<String, BreakingVerdict> groundTruth = new ConcurrentHashMap<>();
		try (var cases = Files.list(clientsPath)) {
			cases.filter(Files::isDirectory)
				.sorted(Comparator.comparing(Path::getFileName))
				.parallel()
				.forEach(caseDir -> {
					var caseName = caseDir.getFileName();
					var clientClasses = clientJarsPath.resolve("%s-classes".formatted(caseName));
					var clientJar = clientJarsPath.resolve("%s.jar".formatted(caseName));
					var v2Jar = v2JarsPath.resolve("%s.jar".formatted(caseName));
					var isSourceBreaking = false;
					var isBinaryBreaking = false;
					var message = new StringBuilder();

					// Compile against V2
					System.out.printf("\tCompiling %s against %s...%n", caseDir, v2Jar);
					ensureJarExists(v2Jar);
					String compilationMessage = JavaCompiler.compileSources(caseDir, clientClasses, List.of(v2Jar), false);
					if (compilationMessage != null) {
						isSourceBreaking = true;
						System.out.printf("\tCompilation error: %s%n", compilationMessage);
						message.append("Compiler: ").append(compilationMessage);
					}

					// Link against V2
					System.out.printf("\tLinking %s against %s...%n", caseDir, v2Jar);
					var mainClass = resolveMainClass(caseDir);
					var linkingMessage = JavaCompiler.linkAgainstJar(clientJar, v2Jar, mainClass);
					if (linkingMessage != null) {
						isBinaryBreaking = true;
						System.out.printf("\tLinking error: %s%n", linkingMessage);
						message.append("Linker: ").append(linkingMessage);
					}

					var verdict = new BreakingVerdict(isBinaryBreaking, isSourceBreaking, 0, 0, 0, message.toString());
					System.out.printf("Groundtruth for %s: %s%n", caseName, verdict);
					groundTruth.put(caseName.toString(), verdict);

					if (Files.isDirectory(clientClasses)) {
						try {
							MoreFiles.deleteRecursively(clientClasses);
						} catch (IOException e) {
							e.printStackTrace();
						}
					}
				});
		} catch (IOException e) {
			throw new RuntimeException("Couldn't list client cases from %s".formatted(clientsPath), e);
		}

		return groundTruth;
	}

	private static String resolveMainClass(Path caseDir) {
		var mainJava = caseDir.resolve("Main.java");
		if (!Files.exists(mainJava)) {
			throw new RuntimeException("Missing Main.java in client case " + caseDir);
		}

		try {
			var source = Files.readString(mainJava);
			for (var line : source.lines().toList()) {
				var trimmed = line.trim();
				if (!trimmed.startsWith("package ")) {
					continue;
				}
				if (!trimmed.endsWith(";")) {
					break;
				}
				var packageName = trimmed.substring("package ".length(), trimmed.length() - 1).trim();
				if (packageName.isEmpty()) {
					break;
				}
				return packageName + ".Main";
			}
			return "Main";
		} catch (IOException e) {
			throw new RuntimeException("Unable to resolve main class for client case " + caseDir, e);
		}
	}

	public static void benchmarkTools(Map<String, BreakingVerdict> groundTruth, Path v1JarsPath, Path v2JarsPath,
	                                  List<Tool> tools, Path workingPath) {
		var toolsWithPaths = tools.stream()
			.map(tool -> jarTool(tool, v1JarsPath, v2JarsPath))
			.toList();
		benchmarkTools(groundTruth, toolsWithPaths, workingPath);
	}

	public static void benchmarkTools(Map<String, BreakingVerdict> groundTruth, List<ToolWithPaths> toolsWithPaths,
	                                  Path workingPath) {
		System.out.printf("Benchmarking %s%n".formatted(
			String.join(", ", toolsWithPaths.stream().map(t -> t.tool().getName()).toList())));
		var casesCsv = workingPath.resolve(CASES_CSV);
		var toolsCsv = workingPath.resolve(TOOLS_CSV);
		var toolsBreakingChanges = new ArrayList<BreakingChangesCount>();
		var metricsByTool = new LinkedHashMap<String, ToolMetrics>();
		toolsWithPaths.forEach(toolWithPaths -> metricsByTool.put(toolWithPaths.tool().getName(), new ToolMetrics()));

		prepareCSV(casesCsv, toolsWithPaths);
		Set<String> completedCases = getCompletedCasesFromCSV(casesCsv);

		LinkedHashMap<String, BreakingVerdict> benchmarkCases = groundTruth.entrySet().stream()
			.sorted(Map.Entry.comparingByKey())
			.collect(Collectors.toMap(
				Map.Entry::getKey,
				Map.Entry::getValue,
				(left, right) -> left,
				LinkedHashMap::new
			));

		var benchmarkCaseStream = benchmarkCases.entrySet().stream()
			.filter(entry -> !completedCases.contains(entry.getKey()));

		benchmarkCaseStream.parallel().forEach(entry -> {
			var caseName = entry.getKey();
			var value = entry.getValue();
			var resultsByTool = new ConcurrentHashMap<String, BreakingVerdict>();
			resultsByTool.put("GroundTruth", value);

			toolsWithPaths.parallelStream().forEach(toolWithPaths -> {
				var tool = toolWithPaths.tool();
				var v1Path = toolWithPaths.v1Path(caseName);
				var v2Path = toolWithPaths.v2Path(caseName);
				ensureJarExists(v1Path);
				ensureJarExists(v2Path);

				BreakingVerdict verdict = tool.analyze(v1Path, v2Path);
				System.out.printf("[%s] %s [bin: %b, src: %b]%n", tool.getName(),
					caseName, verdict.isBinaryBreaking(), verdict.isSourceBreaking());
				resultsByTool.put(tool.getName(), verdict);
			});

			var line = new StringBuilder();
			var gt = resultsByTool.get("GroundTruth");
			line.append(caseName);
				line.append(";%b;%b;%s".formatted(gt.isBinaryBreaking(), gt.isSourceBreaking(),
					csvField(gt.message())));
			toolsWithPaths.forEach(toolWithPaths -> {
				var toolName = toolWithPaths.tool().getName();
				var details = resultsByTool.get(toolName);
				var correctBin = details.isBinaryBreaking() == gt.isBinaryBreaking();
				var correctSrc = details.isSourceBreaking() == gt.isSourceBreaking();
				var inputTokens = details.inputTokens();
				var outputTokens = details.outputTokens();
				var requestTime = details.requestTime();
				var message = details.message();

				updateMetrics(metricsByTool.get(toolName), gt, details);
				line.append(";%b;%b;%b;%b;%d;%d;%f;%s".formatted(details.isBinaryBreaking(), 
					details.isSourceBreaking(),
					correctBin, 
					correctSrc, 
					inputTokens, 
					outputTokens, 
					requestTime, 
						csvField(message)));
			});

			try {
				Files.writeString(casesCsv, line + "\n", StandardOpenOption.APPEND);
			} catch (Exception e) {
				throw new RuntimeException("Unable to append case %s to %s".formatted(caseName, casesCsv), e);
			}

			toolsBreakingChanges.add(new BreakingChangesCount(caseName, resultsByTool));
		});

		writeToolSummaries(metricsByTool, toolsCsv);
	}

	private static String csvField(String value) {
		return value.replace(';', ',').replace('\r', ' ').replace('\n', ' ');
	}

	private static void prepareCSV(Path casesCsv, List<ToolWithPaths> toolsWithPaths) {
		try {
			if (Files.notExists(casesCsv)) {
				Path benchmark = Files.createFile(casesCsv);
				Files.writeString(benchmark, "case;bin;src;message;" +
					toolsWithPaths.stream().map(t -> {
						String name = t.tool().getName();
						String[] nameArray = new String[8];
						Arrays.fill(nameArray, name);
						return "%s_bin;%s_src;correct_%s_bin;correct_%s_src;%s_input_tokens;%s_output_tokens;%s_request_time;%s_message"
							.formatted((Object[]) nameArray);
						})
						.collect(Collectors.joining(";")) + "\n");
			} else {
				removeIncompleteLastLine(casesCsv);
			}
		} catch (IOException e) {
			throw new RuntimeException("Unable to initialize results CSV " + casesCsv, e);
		}
	}

	private static void removeIncompleteLastLine(Path csvPath) throws IOException {
		var lines = Files.readAllLines(csvPath);
		if (lines.isEmpty()) {
			return;
		}
		var expectedFieldCount = lines.get(0).split(";", -1).length;

		int lastNonEmptyLineIndex = -1;
		for (int i = lines.size() - 1; i >= 0; i--) {
			if (!lines.get(i).trim().isEmpty()) {
				lastNonEmptyLineIndex = i;
				break;
			}
		}

		if (lastNonEmptyLineIndex <= 0) {
			return;
		}

		var lastLine = lines.get(lastNonEmptyLineIndex).trim();
		if (lastLine.split(";", -1).length == expectedFieldCount) {
			return;
		}

		lines.remove(lastNonEmptyLineIndex);
		var content = lines.isEmpty() ? "" : String.join("\n", lines) + "\n";
		Files.writeString(csvPath, content);
	}

	private static Set<String> getCompletedCasesFromCSV(Path csvPath) {
		if (Files.notExists(csvPath)) {
			return Set.of();
		}

		try (Stream<String> lines = Files.lines(csvPath)) {
			return lines
				.map(String::trim)
				.filter(line -> !line.isEmpty())
				.map(line -> {
					var separatorIndex = line.indexOf(';');
					return separatorIndex >= 0 ? line.substring(0, separatorIndex) : line;
				})
				.filter(value -> !"case".equals(value))
				.collect(Collectors.toSet());
		} catch (IOException e) {
			throw new RuntimeException("Unable to read completed cases from CSV " + csvPath, e);
		}
	}

	private static void ensureJarExists(Path jarPath) {
		if (Files.exists(jarPath)) {
			return;
		}

		try {
			Files.createDirectories(jarPath.getParent());
			try (var ignored = new JarOutputStream(Files.newOutputStream(jarPath))) {
				// Empty but valid JAR archive.
			}
		} catch (IOException e) {
			throw new RuntimeException("Unable to create empty JAR at " + jarPath, e);
		}
	}

	private static void updateMetrics(ToolMetrics metrics, BreakingVerdict groundTruth, BreakingVerdict predicted) {
		var gtSource = groundTruth.isSourceBreaking();
		var gtBinary = groundTruth.isBinaryBreaking();
		var gtBreaking = gtSource || gtBinary;

		var predSource = predicted.isSourceBreaking();
		var predBinary = predicted.isBinaryBreaking();
		var predBreaking = predSource || predBinary;

		metrics.breaking.update(predBreaking, gtBreaking);
		metrics.source.update(predSource, gtSource);
		metrics.binary.update(predBinary, gtBinary);
	}

	private static void writeToolSummaries(Map<String, ToolMetrics> metricsByTool, Path toolsCsv) {
		try {
			Files.writeString(toolsCsv, "tool;scope;tp;fp;fn;precision;recall;accuracy;f1\n");
		} catch (IOException e) {
			throw new RuntimeException("Unable to initialize tools results CSV " + toolsCsv, e);
		}

		metricsByTool.forEach((toolName, metrics) -> {
			appendScopeMetrics(toolsCsv, toolName, "breaking", metrics.breaking);
			appendScopeMetrics(toolsCsv, toolName, "source", metrics.source);
			appendScopeMetrics(toolsCsv, toolName, "binary", metrics.binary);
		});
	}

	private static void appendScopeMetrics(Path toolsCsv, String toolName, String scope, MetricsCounts metrics) {
		var line = "%s;%s;%d;%d;%d;%s;%s;%s;%s\n".formatted(
			toolName,
			scope,
			metrics.tp,
			metrics.fp,
			metrics.fn,
			formatScore(metrics.precision()),
			formatScore(metrics.recall()),
			formatScore(metrics.accuracy()),
			formatScore(metrics.f1())
		);
		try {
			Files.writeString(toolsCsv, line, StandardOpenOption.APPEND);
		} catch (IOException e) {
			throw new RuntimeException("Unable to append metrics for " + toolName + " (" + scope + ") to " + toolsCsv, e);
		}
	}

	private static String formatScore(double value) {
		return String.format(Locale.ROOT, "%.4f", value);
	}

	private static final class ToolMetrics {
		private final MetricsCounts breaking = new MetricsCounts();
		private final MetricsCounts source = new MetricsCounts();
		private final MetricsCounts binary = new MetricsCounts();
	}

	private static final class MetricsCounts {
		private int tp;
		private int fp;
		private int fn;
		private int total;

		private void update(boolean predictedPositive, boolean actualPositive) {
			total++;
			if (predictedPositive && actualPositive) {
				tp++;
			} else if (predictedPositive) {
				fp++;
			} else if (actualPositive) {
				fn++;
			}
		}

		private double precision() {
			var denominator = tp + fp;
			if (denominator == 0) {
				return 0.0;
			}
			return (double) tp / denominator;
		}

		private double recall() {
			var denominator = tp + fn;
			if (denominator == 0) {
				return 0.0;
			}
			return (double) tp / denominator;
		}

		private double f1() {
			var p = precision();
			var r = recall();
			if (p + r == 0.0) {
				return 0.0;
			}
			return 2.0 * p * r / (p + r);
		}

		private double accuracy() {
			if (total == 0) {
				return 0.0;
			}
			var tn = total - tp - fp - fn;
			return (double) (tp + tn) / total;
		}
	}
}
