package com.aiguardian.data.local

import androidx.room.*
import kotlinx.coroutines.flow.Flow

// ── Entity ────────────────────────────────────────────────────────────────────

@Entity(tableName = "scan_results")
data class ScanResultEntity(
    @PrimaryKey val contentHash: String,
    val riskScore: Int,
    val verdict: String,
    val explanation: String,
    val threatType: String,
    val sourceApp: String,
    val senderTitle: String,
    val rawMessage: String,
    val extractedUrl: String?,
    val scannedAt: Long = System.currentTimeMillis(),
    val overlayShown: Boolean = false
)

// ── DAO ───────────────────────────────────────────────────────────────────────

@Dao
interface ScanResultDao {

    /** Cache lookup — returns hit only if scanned within given timestamp window */
    @Query("""
        SELECT * FROM scan_results
        WHERE contentHash = :hash
          AND scannedAt   > :minTimestamp
        LIMIT 1
    """)
    suspend fun findCached(hash: String, minTimestamp: Long): ScanResultEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(result: ScanResultEntity)

    /** Dashboard: 100 most recent scans, newest first */
    @Query("SELECT * FROM scan_results ORDER BY scannedAt DESC LIMIT 100")
    fun getRecentScans(): Flow<List<ScanResultEntity>>

    /** Stats */
    @Query("SELECT COUNT(*) FROM scan_results WHERE riskScore >= 60")
    fun getScamCount(): Flow<Int>

    @Query("SELECT COUNT(*) FROM scan_results")
    fun getTotalCount(): Flow<Int>

    /** Cleanup — delete entries older than 7 days */
    @Query("DELETE FROM scan_results WHERE scannedAt < :cutoff")
    suspend fun deleteOlderThan(cutoff: Long)
}

// ── Database ──────────────────────────────────────────────────────────────────

@Database(entities = [ScanResultEntity::class], version = 1, exportSchema = false)
abstract class AppDatabase : RoomDatabase() {
    abstract fun scanResultDao(): ScanResultDao
}
