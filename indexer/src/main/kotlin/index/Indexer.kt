package index

import com.google.gson.Gson
import document.WikiDocument
import mu.KLogger
import org.apache.lucene.analysis.Analyzer
import org.apache.lucene.analysis.LowerCaseFilter
import org.apache.lucene.analysis.StopFilter
import org.apache.lucene.analysis.en.EnglishAnalyzer
import org.apache.lucene.analysis.en.PorterStemFilter
import org.apache.lucene.analysis.standard.StandardTokenizer
import org.apache.lucene.document.Document
import org.apache.lucene.document.Field
import org.apache.lucene.document.StringField
import org.apache.lucene.document.TextField
import org.apache.lucene.index.IndexWriter
import org.apache.lucene.index.IndexWriterConfig
import org.apache.lucene.store.NIOFSDirectory
import java.io.File

class Indexer(
    private val logger: KLogger,
    fileIndex: File,
) {
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

    fun updateIndex(documents: List<WikiDocument>) {
        for (document in documents) {
//            // image
//            for (image in document.images) {
//                val doc = Document()
//
//                // image
//                try {
//                    doc.add(Field("doc_id", image.crc64, StringField.TYPE_STORED))
//                    doc.add(Field("page_url", document.pageUrl, StringField.TYPE_STORED))
//                    doc.add(Field("title", document.title, StringField.TYPE_STORED))
//                    doc.add(Field("metadata_title", image.metadata.title, StringField.TYPE_STORED))
//                    doc.add(Field("metadata_description", image.metadata.description, TextField.TYPE_STORED))
//                    doc.add(Field("embedding", image.embedding.joinToString(separator = " "), TextField.TYPE_STORED)) // TODO: check if exists and fix
//                } catch (e: Exception) {
//                    logger.error { "Failed while adding to index image, skip it. DocID: ${document.docId}. CRC64: ${image.crc64}. Error ${e.message}" }
//                    continue
//                }
//
//                writer.addDocument(doc)
//
//                logger.info { "Image added to index. DocID: ${document.docId}. CRC64: ${image.crc64}" }
//            }

            // text
            for (content in document.contents) {
                val doc = Document()
                // vector search
//                doc.add(Field("doc_id", content.contentId, StringField.TYPE_STORED))
//                doc.add(Field("title", document.title, StringField.TYPE_STORED))
//                doc.add(Field("page_url", document.pageUrl, StringField.TYPE_STORED))
//                doc.add(Field("content", content.content, StringField.TYPE_STORED))
//                doc.add(Field("embedding", content.embedding.joinToString(separator = " "), TextField.TYPE_STORED)) // TODO: check if exists and fix

                // full-text search
                try {
                    doc.add(Field("doc_id", content.contentId, StringField.TYPE_STORED))
                    doc.add(Field("title", document.title, StringField.TYPE_STORED))
                    doc.add(Field("page_url", document.pageUrl, StringField.TYPE_STORED))
                    doc.add(Field("content", content.content, TextField.TYPE_STORED))
                    doc.add(Field("embedding", Gson().toJson(content.embedding), StringField.TYPE_STORED))
                    doc.add(
                        Field(
                            "keywords",
                            listOf(document.title, document.categories).joinToString(separator = " "),
                            TextField.TYPE_NOT_STORED
                        ),
                    )
                    doc.add(
                        Field(
                            "references",
                            document.references.joinToString(separator = "\n"),
                            TextField.TYPE_NOT_STORED
                        ),
                    )
                } catch (e: Exception) {
                    logger.error { "Failed while adding to index document, skip it. DocID: ${document.docId}. ContentID: ${content.contentId}. Error ${e.message}" }
                    continue
                }

                writer.addDocument(doc)

                logger.info { "Document added to index. DocID: ${document.docId}. ContentID: ${content.contentId}" }
            }
        }

        writer.commit()

        totalDocuments += documents.size

        logger.info { "${documents.size} new documents added to index" }
        logger.info { "Total documents at full-text search index: $totalDocuments" }
    }
}