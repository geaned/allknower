package com.example

import com.google.gson.annotations.SerializedName
import io.ktor.http.*
import io.ktor.server.application.*
import io.ktor.server.request.*
import io.ktor.server.response.*
import io.ktor.server.routing.*
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import mu.KLogger
import java.time.Duration
import java.time.LocalDateTime

@Serializable
data class SearchRequest(
    val query: String
)

@Serializable
data class VectorSearchRequest(
    val embedding: List<Float>,
    @SerializedName("is_text") val isText: Boolean
)

@Serializable
data class SearchResponse(
    val documents: List<ResultDocument>,
    val latency: Long
)

fun Application.configureRouting(logger: KLogger, app: App) {
    routing {
        get("/") {
            call.respondText("Hello World!")
        }

        post("/basesearch/search") {
            val start = LocalDateTime.now()
            try {
                val req = call.receive<SearchRequest>()
                val requestId = call.request.headers["X-Request-Id"].toString()

                logger.info { "Received request with X-Request-Id: $requestId: ${req.query}" }

                val resultDocuments = app.handleFullTextSearch(query = req.query)

                val response = SearchResponse(
                    documents = resultDocuments,
                    latency = Duration.between(start, LocalDateTime.now()).toMillis(),
                )

                call.response.headers.append("X-Request-Id", requestId)
                call.respond(HttpStatusCode.OK, Json.encodeToString(response))
            } catch (e: Exception) {
                call.response.headers.append("X-Request-Id", call.request.headers["X-Request-Id"].toString())
                call.respond(
                    HttpStatusCode.InternalServerError,
                    "Error processing request: ${e.message}. Latency: ${Duration.between(start, LocalDateTime.now())}",
                )
            }
        }

        post("vectorsearch/search") {
            val start = LocalDateTime.now()
            try {
                val req = call.receive<VectorSearchRequest>()
                val requestId = call.request.headers["X-Request-Id"].toString()

                logger.info { "Received request with X-Request-Id: $requestId: ${req.embedding}" }

                val resultDocuments = if (req.isText) {
                    app.handleVectorTextSearch(query = req.embedding)
                } else {
                    app.handleVectorImageSearch(query = req.embedding)
                }

                val response = SearchResponse(
                    documents = resultDocuments,
                    latency = Duration.between(start, LocalDateTime.now()).toMillis(),
                )

                call.response.headers.append("X-Request-Id", requestId)
                call.respond(HttpStatusCode.OK, Json.encodeToString(response))
            } catch (e: Exception) {
                logger.error { "Error processing request: ${e.message}." }
                call.response.headers.append("X-Request-Id", call.request.headers["X-Request-Id"].toString())
                call.respond(
                    HttpStatusCode.InternalServerError,
                    "Error processing request: ${e.message}. Latency: ${Duration.between(start, LocalDateTime.now())}",
                )
            }
        }
    }
}
