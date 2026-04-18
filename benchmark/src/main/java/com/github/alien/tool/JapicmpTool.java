package com.github.alien.tool;

import japicmp.cmp.JApiCmpArchive;
import japicmp.cmp.JarArchiveComparator;
import japicmp.cmp.JarArchiveComparatorOptions;
import japicmp.config.Options;
import japicmp.model.AccessModifier;
import japicmp.model.JApiAnnotation;
import japicmp.model.JApiClass;
import japicmp.model.JApiCompatibilityChange;
import japicmp.model.JApiConstructor;
import japicmp.model.JApiField;
import japicmp.model.JApiImplementedInterface;
import japicmp.model.JApiMethod;
import japicmp.model.JApiSuperclass;
import japicmp.output.Filter;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.stream.Collectors;

public class JapicmpTool extends Tool {
	@Override
	public String getName() {
		return "japicmp";
	}

	@Override
	public BreakingVerdict analyze(Path v1, Path v2) {
		Options opts = Options.newDefault();
		opts.setAccessModifier(AccessModifier.PACKAGE_PROTECTED);
		opts.setOutputOnlyModifications(true);
		opts.setIgnoreMissingClasses(true);
		opts.setIncludeSynthetic(true);
		var comparatorOptions = JarArchiveComparatorOptions.of(opts);
		var jarArchiveComparator = new JarArchiveComparator(comparatorOptions);

		var v1Archive = new JApiCmpArchive(v1.toFile(), "v1");
		var v2Archive = new JApiCmpArchive(v2.toFile(), "v2");

		List<JApiClass> jApiClasses = jarArchiveComparator.compare(v1Archive, v2Archive);
		List<JApiCompatibilityChange> bcs = new ArrayList<>();
		Filter.filter(jApiClasses, new Filter.FilterVisitor() {
			@Override
			public void visit(Iterator<JApiClass> iterator, JApiClass jApiClass) {
				bcs.addAll(jApiClass.getCompatibilityChanges());
			}

			@Override
			public void visit(Iterator<JApiMethod> iterator, JApiMethod jApiMethod) {
				bcs.addAll(jApiMethod.getCompatibilityChanges());
			}

			@Override
			public void visit(Iterator<JApiConstructor> iterator, JApiConstructor jApiConstructor) {
				bcs.addAll(jApiConstructor.getCompatibilityChanges());
			}

			@Override
			public void visit(Iterator<JApiImplementedInterface> iterator,
			                  JApiImplementedInterface jApiImplementedInterface) {
				bcs.addAll(jApiImplementedInterface.getCompatibilityChanges());
			}

			@Override
			public void visit(Iterator<JApiField> iterator, JApiField jApiField) {
				bcs.addAll(jApiField.getCompatibilityChanges());
			}

			@Override
			public void visit(Iterator<JApiAnnotation> iterator, JApiAnnotation jApiAnnotation) {
				bcs.addAll(jApiAnnotation.getCompatibilityChanges());
			}

			@Override
			public void visit(JApiSuperclass jApiSuperclass) {
				bcs.addAll(jApiSuperclass.getCompatibilityChanges());
			}
		});

		var isBinaryCompatible = bcs.stream().allMatch(JApiCompatibilityChange::isBinaryCompatible);
		var isSourceCompatible = bcs.stream().allMatch(JApiCompatibilityChange::isSourceCompatible);

		return new BreakingVerdict(!isBinaryCompatible, !isSourceCompatible, 0, 0, 0,
			bcs.stream().map(JApiCompatibilityChange::toString).collect(Collectors.joining(", ")));
	}
}
