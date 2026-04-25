package com.aiguardian.service

import android.app.Notification
import android.content.Intent
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.util.Log
import com.aiguardian.data.repository.ScanRepository
import com.aiguardian.util.SettingsDataStore
import com.aiguardian.util.UrlExtractor
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import javax.inject.Inject

@AndroidEntryPoint
class GuardianNotificationListener : NotificationListenerService() {

    @Inject
    lateinit var scanRepository: ScanRepository
    
    @Inject
    lateinit var settingsDataStore: SettingsDataStore

    private val job = SupervisorJob()
    private val serviceScope = CoroutineScope(Dispatchers.IO + job)
    
    // Simple deduplication memory (hash -> timestamp)
    private val recentHashes = mutableMapOf<Int, Long>()

    override fun onListenerConnected() {
        super.onListenerConnected()
        Log.i("GuardianListener", "Notification Listener Connected and Active")
        startForegroundNotification()
    }

    private fun startForegroundNotification() {
        val channelId = "guardian_service_channel"
        val channelName = "AI Guardian Background Service"
        
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
            val channel = android.app.NotificationChannel(
                channelId, channelName, android.app.NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Keeps AI Guardian active in the background"
            }
            val manager = getSystemService(android.app.NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }

        val notification = android.app.Notification.Builder(this, channelId)
            .setContentTitle("AI Guardian Protected")
            .setContentText("Monitoring for scams in real-time...")
            .setSmallIcon(android.R.drawable.ic_lock_idle_lock)
            .setOngoing(true)
            .build()

        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.Q) {
            startForeground(1001, notification, android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE)
        } else {
            startForeground(1001, notification)
        }
    }

    override fun onListenerDisconnected() {
        super.onListenerDisconnected()
        Log.w("GuardianListener", "Notification Listener Disconnected - Potential OEM kill")
    }

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        val packageName = sbn.packageName
        val extras = sbn.notification?.extras
        val title = extras?.getString(Notification.EXTRA_TITLE) ?: "Someone"
        
        serviceScope.launch {
            val watchedApps = settingsDataStore.watchedApps.first()
            val isSocialApp = packageName.contains("whatsapp") || 
                              packageName.contains("telegram") || 
                              packageName.contains("instagram") ||
                              packageName.contains("facebook") ||
                              packageName.contains("messenger")

            if (!isSocialApp && packageName !in watchedApps) return@launch

            val appFriendlyName = when {
                packageName.contains("whatsapp") -> "WhatsApp"
                packageName.contains("instagram") -> "Instagram"
                packageName.contains("telegram") -> "Telegram"
                packageName.contains("messenger") -> "Messenger"
                else -> "Social Media"
            }

            // Aggressively extract text (WhatsApp often hides it in different fields)
            val text = extras?.getCharSequence(Notification.EXTRA_TEXT)?.toString() ?: ""
            val bigText = extras?.getCharSequence(Notification.EXTRA_BIG_TEXT)?.toString() ?: ""
            val summaryText = extras?.getCharSequence(Notification.EXTRA_SUMMARY_TEXT)?.toString() ?: ""
            
            var fullText = listOf(text, bigText, summaryText).filter { it.isNotBlank() }.maxByOrNull { it.length } ?: ""
            
            // Handle WhatsApp Group messages specifically
            if (fullText.isBlank()) {
                val lines = extras?.getCharSequenceArray(Notification.EXTRA_TEXT_LINES)
                if (lines != null && lines.isNotEmpty()) {
                    fullText = lines.last().toString()
                }
            }

            if (fullText.isBlank() || fullText.length < 3) return@launch

            // Deduplicate (ignore identical messages within 30 seconds)
            val contentHash = (packageName + fullText).hashCode()
            val now = System.currentTimeMillis()
            if (recentHashes[contentHash]?.let { now - it < 30_000 } == true) return@launch
            recentHashes[contentHash] = now

            val extractedUrl = UrlExtractor.extract(fullText)
            
            // Production rule: Always show scanning feedback for social apps if message length > 10
            if (fullText.length > 10 || extractedUrl != null) {
                android.os.Handler(android.os.Looper.getMainLooper()).post {
                    android.widget.Toast.makeText(
                        this@GuardianNotificationListener, 
                        "🛡️ AI Guardian: Scanning $appFriendlyName message...", 
                        android.widget.Toast.LENGTH_SHORT
                    ).show()
                }
            }

            // Instant Production Feedback: Show the "Analyzing..." pulse overlay immediately
            triggerOverlay(sender = title, packageName = packageName, isAnalyzing = true)

            val result = scanRepository.scan(
                message = fullText,
                url = extractedUrl,
                sourceApp = packageName,
                senderTitle = title
            )

            android.os.Handler(android.os.Looper.getMainLooper()).post {
                if (result != null) {
                    android.widget.Toast.makeText(this@GuardianNotificationListener, "🛡️ AI Guardian: Server Score: ${result.riskScore}/100", android.widget.Toast.LENGTH_SHORT).show()
                }
            }

            if (result != null) {
                if (result.riskScore >= 20) {
                    triggerOverlay(result.riskScore, result.verdict, result.explanation, result.threatType, title, packageName)
                }
            }
        }
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification) {
        // Not used
    }

    private fun triggerOverlay(
        riskScore: Int = -1, 
        verdict: String = "", 
        explanation: String = "", 
        threatType: String = "", 
        sender: String = "", 
        packageName: String = "",
        isAnalyzing: Boolean = false
    ) {
        val intent = Intent(this, OverlayService::class.java).apply {
            putExtra("risk_score", riskScore)
            putExtra("verdict", verdict)
            putExtra("explanation", explanation)
            putExtra("threat_type", threatType)
            putExtra("source_package", packageName)
            putExtra("sender", sender)
            putExtra("is_analyzing", isAnalyzing)
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
        }
        
        try {
            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
                startForegroundService(intent)
            } else {
                startService(intent)
            }
        } catch (e: Exception) {
            Log.e("GuardianListener", "Failed to start overlay service", e)
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        job.cancel()
    }
}
