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

    val queries = readQueries(type)
    for (query in queries) {
        val (docIds, features) = app.handle(query.text)

        logger.info { "Found ${docIds.size} documents for query: ${query.queryId} - ${query.text}. Stage: $type" }

        if (features != null && docIds.size != features.size) {
            logger.error { "Error: docIds and features have different sizes for query: ${query.queryId} - ${query.text}. Stage: $type" }
            continue
        }

        if (docIds.isEmpty()) {
            results.add(Result(query.queryId, "", emptyList()))
            continue
        }

        docIds.forEachIndexed { index, docId ->
            results.add(Result(query.queryId, docId, features?.get(index) ?: emptyList()))
        }
    }

    val resultsJson = Result.listToJson(results)
    File("qrel_${type}.json").writeText(resultsJson)
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

    fun handle(query: String): Pair<List<String>, MutableList<List<Float>>?> {
        try {
            val (topDocs, features) = searcher.searchDocuments(query)

            val docIds = topDocs.scoreDocs.map { scoreDoc ->
                val doc = storedFields.document(scoreDoc.doc)
                doc.getField("doc_id").stringValue()
            }.toList()

            return Pair(docIds, features)
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
