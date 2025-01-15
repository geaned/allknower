    package config

import com.sksamuel.hoplite.ConfigAlias
import com.sksamuel.hoplite.decoder.Seconds

data class DocumentConsumerConfig(
    @ConfigAlias("bootstrap_servers") val bootstrapServers: String,
    @ConfigAlias("poll_duration_millis") val pollDurationMillis: Long,
    @ConfigAlias("delay_period_millis") val delayPeriodMillis: Long,
    @ConfigAlias("max_document_batch") val maxDocumentBatch: Int,
    @ConfigAlias("batch_duration_seconds") val batchDurationSeconds: Seconds
)

data class Config(
    @ConfigAlias("index_directory") val indexDirectory: String,
    @ConfigAlias("document_topic") val documentTopic: String,
    @ConfigAlias("consumer") val documentConsumerConfig: DocumentConsumerConfig,
)