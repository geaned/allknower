package index

import document.WikiDocument
import mu.KLogger
import org.apache.lucene.analysis.miscellaneous.LimitTokenCountAnalyzer
import org.apache.lucene.analysis.standard.StandardAnalyzer
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
    maxTokenCount: Int = 10000,
) {
    private val analyzer = LimitTokenCountAnalyzer(StandardAnalyzer(), maxTokenCount)
    private val directory = NIOFSDirectory(fileIndex.toPath())
    private val config = IndexWriterConfig(analyzer)
    private val writer = IndexWriter(directory, config)

    fun updateIndex(documents: List<WikiDocument>) {
        for (document in documents) {
            for (content in document.contents) {
                val doc = Document()

                try {
                    doc.add(Field("doc_id", content.contentId, StringField.TYPE_STORED))
                    doc.add(Field("title", document.title, StringField.TYPE_NOT_STORED))
                    doc.add(Field("page_url", document.pageUrl, StringField.TYPE_STORED))
                    doc.add(Field("content", content.content, TextField.TYPE_STORED))
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

        logger.info { "${documents.size} new documents added to index" }
    }
}