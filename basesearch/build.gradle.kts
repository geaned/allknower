import org.jetbrains.kotlin.gradle.tasks.KotlinCompile

plugins {
    kotlin("jvm") version "1.8.0"
    application
}

group = "org.example"
version = "1.0-SNAPSHOT"

repositories {
    mavenCentral()
}

dependencies {
    testImplementation(kotlin("test"))

    // https://mavenlibs.com/maven/dependency/org.apache.lucene/lucene-core
    implementation("org.apache.lucene:lucene-core:9.7.0")
    // https://mavenlibs.com/maven/dependency/org.apache.lucene/lucene-analyzers-common
    implementation("org.apache.lucene:lucene-analyzers-common:8.11.2")
    // https://mavenlibs.com/maven/dependency/org.apache.lucene/lucene-queryparser
    implementation("org.apache.lucene:lucene-queryparser:9.7.0")
    // https://mavenlibs.com/maven/dependency/org.apache.lucene/lucene-queries
    implementation("org.apache.lucene:lucene-queries:9.7.0")
    // https://mavenlibs.com/maven/dependency/org.apache.lucene/lucene-highlighter
    implementation("org.apache.lucene:lucene-highlighter:9.7.0")

    implementation("com.google.code.gson:gson:2.10.1")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.7.3")

    // https://mavenlibs.com/maven/dependency/org.apache.kafka/kafka-clients
    implementation("org.apache.kafka:kafka-clients:3.7.1")

    // https://mvnrepository.com/artifact/org.slf4j/slf4j-api
    implementation("org.slf4j:slf4j-api:2.0.16")
    implementation("org.slf4j:slf4j-simple:2.0.16")

    implementation("aws.sdk.kotlin:s3:1.0.0")

    // https://mavenlibs.com/maven/dependency/com.sksamuel.hoplite/hoplite-core
    implementation("com.sksamuel.hoplite:hoplite-core:2.8.0")
    // https://mavenlibs.com/maven/dependency/com.sksamuel.hoplite/hoplite-yaml
    implementation("com.sksamuel.hoplite:hoplite-yaml:2.8.0")

    // https://mvnrepository.com/artifact/io.github.microutils/kotlin-logging-jvm
    implementation("io.github.microutils:kotlin-logging-jvm:3.0.5")
    // https://mvnrepository.com/artifact/ch.qos.logback/logback-classic
    implementation("ch.qos.logback:logback-classic:1.5.15")
}

tasks.test {
    useJUnitPlatform()
}

kotlin {
    jvmToolchain(8)
}

application {
    mainClass.set("org.example.MainKt")
}
