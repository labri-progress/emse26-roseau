package com.github.alien.tool;

import java.nio.file.Path;

import io.github.cdimascio.dotenv.Dotenv;

public abstract class Tool {
	protected static Dotenv dotenv;
	private static final String ENV_VARS_FILE = ".env";

	static {
		try {
			dotenv = Dotenv.configure().filename(ENV_VARS_FILE).ignoreIfMissing().load();
			dotenv.entries().forEach(entry -> System.setProperty(entry.getKey(), entry.getValue()));
		} catch (Exception e) {
			throw new RuntimeException("Unable to load environment variables from " + ENV_VARS_FILE, e);
		}
	}

	public abstract String getName();
	public abstract BreakingVerdict analyze(Path v1, Path v2);
}
