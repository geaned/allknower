package org.example.search

import org.apache.lucene.index.LeafReader
import org.apache.lucene.index.LeafReaderContext
import org.apache.lucene.index.PostingsEnum
import org.apache.lucene.index.Term
import org.apache.lucene.search.*
import org.apache.lucene.search.similarities.ClassicSimilarity
import org.apache.lucene.search.similarities.Similarity.SimScorer
import kotlin.math.ln
import kotlin.math.pow

class HHProximityQueryV2(
    private val terms: List<Term>,
    private val docIDs: List<Int>,
    val z: Double = 1.75,
) : Query() {
    val termsResults = mutableMapOf<Int, Pair<Float, Float>>()

    fun setTermResults(docId: Int, bm25: Float, hhProximity: Float) {
        termsResults[docId] = Pair(bm25, hhProximity)
    }

    override fun equals(other: Any?): Boolean {
        return sameClassAs(other) && (other as HHProximityQueryV2).terms == terms
    }

    override fun hashCode(): Int {
        return classHash() xor terms.hashCode()
    }

    override fun toString(field: String?): String {
        return "ProximityQuery(${terms.joinToString(",")})"
    }

    override fun visit(visitor: QueryVisitor?) {
        visitor?.consumeTerms(this, *terms.toTypedArray())
    }

    override fun createWeight(searcher: IndexSearcher, scoreMode: ScoreMode, boost: Float): Weight {
        val collectionStats = searcher.collectionStatistics(terms.first().field())

        val termStats = mutableListOf<TermStatistics>()
        for (term in terms) {
            val docFreq = searcher.indexReader.docFreq(term)
            val totalTermFreq = searcher.indexReader.totalTermFreq(term)
            if (docFreq == 0 || totalTermFreq == 0L) {
                continue
            }

            termStats.add(searcher.termStatistics(term, docFreq, totalTermFreq))
        }

        val simScorer = searcher.similarity.scorer(boost, collectionStats, *termStats.toTypedArray())

        return HHProximityWeightV2(this, terms, docIDs, simScorer, z)
    }
}

class HHProximityWeightV2(
    query: Query,
    private val terms: List<Term>,
    private val docIDs: List<Int>,
    private val simScorer: SimScorer,
    private val z: Double = 1.75,
) : Weight(query) {

    override fun isCacheable(ctx: LeafReaderContext?): Boolean {
        return false
    }

    override fun explain(context: LeafReaderContext, doc: Int): Explanation {
        val scorer = scorer(context)
        return if (scorer != null && scorer.iterator().advance(doc) == doc) {
            Explanation.match(scorer.score(), "Proximity score for document")
        } else {
            Explanation.noMatch("No matching terms")
        }
    }

    override fun scorer(context: LeafReaderContext): Scorer? {
        val reader = context.reader()

        val termsStats = terms.mapNotNull { term ->
            reader.postings(term, PostingsEnum.POSITIONS.toInt())?.let { postings ->
                val docsFreq = mutableMapOf<Int, Int>()
                val docPositions = mutableMapOf<Int, List<Int>>()

//                while (postings.nextDoc() != DocIdSetIterator.NO_MORE_DOCS) {
//                    val positions = mutableListOf<Int>()
//                    repeat(postings.freq()) {
//                        positions.add(postings.nextPosition())
//                    }
//
//                    docPositions[postings.docID()] = positions
//                    docsFreq[postings.docID()] = postings.freq()
//                }

                for (docId in docIDs) {
                    postings.advance(docId)
                    if (postings.docID() == docId) {
                        val positions = mutableListOf<Int>()
                        repeat(postings.freq()) {
                            positions.add(postings.nextPosition())
                        }

                        docPositions[postings.docID()] = positions
                        docsFreq[postings.docID()] = postings.freq()
                    }

                    if (postings.docID() == PostingsEnum.NO_MORE_DOCS) {
                        break
                    }
                }

                term to Pair(docsFreq, docPositions)
            }
        }.toMap()

        if (termsStats.isEmpty())
            return null

        val termsPerDocFreq = termsStats.map { (terms, pairStats) ->
            terms to pairStats.first
        }.toMap()
        val termsPerDocPositions = termsStats.map { (terms, pairStats) ->
            terms to pairStats.second
        }.toMap()

        return HHProximityScorerV2(
            this, docIDs, termsPerDocFreq, termsPerDocPositions, reader, simScorer, z
        )
    }
}

