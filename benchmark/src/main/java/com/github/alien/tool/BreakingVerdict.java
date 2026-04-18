package com.github.alien.tool;

public record BreakingVerdict(boolean isBinaryBreaking, boolean isSourceBreaking, int inputTokens, int outputTokens, double requestTime, String message) {}
