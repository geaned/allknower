package org.example

import color.Color
import color.PrintColorizer
import document.Content
import document.Image
import document.WikiDocument
import index.Indexer
import search.Searcher
import java.io.File


const val INDEX_DIR = "index/v2"
const val DOCUMENTS_FILE = "src/main/resources/wikir_en78k.json"

fun main() {
    val indexFile = File(INDEX_DIR)

    if (indexFile.exists()) {
        indexFile.deleteRecursively()
        println("Directory deleted successfully.")
    }
    val indexer = Indexer(indexFile)
    buildIndex(indexer)

    val searcher = Searcher(fileIndex = indexFile)

    val query = "Alabama"
    val topDocs = searcher.SearchDocuments(query)

    println(
        PrintColorizer().ColorizeForeground(
            "L1 TopDocs:",
            Color.YELLOW
        )
    )
    searcher.PrintResults(topDocs)
}

fun buildIndex(indexer: Indexer) {
    val documents = WikiDocument.listFromJson(File(DOCUMENTS_FILE).readText())

    indexer.UpdateIndex(documents)
}

//class CustomNGramAnalyzer(private val minGram: Int, private val maxGram: Int) : Analyzer() {
//    override fun createComponents(fieldName: String): TokenStreamComponents {
//        val tokenizer: Tokenizer = NGramTokenizer(minGram, maxGram)
//
//        var tokenStream: TokenStream = LowerCaseFilter(tokenizer)
//        tokenStream = PorterStemFilter(tokenStream)
//
//        return TokenStreamComponents(tokenizer, tokenStream)
//    }
//}

// Функция для тестирования анализатора
//fun analyzeText(analyzer: Analyzer, text: String) {
//    analyzer.tokenStream("field", StringReader(text)).use { tokenStream ->
//        val charTermAttribute = tokenStream.getAttribute(CharTermAttribute::class.java)
//        tokenStream.reset()
//
//        // Выводим каждый токен (n-грамму) после обработки
//        while (tokenStream.incrementToken()) {
//            println(charTermAttribute.toString())
//        }
//
//        tokenStream.end()
//    }
//}

//fun generateNGrams(text: String) {
//    val analyzer = CustomNGramAnalyzer(2, 3)  // Создаем анализатор для n-грамм длиной от 2 до 3 символов
//
//    // Анализируем текст
//    println("Analyzed tokens:")
//    analyzeText(analyzer, text)
//}

//fun getNGrams(text: String): List<String> {
//    val ngramTokenizer = NGramTokenizer(2, 3)
//    ngramTokenizer.setReader(StringReader(text))
//
//    ngramTokenizer.reset()
//
//    val ngrams = mutableListOf<String>()
//    while (ngramTokenizer.incrementToken()) {
//        ngrams.add(ngramTokenizer.getAttribute(CharTermAttribute::class.java).toString())
//    }
//
//    return ngrams
//}

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
