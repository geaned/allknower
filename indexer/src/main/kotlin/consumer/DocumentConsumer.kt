package consumer

import com.sksamuel.hoplite.decoder.duration
import config.DocumentConsumerConfig
import document.WikiDocument
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.delay
import mu.KLogger
import org.apache.kafka.clients.consumer.*
import org.apache.kafka.common.serialization.StringDeserializer
import java.time.Duration
import java.time.Instant
import java.util.*
import kotlin.time.toJavaDuration


class DocumentConsumer(
    val logger: KLogger,
    val documentChannel: Channel<List<WikiDocument>>,

    val cfg: DocumentConsumerConfig,
) {
    private val consumer = createConsumer(cfg.bootstrapServers, cfg.groupId)
    private val documentsToIndex = mutableListOf<WikiDocument>()
    private var lastTimeCommit = Instant.now()


    suspend fun Consume(topic: String) {
        consumer.subscribe(listOf(topic))

        while (true) {
            val messages: ConsumerRecords<String, String> = consumer.poll(Duration.ofMillis(cfg.pollDurationMillis))

            for (message: ConsumerRecord<String, String> in messages) {
                val document = WikiDocument.fromJson(message.value())
                if (!document.redirect) {
                    documentsToIndex.add(document)
                }
            }

            val duration = Duration.between(lastTimeCommit, Instant.now())
            if ((documentsToIndex.count() >= cfg.maxDocumentBatch) || (duration > cfg.batchDurationSeconds.duration().toJavaDuration())) {
                if (documentsToIndex.isEmpty()) {
                    logger.warn { "Empty list of documents for indexing" }
                    continue
                }

                documentChannel.send(documentsToIndex.toMutableList())

                logger.info { "Sending ${documentsToIndex.size} documents from Kafka topic to indexing" }

                consumer.commitSync(Duration.ofSeconds(10))

                lastTimeCommit = Instant.now()
                documentsToIndex.clear()

                logger.debug { "Waiting ${cfg.delayPeriodMillis} milliseconds for indexing..." }

                delay(cfg.delayPeriodMillis)
            }
        }
    }

    private fun createConsumer(bootstrapServers: String, groupId: String): Consumer<String, String> {
        val props = Properties()
        with (props) {
            put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers)
            put(ConsumerConfig.GROUP_ID_CONFIG, groupId)
            put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest")
            put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, "true")
            put(ConsumerConfig.AUTO_COMMIT_INTERVAL_MS_CONFIG, "1000")
            put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer().javaClass.name)
            put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, StringDeserializer().javaClass.name)
        }

        return KafkaConsumer<String, String>(props)
    }
}
