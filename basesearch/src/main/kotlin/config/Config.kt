package config

import com.sksamuel.hoplite.ConfigAlias

data class Config(
    @ConfigAlias("index_directory") val indexDirectory: String,
    @ConfigAlias("l0_num_docs") val l0NumDocs: Int,
    @ConfigAlias("l1_num_docs") val l1NumDocs: Int
)