package index

import document.WikiDocument

abstract class Indexer {
    abstract fun updateIndex(documents: List<WikiDocument>)
}