class HHProximityScorerV2(
    weight: Weight,
    private val docIDs: List<Int>,
    private val termsPerDocFreq: Map<Term, Map<Int, Int>>,
    private val termsPerDocPositions: Map<Term, MutableMap<Int, List<Int>>>,
    private val reader: LeafReader,
    private val simScorer: SimScorer,
    private val z: Double
) : Scorer(weight) {
    private val tfidfSimilarity = ClassicSimilarity()

    override fun score(): Float {
        if (!docIDs.contains(docID())) {
            return 0.0f
        }

        var hhProximityScore = 0.0
        var bm25Score = 0.0

//        val termPositions = mutableMapOf<Term, List<Int>>()
//        for ((term, docPositionsMap) in termsPerDocPositions) {
//            if (docIDs.contains(docID())) {
//                val positions = docPositionsMap[docID()] ?: emptyList()
//                termPositions[term] = positions
//            }
//        }

        val termPositions = termsPerDocPositions.map { (term, docPositionsMap) ->
            val positions = docPositionsMap[docID()] ?: emptyList()
            term to positions
        }.toMap()

        for ((term, positions) in termPositions) {
            if (positions.isEmpty()) {
                continue
            }

            var atc = 0.0
            for (pos in positions) {
                val tc = termPositions.entries.sumOf { (otherTerm, otherPositions) ->
                    val ts = if (otherTerm == term) 0.25 else 1.0


                    val posIdx = otherPositions.binarySearch(pos)
                    val leftDistance = if (posIdx > 0) pos - otherPositions[posIdx - 1] else Double.MAX_VALUE
                    val rightDistance = if (posIdx < otherPositions.size - 1) otherPositions[posIdx + 1] - pos else Double.MAX_VALUE

//                    val leftDistance = otherPositions.lastOrNull { it < pos }?.let { pos - it } ?: Double.MAX_VALUE
//                    val rightDistance = otherPositions.firstOrNull { it > pos }?.let { it - pos } ?: Double.MAX_VALUE

                    val idfOther = tfidfSimilarity.idf(reader.docFreq(otherTerm).toLong(), reader.numDocs().toLong())

                    (idfOther / leftDistance.toDouble().pow(z) + idfOther / rightDistance.toDouble().pow(z)) * ts

                }

                atc += tc
            }

            val idf = tfidfSimilarity.idf(reader.docFreq(term).toLong(), reader.numDocs().toLong())

            hhProximityScore += atc * idf

//            val norms = reader.getNormValues(term.field())
//            norms.advance(docID())

            bm25Score += simScorer.score((termsPerDocFreq[term]?.get(docID())?.toFloat() ?: 0.0f), 1)
        }

        hhProximityScore = ln(1 + hhProximityScore)

        if (bm25Score != 0.0 || hhProximityScore != 0.0) {
            (weight.query as HHProximityQueryV2).setTermResults(docID(), bm25Score.toFloat(), hhProximityScore.toFloat())
        }

        return (0.5 * bm25Score + 0.5 * hhProximityScore).toFloat()
    }

    private val iterator: DocIdSetIterator = object : DocIdSetIterator() {
        private var docIndex = -1

        override fun docID(): Int {
            val resultID = if (docIndex == -1) {
                -1
            } else {
                if (docIndex in docIDs.indices) docIDs[docIndex] else NO_MORE_DOCS
            }

            return resultID
        }

        override fun nextDoc(): Int {
            docIndex++
            return if (docIndex in docIDs.indices) docIDs[docIndex] else NO_MORE_DOCS
        }

        override fun advance(target: Int): Int {
            while (docIndex + 1 < docIDs.size && docIDs[docIndex + 1] < target) {
                docIndex++
            }
            return nextDoc()
        }

        override fun cost(): Long = docIDs.size.toLong()
    }

    override fun docID(): Int {
        return this.iterator.docID()
    }

    override fun iterator(): DocIdSetIterator = iterator

    override fun getMaxScore(upTo: Int): Float {
        return Float.MAX_VALUE
    }
}