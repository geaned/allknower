package org.example

import document.Content
import document.Image
import document.WikiDocument
import index.Indexer
import org.apache.lucene.analysis.ngram.NGramTokenizer
import org.apache.lucene.analysis.tokenattributes.CharTermAttribute
import search.Searcher
import java.io.File
import java.io.StringReader


const val INDEX_DIR = "index/v1"
const val DOCUMENTS_FILE = "src/main/resources/books.json"

fun main() {
    val indexFile = File(INDEX_DIR)
    if (indexFile.exists()) {
        indexFile.deleteRecursively()
        println("Directory deleted successfully.")
    }

    val indexer = Indexer(indexFile)
    buildIndex(indexer)

    val searcher = Searcher(fileIndex = indexFile)

    val query = "пьер"
    val topDocs = searcher.SearchDocuments(query)

    searcher.PrintResults(topDocs)
}

fun buildIndex(indexer: Indexer) {
    val documents = WikiDocument.listFromJson(File(DOCUMENTS_FILE).readText())

    indexer.UpdateIndex(documents)
}

fun getNGrams(text: String): List<String> {
    val ngramTokenizer = NGramTokenizer(2, 3)
    ngramTokenizer.setReader(StringReader(text))

    ngramTokenizer.reset()

    val ngrams = mutableListOf<String>()
    while (ngramTokenizer.incrementToken()) {
        ngrams.add(ngramTokenizer.getAttribute(CharTermAttribute::class.java).toString())
    }

    return ngrams
}

fun  generateJson() {
    val document = WikiDocument(
        docId = "1",
        title = "Книга",
        pageUrl = "https://ru.wikipedia.org/wiki/Книга",
        images = listOf(
            Image(
                crc64 = "123456",
                image = "https://upload.wikimedia.org/wikipedia/commons/1/1b/Book_icon_Noun_Project_17688.svg",
                metadata = document.Metadata(title = "Книга"),
            )
        ),
        references = listOf("https://ru.wikipedia.org/wiki/Книга"),
        categories = listOf("Книги"),
        contents = listOf(
            Content(
                contentId = "1",
                content = "Книга — письменное произведение, представляющее собой совокупнос",
            )
        ),
        redirect = false,
    )

    val jsonDocument = WikiDocument.toJson(document)
    val file = File("src/main/resources/document_example.json")
    file.writeText(jsonDocument)
}
