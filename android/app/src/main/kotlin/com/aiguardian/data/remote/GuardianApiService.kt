package com.aiguardian.data.remote

import com.google.gson.annotations.SerializedName
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST

// ── Retrofit Interface ────────────────────────────────────────────────────────

interface GuardianApiService {
    @POST("scan")
    suspend fun scan(@Body request: ScanRequest): Response<ScanResponse>

    @GET("health")
    suspend fun health(): Response<HealthResponse>
}

// ── Request Model ─────────────────────────────────────────────────────────────

data class ScanRequest(
    val message: String?,
    val url: String?
)

// ── Response Models ───────────────────────────────────────────────────────────

data class ScanResponse(
    @SerializedName("combined_score") val combinedScore: Int = 0,
    @SerializedName("risk_score")     val riskScore: Int = 0,
    val explanation: String = "",
    val verdict: String = "",
    val evidence: List<String> = emptyList(),
    @SerializedName("threat_type")    val threatType: String = "",
    @SerializedName("llm_verdict")    val llmVerdict: LlmVerdict? = null,
    @SerializedName("message_id")     val messageId: String = ""
)

data class LlmVerdict(
    @SerializedName("scam_probability") val scamProbability: Int = 0,
    @SerializedName("threat_type")      val threatType: String = "",
    val explanation: String = "",
    val confidence: Double = 0.0
)

data class HealthResponse(
    val status: String,
    val service: String,
    val version: String,
    val postgresql: String
)
