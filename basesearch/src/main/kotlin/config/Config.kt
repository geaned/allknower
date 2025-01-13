package config

import com.sksamuel.hoplite.ConfigAlias

data class Config(
    @ConfigAlias("index_directory") val indexDirectory: String,
)