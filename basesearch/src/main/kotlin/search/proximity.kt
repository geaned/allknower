package org.example.search
//
//import org.apache.lucene.index.FieldInvertState
//import org.apache.lucene.index.IndexReader
//import org.apache.lucene.index.PostingsEnum
//import org.apache.lucene.search.CollectionStatistics
//import org.apache.lucene.search.TermStatistics
//import org.apache.lucene.search.similarities.BasicStats
//import org.apache.lucene.search.similarities.Similarity
//import org.apache.lucene.search.similarities.ClassicSimilarity
//import org.apache.lucene.search.similarities.Similarity.SimScorer
//import org.apache.lucene.search.similarities.SimilarityBase
//import org.apache.lucene.util.BytesRef
//import kotlin.math.ln
//import kotlin.math.log
//import kotlin.math.pow
//
//
//class MyScorer : SimScorer() {
//    override fun score(freq: Float, norm: Long): Float {
//        val explain = this.explain(freq, norm)
//
//    }
//
//}
//
//
//class MyProximity : SimilarityBase() {
//    override fun toString(): String {
//        TODO("Not yet implemented")
//    }
//
//    override fun score(stats: BasicStats?, freq: Double, docLen: Double): Double {
//        if (stats != null) {
//        }
//        TODO("Not yet implemented")
//    }
//
//}
//
//class HHProximitySimilarity(private val indexReader: IndexReader) : Similarity() {
//
//    private val z: Double = 1.75 // Константа z, как указано в формуле
//
//    override fun computeNorm(state: FieldInvertState?): Long {
//        // Нормализация длины поля. Можно просто вернуть 1 в случае, если длина поля
//        // не влияет на расчет HHProximity, или использовать state.length().
//        return 1L
//    }
//
//    override fun scorer(
//        boost: Float,
//        collectionStats: CollectionStatistics?,
//        vararg termStats: TermStatistics?
//    ): SimScorer {
//        // Реализация вычисления оценки HHProximity
//        return HHProximityScorer(boost, collectionStats, termStats)
//    }
//
//    private inner class HHProximityScorer(
//        private val boost: Float,
//        private val collectionStats: CollectionStatistics?,
//        private val termStats: Array<out TermStatistics?>
//    ) : SimScorer() {
//
//        // Оценка idf для терма
//        private fun idf(termFreq: Long, docFreq: Long, docCount: Long): Double {
//            return ln(1.0 + (docCount.toDouble() / (docFreq + 1.0)))
//        }
//
//        // Вычисление расстояния между позициями слова
//        private fun proximityDistance(position1: Int, position2: Int): Int {
//            return kotlin.math.abs(position1 - position2)
//        }
//
//        // Вычисление функции tc(d, t, p) для заданной позиции
//        private fun computeTC(
//            docPositions: Map<String, List<Int>>, // Позиции слов в документе
//            queryTerms: List<String>,             // Слова запроса
//            targetTerm: String,                   // Целевое слово t
//            targetPosition: Int                   // Позиция p в документе
//        ): Double {
//            var tc = 0.0
//            for (queryTerm in queryTerms) {
//                if (queryTerm == targetTerm) continue // Игнорируем влияние самого терма
//                val idfValue = idfForTerm(queryTerm)
//                val positions = docPositions[queryTerm] ?: continue
//
//                // Найти минимальные расстояния слева (lmd) и справа (rmd)
//                val lmd = positions.filter { it < targetPosition }
//                    .minOfOrNull { proximityDistance(targetPosition, it) } ?: Int.MAX_VALUE
//                val rmd = positions.filter { it > targetPosition }
//                    .minOfOrNull { proximityDistance(targetPosition, it) } ?: Int.MAX_VALUE
//
//                // Вычисление tc по формуле
//                tc += idfValue * (
//                        (1.0 / lmd.toDouble().pow(z)) +
//                                (1.0 / rmd.toDouble().pow(z))
//                        )
//            }
//            return tc
//        }
//
//        // Вычисление atc(d, t) для терма t
//        private fun computeATC(
//            docPositions: Map<String, List<Int>>, // Позиции слов в документе
//            queryTerms: List<String>,             // Слова запроса
//            targetTerm: String                    // Целевое слово t
//        ): Double {
//            val positions = docPositions[targetTerm] ?: return 0.0
//            var atc = 0.0
//            for (position in positions) {
//                atc += computeTC(docPositions, queryTerms, targetTerm, position)
//            }
//            return atc
//        }
//
//        // Вычисление idf для терма (с использованием статистики)
//        private fun idfForTerm(term: String): Double {
//            val termStat = termStats.find { it?.term()?.utf8ToString() == term }
//            if (termStat != null && collectionStats != null) {
//                return idf(
//                    termStat.totalTermFreq(),
//                    termStat.docFreq(),
//                    collectionStats.docCount()
//                )
//            }
//            return 0.0
//        }
//
//        // Основной метод для вычисления оценки документа
//        override fun score(docId: Int, freq: Float): Float {
//            // Здесь мы предполагаем, что информация о позициях термов в документе доступна.
//            // В реальной реализации нужно будет использовать Lucene для получения позиций слов.
//            val docPositions = getDocumentPositions(docId) // Позиции слов в документе (требует реализации)
//            val queryTerms = termStats.mapNotNull { it?.term()?.utf8ToString() } // Слова запроса
//
//            // HHProximity по формуле
//            var hhProximity = 0.0
//            for (queryTerm in queryTerms) {
//                val atc = computeATC(docPositions, queryTerms, queryTerm)
//                val idfValue = idfForTerm(queryTerm)
//                hhProximity += atc * idfValue
//            }
//
//            // Применяем log из формулы HHProximity
//            hhProximity = ln(1.0 + hhProximity)
//
//            // Учитываем boost (усиление от внешних факторов поиска)
//            return (boost * hhProximity).toFloat()
//        }
//
//        private fun getDocumentPositions(docId: Int): Map<String, List<Int>> {
//            val termPositions = mutableMapOf<String, MutableList<Int>>()
//
//            // Получаем TermVector для документа
//            val termVector = indexReader.getTermVector(docId, "content") // "content" — поле с текстом
//            if (termVector != null) {
//                val termsEnum = termVector.iterator()
//                while (true) {
//                    val term = termsEnum.next() ?: break
//                    val positions = mutableListOf<Int>()
//
//                    // Извлекаем позиции терма (если доступны позиции)
//                    val postingsEnum = termsEnum.postings(null, PostingsEnum.POSITIONS.toInt())
//                    postingsEnum?.let {
//                        while (it.nextDoc() != PostingsEnum.NO_MORE_DOCS) {
//                            for (i in 0 until it.freq()) {
//                                positions.add(it.nextPosition())
//                            }
//                        }
//                    }
//                    termPositions[term.utf8ToString()] = positions
//                }
//            }
//
//            return termPositions
//        }
//
//        override fun score(freq: Float, norm: Long): Float {
//            TODO("Not yet implemented")
//        }
//    }
//}