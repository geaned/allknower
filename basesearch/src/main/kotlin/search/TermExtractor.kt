package search

import org.apache.lucene.analysis.Analyzer
import org.apache.lucene.analysis.LowerCaseFilter
import org.apache.lucene.analysis.TokenStream
import org.apache.lucene.analysis.en.PorterStemFilter
import org.apache.lucene.analysis.standard.StandardTokenizer
import org.apache.lucene.analysis.tokenattributes.CharTermAttribute
import org.apache.lucene.index.Term
import java.io.StringReader

class TermExtractor {
    fun ExtractTerms(fieldName: String, queryText: String): List<Term> {
        val terms = mutableListOf<Term>()

        val analyzer = object : Analyzer() {
            override fun createComponents(fieldName: String): TokenStreamComponents {
                val tokenizer = StandardTokenizer()
                var tokenStream: TokenStream = LowerCaseFilter(tokenizer)
                tokenStream = PorterStemFilter(tokenStream)
                return TokenStreamComponents(tokenizer, tokenStream)
            }
        }

        analyzer.tokenStream(fieldName, StringReader(queryText)).use { tokenStream ->
            val charTermAttribute = tokenStream.addAttribute(CharTermAttribute::class.java)

            tokenStream.reset()

            while (tokenStream.incrementToken()) {
                val termText = charTermAttribute.toString()
                terms.add(Term(fieldName, termText))
            }
            tokenStream.end()
        }

        analyzer.close()

        return terms
    }
}