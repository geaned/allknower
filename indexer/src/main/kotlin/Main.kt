import archivator.addFolderToZip
import aws.sdk.kotlin.runtime.auth.credentials.StaticCredentialsProvider
import aws.sdk.kotlin.services.s3.S3Client
import aws.sdk.kotlin.services.s3.model.GetObjectRequest
import aws.sdk.kotlin.services.s3.putObject
import aws.smithy.kotlin.runtime.content.ByteStream
import aws.smithy.kotlin.runtime.content.fromFile
import aws.smithy.kotlin.runtime.content.writeToFile
import aws.smithy.kotlin.runtime.net.url.Url
import com.sksamuel.hoplite.ConfigLoader
import config.Config
import consumer.DocumentConsumer
import document.WikiDocument
import index.Indexer
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import java.io.File
import java.util.zip.ZipFile

const val configPath = "config/config.yml"

const val ACCESS_KEY_ID = "<ACCESS_KEY_ID>"
const val SECRET_ACCESS_KEY = "<SECRET_ACCESS_KEY>"

fun main(): Unit = runBlocking {
    val config = ConfigLoader().loadConfigOrThrow<Config>(configPath)

    val getRequest = GetObjectRequest {
        bucket = config.s3Config.bucket
        key = config.s3Config.key
    }
    S3Client
        .fromEnvironment {
            region = config.s3Config.region
            endpointUrl = Url.parse(config.s3Config.endpointUrl)
            credentialsProvider = StaticCredentialsProvider {
                accessKeyId = ACCESS_KEY_ID
                secretAccessKey = SECRET_ACCESS_KEY
            }
        }
        .use { s3 ->
            s3.getObject(getRequest) { resp ->
                val myFile = File(config.indexArchiveFile)
                resp.body?.writeToFile(myFile)
                println("Successfully read!")
            }
        }

    val indexDirectory = File(config.indexDirectory)
    if (indexDirectory.exists()) {
        indexDirectory.deleteRecursively()
        println("Directory deleted successfully.")
    }

    val zipFileName = config.s3Config.key
    ZipFile(zipFileName).use { zip ->
        zip.entries().asSequence().forEach { entry ->
            zip.getInputStream(entry).use { input ->
                File("${config.indexDirectory}/${entry.name}").outputStream().use { output ->
                    input.copyTo(output)
                }
            }
        }
    }

    val documentChannel = Channel<List<WikiDocument>>()
    val indexer = Indexer(indexDirectory)
    val documentConsumer = DocumentConsumer(documentChannel, config.documentConsumerConfig)

    coroutineScope {
        launch { documentConsumer.Consume(config.documentTopic) }

        launch { documentIndexing(documentChannel, indexer, config) }
    }.join()

    documentChannel.close()
}

suspend fun documentIndexing(
    documentChannel: Channel<List<WikiDocument>>,
    indexer: Indexer,
    config: Config,
) {
    for (documents in documentChannel) {
        indexer.UpdateIndex(documents)

        addFolderToZip(config.indexDirectory, config.indexArchiveFile)

        coroutineScope {
            launch {
                S3Client
                    .fromEnvironment {
                        region = config.s3Config.region
                        endpointUrl = Url.parse(config.s3Config.endpointUrl)
                        credentialsProvider = StaticCredentialsProvider {
                            accessKeyId = ACCESS_KEY_ID
                            secretAccessKey = SECRET_ACCESS_KEY
                        }
                    }
                    .use { s3 ->
                        s3.putObject {
                            bucket = config.s3Config.bucket
                            key = config.s3Config.key
                            body = ByteStream.fromFile(File(config.indexArchiveFile))
                        }
                    }
            }
        }
    }
}
