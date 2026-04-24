package com.aiguardian.receiver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED || 
            intent.action == "android.intent.action.QUICKBOOT_POWERON" || 
            intent.action == "com.htc.intent.action.QUICKBOOT_POWERON") {
            
            Log.d("BootReceiver", "Boot completed, ensuring AI Guardian services are ready.")
            // Android automatically restarts NotificationListenerService if the user granted the permission.
            // But we can add a persistent notification here in the future to keep the app process alive.
        }
    }
}
