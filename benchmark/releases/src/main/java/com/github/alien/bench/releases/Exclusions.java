package com.github.alien.bench.releases;

import io.github.alien.roseau.api.model.API;
import io.github.alien.roseau.api.model.Annotation;
import io.github.alien.roseau.api.model.Symbol;
import io.github.alien.roseau.api.model.TypeDecl;
import io.github.alien.roseau.api.model.TypeMemberDecl;
import io.github.alien.roseau.options.RoseauOptions;

import java.util.List;
import java.util.Optional;
import java.util.regex.Pattern;

/**
 * Decides whether a symbol falls outside a library's public API, following the exclusion rules
 * declared in {@code walk.yaml}.
 * <p>
 * This is a copy of the matcher {@code roseau-git}'s {@code CsvReporter} applies during the
 * commit-level walk. The release-level analysis must classify symbols exactly the same way, or the
 * two sides of the comparison would not be counting the same population.
 */
record Exclusions(List<Pattern> namePatterns, List<RoseauOptions.AnnotationExclusion> annotations) {
	static Exclusions of(RoseauOptions.Exclude exclusions) {
		return new Exclusions(exclusions.names().stream().map(Pattern::compile).toList(),
			exclusions.annotations());
	}

	Optional<String> matchedRule(Symbol symbol, API api) {
		if (symbol == null) {
			return Optional.empty();
		}
		Optional<String> byName = namePatterns.stream()
			.filter(p -> p.matcher(symbol.getQualifiedName()).matches())
			.findFirst()
			.map(p -> "name:" + p.pattern());
		if (byName.isPresent()) {
			return byName;
		}
		return switch (symbol) {
			case TypeDecl type -> matchedAnnotation(type)
				.or(() -> type.getEnclosingType()
					.flatMap(api.analyzer().resolver()::resolve)
					.flatMap(enclosing -> matchedRule(enclosing, api)));
			case TypeMemberDecl member -> api.analyzer().resolver().resolve(member.getContainingType())
				.flatMap(type -> matchedRule(type, api))
				.or(() -> matchedAnnotation(member));
		};
	}

	private Optional<String> matchedAnnotation(Symbol symbol) {
		return annotations.stream()
			.filter(excl -> symbol.getAnnotations().stream().anyMatch(ann -> matches(ann, excl)))
			.findFirst()
			.map(excl -> "annotation:" + excl.name());
	}

	private static boolean matches(Annotation annotation, RoseauOptions.AnnotationExclusion exclusion) {
		String actual = annotation.actualAnnotation().getQualifiedName();
		String expected = exclusion.name();
		if (expected.contains(".")) {
			return actual.equals(expected) && annotation.hasValues(exclusion.args());
		}
		String simpleName = actual.contains(".") ? actual.substring(actual.lastIndexOf('.') + 1) : actual;
		return simpleName.equals(expected) && annotation.hasValues(exclusion.args());
	}
}
