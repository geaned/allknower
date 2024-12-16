package search

import color.Color
import color.PrintColorizer
import org.apache.lucene.analysis.LowerCaseFilter
import org.apache.lucene.analysis.StopFilter
import org.apache.lucene.analysis.TokenStream
import org.apache.lucene.analysis.en.EnglishAnalyzer
import org.apache.lucene.analysis.en.PorterStemFilter
import org.apache.lucene.analysis.miscellaneous.LimitTokenCountAnalyzer
import org.apache.lucene.analysis.standard.StandardTokenizer
import org.apache.lucene.analysis.tokenattributes.CharTermAttribute
import org.apache.lucene.index.DirectoryReader
import org.apache.lucene.index.IndexReader
import org.apache.lucene.index.Term
import org.apache.lucene.queryparser.classic.QueryParser
import org.apache.lucene.search.*
import org.apache.lucene.search.similarities.BM25Similarity
import org.apache.lucene.search.similarities.ClassicSimilarity
import org.apache.lucene.store.NIOFSDirectory
import java.io.File
import java.io.StringReader
import FeatureCalculator

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

        val features = calculateFeatures(reader, query, l1TopDocs)
        println(features)
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

    fun tokenizeAndStem(text: String): List<String> {
        // Initialize tokenizer and filter for stemming
        val tokenizer = StandardTokenizer()
        tokenizer.setReader(StringReader(text))

        // Create a token stream: apply lowercasing and stemming (Porter Stemmer)
        val stopwords = EnglishAnalyzer.getDefaultStopSet()
        val tokenStream: TokenStream = StopFilter(PorterStemFilter(LowerCaseFilter(tokenizer)), stopwords)

        // Collect the token terms after processing
        val stemmedTokens = mutableListOf<String>()
        val termAttribute: CharTermAttribute = tokenStream.addAttribute(CharTermAttribute::class.java)
        tokenStream.reset()

        while (tokenStream.incrementToken()) {
            stemmedTokens.add(termAttribute.toString())
        }
        tokenStream.end()
        tokenStream.close()

        return stemmedTokens
    }

    fun calculateFeatures(reader: IndexReader, query: String, docs: TopDocs): MutableList<List<Float>> {
        val queryTokens = tokenizeAndStem(query)

        val storedFields = reader.storedFields()

        val docsTokens = mutableListOf<List<String>>()

        docs.scoreDocs.forEach {
            println(storedFields.document(it.doc).fields)
            val document = storedFields.document(it.doc)

            var docText = document.getField("title")?.stringValue()
            if (docText.isNullOrBlank()) {
                docText = ""
            }

            // Assuming the text is stored in a field named "content"
            docsTokens.add(tokenizeAndStem(docText))
        }

        val featureCalculator = FeatureCalculator()
        val features = mutableListOf<List<Float>>()

        docsTokens.forEach{
            features.add(featureCalculator.calculateFeaturesByDoc(queryTokens, it))
        }

        val featuresStatistics =  mutableListOf<Float>()
        val featuresMinMaxScaled = mutableListOf<List<Float>>()

        val selectedFeaturesIndices = listOf(0, 1, 3, 5, 10, 13, 14, 15)
        val featuresToCalculateStatisticsIndices: Map<Int, List<Int>> = mapOf(
            0 to listOf(0, 1, 2),
            1 to listOf(0, 3),
            4 to listOf(2),
            6 to listOf(2),
            10 to listOf(2, 3)
        )
        val featuresToMinMaxScaleIndices = listOf(0, 1, 6)

        featuresToCalculateStatisticsIndices.forEach { it ->
            val idx = it.key
            val featureSlice = features.map { it[idx] }
            val featureSliceStatistics = featureCalculator.calculateStatistics(featureSlice)
            featureSliceStatistics.forEachIndexed { index, value ->
                if (it.value.contains(index)) {
                    featuresStatistics.add(value)
                }
            }

            if (featuresToMinMaxScaleIndices.contains(idx)) {
                featuresMinMaxScaled.add(
                    featureCalculator.minMaxScale(
                        featureSlice,
                        featureSliceStatistics[1],
                        featureSliceStatistics[0],
                    )
                )
            }
        }

        features.forEachIndexed { index, docFeatures ->
            val bm25ScoreScaled = featuresMinMaxScaled[0][index]
            val hHProximityScore = featuresMinMaxScaled[1][index]
            val bigramCoverageUnnormalizedScaled = featuresMinMaxScaled[2][index]

            features[index] = selectedFeaturesIndices.mapNotNull { innerIndex ->
                docFeatures.getOrNull(innerIndex)
            } + featuresStatistics + listOf(bm25ScoreScaled, hHProximityScore, bigramCoverageUnnormalizedScaled)

        }

        return features
    }
}
