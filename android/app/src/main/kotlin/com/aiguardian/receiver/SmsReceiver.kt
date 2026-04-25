package com.aiguardian.receiver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.provider.Telephony
import android.util.Log
import com.aiguardian.data.repository.ScanRepository
import com.aiguardian.service.OverlayService
import com.aiguardian.util.UrlExtractor
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import javax.inject.Inject

@AndroidEntryPoint
class SmsReceiver : BroadcastReceiver() {

    @Inject
    lateinit var scanRepository: ScanRepository

    private val job = SupervisorJob()
    private val scope = CoroutineScope(Dispatchers.IO + job)

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Telephony.Sms.Intents.SMS_RECEIVED_ACTION) return

        val messages = Telephony.Sms.Intents.getMessagesFromIntent(intent)
        for (sms in messages) {
            val sender = sms.displayOriginatingAddress ?: "Unknown"
            val body = sms.displayMessageBody ?: ""
            
            Log.d("SmsReceiver", "Intercepted SMS from $sender: $body")

            // Instant Production Feedback: Show the "Analyzing..." pulse overlay immediately
            triggerOverlay(context, sender = sender, isAnalyzing = true)

            scope.launch {
                val url = UrlExtractor.extract(body)
                
                // Show instant "Analyzing..." Toast feedback
                android.os.Handler(android.os.Looper.getMainLooper()).post {
                    android.widget.Toast.makeText(context, "🛡️ AI Guardian: Analyzing SMS from $sender...", android.widget.Toast.LENGTH_SHORT).show()
                }

                val result = scanRepository.scan(
                    message = body,
                    url = url,
                    sourceApp = "com.android.mms", // Generic MMS app
                    senderTitle = sender
                )

                android.os.Handler(android.os.Looper.getMainLooper()).post {
                    if (result != null) {
                        android.widget.Toast.makeText(context, "🛡️ AI Guardian: Server Score: ${result.riskScore}/100", android.widget.Toast.LENGTH_SHORT).show()
                    }
                }

                if (result != null && result.riskScore >= 20) {
                    triggerOverlay(context, result.riskScore, result.verdict, result.explanation, result.threatType, sender)
                }
            }
        }
    }

    private fun triggerOverlay(
        context: Context,
        riskScore: Int = -1,
        verdict: String = "",
        explanation: String = "",
        threatType: String = "",
        sender: String = "",
        isAnalyzing: Boolean = false
    ) {
        val intent = Intent(context, OverlayService::class.java).apply {
            putExtra("risk_score", riskScore)
            putExtra("verdict", verdict)
            putExtra("explanation", explanation)
            putExtra("threat_type", threatType)
            putExtra("sender", sender)
            putExtra("source_package", "com.android.mms")
            putExtra("is_analyzing", isAnalyzing)
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
        }
        
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
            context.startForegroundService(intent)
        } else {
            context.startService(intent)
        }
    }
}
