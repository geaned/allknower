import com.google.gson.Gson
import com.google.gson.annotations.SerializedName
import com.google.gson.reflect.TypeToken

data class WikiDocument(
    @SerializedName("doc_id") val docId: String,
    @SerializedName("page_url") val pageUrl: String,
    @SerializedName("title") val title: String,
    @SerializedName("contents") val contents: List<Content>,
    @SerializedName("images") val images: List<Image>,
    @SerializedName("references") val references: List<WikiDocument>,
    @SerializedName("categories") val categories: List<String>
) {
    companion object {
        fun fromJson(jsonString: String): WikiDocument = Gson().fromJson(jsonString, WikiDocument::class.java)
        fun toJson(document: WikiDocument): String = Gson().toJson(document)

        fun listFromJson(jsonString: String): List<WikiDocument> {
            val typeToken = object : TypeToken<List<WikiDocument>>() {}.type
            return Gson().fromJson(jsonString, typeToken)
        }
    }
}

data class Content(
    @SerializedName("content_id") val contentId: String, // UUIDv9
    @SerializedName("content") val content: String
)

data class Image(
    @SerializedName("image_id") val imageId: String, // UUIDv9
    @SerializedName("image") val image: String // Base64-encoded image
)