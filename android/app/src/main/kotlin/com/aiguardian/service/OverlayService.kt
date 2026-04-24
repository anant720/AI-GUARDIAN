package com.aiguardian.service

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.PixelFormat
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.WindowManager
import android.view.animation.OvershootInterpolator
import android.widget.Button
import android.widget.ImageView
import android.widget.ProgressBar
import android.widget.TextView
import androidx.core.app.NotificationCompat
import com.aiguardian.R
import com.aiguardian.ui.MainActivity
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class OverlayService : Service() {

    private lateinit var windowManager: WindowManager
    private var overlayView: View? = null
    private val handler = Handler(Looper.getMainLooper())
    private var autoDismissRunnable: Runnable? = null
    private var progressRunnable: Runnable? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startForegroundWithNotification()

        val riskScore = intent?.getIntExtra("risk_score", 0) ?: return START_NOT_STICKY
        val verdict = intent.getStringExtra("verdict") ?: ""
        val explanation = intent.getStringExtra("explanation") ?: ""
        val threatType = intent.getStringExtra("threat_type") ?: ""
        val sender = intent.getStringExtra("sender") ?: "Unknown"
        val sourcePkg = intent.getStringExtra("source_package") ?: ""

        // If overlay is already showing, dismiss it first
        if (overlayView != null) {
            windowManager.removeView(overlayView)
            overlayView = null
        }

        showOverlay(riskScore, verdict, explanation, threatType, sender, sourcePkg)
        return START_NOT_STICKY
    }

    private fun startForegroundWithNotification() {
        val channelId = "guardian_overlay_service"
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                channelId, "AI Guardian Active", NotificationManager.IMPORTANCE_LOW
            )
            val manager = getSystemService(NotificationManager::class.java)
            manager?.createNotificationChannel(channel)
        }

        val notification = NotificationCompat.Builder(this, channelId)
            .setContentTitle("AI Guardian Active")
            .setContentText("Monitoring for scams and phishing attempts.")
            .setSmallIcon(android.R.drawable.ic_secure)
            .build()

        startForeground(1, notification)
    }

    private fun showOverlay(
        riskScore: Int, verdict: String, explanation: String,
        threatType: String, sender: String, sourcePkg: String
    ) {
        val params = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            WindowManager.LayoutParams(
                WindowManager.LayoutParams.MATCH_PARENT,
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                        WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
                PixelFormat.TRANSLUCENT
            )
        } else {
            @Suppress("DEPRECATION")
            WindowManager.LayoutParams(
                WindowManager.LayoutParams.MATCH_PARENT,
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.TYPE_PHONE,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                        WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
                PixelFormat.TRANSLUCENT
            )
        }.apply {
            gravity = Gravity.TOP or Gravity.CENTER_HORIZONTAL
            y = 80 // 80px from top
        }

        windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
        val inflater = LayoutInflater.from(this)
        val view = inflater.inflate(R.layout.overlay_scam_card, null)

        val riskColor = when {
            riskScore >= 75 -> Color.parseColor("#F43F5E")
            riskScore >= 50 -> Color.parseColor("#F59E0B")
            else -> Color.parseColor("#10B981")
        }
        val riskLabelText = when {
            riskScore >= 75 -> "🚨 SCAM DETECTED"
            riskScore >= 50 -> "⚠️ SUSPICIOUS"
            else -> "✅ SAFE"
        }

        view.apply {
            try {
                val pm = packageManager
                val icon = pm.getApplicationIcon(sourcePkg)
                findViewById<ImageView>(R.id.app_icon).setImageDrawable(icon)
            } catch (e: Exception) {
                // Fallback to default if not found
            }

            findViewById<TextView>(R.id.sender_name).text = sender
            findViewById<TextView>(R.id.risk_label).apply {
                text = riskLabelText
                setTextColor(riskColor)
            }
            findViewById<TextView>(R.id.risk_score_badge).apply {
                text = "$riskScore/100"
                setBackgroundColor(riskColor)
            }
            findViewById<TextView>(R.id.threat_type_label).text = threatType.replace("_", " ").uppercase()
            findViewById<TextView>(R.id.explanation_text).text = explanation

            findViewById<Button>(R.id.btn_dismiss).setOnClickListener { dismiss() }
            findViewById<Button>(R.id.btn_details).setOnClickListener {
                val i = Intent(this@OverlayService, MainActivity::class.java).apply {
                    flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                }
                startActivity(i)
                dismiss()
            }

            val progressBar = findViewById<ProgressBar>(R.id.countdown_bar)
            progressBar.max = AUTO_DISMISS_MS.toInt()
            progressBar.progress = AUTO_DISMISS_MS.toInt()

            val updateInterval = 50L
            var timeRemaining = AUTO_DISMISS_MS

            progressRunnable = object : Runnable {
                override fun run() {
                    timeRemaining -= updateInterval
                    progressBar.progress = timeRemaining.toInt()
                    if (timeRemaining > 0) {
                        handler.postDelayed(this, updateInterval)
                    }
                }
            }
            handler.post(progressRunnable!!)
        }

        // Animate in
        view.translationY = -800f
        windowManager.addView(view, params)
        overlayView = view
        view.animate()
            .translationY(0f)
            .setDuration(400)
            .setInterpolator(OvershootInterpolator(1.2f))
            .start()

        autoDismissRunnable = Runnable { dismiss() }
        handler.postDelayed(autoDismissRunnable!!, AUTO_DISMISS_MS)
    }

    private fun dismiss() {
        autoDismissRunnable?.let { handler.removeCallbacks(it) }
        progressRunnable?.let { handler.removeCallbacks(it) }
        
        overlayView?.animate()
            ?.translationY(-800f)
            ?.setDuration(300)
            ?.withEndAction {
                try {
                    overlayView?.let { windowManager.removeView(it) }
                } catch (e: Exception) {}
                overlayView = null
                stopSelf()
            }?.start()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    companion object {
        const val AUTO_DISMISS_MS = 10_000L
    }
}
