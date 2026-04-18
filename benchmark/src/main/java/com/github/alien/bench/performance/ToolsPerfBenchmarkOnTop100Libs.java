package com.github.alien.bench.performance;

import com.github.alien.bench.performance.state.JarLibrariesState;
import com.github.alien.bench.performance.state.SourcesLibrariesState;
import com.github.alien.tool.JapicmpTool;
import com.github.alien.tool.RevapiTool;
import com.github.alien.tool.RoseauTool;
import org.openjdk.jmh.annotations.Benchmark;
import org.openjdk.jmh.annotations.BenchmarkMode;
import org.openjdk.jmh.annotations.Fork;
import org.openjdk.jmh.annotations.Measurement;
import org.openjdk.jmh.annotations.Mode;
import org.openjdk.jmh.annotations.OutputTimeUnit;
import org.openjdk.jmh.annotations.Scope;
import org.openjdk.jmh.annotations.State;
import org.openjdk.jmh.annotations.Warmup;
import org.openjdk.jmh.infra.Blackhole;

import java.util.concurrent.TimeUnit;

@Fork(5)
@Warmup(iterations = 10)
@Measurement(iterations = 10)
@OutputTimeUnit(TimeUnit.MILLISECONDS)
@BenchmarkMode({Mode.SingleShotTime})
@State(Scope.Benchmark)
public class ToolsPerfBenchmarkOnTop100Libs {
	private final JapicmpTool japicmp = new JapicmpTool();
	private final RevapiTool revapi = new RevapiTool();
	private final RoseauTool roseau = new RoseauTool();

	@Benchmark
	public void roseauJdtSources(SourcesLibrariesState state, Blackhole blackhole) {
		blackhole.consume(roseau.analyze(state.sourcesPath, state.sourcesPath));
	}

	@Benchmark
	public void roseauJar(JarLibrariesState state, Blackhole blackhole) {
		blackhole.consume(roseau.analyze(state.jarPath, state.jarPath));
	}

	@Benchmark
	public void japicmp(JarLibrariesState state, Blackhole blackhole) {
		blackhole.consume(japicmp.analyze(state.jarPath, state.jarPath));
	}

	@Benchmark
	public void revapi(JarLibrariesState state, Blackhole blackhole) {
		blackhole.consume(revapi.analyze(state.jarPath, state.jarPath));
	}
}
