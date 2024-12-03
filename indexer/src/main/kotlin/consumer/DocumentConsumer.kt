package consumer

import document.WikiDocument
import com.sksamuel.hoplite.decoder.duration
import config.DocumentConsumerConfig
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.delay
import org.apache.kafka.clients.consumer.*
import org.apache.kafka.common.serialization.StringDeserializer
import java.time.Duration
import java.time.Instant
import java.util.*
import kotlin.time.toJavaDuration


class DocumentConsumer(
    val documentChannel: Channel<List<WikiDocument>>,

    val cfg: DocumentConsumerConfig,
) {
    private val consumer = createConsumer(cfg.bootstrapServers)

    private val lastTimeCommit = Instant.now()


    suspend fun Consume(topic: String) {
        consumer.subscribe(listOf(topic))

        while (true) {
            delay(cfg.delayPeriodMillis)

            val messages: ConsumerRecords<String, String> = consumer.poll(Duration.ofSeconds(10))

            if (!messages.isEmpty) {
                val duration = Duration.between(lastTimeCommit, Instant.now())
                if ((messages.count() >= cfg.maxDocumentBatch) || (duration > cfg.batchDurationSeconds.duration().toJavaDuration())) {
                    val documentsToIndex = mutableListOf<WikiDocument>()

                    for (message: ConsumerRecord<String, String> in messages) {
                        val document = WikiDocument.fromJson(message.value())
                        documentsToIndex.add(WikiDocument.fromJson(message.value()))

                        println("Consumer reading message: ${document}")
                    }

                    documentChannel.send(documentsToIndex)

                    consumer.commitSync(Duration.ofSeconds(10))
                }
            } else {
                println("No messages to read and poll timeout reached")
            }
        }
    }

    private fun createConsumer(bootstrapServers: String): Consumer<String, String> {
        val props = Properties()
        with (props) {
            put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers)
            put(ConsumerConfig.GROUP_ID_CONFIG, "indexer")
            put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, "true")
            put(ConsumerConfig.AUTO_COMMIT_INTERVAL_MS_CONFIG, "1000")
            put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer().javaClass.name)
            put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, StringDeserializer().javaClass.name)
        }

        return KafkaConsumer<String, String>(props)
    }
}
