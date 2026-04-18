package com.github.alien.bench.performance.state;

import org.openjdk.jmh.annotations.Param;
import org.openjdk.jmh.annotations.Scope;
import org.openjdk.jmh.annotations.State;

import java.nio.file.Path;

@State(Scope.Benchmark)
public abstract class LibrariesState {
	protected Path librariesPath = Path.of("../libraries-dataset/2_libs_download/output/libs");

	@Param({ "junit-4.13.2", "slf4j-api-2.0.16", "guava-33.4.0-jre", "mockito-core-5.15.2", "jackson-databind-2.18.2",
		"commons-lang3-3.17.0", "logback-classic-1.5.16", "commons-io-2.18.0", "lombok-1.18.36", "gson-2.12.1",
		"javax.servlet-api-4.0.1", "log4j-1.2.17", "assertj-core-3.27.3", "slf4j-reload4j-2.0.16",
		"junit-jupiter-api-5.11.4", "junit-jupiter-engine-5.11.4", "slf4j-simple-2.0.16", "jackson-core-2.18.2",
		"spring-context-6.2.3", "mockito-all-1.10.19", "httpclient-4.5.14", "jsr305-3.0.2", "jackson-annotations-2.18.2",
		"commons-codec-1.18.0", "commons-lang-2.6", "servlet-api-2.5", "commons-logging-1.3.5", "log4j-core-2.24.3",
		"testng-7.11.0", "spring-boot-configuration-processor-3.4.2", "spring-test-6.2.3", "junit-jupiter-5.11.4",
		"log4j-api-2.24.3", "joda-time-2.13.1", "jcl-over-slf4j-2.0.16", "spring-web-6.2.3",
		"spring-boot-autoconfigure-3.4.2", "h2-2.3.232", "spring-core-6.2.3", "maven-plugin-api-3.9.9",
		"log4j-slf4j-impl-2.24.3", "mysql-connector-j-9.6.0", "hamcrest-all-1.3", "annotations-26.0.2",
		"spring-beans-6.2.3", "javax.inject-1", "org.osgi.core-6.0.0", "javax.annotation-api-1.3.2", "fastjson-2.0.55",
		"commons-collections-3.2.2", "validation-api-2.0.1.Final", "junit-jupiter-params-5.11.4",
		"jackson-datatype-jsr310-2.18.2", "hamcrest-library-3.0", "jaxb-api-2.3.1", "logback-core-1.5.16", "json-20250107",
		"spring-webmvc-6.2.3", "commons-beanutils-1.10.1", "protobuf-java-4.29.3", "retrofit-2.11.0",
		"maven-plugin-annotations-3.15.1" })
	protected String library;
}
