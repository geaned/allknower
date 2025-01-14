package org.example

import color.Color
import color.PrintColorizer
import com.sksamuel.hoplite.ConfigLoader
import config.Config
import search.Searcher
import java.io.File


const val configPath = "config/config.yml"

suspend fun main() {
    val config = ConfigLoader().loadConfigOrThrow<Config>(configPath)

    val indexDirectory = File(config.indexDirectory)

    val searcher = Searcher(fileIndex = indexDirectory)

    val query = "Alabama"

    val topDocs = searcher.SearchDocuments(query)

    println(
        PrintColorizer().ColorizeForeground(
            "L1 TopDocs:",
            Color.YELLOW
        )
    )
    searcher.PrintResults(topDocs)
}
