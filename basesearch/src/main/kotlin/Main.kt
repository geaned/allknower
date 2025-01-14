package org.example

import color.Color
import color.PrintColorizer
import com.sksamuel.hoplite.ConfigLoader
import config.Config
import org.apache.lucene.index.DirectoryReader
import org.apache.lucene.search.TopDocs
import query.Query
import query.Result
import search.Searcher
import java.io.File
import mu.KotlinLogging
import search.SearchResult
import java.time.Duration
import java.time.LocalDateTime


const val configPath = "config/config.yml"

private val logger = KotlinLogging.logger {}

// TODO: for debug query = "Aérospatiale"
// TODO: одинаковый analyzer

fun main() {
    val config = ConfigLoader().loadConfigOrThrow<Config>(configPath)

    val searcher = Searcher(logger, config)
    val app = App(searcher)

    for (type in listOf("test", "validation")) {
        logger.info { "Running experiment for $type queries" }
        runExperiment(app, type)
    }
}

fun runExperiment(app: App, type: String) {
    val results = mutableListOf<Result>()

    val searchTimings = mutableListOf<Float>()
    val l0DiffTimings = mutableListOf<Float>()
    val l1DiffTimings = mutableListOf<Float>()

    val queries = readQueries(type)
    for (query in queries) {
        val start = LocalDateTime.now()

        val (docIds, searchResult) = app.handle(query.text)

        logger.info { "Found ${docIds.size} documents for query: ${query.queryId} - ${query.text}. Stage: $type" }

        if (searchResult == null) {
            logger.error { "searchResult is null: ${query.queryId} - ${query.text}. Stage: $type" }
        }

        if (searchResult != null) {
            if (searchResult.features != null && docIds.size != searchResult.features.size) {
                logger.error { "Error: docIds and features have different sizes for query: ${query.queryId} - ${query.text}. Stage: $type" }
                continue
            }
        }

        if (docIds.isEmpty()) {
            results.add(Result(query.queryId, "", emptyList()))
            continue
        }

        docIds.forEachIndexed { index, docId ->
            if (searchResult != null) {
                results.add(Result(query.queryId, docId, searchResult.features?.get(index) ?: emptyList()))
            }
        }

        val end = LocalDateTime.now()
        val diff = Duration.between(start, end)

        searchTimings.add(diff.toMillis().toFloat())
        if (searchResult != null) {
            l0DiffTimings.add(searchResult.l0DiffTime.toMillis().toFloat())
        }
        if (searchResult != null) {
            l1DiffTimings.add(searchResult.l1DiffTime.toMillis().toFloat())
        }

        println()
        logger.info { "Current timings for query: $query: ${diff.toMillis()}" }

        logger.info { "STATS L0 (max, min, mean, median): ${calculateStatistics(l0DiffTimings)}" }
        logger.info { "STATS L1 (max, min, mean, median): ${calculateStatistics(l0DiffTimings)}" }
        logger.info { "STATS BASE SEARCH (max, min, mean, median): ${calculateStatistics(l0DiffTimings)}" }
    }

    val resultsJson = Result.listToJson(results)
    File("qrel_${type}.json").writeText(resultsJson)

    logger.info { "Successfully write to file qrel_${type}.json" }
}

fun readQueries(type: String): List<Query> {
    var query: List<Query> = mutableListOf()
    when (type) {
        "training" -> query = Query.listFromJson(File("src/main/resources/wikir_queries_training.json").readText())
        "validation" -> query =  Query.listFromJson(File("src/main/resources/wikir_queries_training.json").readText())
        "test" -> query =  Query.listFromJson(File("src/main/resources/wikir_queries_training.json").readText())
    }

    return query
}

class App(
    private val searcher: Searcher,
) {
    private val storedFields = DirectoryReader.open(searcher.directory).storedFields()

    fun handle(query: String): Pair<List<String>, SearchResult?> {
        try {
            val searchResult = searcher.searchDocuments(query)

            val docIds = searchResult.topDocs.scoreDocs.map { scoreDoc ->
                val doc = storedFields.document(scoreDoc.doc)
                doc.getField("doc_id").stringValue()
            }.toList()

            return Pair(docIds, searchResult)
        } catch (e: Exception) {
            logger.error { "Failed to search documents for query: $query" }
            e.printStackTrace()
            return Pair(emptyList(), null)
        }
    }

    private fun printResults(topDocs: TopDocs) {
        println(
            PrintColorizer().ColorizeForeground(
                "L1 TopDocs:",
                Color.YELLOW
            )
        )
        searcher.printResults(topDocs)
    }
}

fun calculateStatistics(values: List<Float>): List<Float> {
    val maxValue: Float = values.maxOrNull() ?: Float.NEGATIVE_INFINITY
    val minValue = values.minOrNull() ?: Float.POSITIVE_INFINITY
    val meanValue = values.average().toFloat()
    val medianValue = median(values)

    return listOf(maxValue, minValue, meanValue, medianValue)
}

private fun median(values: List<Float>): Float {
    val sortedValues = values.sorted()
    val size = sortedValues.size
    return if (size % 2 == 0) {
        (sortedValues[size / 2 - 1] + sortedValues[size / 2]) / 2
    } else {
        sortedValues[size / 2]
    }
}
