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

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        val packageName = sbn.packageName
        
        serviceScope.launch {
            val watchedApps = settingsDataStore.watchedApps.first()
            if (packageName !in watchedApps) return@launch

            val extras = sbn.notification.extras
            val title = extras.getString(Notification.EXTRA_TITLE) ?: ""
            val text = extras.getCharSequence(Notification.EXTRA_TEXT)?.toString() ?: ""
            val bigText = extras.getCharSequence(Notification.EXTRA_BIG_TEXT)?.toString() ?: text
            
            val fullText = if (bigText.length > text.length) bigText else text
            if (fullText.isBlank()) return@launch

            // Deduplicate
            val contentHash = (packageName + title + fullText).hashCode()
            val now = System.currentTimeMillis()
            if (recentHashes[contentHash]?.let { now - it < 60_000 } == true) return@launch
            recentHashes[contentHash] = now

            val extractedUrl = UrlExtractor.extract(fullText)
            
            // Avoid scanning completely safe mundane messages if there's no URL 
            // and it's extremely short, to save backend load, unless configured to scan all
            if (extractedUrl == null && fullText.length < 10) return@launch

            Log.d("GuardianListener", "Scanning notification from $packageName")
            
            val result = scanRepository.scan(
                message = fullText,
                url = extractedUrl,
                sourceApp = packageName,
                senderTitle = title
            )

            if (result != null) {
                val threshold = settingsDataStore.riskThreshold.first()
                if (result.riskScore >= threshold) {
                    triggerOverlay(result.riskScore, result.verdict, result.explanation, result.threatType, title, packageName)
                }
            }
        }
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification) {
        // Not used, but part of lifecycle
    }

    private fun triggerOverlay(
        riskScore: Int, 
        verdict: String, 
        explanation: String, 
        threatType: String, 
        sender: String, 
        packageName: String
    ) {
        val intent = Intent(this, OverlayService::class.java).apply {
            putExtra("risk_score", riskScore)
            putExtra("verdict", verdict)
            putExtra("explanation", explanation)
            putExtra("threat_type", threatType)
            putExtra("source_package", packageName)
            putExtra("sender", sender)
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
        }
        
        try {
            startService(intent)
        } catch (e: Exception) {
            Log.e("GuardianListener", "Failed to start overlay service", e)
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        job.cancel()
    }
}
