package com.vg.streamdesk

import com.squareup.moshi.Json
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

data class WindowInfo(
    val id: String,
    val title: String
)

data class MediaInfo(
    val title: String,
    val artist: String,
    val status: String,
    val position: Float,
    val duration: Float,
    val player: String,
    val artUrl: String? = null,
    val playerIconUrl: String? = null
)

data class BackupStatus(
    @Json(name = "is_running") val isRunning: Boolean,
    @Json(name = "last_log") val lastLog: String
)

data class SimpleResponse(
    val status: String
)

interface StreamDeskApi {
    @GET("dock/windows")
    suspend fun getWindows(): List<WindowInfo>

    @POST("dock/activate/{id}")
    suspend fun activateWindow(@Path("id") id: String): SimpleResponse

    @GET("media/info")
    suspend fun getMediaInfo(): MediaInfo

    @POST("media/control/{command}")
    suspend fun controlMedia(@Path("command") command: String): SimpleResponse

    @POST("media/seek/{position}")
    suspend fun seekMedia(@Path("position") position: Float): SimpleResponse

    @POST("system/volume/{dir}")
    suspend fun controlVolume(@Path("dir") dir: String): SimpleResponse

    @POST("system/lock")
    suspend fun lockScreen(): SimpleResponse

    @POST("launch/youtube")
    suspend fun launchYoutube(): SimpleResponse

    @POST("launch/zalo")
    suspend fun launchZalo(): SimpleResponse

    @GET("backup/status")
    suspend fun getBackupStatus(): BackupStatus

    @POST("backup/start")
    suspend fun startBackup(): SimpleResponse

    @POST("backup/stop")
    suspend fun stopBackup(): SimpleResponse
}
