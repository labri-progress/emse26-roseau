package com.github.alien.bench.accuracy;

import com.github.alien.tool.JapicmpTool;
import com.github.alien.tool.RevapiTool;
import com.github.alien.tool.RoseauTool;
import com.github.alien.tool.Tool;

import java.nio.file.Path;
import java.util.List;

public class JezekStaticBenchmark {
	private static final Path BENCHMARK_PATH = Path.of("../jezek-dataset");
	private static final Path V1_PATH = BENCHMARK_PATH.resolve("v1", "src", "testing_lib");
	private static final Path V2_PATH = BENCHMARK_PATH.resolve("v2", "src", "testing_lib");
	private static final Path CLIENT_PATH = BENCHMARK_PATH.resolve("client", "src");

	private static final Path WORKING_PATH = Path.of("working-dir-static");
	private static final Path V1_JARS_PATH = WORKING_PATH.resolve("v1");
	private static final Path V2_JARS_PATH = WORKING_PATH.resolve("v2");
	private static final Path CLIENT_JARS_PATH = WORKING_PATH.resolve("client");

	private static final List<Tool> JAR_TOOLS = List.of(
		new RoseauTool(),
		new JapicmpTool(),
		new RevapiTool()
	);

	static void main() throws Exception {
		Benchmark.runBenchmark(
			V1_PATH, V2_PATH, CLIENT_PATH,
			WORKING_PATH,
			V1_JARS_PATH, V2_JARS_PATH, CLIENT_JARS_PATH,
			JAR_TOOLS, List.of());
	}
}
