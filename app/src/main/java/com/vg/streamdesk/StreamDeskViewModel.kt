package com.vg.streamdesk

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory

class StreamDeskViewModel : ViewModel() {

    private val moshi = Moshi.Builder()
        .add(KotlinJsonAdapterFactory())
        .build()

    // Sử dụng localhost:8999 vì adb reverse sẽ map cổng này
    private val api = Retrofit.Builder()
        .baseUrl("http://127.0.0.1:8999/")
        .addConverterFactory(MoshiConverterFactory.create(moshi))
        .build()
        .create(StreamDeskApi::class.java)

    private val _mediaInfo = MutableStateFlow<MediaInfo?>(null)
    val mediaInfo: StateFlow<MediaInfo?> = _mediaInfo.asStateFlow()

    private val _windows = MutableStateFlow<List<WindowInfo>>(emptyList())
    val windows: StateFlow<List<WindowInfo>> = _windows.asStateFlow()

    private val _backupStatus = MutableStateFlow<BackupStatus?>(null)
    val backupStatus: StateFlow<BackupStatus?> = _backupStatus.asStateFlow()

    init {
        startPolling()
    }

    private fun startPolling() {
        viewModelScope.launch {
            while (true) {
                try {
                    _mediaInfo.value = api.getMediaInfo()
                    _windows.value = api.getWindows()
                    _backupStatus.value = api.getBackupStatus()
                } catch (e: Exception) {
                    e.printStackTrace()
                }
                delay(2000) // Poll mỗi 2 giây
            }
        }
    }

    fun controlMedia(command: String) {
        viewModelScope.launch {
            try { api.controlMedia(command) } catch (e: Exception) {}
        }
    }

    fun seekMedia(position: Float) {
        viewModelScope.launch {
            try { api.seekMedia(position) } catch (e: Exception) {}
        }
    }

    fun controlVolume(dir: String) {
        viewModelScope.launch {
            try { api.controlVolume(dir) } catch (e: Exception) {}
        }
    }

    fun lockScreen() {
        viewModelScope.launch {
            try { api.lockScreen() } catch (e: Exception) {}
        }
    }

    fun activateWindow(id: String) {
        viewModelScope.launch {
            try { api.activateWindow(id) } catch (e: Exception) {}
        }
    }

    fun launchYoutube() {
        viewModelScope.launch {
            try { api.launchYoutube() } catch (e: Exception) {}
        }
    }

    fun launchZalo() {
        viewModelScope.launch {
            try { api.launchZalo() } catch (e: Exception) {}
        }
    }

    fun startBackup() {
        viewModelScope.launch { try { api.startBackup() } catch (e: Exception) { e.printStackTrace() } }
    }

    fun stopBackup() {
        viewModelScope.launch { try { api.stopBackup() } catch (e: Exception) { e.printStackTrace() } }
    }
}
