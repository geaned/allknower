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
import vectorsearch.VectorSearcher


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
    val vectorTextSearcher = VectorSearcher(logger, config, config.vectorTextIndexDirectory)
    val vectorImageSearcher = VectorSearcher(logger, config, config.vectorImageIndexDirectory)

    val app = App(searcher, vectorTextSearcher, vectorImageSearcher)

    configureRouting(logger, app)
}

class App(
    private val searcher: Searcher,
    private val vectorTextSearcher: VectorSearcher,
    private val vectorImageSearcher: VectorSearcher,
) {
    fun handleFullTextSearch(query: String): List<ResultDocument> {
        val (topDocs, features) = searcher.searchDocuments(query)

        val storedFields = DirectoryReader.open(searcher.directory).storedFields()

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
                    metadataTitle = null,
                    metadataDescription = null,
                )
            )
        }

        return resultDocuments
    }

    fun handleVectorTextSearch(query: List<Float>): List<ResultDocument> {
        logger.info { "Received vector text search request." }

        val topDocs = vectorTextSearcher.search(query)

        logger.info { "Found ${topDocs.scoreDocs.size} documents at vector text index." }

        val storedFields = DirectoryReader.open(vectorTextSearcher.directory).storedFields()

        val resultDocuments = mutableListOf<ResultDocument>()
        topDocs.scoreDocs.forEach { scoreDoc ->
            val doc = storedFields.document(scoreDoc.doc)

            val docId = doc.getField("doc_id").stringValue()
            val pageUrl = doc.getField("page_url").stringValue()
            val title = doc.getField("title").stringValue()
            val content = doc.getField("content")?.stringValue()

            val embeddingSerialized = doc.getField("embedding_serialized").stringValue()
            val typeToken = object : TypeToken<List<Float>>() {}.type
            val embedding: List<Float> = Gson().fromJson(embeddingSerialized, typeToken)

            resultDocuments.add(
                ResultDocument(
                    docId = docId,
                    pageUrl = pageUrl,
                    title = title,
                    content = content,
                    isText = true,
                    features = listOf(scoreDoc.score),
                    embedding = embedding,
                    metadataTitle = null,
                    metadataDescription = null,
                )
            )
        }

        return resultDocuments
    }

    fun handleVectorImageSearch(query: List<Float>): List<ResultDocument> {
        logger.info { "Received vector image search request." }

        val topDocs = vectorImageSearcher.search(query)

        logger.info { "Found ${topDocs.scoreDocs.size} documents at vector image index." }

        val storedFields = DirectoryReader.open(vectorImageSearcher.directory).storedFields()

        val resultDocuments = mutableListOf<ResultDocument>()
        topDocs.scoreDocs.forEach { scoreDoc ->
            val doc = storedFields.document(scoreDoc.doc)

            val docId = doc.getField("doc_id").stringValue()
            val pageUrl = doc.getField("page_url").stringValue()
            val title = doc.getField("title").stringValue()
            val content = doc.getField("content")?.stringValue()
            val metadataTitle = doc.getField("metadata_title")?.stringValue()
            val metadataDescription = doc.getField("metadata_description")?.stringValue()

            val embeddingSerialized = doc.getField("embedding_serialized").stringValue()
            val typeToken = object : TypeToken<List<Float>>() {}.type
            val embedding: List<Float> = Gson().fromJson(embeddingSerialized, typeToken)

            resultDocuments.add(
                ResultDocument(
                    docId = docId,
                    pageUrl = pageUrl,
                    title = title,
                    content = content,
                    isText = false,
                    features = listOf(scoreDoc.score),
                    embedding = embedding,
                    metadataTitle = metadataTitle,
                    metadataDescription = metadataDescription,
                )
            )
        }

        return resultDocuments
    }

    private fun printResults(topDocs: TopDocs) {
        println(
            PrintColorizer().ColorizeForeground(
                "TopDocs:",
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
    @SerializedName("metadata_title") val metadataTitle: String?,
    @SerializedName("metadata_description") val metadataDescription: String?
)
