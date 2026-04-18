package com.github.alien.compiler;

import javax.tools.Diagnostic;
import javax.tools.DiagnosticCollector;
import javax.tools.ToolProvider;
import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.jar.JarEntry;
import java.util.jar.JarOutputStream;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

public class JavaCompiler {
	private static final int JAVA_VERSION = 25;
	private static final javax.tools.JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
	private static final Pattern LINKER_ERRORS = Pattern.compile("^.*java\\.lang\\.\\w+Error:.*");

	public static void packageSources(Path sourcesPath, Path classesPath, Path jarPath, List<Path> classpath,
	                                  boolean throwOnError) {
		try {
			Files.createDirectories(classesPath);
			compileSources(sourcesPath, classesPath, classpath, throwOnError);
			packageJar(classesPath, jarPath);
		} catch (IOException e) {
			throw new RuntimeException("Error while packaging sources %s".formatted(sourcesPath), e);
		}
	}

	public static String compileSources(Path sourcesPath, Path classesPath, List<Path> classpath, boolean throwOnError) {
		var diagnostics = new DiagnosticCollector<>();
		try (var fileManager = compiler.getStandardFileManager(diagnostics, null, null)) {
			var options = new ArrayList<String>();
			options.add("-source");
			options.add(String.valueOf(JAVA_VERSION));
			options.add("-d");
			options.add(classesPath.toString());
			if (!classpath.isEmpty()) {
				options.add("-cp");
				options.add(classpath.stream().map(Path::toString).collect(Collectors.joining(File.pathSeparator)));
			}

			var sourceFiles = Files.list(sourcesPath)
				.filter(p -> p.toString().endsWith(".java"))
				.map(Path::toFile)
				.toList();
			var compilationUnits = fileManager.getJavaFileObjectsFromFiles(sourceFiles);
			var compile = compiler.getTask(null, fileManager, diagnostics, options, null, compilationUnits);
			compile.call();
		} catch (Exception e) {
			throw new RuntimeException("Error while compiling sources", e);
		}

		var errors = diagnostics.getDiagnostics().stream()
			.filter(diagnostic -> diagnostic.getKind() == Diagnostic.Kind.ERROR)
			.toList();

		if (!errors.isEmpty()) {
			var msg = errors.stream()
				.map(Diagnostic::getCode)
				.collect(Collectors.joining(", "));
			if (throwOnError) {
				throw new RuntimeException("Error while compiling sources: " + msg);
			}
			return msg;
		} else {
			return null;
		}
	}

	public static String linkAgainstJar(Path clientJar, Path libraryJar, String mainClass) {
		var classpath = String.join(File.pathSeparator, clientJar.toString(), libraryJar.toString());
		var pb = new ProcessBuilder("java", "-cp", classpath, mainClass);
		pb.redirectErrorStream(true);

		try {
			var process = pb.start();
			int exitCode = process.waitFor();
			if (exitCode != 0) {
				var out = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
				var firstLine = out.lines()
					.map(String::trim)
					.filter(line -> !line.isEmpty())
					.findFirst()
					.orElse("No message");
				// Main execution throws an exception, not a linker problem per se, but a behavioral change
				if (firstLine.startsWith("Exception in thread \"main\"") && !LINKER_ERRORS.matcher(firstLine).matches()) {
					throw new RuntimeException("Suspicious exception raised when executing main(): " + firstLine);
				}
				// UnsatisfiedLinkError are raised at run time for native methods for which the native implementation cannot be found
				// This is not a linking problem per se
				if (firstLine.startsWith("Exception in thread \"main\" java.lang.UnsatisfiedLinkError:")) {
					System.err.println("Couldn't find native binding; expected");
					return null;
				}
				// The Java launcher often prints a generic first line and the real linker cause on a "Caused by" line.
				if (firstLine.startsWith("Error: Unable to initialize main class")) {
					var cause = out.lines()
						.map(String::trim)
						.filter(line -> line.startsWith("Caused by: "))
						.findFirst()
						.orElse(null);
					if (cause != null) {
						return cause;
					}
				}
				return firstLine;
			}
			return null;
		} catch (InterruptedException | IOException e) {
			throw new RuntimeException("Error while linking client", e);
		}
	}

	private static void packageJar(Path classesPath, Path jarPath) throws IOException {
		try (var jos = new JarOutputStream(Files.newOutputStream(jarPath))) {
			var classFiles = Files.walk(classesPath)
				.filter(p -> p.toString().endsWith(".class"))
				.toList();

			for (var classFile : classFiles) {
				var entryName = classesPath.relativize(classFile).toString().replace(File.separatorChar, '/');
				var entry = new JarEntry(entryName);
				jos.putNextEntry(entry);
				Files.copy(classFile, jos);
				jos.closeEntry();
			}
		}
	}

	public static void ensureJavaVersion(int version) {
		var pb = new ProcessBuilder("javac", "-version");
		pb.redirectErrorStream(true);

		try {
			var process = pb.start();
			int exitCode = process.waitFor();
			if (exitCode != 0) {
				throw new IllegalStateException("Couldn't run javac -version");
			} else {
				var out = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
				if (!out.contains("javac " + version)) {
					throw new IllegalStateException("Expected Java version " + version + " but got " + out);
				}
			}
		} catch (InterruptedException | IOException e) {
			throw new IllegalStateException(e);
		}
	}
}
