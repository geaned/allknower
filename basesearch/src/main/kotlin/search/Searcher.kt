package search
import color.Color
import color.PrintColorizer
import org.apache.lucene.analysis.en.EnglishAnalyzer
import org.apache.lucene.index.DirectoryReader
import org.apache.lucene.index.IndexReader
import org.apache.lucene.queryparser.classic.QueryParser
import org.apache.lucene.search.IndexSearcher
import org.apache.lucene.search.Query
import org.apache.lucene.search.TopDocs
import org.apache.lucene.search.similarities.BM25Similarity
import org.apache.lucene.search.similarities.ClassicSimilarity
import org.apache.lucene.store.NIOFSDirectory
import org.example.search.HHProximityQueryV2
import java.io.File


class Searcher(
    val fileIndex: File,
    val searchField: String = "content",
    ) {
    private val defaultOperator: QueryParser.Operator = QueryParser.OR_OPERATOR

    val analyzer = EnglishAnalyzer()
    val directory = NIOFSDirectory(fileIndex.toPath())

    val termExtractor = TermExtractor()

    fun SearchDocuments(query: String): TopDocs {
        val reader = DirectoryReader.open(directory)

        val terms = termExtractor.ExtractTerms(searchField, query)
        println(
            PrintColorizer().Colorize(
                "Searching for: $terms\n",
                Color.LIGHT_RED
            )
        )

        val queryParser = QueryParser(searchField, analyzer)
        queryParser.defaultOperator = defaultOperator

        val queryObj = queryParser.parse(query)

        val l0TopDocs = l0Search(reader, queryObj)

        println(
            PrintColorizer().ColorizeForeground(
                "L0 TopDocs:",
                Color.RED
            )
        )
        this.PrintResults(l0TopDocs)
        println()

        val l0Hits = l0TopDocs.scoreDocs
        val docIds = l0Hits.map { it.doc }.toList()

        val proximityQuery = HHProximityQueryV2(terms, docIds)
        val l1TopDocs = l1Search(reader, proximityQuery, docIds)

        println(
            PrintColorizer().ColorizeForeground(
                "TopDocs BaseStats:",
                Color.BLUE
            )
        )
        l1TopDocs.scoreDocs.forEach {
            val tfidfScore = l0TopDocs.scoreDocs.find { scoreDoc -> scoreDoc.doc == it.doc }?.score
            println("Doc: ${reader.storedFields().document(it.doc).getField("title").stringValue()}\n" +
                    "TFIDF Score: ${tfidfScore}\n" +
                    "Final Score: ${it.score}\n")
        }

        reader.close()

        return l1TopDocs
    }

    fun l0Search(reader: IndexReader, query: Query): TopDocs {
        val l0Searcher = IndexSearcher(reader)
        l0Searcher.similarity = ClassicSimilarity()

        return l0Searcher.search(query, 10_000)
    }

    fun l1Search(reader: IndexReader, query: Query, docIds: List<Int>): TopDocs {
        val l1Searcher = IndexSearcher(reader)
        l1Searcher.similarity = BM25Similarity()

//        // Создаем TermsQuery для поиска только по документам из фазы L0
//        val termQuery = BooleanQuery.Builder().apply {
//            val storedFields = reader.storedFields()
//            docIds.forEach { docId ->
//                val storedDocId = storedFields.document(docId).getField(idField).stringValue()
//                val term = Term(idField, storedDocId)  // Предполагаем, что idField содержит ID документа
//                add(TermQuery(term), BooleanClause.Occur.SHOULD)
//            }
//        }.build()
//
//        val combinedQuery = BooleanQuery.Builder()
//            .add(query, BooleanClause.Occur.MUST)
//            .add(termQuery, BooleanClause.Occur.FILTER)
//            .build()

        return l1Searcher.search(query, 1_000)
    }

    fun PrintResults(searchResult: TopDocs) {
        val reader = DirectoryReader.open(directory)

        println(
            PrintColorizer().Colorize(
                "Found ${searchResult.totalHits.value} documents:",
                Color.BLUE,
            )
        )

        val storedFields = reader.storedFields()
        for (scoreDoc in searchResult.scoreDocs) {
            val doc = storedFields.document(scoreDoc.doc)

            doc.getField("page_url")?.let {
                println(it.stringValue())
            }

            val table = doc.fields.associate { it.name() to it.stringValue() }

            println(
                PrintColorizer().Colorize(
                    "${table["doc_id"]}: \"${table["title"]}\". Score: ${scoreDoc.score}. DocID at index: ${scoreDoc.doc}",
                    Color.GREEN,
                )
            )
        }

        reader.close()
    }
}
