import aws.sdk.kotlin.services.s3.S3Client
import aws.smithy.kotlin.runtime.net.url.Url
import kotlinx.coroutines.runBlocking
import java.io.File

const val BOOTSTRAP_SERVERS = "localhost:9091,localhost:9092,localhost:9093"
const val TOPIC = "crawler_documents"

const val INDEX_DIR = "index/v1"

const val S3_REGION = "ru-central1"
const val S3_ENDPOINT_URL = "https://storage.yandexcloud.net"

fun main(args: Array<String>) = runBlocking {
    val indexFile = File(INDEX_DIR)
    if (indexFile.exists()) {
        indexFile.deleteRecursively()
        println("Directory deleted successfully.")
    }

    val indexer = Indexer(indexFile)

    val consumer = createConsumer(BOOTSTRAP_SERVERS)

    val client = S3Client
        .fromEnvironment {
            region = S3_REGION
            endpointUrl = Url.parse(S3_ENDPOINT_URL)
        }

    val documentConsumer = DocumentConsumer(BOOTSTRAP_SERVERS, TOPIC)


    println("Program arguments: ${args.joinToString()}")
}