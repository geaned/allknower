package search

import color.Color
import color.PrintColorizer
import org.apache.lucene.analysis.LowerCaseFilter
import org.apache.lucene.analysis.StopFilter
import org.apache.lucene.analysis.TokenStream
import org.apache.lucene.analysis.en.EnglishAnalyzer
import org.apache.lucene.analysis.en.PorterStemFilter
import org.apache.lucene.analysis.standard.StandardTokenizer
import org.apache.lucene.analysis.tokenattributes.CharTermAttribute
import org.apache.lucene.index.DirectoryReader
import org.apache.lucene.index.IndexReader
import org.apache.lucene.queryparser.classic.QueryParser
import org.apache.lucene.search.IndexSearcher
import org.apache.lucene.search.Query
import org.apache.lucene.search.TopDocs
import org.apache.lucene.search.TotalHits
import org.apache.lucene.search.similarities.BM25Similarity
import org.apache.lucene.search.similarities.ClassicSimilarity
import org.apache.lucene.store.NIOFSDirectory
import org.example.search.HHProximityQueryV2
import java.io.File
import java.io.StringReader


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
        val l0TopDocs = filterTopDocsByScore(l0Search(reader, queryObj), 0.0f)

        val l0Hits = l0TopDocs.scoreDocs
        val docIds = l0Hits.map { it.doc }.toList().sorted()

        val proximityQuery = HHProximityQueryV2(terms, docIds)
        val l1TopDocs = filterTopDocsByScore(l1Search(reader, proximityQuery), 0.0f)

        // termsResults: docId -> (bm25, hhProximity)
//        val features = calculateFeatures(reader, query, l1TopDocs, proximityQuery.termsResults)

        reader.close()

        return l1TopDocs
    }

    fun l0Search(reader: IndexReader, query: Query, topHitsSize: Int = 10_000): TopDocs {
        val l0Searcher = IndexSearcher(reader)
        l0Searcher.similarity = ClassicSimilarity()

        return l0Searcher.search(query, topHitsSize)
    }

    fun l1Search(reader: IndexReader, query: Query, topHitsSize: Int = 1_000): TopDocs {
        val l1Searcher = IndexSearcher(reader)
        l1Searcher.similarity = BM25Similarity()

        return l1Searcher.search(query, topHitsSize)
    }

    fun filterTopDocsByScore(topDocs: TopDocs, minScore: Float): TopDocs {
        val filteredScoreDocs = topDocs.scoreDocs.filter { it.score > minScore }

        return TopDocs(
            TotalHits(filteredScoreDocs.size.toLong(), TotalHits.Relation.EQUAL_TO),
            filteredScoreDocs.toTypedArray(),
        )
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
                    "${table["doc_id"]}. Score: ${scoreDoc.score}. DocID at index: ${scoreDoc.doc}",
                    Color.GREEN,
                )
            )
        }

        reader.close()
    }

    private fun tokenizeAndStem(text: String): List<String> {
        val tokenizer = StandardTokenizer()
        tokenizer.setReader(StringReader(text))

        val stopwords = EnglishAnalyzer.getDefaultStopSet()
        val tokenStream: TokenStream = StopFilter(PorterStemFilter(LowerCaseFilter(tokenizer)), stopwords)

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

    private fun calculateFeatures(
        reader: IndexReader,
        query: String,
        docs: TopDocs,
        termsStats: MutableMap<Int, Pair<Float, Float>>
    ): MutableList<List<Float>> {
        val queryTokens = tokenizeAndStem(query)

        val storedFields = reader.storedFields()

        val docsTokens = mutableListOf<List<String>>()

        val bm25Scores = mutableListOf<Float>()
        val hhProximityScores = mutableListOf<Float>()

        docs.scoreDocs.forEach {
            println(storedFields.document(it.doc).fields)
            val document = storedFields.document(it.doc)

            var docText = document.getField("title")?.stringValue()
            if (docText.isNullOrBlank()) {
                docText = ""
            }

            // Assuming the text is stored in a field named "content"
            docsTokens.add(tokenizeAndStem(docText))

            bm25Scores.add(termsStats[it.doc]?.first ?: 0.0f)
            hhProximityScores.add(termsStats[it.doc]?.second ?: 0.0f)
        }

        val featureCalculator = FeatureCalculator()
        val features = mutableListOf<List<Float>>()

        docsTokens.forEach {
//            features.add(featureCalculator.calculateFeaturesByDoc(queryTokens, it))
        }

        val featuresStatistics = mutableListOf<Float>()
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

