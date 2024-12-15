package search

import color.Color
import color.PrintColorizer
import org.apache.lucene.analysis.en.EnglishAnalyzer
import org.apache.lucene.analysis.miscellaneous.LimitTokenCountAnalyzer
import org.apache.lucene.index.DirectoryReader
import org.apache.lucene.index.IndexReader
import org.apache.lucene.index.Term
import org.apache.lucene.queryparser.classic.QueryParser
import org.apache.lucene.search.*
import org.apache.lucene.search.similarities.BM25Similarity
import org.apache.lucene.search.similarities.ClassicSimilarity
import org.apache.lucene.store.NIOFSDirectory
import java.io.File


class Searcher(
    val fileIndex: File,
    val searchField: String = "content",
    val idField: String = "doc_id",
    maxTokenCount: Int = 10000,
    ) {
    private val defaultOperator: QueryParser.Operator = QueryParser.OR_OPERATOR

    val analyzer = LimitTokenCountAnalyzer(EnglishAnalyzer(), maxTokenCount)
    val directory = NIOFSDirectory(fileIndex.toPath())

    fun SearchDocuments(query: String): TopDocs {
        val reader = DirectoryReader.open(directory)

        val queryParser = QueryParser(searchField, analyzer)
        queryParser.defaultOperator = defaultOperator

        val queryObj = queryParser.parse(query)

        val l0TopDocs = l0Search(reader, queryObj)

        val l0Hits = l0TopDocs.scoreDocs
        val docIds = l0Hits.map { it.doc }.toList()

        val l1TopDocs = l1Search(reader, queryObj, docIds)

        l1TopDocs.scoreDocs.forEach {
            val tfidfScore = l0TopDocs.scoreDocs.find { scoreDoc -> scoreDoc.doc == it.doc }?.score
            println("Doc: ${reader.storedFields().document(it.doc).getField("title").stringValue()}\nTFIDF Score: ${tfidfScore}")
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

        // Создаем TermsQuery для поиска только по документам из фазы L0
        val termQuery = BooleanQuery.Builder().apply {
            val storedFields = reader.storedFields()
            docIds.forEach { docId ->
                val storedDocId = storedFields.document(docId).getField(idField).stringValue()
                val term = Term(idField, storedDocId)  // Предполагаем, что idField содержит ID документа
                add(TermQuery(term), BooleanClause.Occur.SHOULD)
            }
        }.build()

        val combinedQuery = BooleanQuery.Builder()
            .add(query, BooleanClause.Occur.MUST)
            .add(termQuery, BooleanClause.Occur.FILTER)
            .build()

        return l1Searcher.search(combinedQuery, 1_000)
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

            doc.getField("content")?.let {
                println(it.stringValue())
            }

            val table = doc.fields.associate { it.name() to it.stringValue() }

            println(
                PrintColorizer().Colorize(
                    "${table["doc_id"]}: \"${table["title"]}\". Score: ${scoreDoc.score}",
                    Color.GREEN,
                )
            )
        }

        reader.close()
    }
}
