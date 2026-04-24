package com.aiguardian.util

import android.content.Context
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.core.stringSetPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.dataStore by preferencesDataStore(name = "settings")

class SettingsDataStore(private val context: Context) {

    companion object {
        val BACKEND_URL = stringPreferencesKey("backend_url")
        val RISK_THRESHOLD = intPreferencesKey("risk_threshold")
        val AUTO_DISMISS_DELAY = intPreferencesKey("auto_dismiss_delay")
        val VIBRATE_ON_SCAM = booleanPreferencesKey("vibrate_on_scam")
        val WATCHED_APPS = stringSetPreferencesKey("watched_apps")
        
        val DEFAULT_APPS = setOf(
            "com.whatsapp",
            "org.telegram.messenger",
            "com.google.android.gm",
            "com.instagram.android",
            "com.facebook.katana",
            "com.twitter.android",
            "com.snapchat.android",
            "com.linkedin.android",
            "com.android.mms",
            "com.google.android.apps.messaging"
        )
    }

    val backendUrl: Flow<String> = context.dataStore.data.map { it[BACKEND_URL] ?: "https://ai-guardian-api.onrender.com/" }
    
    val riskThreshold: Flow<Int> = context.dataStore.data.map { it[RISK_THRESHOLD] ?: 60 }
    
    val watchedApps: Flow<Set<String>> = context.dataStore.data.map { it[WATCHED_APPS] ?: DEFAULT_APPS }

    suspend fun setBackendUrl(url: String) {
        context.dataStore.edit { it[BACKEND_URL] = url }
    }

    suspend fun setRiskThreshold(threshold: Int) {
        context.dataStore.edit { it[RISK_THRESHOLD] = threshold }
    }
}
