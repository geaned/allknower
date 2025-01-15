package config

import com.sksamuel.hoplite.ConfigAlias

data class Config(
    @ConfigAlias("full_text_index_directory") val fullTextIndexDirectory: String,
    @ConfigAlias("vector_text_index_directory") val vectorTextIndexDirectory: String,
    @ConfigAlias("vector_image_index_directory") val vectorImageIndexDirectory: String,

    @ConfigAlias("l0_num_docs") val l0NumDocs: Int,
    @ConfigAlias("l1_num_docs") val l1NumDocs: Int,

    @ConfigAlias("vector_search_num_nearest_neighbor") val vectorSearchNumNearestNeighbor: Int,
    @ConfigAlias("vector_search_num_documents") val vectorSearchNumDocuments: Int,
)