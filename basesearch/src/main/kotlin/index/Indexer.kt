package index

import document.WikiDocument
import org.apache.lucene.analysis.Analyzer
import org.apache.lucene.analysis.LowerCaseFilter
import org.apache.lucene.analysis.en.EnglishAnalyzer
import org.apache.lucene.analysis.miscellaneous.LimitTokenCountAnalyzer
import org.apache.lucene.analysis.ngram.NGramTokenizer
import org.apache.lucene.document.Document
import org.apache.lucene.document.Field
import org.apache.lucene.document.StringField
import org.apache.lucene.document.TextField
import org.apache.lucene.index.IndexWriter
import org.apache.lucene.index.IndexWriterConfig
import org.apache.lucene.store.NIOFSDirectory
import java.io.File

class Indexer(
    val fileIndex: File,
    maxTokenCount: Int = 10000,
) {
    val analyzer = LimitTokenCountAnalyzer(EnglishAnalyzer(), maxTokenCount)
    val config = IndexWriterConfig(analyzer)
    val directory = NIOFSDirectory(fileIndex.toPath())

    fun UpdateIndex(documents: List<WikiDocument>) {
        val writer = IndexWriter(directory, config)

        // TODO
        val nGramAnalyzer = object : Analyzer() {
            override fun createComponents(fieldName: String): TokenStreamComponents {
                val tokenizer = NGramTokenizer(3, 5)
                val filter = LowerCaseFilter(tokenizer)
                return TokenStreamComponents(tokenizer, filter)
            }
        }

        for (document in documents) {
            val doc = Document()

            doc.add(Field("doc_id", document.docId, StringField.TYPE_STORED))
            doc.add(Field("title", document.title, TextField.TYPE_STORED))
            doc.add(Field("page_url", document.pageUrl, StringField.TYPE_STORED))
            doc.add(Field("content", document.contents.joinToString(separator = "\n\n"), TextField.TYPE_NOT_STORED))
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

        writer.close()
    }
}