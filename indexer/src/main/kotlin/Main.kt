import com.sksamuel.hoplite.ConfigLoader
import config.Config
import consumer.DocumentConsumer
import document.WikiDocument
import index.Indexer
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import mu.KotlinLogging
import java.io.File


const val configPath = "config/config.yml"

private val logger = KotlinLogging.logger {}

fun main(): Unit = runBlocking {
    logger.info { "Starting Indexer." }

    val config = ConfigLoader().loadConfigOrThrow<Config>(configPath)

    val indexDirectory = File(config.indexDirectory)
    indexDirectory.mkdirs()

    val documentsChannel = Channel<List<WikiDocument>>()
    val indexer = Indexer(logger, indexDirectory)
    val documentConsumer = DocumentConsumer(logger, documentsChannel, config.documentConsumerConfig)

    coroutineScope {
        launch { documentConsumer.Consume(config.documentTopic) }

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

        indexer.updateIndex(documents)
    }
}
