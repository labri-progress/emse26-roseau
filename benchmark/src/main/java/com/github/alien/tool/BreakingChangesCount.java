package com.github.alien.tool;

import java.util.Map;

public record BreakingChangesCount(String name, Map<String, BreakingVerdict> counts) {}
