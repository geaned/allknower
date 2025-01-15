package index

import document.WikiDocument
import mu.KLogger
import org.apache.lucene.analysis.Analyzer
import org.apache.lucene.analysis.LowerCaseFilter
import org.apache.lucene.analysis.StopFilter
import org.apache.lucene.analysis.en.EnglishAnalyzer
import org.apache.lucene.analysis.en.PorterStemFilter
import org.apache.lucene.analysis.standard.StandardTokenizer
import org.apache.lucene.document.*
import org.apache.lucene.index.IndexWriter
import org.apache.lucene.index.IndexWriterConfig
import org.apache.lucene.store.NIOFSDirectory
import java.io.File

class VectorImageSearchIndexer(
    private val logger: KLogger,
    fileIndex: File,
): Indexer() {
    private val analyzer = object : Analyzer() {
        override fun createComponents(fieldName: String): TokenStreamComponents {
            val tokenizer = StandardTokenizer()
            val tokenStream = StopFilter(PorterStemFilter(LowerCaseFilter(tokenizer)), EnglishAnalyzer.getDefaultStopSet())
            return TokenStreamComponents(tokenizer, tokenStream)
        }
    }
    private val directory = NIOFSDirectory(fileIndex.toPath())
    private val config = IndexWriterConfig(analyzer)
    private val writer = IndexWriter(directory, config)

    private var totalDocuments = 0

    override fun updateIndex(documents: List<WikiDocument>) {
        for (document in documents) {
            if (document.images.isEmpty()) {
                logger.info { "No images to index. DocID: ${document.docId}" }
                continue
            }

            for (image in document.images) {
                val doc = Document()

                try {
                    doc.add(Field("doc_id", image.crc64, StringField.TYPE_STORED))
                    doc.add(Field("page_url", document.pageUrl, StringField.TYPE_STORED))
                    doc.add(Field("title", document.title, StringField.TYPE_STORED))
                    doc.add(Field("embedding_serialized", image.embedding.joinToString(separator = " "), StringField.TYPE_STORED))
                    doc.add(KnnFloatVectorField("embedding", image.embedding.toFloatArray()))

                    if (image.metadata != null) {
                        doc.add(Field("metadata_title", image.metadata.title, TextField.TYPE_STORED))
                        doc.add(Field("metadata_description", image.metadata.description, TextField.TYPE_STORED))
                    }
                } catch (e: Exception) {
                    logger.error { "Failed while adding to index image, skip it. DocID: ${document.docId}. CRC64: ${image.crc64}. Error ${e.message}" }
                    continue
                }

                writer.addDocument(doc)

                logger.info { "Image added to index. DocID: ${document.docId}. CRC64: ${image.crc64}" }
            }
        }

        writer.commit()

        totalDocuments += documents.size

        logger.info { "${documents.size} new documents added to index" }
        logger.info { "Total documents at vector image search index: $totalDocuments" }
    }
}