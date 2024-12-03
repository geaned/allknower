package archivator

import java.io.*
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

fun addFolderToZip(
    folder: String,
    zipFileName: String = folder.substring(folder.lastIndexOf("/"))
) {

    val folderToZip = File(folder)
    var out: ZipOutputStream? = null
    try {
        out = ZipOutputStream(
            BufferedOutputStream(FileOutputStream(zipFileName))
        )
        recursivelyAddZipEntries(folderToZip, folderToZip.absolutePath, out)
    } catch (e: Exception) {
        println("ZIP Err: ${e.message}")
    } finally {
        out?.close()
    }

}


private fun recursivelyAddZipEntries(
    folder: File,
    basePath: String,
    out: ZipOutputStream
) {

    val files = folder.listFiles() ?: return
    for (file in files) {

        if (file.isDirectory) {
            recursivelyAddZipEntries(file, basePath, out)
        } else {
            val origin = BufferedInputStream(FileInputStream(file))
            origin.use {
                val entryName = file.absolutePath.substring(basePath.length)
                out.putNextEntry(ZipEntry(entryName))
                origin.copyTo(out, 1024)
            }
        }
    }
}