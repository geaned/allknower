package org.example.search
//
//import org.apache.lucene.index.IndexReader
//import org.apache.lucene.index.PostingsEnum
//import org.apache.lucene.index.Term
//import org.apache.lucene.search.DocIdSetIterator
//import org.apache.lucene.search.Scorer
//import org.apache.lucene.search.Weight
//import org.apache.lucene.search.similarities.Similarity
//import org.apache.lucene.search.similarities.Similarity.SimScorer
//import java.lang.Math.pow
//import kotlin.math.ln
//
//class HHProximityScorer(
//    weight: Weight,
//    val similarity: Similarity,
//    private val simScorer: SimScorer,
//    private val proximityWeight: Float,
//    private val bm25Weight: Float,
//    private val termsPostings: List<Pair<Term, PostingsEnum>>,
//    private val reader: IndexReader,
//    private val z: Float
//) : Scorer(weight) {
//
//    private val docIterator = termsPostings.first().second
//
//    override fun docID(): Int {
//        return docIterator.docID()
//    }
//
//    override fun iterator(): DocIdSetIterator {
//        return docIterator
//    }
//
//    override fun getMaxScore(upTo: Int): Float {
//        return Float.MAX_VALUE
//    }
//
//    override fun score(): Float {
//        return proximityWeight * proximityScore() + bm25Weight * simScorer.score()
//    }
//
//    fun proximityScore(): Float {
////        return 0f
//
//        val currentDoc = docID()
//        // Получаем IDF для каждого термина
//        val idfs = termsPostings.map { (term, _) ->
//            val df = reader.docFreq(term)
//            val idf = ln((reader.maxDoc() + 1).toDouble() / (df + 1)) + 1.0  // Стандартная формула IDF
//            term to idf
//        }.toMap()
//
//        // Сохраняем позиции каждого термина в документе
//        val termPositions = termsPostings.map { (term, postingsEnum) ->
//            val positions = mutableListOf<Int>()
//            postingsEnum.advance(currentDoc)
//            val freq = postingsEnum.freq()
//            for (i in 0 until freq) {
//                positions.add(postingsEnum.nextPosition())
//            }
//            term to positions
//        }.toMap()
//
//        var totalProximityScore = 0.0
//
//        // Для каждого термина и его позиций в документе рассчитываем "кучность"
//        for ((term, positions) in termPositions) {
//            val idf = idfs[term] ?: 0.0
//            var atc = 0.0
//
//            for (pos in positions) {
//                var tc = 0.0
//                for ((otherTerm, otherPositions) in termPositions) {
//                    if (term == otherTerm) continue  // Фильтруем сам термин
//                    val otherIdf = idfs[otherTerm] ?: 0.0
//
//                    // Рассчитываем минимальные расстояния до других терминов
//                    val lmd = leftMinDistance(pos, otherPositions)
//                    val rmd = rightMinDistance(pos, otherPositions)
//
//                    // Рассчитываем tc(d, t, p) для текущей позиции
//                    tc += (otherIdf / pow(lmd, z.toDouble())) + (otherIdf / pow(rmd, z.toDouble()))
//                }
//                atc += tc
//            }
//
//            // Умножаем на IDF термина и добавляем к суммарной "кучности"
//            totalProximityScore += atc * idf
//        }
//
//        // Финальная оценка HHProximity с логарифмом
//        return ln(1 + totalProximityScore).toFloat()
//    }
//
//    // Функция для нахождения минимального расстояния слева
//    private fun leftMinDistance(pos: Int, otherPositions: List<Int>): Double {
//        return otherPositions.filter { it < pos }.maxOrNull()?.let { (pos - it).toDouble() } ?: Double.MAX_VALUE
//    }
//
//    // Функция для нахождения минимального расстояния справа
//    private fun rightMinDistance(pos: Int, otherPositions: List<Int>): Double {
//        return otherPositions.filter { it > pos }.minOrNull()?.let { (it - pos).toDouble() } ?: Double.MAX_VALUE
//    }
//
//    override fun advanceShallow(target: Int): Int {
//        return docIterator.advance(target)
//    }
//}