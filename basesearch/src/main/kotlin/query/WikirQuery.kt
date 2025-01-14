package query

import com.google.gson.Gson
import com.google.gson.annotations.SerializedName
import com.google.gson.reflect.TypeToken


data class Query(
    @SerializedName("query_id") val queryId: String,
    @SerializedName("text") val text: String,
) {
    companion object {
        fun fromJson(jsonString: String): Query = Gson().fromJson(jsonString, Query::class.java)
        fun toJson(query: Query): String = Gson().toJson(query)

        fun listFromJson(jsonString: String): List<Query> {
            val typeToken = object : TypeToken<List<Query>>() {}.type
            return Gson().fromJson(jsonString, typeToken)
        }
    }
}

data class Result(
    @SerializedName("query_id") val queryId: String,
    @SerializedName("doc_id") val docId: String,
    @SerializedName("features") val features: List<Float>,
) {
    companion object {
        fun fromJson(jsonString: String): Result = Gson().fromJson(jsonString, Result::class.java)
        fun toJson(result: Result): String = Gson().toJson(result)

        fun listFromJson(jsonString: String): List<Result> {
            val typeToken = object : TypeToken<List<Result>>() {}.type
            return Gson().fromJson(jsonString, typeToken)
        }
        fun listToJson(results: List<Result>): String = Gson().toJson(results)
    }
}

