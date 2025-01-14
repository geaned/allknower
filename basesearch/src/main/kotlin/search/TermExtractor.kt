package search

import org.apache.lucene.analysis.standard.StandardAnalyzer
import org.apache.lucene.analysis.tokenattributes.CharTermAttribute
import org.apache.lucene.index.Term
import java.io.StringReader

class TermExtractor {
    fun extractTerms(fieldName: String, queryText: String): List<Term> {
        val terms = mutableListOf<Term>()

        val analyzer = StandardAnalyzer()
//        val analyzer = object : Analyzer() {
//            override fun createComponents(fieldName: String): TokenStreamComponents {
//                val tokenizer = StandardTokenizer()
//                val tokenStream = StopFilter(PorterStemFilter(LowerCaseFilter(tokenizer)), EnglishAnalyzer.getDefaultStopSet())
//                return TokenStreamComponents(tokenizer, tokenStream)
//            }
//        }

        analyzer.tokenStream(fieldName, StringReader(queryText)).use { tokenStream ->
            val charTermAttribute = tokenStream.addAttribute(CharTermAttribute::class.java)

            tokenStream.reset()

            while (tokenStream.incrementToken()) {
                terms.add(Term(fieldName, charTermAttribute.toString()))
            }
            tokenStream.end()
        }

        analyzer.close()

        return terms
    }
}