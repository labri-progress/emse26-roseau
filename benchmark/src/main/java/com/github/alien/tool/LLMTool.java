package com.github.alien.tool;

import java.util.regex.Pattern;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Comparator;
import java.util.Locale;

public abstract class LLMTool extends Tool{

	private static final Pattern SOURCE_INCOMPATIBLE = Pattern.compile("(?im)^\\s*Source incompatible:\\s*(YES|NO)\\s*$");
	private static final Pattern BINARY_INCOMPATIBLE = Pattern.compile("(?im)^\\s*Binary incompatible:\\s*(YES|NO)\\s*$");
    private static final Path SYSTEM_PROMPT = Path.of("src/main/resources/prompt_system.txt");
	private static final Path USER_PROMPT = Path.of("src/main/resources/prompt_user.txt");
	protected static final double TEMPERATURE = 0.3;
	protected static final double TOP_P = 1.0;
	protected static final int MAX_TOKENS = 5120;
	protected static final int MAX_TOKENS_THINKING_MODE = 4096;
	protected static final int MAX_PROMPT_RETRIES = 10;

	protected int inputTokens = 0; 
    protected int outputTokens = 0;
    protected double requestTime = 0;

	protected abstract String askModel(String systemPrompt, String userPrompt);

    @Override
	public BreakingVerdict analyze(Path v1, Path v2) {
		var v1Source = extractSourceCode(v1);
		var v2Source = extractSourceCode(v2);
		var systemPrompt = buildSystemPrompt(SYSTEM_PROMPT);
		var userPrompt = buildUserPrompt(USER_PROMPT, v1Source, v2Source);
		var answer = askModel(systemPrompt, userPrompt);

		return parseVerdict(answer);
	}

	protected static String buildSystemPrompt(Path prompt) {
		try {
			return Files.readString(prompt, StandardCharsets.UTF_8);
		} catch (IOException e) {
			e.printStackTrace();
			return "<NO PROMPT>";
		}
	}

	protected String buildUserPrompt(Path prompt, String v1Source, String v2Source) {
		try {
			String promptTemplate = Files.readString(prompt, StandardCharsets.UTF_8);
			return promptTemplate.formatted(v1Source, v2Source);
		} catch (IOException e) {
			e.printStackTrace();
			return "<NO PROMPT>";
		}
	}
	
	protected BreakingVerdict parseVerdict(String rawAnswer) {
		var sourceIncompatible = parseFlag(SOURCE_INCOMPATIBLE, rawAnswer, "Source incompatible");
		var binaryIncompatible = parseFlag(BINARY_INCOMPATIBLE, rawAnswer, "Binary incompatible");

		return new BreakingVerdict(
			binaryIncompatible,
			sourceIncompatible,
			inputTokens,
			outputTokens,
			requestTime,
			"raw_response=" + rawAnswer.replace('\n', ' ').trim()
		);
	}

	private static boolean parseFlag(Pattern pattern, String text, String fieldName) {
		var matcher = pattern.matcher(text);
		if (!matcher.find()) {
			throw new IllegalArgumentException("Missing field in model output: " + fieldName + ". Output: " + text);
		}
		return "YES".equals(matcher.group(1).toUpperCase(Locale.ROOT));
	}

    protected static String extractSourceCode(Path sourceDirectory) {
		try (var files = Files.walk(sourceDirectory)) {
			var javaFiles = files
				.filter(path -> Files.isRegularFile(path) && path.toString().endsWith(".java"))
				.sorted(Comparator.comparing(Path::toString))
				.toList();

			if (javaFiles.isEmpty()) {
				return "<NO CODE>";
			}

			var source = new StringBuilder();
			for (var javaFile : javaFiles) {
				source.append("// File: ")
					.append(sourceDirectory.relativize(javaFile))
					.append("\n");
				source.append(Files.readString(javaFile, StandardCharsets.UTF_8));
				source.append("\n\n");
			}

			return source.toString();
		} catch (IOException e) {
			e.printStackTrace();
			return "<NO CODE>";
		}
	}
}
