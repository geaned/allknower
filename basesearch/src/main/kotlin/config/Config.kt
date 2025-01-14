package config

import com.sksamuel.hoplite.ConfigAlias

data class S3Config(
    @ConfigAlias("region") val region: String,
    @ConfigAlias("endpoint_url") val endpointUrl: String,
    @ConfigAlias("bucket") val bucket: String,
    @ConfigAlias("key") val key: String,
)

data class Config(
    @ConfigAlias("index_directory") val indexDirectory: String,
    @ConfigAlias("index_archive_file") val indexArchiveFile: String,
    @ConfigAlias("s3") val s3Config: S3Config,
)