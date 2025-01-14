package org.example.search
//
//import org.apache.lucene.index.LeafReaderContext
//import org.apache.lucene.index.PostingsEnum
//import org.apache.lucene.index.Term
//import org.apache.lucene.index.TermStates
//import org.apache.lucene.search.*
//
//class ProximityQuery(
//    private val terms: List<Term>,
//    val proximityWeight: Float,
//    val bm25Weight: Float,
//    val z: Float = 1.75f
//) : Query() {
//
//    override fun createWeight(searcher: IndexSearcher, scoreMode: ScoreMode, boost: Float): Weight {
//        return ProximityWeight(this, terms, searcher, scoreMode, z, boost)
//    }
//
//    override fun visit(visitor: QueryVisitor?) {
//        visitor?.visitLeaf(this)
//    }
//
//    override fun toString(field: String?): String {
//        return "ProximityQuery(${terms.joinToString(",")})"
//    }
//
//    override fun equals(other: Any?): Boolean {
//        return sameClassAs(other) && (other as ProximityQuery).terms == terms
//    }
//
//    override fun hashCode(): Int {
//        return classHash() xor terms.hashCode()
//    }
//
//    class ProximityWeight(
//        query: Query,
//        private val terms: List<Term>,
//        private val searcher: IndexSearcher,
//        private val scoreMode: ScoreMode,
//        private val termStates: TermStates,
//        val proximityWeight: Float,
//        val bm25Weight: Float,
//        private val z: Float,
//        boost: Float
//    ) : Weight(query) {
//        private lateinit var term: Term
//        val similarity = searcher.similarity
//
//
//        override fun explain(context: LeafReaderContext, doc: Int): Explanation {
//            val scorer = scorer(context)
//            return if (scorer != null && scorer.iterator().advance(doc) == doc) {
//                Explanation.match(scorer.score(), "Proximity score for document")
//            } else {
//                Explanation.noMatch("No matching terms")
//            }
//        }
//
//        override fun isCacheable(ctx: LeafReaderContext): Boolean {
//            return false
//        }
//
//        override fun scorer(context: LeafReaderContext): Scorer? {
//            val termsPostings = terms.map { term ->
//                val postings = context.reader().postings(term, PostingsEnum.POSITIONS.toInt())
//                term to postings
//            }
//
//            val collectionStats: CollectionStatistics
//            val termStats: TermStatistics?
//            if (scoreMode.needsScores()) {
//                collectionStats = searcher.collectionStatistics(term.field())
//                termStats =
//                    if (termStates.docFreq() > 0)
//                        searcher.termStatistics(term, termStates.docFreq(), termStates.totalTermFreq())
//                    else
//                        null
//            } else {
//                // we do not need the actual stats, use fake stats with docFreq=maxDoc=ttf=1
//                collectionStats = CollectionStatistics(term.field(), 1, 1, 1, 1)
//                termStats = TermStatistics(term.bytes(), 1, 1)
//            }
//
//            return if (termsPostings.all { it.second != null }) {
//                HHProximityScorer(this, similarity, proximityWeight, bm25Weight, termsPostings, context.reader(), z)
//            } else {
//                null
//            }
//        }
//    }
//}