package com.example

import color.Color
import color.PrintColorizer
import com.google.gson.Gson
import com.google.gson.annotations.SerializedName
import com.google.gson.reflect.TypeToken
import com.sksamuel.hoplite.ConfigLoader
import config.Config
import io.ktor.serialization.kotlinx.json.*
import io.ktor.server.application.*
import io.ktor.server.plugins.contentnegotiation.*
import kotlinx.serialization.Serializable
import org.apache.lucene.index.DirectoryReader
import org.apache.lucene.search.TopDocs
import search.Searcher


private val logger = mu.KotlinLogging.logger {}

fun main(args: Array<String>) {
    io.ktor.server.netty.EngineMain.main(args)
}

fun Application.module() {
    install(ContentNegotiation) {
        json()
    }

    val config = ConfigLoader().loadConfigOrThrow<Config>("src/main/resources/config.yml")

    val searcher = Searcher(logger, config)
    val app = App(searcher)

    configureRouting(logger, app)
}

class App(
    private val searcher: Searcher,
) {
    private val storedFields = DirectoryReader.open(searcher.directory).storedFields()

    fun handle(query: String): List<ResultDocument> {
        val (topDocs, features) = searcher.searchDocuments(query)

        val resultDocuments = mutableListOf<ResultDocument>()
        topDocs.scoreDocs.forEachIndexed { index, scoreDoc ->
            val doc = storedFields.document(scoreDoc.doc)

            val docId = doc.getField("doc_id").stringValue()
            val pageUrl = doc.getField("page_url").stringValue()
            val title = doc.getField("title").stringValue()
            val content = doc.getField("content")?.stringValue()

            val embeddingSerialized = doc.getField("embedding")?.stringValue()
            var embedding = emptyList<Float>()
            if (embeddingSerialized != null) {
                val typeToken = object : TypeToken<List<Float>>() {}.type
                val embeddingDeserialized: List<Float> = Gson().fromJson(embeddingSerialized, typeToken)
                embedding = embeddingDeserialized
            }

            val resultFeatures = features?.get(index) ?: emptyList<Float>()

            resultDocuments.add(
                ResultDocument(
                    docId = docId,
                    pageUrl = pageUrl,
                    title = title,
                    content = content,
                    isText = true,
                    features = resultFeatures,
                    embedding = embedding,
                )
            )
        }

        return resultDocuments
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

@Serializable
data class ResultDocument(
    @SerializedName("doc_id") val docId: String,
    @SerializedName("page_url") val pageUrl: String,
    @SerializedName("title") val title: String,
    @SerializedName("content") val content: String?,
    @SerializedName("is_text") val isText: Boolean,
    @SerializedName("features") val features: List<Float>,
    @SerializedName("embedding") val embedding: List<Float>,
)
