package com.vg.streamdesk
import com.vg.streamdesk.R

import androidx.compose.foundation.background
import androidx.compose.foundation.basicMarquee
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.automirrored.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.blur
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle

import androidx.compose.ui.platform.LocalConfiguration
import android.content.res.Configuration
import androidx.compose.foundation.BorderStroke
import androidx.compose.ui.graphics.vector.rememberVectorPainter
import androidx.compose.ui.layout.ContentScale
import coil.compose.AsyncImage
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.platform.LocalContext
import android.app.Activity
import android.content.Intent
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.input.pointer.PointerEventPass
import kotlinx.coroutines.delay

val SpotifyBlack = Color(0xFF050F0C)
val SpotifyDarkGreen = Color(0xFF12241E)
val SpotifyLightGreen = Color(0xFF1DB954)
val SpotifyGray = Color(0xFFB3B3B3)

@OptIn(ExperimentalMaterial3Api::class, ExperimentalFoundationApi::class)
@Composable
fun MainScreen(viewModel: StreamDeskViewModel) {
    val mediaInfo by viewModel.mediaInfo.collectAsStateWithLifecycle()
    val windows by viewModel.windows.collectAsStateWithLifecycle()
    val backupStatus by viewModel.backupStatus.collectAsStateWithLifecycle()
    
    val pagerState = rememberPagerState(pageCount = { 3 })
    val coroutineScope = rememberCoroutineScope()
    
    // Track last interaction time
    var lastInteractionTime by remember { mutableLongStateOf(System.currentTimeMillis()) }
    
    // Auto-switch to Media Page if idle for 10s and playing
    LaunchedEffect(mediaInfo?.status) {
        while (true) {
            delay(1000)
            val currentTime = System.currentTimeMillis()
            if (currentTime - lastInteractionTime >= 10000) {
                if (mediaInfo?.status == "Playing" && pagerState.currentPage != 1) {
                    pagerState.animateScrollToPage(1)
                }
            }
        }
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(SpotifyBlack)
            .pointerInput(Unit) {
                awaitPointerEventScope {
                    while (true) {
                        awaitPointerEvent(PointerEventPass.Initial)
                        lastInteractionTime = System.currentTimeMillis()
                    }
                }
            }
    ) {
        val context = LocalContext.current
        
        HorizontalPager(
            state = pagerState,
            modifier = Modifier.fillMaxSize()
        ) { page ->
            // Mỗi trang sẽ được bọc trong vùng Safe Area chuẩn
            Box(modifier = Modifier.fillMaxSize().windowInsetsPadding(WindowInsets.safeDrawing)) {
                when (page) {
                    0 -> DeckPage(windows, mediaInfo, viewModel) { targetPage ->
                        coroutineScope.launch { pagerState.animateScrollToPage(targetPage) }
                    }
                    1 -> MediaPage(mediaInfo, viewModel)
                    2 -> BackupPage(backupStatus, viewModel)
                }
            }
        }

        // App Logo at Top-Center to minimize
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 12.dp),
            contentAlignment = Alignment.TopCenter
        ) {
            AsyncImage(
                model = R.drawable.app_logo, // We will create this
                contentDescription = "Minimize",
                modifier = Modifier
                    .size(40.dp)
                    .clickable {
                        val intent = Intent(Intent.ACTION_MAIN).apply {
                            addCategory(Intent.CATEGORY_HOME)
                            flags = Intent.FLAG_ACTIVITY_NEW_TASK
                        }
                        context.startActivity(intent)
                    }
            )
        }
    }
}

