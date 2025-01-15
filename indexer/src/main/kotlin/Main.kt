import com.sksamuel.hoplite.ConfigLoader
import config.Config
import consumer.DocumentConsumer
import document.WikiDocument
import index.FullTextSearchIndexer
import index.Indexer
import index.VectorImageSearchIndexer
import index.VectorTextSearchIndexer
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import mu.KotlinLogging
import java.io.File


const val configPath = "config/config.yml"

private val logger = KotlinLogging.logger {}

fun main(args: Array<String>): Unit = runBlocking {
    logger.info { "Starting Indexer with args: $args" }

    val (serviceType, topic) = args

    val config = ConfigLoader().loadConfigOrThrow<Config>(configPath)

    val indexDirectory = File(config.indexDirectory)
    indexDirectory.mkdirs()

    val indexer =
    when (serviceType) {
        "vector-image" ->  VectorImageSearchIndexer(logger, indexDirectory)
        "vector-text" -> VectorTextSearchIndexer(logger, indexDirectory)
        "full-text" -> FullTextSearchIndexer(logger, indexDirectory)

        else -> throw IllegalArgumentException("Unknown service type: $serviceType")
    }

    val documentsChannel = Channel<List<WikiDocument>>()
    val documentConsumer = DocumentConsumer(logger, documentsChannel, config.documentConsumerConfig)

    coroutineScope {
        launch { documentConsumer.Consume(topic) }

        launch { documentIndexing(documentsChannel, indexer) }
    }.join()

    documentsChannel.close()
}

suspend fun documentIndexing(
    documentsChannel: Channel<List<WikiDocument>>,
    indexer: Indexer,
) {
    for (documents in documentsChannel) {
        logger.info { "Read from channel ${documents.size} documents." }
        try {
            indexer.updateIndex(documents)
        } catch (e: Exception) {
            logger.error { "Failed to update index. Error: ${e.message}" }
        }
    }
}
