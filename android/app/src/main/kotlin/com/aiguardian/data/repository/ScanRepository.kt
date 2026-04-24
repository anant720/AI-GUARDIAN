package com.aiguardian.data.repository

import android.util.Log
import com.aiguardian.data.local.ScanResultDao
import com.aiguardian.data.local.ScanResultEntity
import com.aiguardian.data.remote.GuardianApiService
import com.aiguardian.data.remote.ScanRequest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.security.MessageDigest
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ScanRepository @Inject constructor(
    private val api: GuardianApiService,
    private val dao: ScanResultDao
) {
    /**
     * Scans a message/url by first checking the local cache (valid for 30 min).
     * If not found, calls the remote AI Guardian backend.
     */
    suspend fun scan(
        message: String,
        url: String?,
        sourceApp: String,
        senderTitle: String
    ): ScanResultEntity? = withContext(Dispatchers.IO) {
        // 1. Generate unique hash for this content
        val contentString = message + (url ?: "")
        val hash = sha256(contentString)

        // 2. Check cache (valid for 30 minutes)
        val cacheWindowMs = 30 * 60 * 1000L
        val minTimestamp = System.currentTimeMillis() - cacheWindowMs
        
        val cached = dao.findCached(hash, minTimestamp)
        if (cached != null) {
            Log.d("GuardianRepository", "Cache HIT for 30m window")
            return@withContext cached
        }

        // 3. Cache Miss - Call API
        try {
            val request = ScanRequest(message = message, url = url)
            val response = api.scan(request)
            
            if (response.isSuccessful && response.body() != null) {
                val body = response.body()!!
                
                // Construct entity
                val entity = ScanResultEntity(
                    contentHash = hash,
                    riskScore = maxOf(body.combinedScore, body.riskScore),
                    verdict = body.verdict,
                    explanation = body.explanation,
                    threatType = body.llmVerdict?.threatType ?: body.threatType,
                    sourceApp = sourceApp,
                    senderTitle = senderTitle,
                    rawMessage = message,
                    extractedUrl = url
                )
                
                // Save to local cache
                dao.insert(entity)
                return@withContext entity
            } else {
                Log.e("GuardianRepository", "API Error: ${response.code()} ${response.errorBody()?.string()}")
                return@withContext null
            }
        } catch (e: Exception) {
            Log.e("GuardianRepository", "Network or parsing error", e)
            return@withContext null // Fail open - don't show false alarms on network errors
        }
    }

    private fun sha256(input: String): String {
        val bytes = MessageDigest.getInstance("SHA-256").digest(input.toByteArray())
        return bytes.joinToString("") { "%02x".format(it) }
    }
}