@Composable
fun DeckPage(
    windows: List<WindowInfo>, 
    mediaInfo: MediaInfo?, 
    viewModel: StreamDeskViewModel,
    onNavigate: (Int) -> Unit
) {
    BoxWithConstraints(
        modifier = Modifier
            .fillMaxSize()
            .padding(8.dp) // Padding nội bộ nhẹ nhàng
    ) {
        val screenWidth = maxWidth
        val screenHeight = maxHeight
        
        val itemsCount = 5 + windows.size
        val columns = if (screenWidth > screenHeight) 7 else 4
        val rows = Math.ceil(itemsCount.toDouble() / columns).toInt()
        
        val horizontalGap = 16.dp
        val verticalGap = 16.dp
        
        val labelOverhead = 24.dp
        val totalVerticalGaps = verticalGap * (rows - 1)
        val availableHeightForIcons = screenHeight - (labelOverhead * rows) - totalVerticalGaps - 4.dp
        
        val heightBasedSize = availableHeightForIcons / rows
        val widthBasedSize = (screenWidth - (horizontalGap * (columns - 1))) / columns
        
        val itemSize = minOf(widthBasedSize, heightBasedSize).coerceIn(56.dp, 100.dp)
        
        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            LazyVerticalGrid(
                columns = GridCells.Fixed(columns),
                modifier = Modifier.width(itemSize * columns + horizontalGap * (columns - 1)),
                userScrollEnabled = false,
                horizontalArrangement = Arrangement.spacedBy(horizontalGap, Alignment.CenterHorizontally),
                verticalArrangement = Arrangement.spacedBy(verticalGap, Alignment.CenterVertically)
            ) {
                item { DeckIconButton("Lock", Icons.Default.Lock, Color(0xFFFF5F6D), itemSize) { viewModel.lockScreen() } }
                item { DeckIconButton("Vol Up", Icons.Default.VolumeUp, SpotifyLightGreen, itemSize) { viewModel.controlVolume("up") } }
                item { DeckIconButton("Vol Down", Icons.Default.VolumeDown, SpotifyLightGreen, itemSize) { viewModel.controlVolume("down") } }
                item { 
                    DeckIconButton("YouTube", Icons.Default.PlayArrow, Color(0xFFFF0200), itemSize) { 
                        viewModel.launchYoutube() 
                        onNavigate(1)
                    } 
                }
                item { 
                    DeckLaunchButton("Zalo", "https://cdn.haitrieu.com/wp-content/uploads/2022/01/Logo-Zalo-Arc.png", itemSize) { 
                        viewModel.launchZalo() 
                    } 
                }
                items(windows) { window ->
                    DeckWindowButton(window, itemSize) { 
                        viewModel.activateWindow(window.id)
                        // If this window is likely the current media player, switch to Media tab
                        val currentPlayer = mediaInfo?.player?.lowercase() ?: ""
                        if (currentPlayer.isNotEmpty() && (
                            window.title.lowercase().contains(currentPlayer) || 
                            currentPlayer.contains(window.title.lowercase())
                        )) {
                            onNavigate(1)
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun MediaPage(info: MediaInfo?, viewModel: StreamDeskViewModel) {
    // Slider Seek State
    var sliderValue by remember { mutableStateOf(0f) }
    var isDragging by remember { mutableStateOf(false) }

    LaunchedEffect(info) {
        if (!isDragging && info != null && info.duration > 0) {
            sliderValue = info.position / info.duration
        }
    }

    Box(modifier = Modifier.fillMaxSize()) {
        AsyncImage(
            model = info?.artUrl ?: "http://127.0.0.1:8999/media/art",
            contentDescription = null,
            modifier = Modifier.fillMaxSize().blur(100.dp),
            contentScale = ContentScale.Crop,
            alpha = 0.3f
        )
        
        Box(modifier = Modifier.fillMaxSize().background(SpotifyBlack.copy(alpha = 0.7f)))

        Row(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp), 
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(40.dp)
        ) {
            // Album Art - Kích thước hài hòa (75% Safe Height)
            Card(
                modifier = Modifier.fillMaxHeight(0.75f).aspectRatio(1f),
                shape = RoundedCornerShape(16.dp),
                elevation = CardDefaults.cardElevation(defaultElevation = 24.dp)
            ) {
                AsyncImage(
                    model = info?.artUrl ?: "http://127.0.0.1:8999/media/art",
                    contentDescription = null,
                    modifier = Modifier.fillMaxSize(),
                    contentScale = ContentScale.Crop
                )
            }
            
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = info?.title ?: "No Media Playing",
                    fontSize = 28.sp,
                    fontWeight = FontWeight.Bold,
                    color = SpotifyLightGreen,
                    maxLines = 1,
                    modifier = Modifier.basicMarquee(iterations = Int.MAX_VALUE)
                )
                Text(info?.artist ?: "Unknown Artist", fontSize = 18.sp, color = SpotifyLightGreen.copy(alpha = 0.7f))
                
                Spacer(modifier = Modifier.height(24.dp))
                
                Column {
                    Slider(
                        value = sliderValue,
                        onValueChange = { 
                            isDragging = true
                            sliderValue = it 
                        },
                        onValueChangeFinished = {
                            isDragging = false
                            viewModel.seekMedia(sliderValue)
                        },
                        enabled = true,
                        colors = SliderDefaults.colors(thumbColor = SpotifyLightGreen, activeTrackColor = SpotifyLightGreen, inactiveTrackColor = Color.White.copy(alpha = 0.1f)),
                        modifier = Modifier.height(12.dp)
                    )
                    Row(modifier = Modifier.fillMaxWidth().padding(top = 4.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text(formatTime(info?.position?.toInt() ?: 0), color = SpotifyGray, fontSize = 11.sp)
                        Text(formatTime(info?.duration?.toInt() ?: 0), color = SpotifyGray, fontSize = 11.sp)
                    }
                }

                Spacer(modifier = Modifier.height(24.dp))

                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.Center,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    IconButton(onClick = { viewModel.controlMedia("previous") }) {
                        Icon(Icons.Filled.SkipPrevious, null, tint = SpotifyLightGreen, modifier = Modifier.size(56.dp))
                    }
                    Spacer(modifier = Modifier.width(32.dp))
                    FloatingActionButton(
                        onClick = { viewModel.controlMedia("play-pause") },
                        containerColor = SpotifyLightGreen,
                        contentColor = Color.Black,
                        shape = CircleShape,
                        modifier = Modifier.size(72.dp)
                    ) {
                        Icon(if (info?.status == "Playing") Icons.Default.Pause else Icons.Default.PlayArrow, null, modifier = Modifier.size(40.dp))
                    }
                    Spacer(modifier = Modifier.width(32.dp))
                    IconButton(onClick = { viewModel.controlMedia("next") }) {
                        Icon(Icons.Filled.SkipNext, null, tint = SpotifyLightGreen, modifier = Modifier.size(56.dp))
                    }
                }
            }
        }
    }
}

@Composable
fun BackupPage(status: BackupStatus?, viewModel: StreamDeskViewModel) {
    Row(
        modifier = Modifier.fillMaxSize().padding(32.dp),
        horizontalArrangement = Arrangement.spacedBy(32.dp)
    ) {
        Column(modifier = Modifier.weight(0.35f), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Text("SYSTEM BACKUP", fontSize = 12.sp, fontWeight = FontWeight.Black, color = SpotifyLightGreen)
            
            Box(
                modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(8.dp)).background(SpotifyDarkGreen).padding(16.dp),
                contentAlignment = Alignment.Center
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(modifier = Modifier.size(8.dp).clip(CircleShape).background(if (status?.isRunning == true) SpotifyLightGreen else Color.Red))
                    Spacer(modifier = Modifier.width(12.dp))
                    Text(if (status?.isRunning == true) "RUNNING" else "STOPPED", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                }
            }

            Button(
                onClick = { viewModel.startBackup() },
                modifier = Modifier.fillMaxWidth().height(90.dp),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(containerColor = SpotifyLightGreen, contentColor = Color.Black)
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Icon(Icons.Default.Upload, null, modifier = Modifier.size(28.dp))
                    Text("START TRIGGER", fontWeight = FontWeight.Black)
                }
            }
            
            Button(
                onClick = { viewModel.stopBackup() },
                modifier = Modifier.fillMaxWidth().height(64.dp),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF282828), contentColor = Color.White)
            ) {
                Text("KILL PROCESS", fontWeight = FontWeight.Bold)
            }
        }

        Card(
            modifier = Modifier.weight(0.65f).fillMaxHeight(),
            colors = CardDefaults.cardColors(containerColor = Color(0xFF121212)),
            shape = RoundedCornerShape(12.dp),
            border = BorderStroke(1.dp, Color.White.copy(alpha = 0.1f))
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text("BACKUP LOGS", color = SpotifyLightGreen, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                Spacer(modifier = Modifier.height(8.dp))
                Box(modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState())) {
                    Text(status?.lastLog ?: "Waiting for logs...", color = Color(0xFFBBBBBB), fontSize = 11.sp, fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace)
                }
            }
        }
    }
}

