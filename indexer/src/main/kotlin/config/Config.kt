package config

import com.sksamuel.hoplite.ConfigAlias
import com.sksamuel.hoplite.decoder.Seconds

data class DocumentConsumerConfig(
    @ConfigAlias("bootstrap_servers") val bootstrapServers: String,
    @ConfigAlias("delay_period_millis") val delayPeriodMillis: Long,
    @ConfigAlias("max_document_batch") val maxDocumentBatch: Int,
    @ConfigAlias("batch_duration_seconds") val batchDurationSeconds: Seconds
)

data class S3Config(
    @ConfigAlias("region") val region: String,
    @ConfigAlias("endpoint_url") val endpointUrl: String,
    @ConfigAlias("bucket") val bucket: String,
    @ConfigAlias("key") val key: String,
    )

data class Config(
    @ConfigAlias("index_directory") val indexDirectory: String,
    @ConfigAlias("index_archive_file") val indexArchiveFile: String,
    @ConfigAlias("document_topic") val documentTopic: String,
    @ConfigAlias("consumer") val documentConsumerConfig: DocumentConsumerConfig,
    @ConfigAlias("s3") val s3Config: S3Config,
)