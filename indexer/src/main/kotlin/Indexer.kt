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
    fileIndex: File,
    maxTokenCount: Int = 10000,
) {
    val analyzer = LimitTokenCountAnalyzer(StandardAnalyzer(), maxTokenCount)
    val directory = NIOFSDirectory(fileIndex.toPath())
    val config = IndexWriterConfig(analyzer)
    val writer = IndexWriter(directory, config)

    fun UpdateIndex(documents: List<WikiDocument>) {
        for (document in documents) {
            val doc = Document()
            doc.add(Field("doc_id", document.docId, StringField.TYPE_STORED))
            doc.add(Field("title", document.title, StringField.TYPE_STORED))
            doc.add(Field("page_url", document.pageUrl, StringField.TYPE_STORED))
            doc.add(Field("content", document.contents.joinToString(separator = "\n"), TextField.TYPE_STORED))
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

            writer.addDocument(doc)
        }

        writer.commit()

        println("${documents.size} added to index")
    }
}