class FeatureCalculator {
    // Function to calculate n-gram coverage between query and document tokens
    private fun calculateQueryTokenNgramCoverage(queryTokens: List<String>, docTokens: List<String>, n: Int = 1): Pair<Int, Float> {
        if (n > minOf(queryTokens.size, docTokens.size)) {
            return Pair(0, 0f)
        }

        val queryNgramCounter = mutableMapOf<List<String>, Int>()
        for (i in 0 until queryTokens.size - n + 1) {
            queryNgramCounter[queryTokens.subList(i, i + n)] = 0
        }

        for (i in 0 until docTokens.size - n + 1) {
            val docNgram = docTokens.subList(i, i + n)
            if (queryNgramCounter.containsKey(docNgram) && queryNgramCounter[docNgram] == 0) {
                queryNgramCounter[docNgram] = 1
            }
        }

        val queryTokenNgramCoverage = queryNgramCounter.values.sum()
        return Pair(queryTokenNgramCoverage, queryTokenNgramCoverage.toFloat() / queryNgramCounter.size)
    }

    // Function to calculate the first occurrence of query tokens in the document
    private fun calculateQueryTokenFirstOccurrence(queryTokens: List<String>, docTokens: List<String>): Pair<Int, Float> {
        var firstOccurrence = docTokens.size
        for (i in docTokens.indices) {
            if (docTokens[i] in queryTokens) {
                firstOccurrence = i
                break
            }
        }
        return Pair(firstOccurrence, firstOccurrence.toFloat() / docTokens.size)
    }

    // Function to calculate features for a document
    fun calculateFeaturesByDoc(
        queryTokens: List<String>,
        docTokens: List<String>,
    ): List<Float> {
        val docLength = docTokens.size
        val (queryTokenFirstOccurrenceUnnormalized, queryTokenFirstOccurrenceNormalized) = calculateQueryTokenFirstOccurrence(queryTokens, docTokens)
        val (queryTokenLastOccurrenceUnnormalized, _) = calculateQueryTokenFirstOccurrence(queryTokens, docTokens.reversed())
        val queryTokenLastOccurrenceUnnormalizedAdjusted = docLength - 1 - queryTokenLastOccurrenceUnnormalized
        val queryTokenLastOccurrenceNormalized = queryTokenLastOccurrenceUnnormalizedAdjusted.toFloat() / docLength
        val spanLengthUnnormalized = queryTokenLastOccurrenceUnnormalizedAdjusted - queryTokenFirstOccurrenceUnnormalized + 1
        val spanLengthNormalized = spanLengthUnnormalized.toFloat() / docLength

        val (unigramCoverageUnnormalized, unigramCoverageNormalized) = calculateQueryTokenNgramCoverage(queryTokens, docTokens, n = 1)
        val (bigramCoverageUnnormalized, bigramCoverageNormalized) = calculateQueryTokenNgramCoverage(queryTokens, docTokens, n = 2)
        val (trigramCoverageUnnormalized, trigramCoverageNormalized) = calculateQueryTokenNgramCoverage(queryTokens, docTokens, n = 1)



        return listOf(
            0f, // Placeholder for BM25 score (implement if needed)
            0f, // Placeholder for HHProximity score (implement if needed)
            queryTokens.size.toFloat(),
            docLength.toFloat(),
            unigramCoverageUnnormalized.toFloat(),
            unigramCoverageNormalized,
            bigramCoverageUnnormalized.toFloat(),
            bigramCoverageNormalized,
            trigramCoverageUnnormalized.toFloat(),
            trigramCoverageNormalized,
            queryTokenFirstOccurrenceUnnormalized.toFloat(),
            queryTokenFirstOccurrenceNormalized,
            queryTokenLastOccurrenceUnnormalizedAdjusted.toFloat(),
            queryTokenLastOccurrenceNormalized,
            spanLengthUnnormalized.toFloat(),
            spanLengthNormalized
        )
    }

    fun calculateStatistics(values: List<Float>): List<Float> {
        val maxValue: Float = values.maxOrNull() ?: Float.NEGATIVE_INFINITY
        val minValue = values.minOrNull() ?: Float.POSITIVE_INFINITY
        val meanValue = values.average().toFloat()
        val medianValue = median(values)

        return listOf(maxValue, minValue, meanValue, medianValue)
    }

    // Helper function to compute the median of a list
    private fun median(values: List<Float>): Float {
        val sortedValues = values.sorted()
        val size = sortedValues.size
        return if (size % 2 == 0) {
            (sortedValues[size / 2 - 1] + sortedValues[size / 2]) / 2
        } else {
            sortedValues[size / 2]
        }
    }

    fun minMaxScale(values: List<Float>, min: Float, max: Float): List<Float> {
        return values.map { (it - min) / (max - min + 1e-9f) }
    }
}