@Composable
fun DeckIconButton(text: String, icon: ImageVector, color: Color, size: androidx.compose.ui.unit.Dp, onClick: () -> Unit) {
    Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.width(size)) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .aspectRatio(1f)
                .clip(RoundedCornerShape(12.dp))
                .background(SpotifyDarkGreen)
                .clickable { onClick() },
            contentAlignment = Alignment.Center
        ) {
            Icon(icon, contentDescription = null, tint = color, modifier = Modifier.fillMaxSize(0.6f))
        }
        Spacer(modifier = Modifier.height(2.dp))
        Text(text, color = Color.White, fontSize = 12.sp, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis, textAlign = TextAlign.Center)
    }
}

@Composable
fun DeckLaunchButton(text: String, iconUrl: String, size: androidx.compose.ui.unit.Dp, onClick: () -> Unit) {
    Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.width(size)) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .aspectRatio(1f)
                .clip(RoundedCornerShape(12.dp))
                .background(SpotifyDarkGreen)
                .clickable { onClick() },
            contentAlignment = Alignment.Center
        ) {
            AsyncImage(model = iconUrl, contentDescription = null, modifier = Modifier.fillMaxSize(0.65f).clip(RoundedCornerShape(4.dp)))
        }
        Spacer(modifier = Modifier.height(2.dp))
        Text(text, color = Color.White, fontSize = 12.sp, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis, textAlign = TextAlign.Center)
    }
}

@Composable
fun DeckWindowButton(window: WindowInfo, size: androidx.compose.ui.unit.Dp, onClick: () -> Unit) {
    Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.width(size)) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .aspectRatio(1f)
                .clip(RoundedCornerShape(12.dp))
                .background(SpotifyDarkGreen)
                .clickable { onClick() },
            contentAlignment = Alignment.Center
        ) {
            AsyncImage(
                model = "http://127.0.0.1:8999/dock/icon/${window.id}",
                contentDescription = window.title,
                modifier = Modifier.fillMaxSize(0.7f)
            )
        }
        Spacer(modifier = Modifier.height(2.dp))
        Text(window.title, color = Color.White, fontSize = 12.sp, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis, textAlign = TextAlign.Center)
    }
}

fun formatTime(seconds: Int): String {
    val m = seconds / 60
    val s = seconds % 60
    return "%02d:%02d".format(m, s)
}
