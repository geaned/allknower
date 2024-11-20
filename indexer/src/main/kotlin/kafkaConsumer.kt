import kotlinx.coroutines.delay
import org.apache.kafka.clients.consumer.Consumer
import org.apache.kafka.clients.consumer.ConsumerRecord
import org.apache.kafka.clients.consumer.ConsumerConfig
import org.apache.kafka.clients.consumer.ConsumerRecords
import org.apache.kafka.clients.consumer.KafkaConsumer
import org.apache.kafka.common.serialization.StringDeserializer
import java.time.Duration
import java.util.*

class DocumentConsumer(
    bootstrapServers: String,
    private val delayPeriodMillis: Long,
) {
    private val consumer = createConsumer(bootstrapServers)

    suspend fun Consume(topic: String) {
        consumer.subscribe(listOf(topic))

        while (true) {
            delay(delayPeriodMillis)

            val messages: ConsumerRecords<String, String> = consumer.poll(Duration.ofSeconds(10))

            if (!messages.isEmpty) {
                for (message: ConsumerRecord<String, String> in messages) {
                    message.value() // TODO
                    println("Consumer reading message: ${message.value()}")
                }

                consumer.commitSync(Duration.ofSeconds(10))
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
