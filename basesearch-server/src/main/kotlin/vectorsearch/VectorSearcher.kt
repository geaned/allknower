package vectorsearch

import config.Config
import mu.KLogger
import org.apache.lucene.index.DirectoryReader
import org.apache.lucene.search.IndexSearcher
import org.apache.lucene.search.KnnFloatVectorQuery
import org.apache.lucene.search.TopDocs
import org.apache.lucene.store.NIOFSDirectory
import java.io.File

class VectorSearcher(
    private val logger: KLogger,
    private val cfg: Config,
    val indexDirectory: String,
    val searchField: String = "embedding",
) {
    val directory = NIOFSDirectory(File(indexDirectory).toPath())

    fun search(query: List<Float>): TopDocs {
        val reader = DirectoryReader.open(directory)
        val searcher = IndexSearcher(reader)

        val knnQuery = KnnFloatVectorQuery(searchField, query.toFloatArray(), cfg.vectorSearchNumNearestNeighbor)
        val topDocs = searcher.search(knnQuery, cfg.vectorSearchNumDocuments)

        reader.close()

        return topDocs
    }
}