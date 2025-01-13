package org.example

import color.Color
import color.PrintColorizer
import com.sksamuel.hoplite.ConfigLoader
import config.Config
import query.Query
import search.Searcher
import java.io.File


const val configPath = "config/config.yml"

fun main() {
    val config = ConfigLoader().loadConfigOrThrow<Config>(configPath)

    val indexDirectory = File(config.indexDirectory)

    val searcher = Searcher(fileIndex = indexDirectory)
    val app = App(searcher)


}

fun runExperiment(app: App, type: String) {
//    val result = mutableMapOf<Int, >()

    val queries = readQueries(type)
    for (query in queries) {
        app.handle(query.text)
    }


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
    val searcher: Searcher,
) {
    fun handle(query: String) {
        val (topDocs, _) = searcher.searchDocuments(query)

        println(
            PrintColorizer().ColorizeForeground(
                "L1 TopDocs:",
                Color.YELLOW
            )
        )
        searcher.printResults(topDocs)
    }
}
