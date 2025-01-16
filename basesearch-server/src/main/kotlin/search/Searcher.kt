package search

import color.Color
import color.PrintColorizer
import config.Config
import mu.KLogger
import org.apache.lucene.analysis.Analyzer
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
    private val logger: KLogger,
    private val cfg: Config,
    val searchField: String = "content",
) {
    private val defaultOperator: QueryParser.Operator = QueryParser.AND_OPERATOR

    val analyzer = object : Analyzer() {
        override fun createComponents(fieldName: String): TokenStreamComponents {
            val tokenizer = StandardTokenizer()
            val tokenStream = StopFilter(PorterStemFilter(LowerCaseFilter(tokenizer)), EnglishAnalyzer.getDefaultStopSet())
            return TokenStreamComponents(tokenizer, tokenStream)
        }
    }
    val directory = NIOFSDirectory(File(cfg.fullTextIndexDirectory).toPath())

    val termExtractor = TermExtractor()

    fun searchDocuments(query: String): Pair<TopDocs, MutableList<List<Float>>?> {
        val reader = DirectoryReader.open(directory)

        val terms = termExtractor.extractTerms(searchField, query)

        logger.debug { "Searching for: $terms" }

        val queryParser = QueryParser(searchField, analyzer)
        queryParser.defaultOperator = defaultOperator

        val queryObj = queryParser.parse(query)
        val l0TopDocs = filterTopDocsByScore(l0Search(reader, queryObj), 0.0f)

        val l0Hits = l0TopDocs.scoreDocs
        val docIds = l0Hits.map { it.doc }.toList().sorted()

        logger.info { "Found ${l0Hits.size} documents on L0 stage for query: $query" }

        if (l0Hits.isEmpty()) {
            reader.close()
            return Pair(l0TopDocs, mutableListOf())
        }

        val proximityQuery = HHProximityQueryV2(terms, docIds)
        val l1TopDocs = filterTopDocsByScore(l1Search(reader, proximityQuery), 0.0f)

        logger.info { "Found ${l1TopDocs.scoreDocs.size} documents on L1 stage for query: $query" }

        if (l1TopDocs.scoreDocs.isEmpty()) {
            reader.close()
            return Pair(l1TopDocs, mutableListOf())
        }

        // termsResults: docId -> (bm25, hhProximity)
        val features = calculateFeatures(reader, query, l1TopDocs, proximityQuery.termsResults)

        reader.close()

        return Pair(l1TopDocs, features)
    }

    fun l0Search(reader: IndexReader, query: Query, topHitsSize: Int = cfg.l0NumDocs): TopDocs {
        val l0Searcher = IndexSearcher(reader)
        l0Searcher.similarity = ClassicSimilarity()

        return l0Searcher.search(query, topHitsSize)
    }

    fun l1Search(reader: IndexReader, query: Query, topHitsSize: Int = cfg.l1NumDocs): TopDocs {
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

    fun printResults(searchResult: TopDocs) {
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
            val document = storedFields.document(it.doc)

            var docText = document.getField("content")?.stringValue()
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

        docsTokens.forEachIndexed { index, it ->
            features.add(featureCalculator.calculateFeaturesByDoc(queryTokens, bm25Scores[index], hhProximityScores[index], it))
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

