package search

//import org.apache.lucene.search.similarities.BasicStats
//import org.apache.lucene.search.similarities.SimilarityBase
//import kotlin.math.ln
//
//
//class MySimilarity : SimilarityBase() {
//    override fun toString(): String {
//        TODO("Not yet implemented")
//    }
//
//    override fun score(stats: BasicStats?, freq: Double, docLen: Double): Double {
//        TODO("Not yet implemented")
//    }
//}



//class HHProximitySimilarity : Similarity() {
//
//    override fun computeWeight(
//        collectionStats: Similarity.CollectionStatistics?,
//        vararg termStats: Similarity.TermStatistics?
//    ): SimWeight {
//        return object : SimWeight() {}
//    }
//
//    override fun simScorer(
//        weight: SimWeight?,
//        context: org.apache.lucene.index.LeafReaderContext
//    ): SimScorer {
//        val reader = context.reader()
//        return object : SimScorer() {
//            override fun score(doc: Int, freq: Float): Float {
//                val hhProximity = calculateHHProximity(doc, reader)
//                return hhProximity
//            }
//
//            override fun computeSlopFactor(distance: Int): Float {
//                return 1f / (1 + distance) // Чем меньше расстояние, тем выше оценка.
//            }
//
//            override fun computePayloadFactor(
//                doc: Int,
//                start: Int,
//                end: Int,
//                payload: BytesRef?
//            ): Float {
//                return 1f
//            }
//        }
//    }
//
//    override fun computeNorm(state: FieldInvertState?): Long {
//        return 1L
//    }
//
//    private fun calculateHHProximity(docId: Int, reader: org.apache.lucene.index.LeafReader): Float {
//        val termVectors = reader.getTermVector(docId, "content")
//        if (termVectors != null) {
//            val termsEnum = termVectors.iterator()
//            val termPositions = mutableMapOf<String, MutableList<Int>>()
//
//            // Собираем позиции термов
//            while (termsEnum.next() != null) {
//                val term = termsEnum.term().utf8ToString()
//                val postings = termsEnum.postings(null, PostingsEnum.POSITIONS)
//                val positions = mutableListOf<Int>()
//                while (postings.nextDoc() != PostingsEnum.NO_MORE_DOCS) {
//                    for (i in 0 until postings.freq()) {
//                        positions.add(postings.nextPosition())
//                    }
//                }
//                termPositions[term] = positions
//            }
//
//            // Вычисляем HHProximity
//            return calculateProximity(termPositions)
//        }
//        return 0f
//    }
//
//    private fun calculateProximity(termPositions: Map<String, MutableList<Int>>): Float {
//        var proximityScore = 0.0
//        val terms = termPositions.keys.toList()
//
//        // Считаем расстояния между всеми парами термов
//        for (i in terms.indices) {
//            for (j in i + 1 until terms.size) {
//                val positions1 = termPositions[terms[i]] ?: continue
//                val positions2 = termPositions[terms[j]] ?: continue
//
//                for (pos1 in positions1) {
//                    for (pos2 in positions2) {
//                        val distance = kotlin.math.abs(pos1 - pos2)
//                        proximityScore += exp(-distance.toDouble()) // Функция убывания
//                    }
//                }
//            }
//        }
//        return proximityScore.toFloat()
//    }
//}

//import org.apache.lucene.index.FieldInvertState
//import org.apache.lucene.index.LeafReader
//import org.apache.lucene.index.PostingsEnum
//import org.apache.lucene.search.CollectionStatistics
//import org.apache.lucene.search.TermStatistics
//import org.apache.lucene.search.similarities.Similarity
//import org.apache.lucene.util.BytesRef
//import kotlin.math.exp
//
//class HHProximitySimilarity : Similarity() {
//
//    override fun computeNorm(state: FieldInvertState): Long {
//        // Возвращаем нормировку (можно использовать длину документа)
//        return state.length.toLong()
//    }
//
//    override fun scorer(
//        boost: Float,
//        collectionStats: CollectionStatistics?,
//        termStats: Array<TermStatistics>
//    ): SimScorer {
//        return object : SimScorer() {
//            override fun score(
//                leafReader: LeafReader,
//                doc: Int,
//                freq: Float
//            ): Float {
//                // Вычисляем HHProximity для документа
//                return calculateHHProximity(doc, leafReader, termStats).toFloat()
//            }
//
//            override fun computeSlopFactor(distance: Int): Float {
//                return 1f / (1 + distance) // Чем меньше расстояние, тем выше оценка
//            }
//
//            override fun computePayloadFactor(doc: Int, start: Int, end: Int, payload: BytesRef?): Float {
//                return 1f // Не используем payload
//            }
//
//            override fun score(freq: Float, norm: Long): Float {
//                TODO("Not yet implemented")
//            }
//        }
//    }
//
//    private fun calculateHHProximity(
//        docId: Int,
//        reader: LeafReader,
//        collectionStats: CollectionStatistics,
//        termStats: Array<TermStatistics>
//    ): Double {
//        val termsEnum = termStats.iterator()
//        val termPositions = mutableMapOf<String, MutableList<Int>>()
//
//        while (termsEnum.hasNext()) {
//            val term = termsEnum.next().term().utf8ToString()
//
//            val postings = reader.postings(term, PostingsEnum.POSITIONS.toInt())
//            val positions = mutableListOf<Int>()
//            while (postings.nextDoc() != PostingsEnum.NO_MORE_DOCS) {
//                for (i in 0 until postings.freq()) {
//                    positions.add(postings.nextPosition())
//                }
//            }
//            termPositions[term] = positions
//        }
//
//
//
//        val termVectors = reader.getTermVector(docId, "content")
//        if (termVectors != null) {
//            val termsEnum = termVectors.iterator()
//            val termPositions = mutableMapOf<String, MutableList<Int>>()
//
//            // Собираем позиции термов
//            while (termsEnum.next() != null) {
//                val term = termsEnum.term().utf8ToString()
//                val postings = termsEnum.postings(null, PostingsEnum.POSITIONS.toInt())
//                val positions = mutableListOf<Int>()
//                postings?.let {
//                    while (it.nextDoc() != PostingsEnum.NO_MORE_DOCS) {
//                        for (i in 0 until it.freq()) {
//                            positions.add(it.nextPosition())
//                        }
//                    }
//                }
//                termPositions[term] = positions
//            }
//
//            // Вычисляем HHProximity
//            return calculateProximity(termPositions)
//        }
//        return 0.0
//    }
//
//    private fun calculateProximity(termPositions: Map<String, MutableList<Int>>): Double {
//        var proximityScore = 0.0
//        val terms = termPositions.keys.toList()
//
//        // Считаем расстояния между всеми парами термов
//        for (i in terms.indices) {
//            for (j in i + 1 until terms.size) {
//                val positions1 = termPositions[terms[i]] ?: continue
//                val positions2 = termPositions[terms[j]] ?: continue
//
//                for (pos1 in positions1) {
//                    for (pos2 in positions2) {
//                        val distance = kotlin.math.abs(pos1 - pos2)
//                        proximityScore += exp(-distance.toDouble()) // Функция убывания
//                    }
//                }
//            }
//        }
//        return proximityScore
//    }
//}