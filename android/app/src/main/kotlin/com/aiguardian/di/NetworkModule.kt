package com.aiguardian.di

import com.aiguardian.data.remote.GuardianApiService
import com.aiguardian.util.SettingsDataStore
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    @Provides
    @Singleton
    fun provideOkHttpClient(): OkHttpClient {
        val logging = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        }
        
        return OkHttpClient.Builder()
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS) // AI scans can take time
            .addInterceptor(logging)
            .build()
    }

    // We use dynamic base URL from DataStore through a custom Retrofit factory if needed,
    // or just fetch it here blocking for startup. A better approach in prod is an interceptor
    // but for simplicity we fetch the current value.
    @Provides
    @Singleton
    fun provideRetrofit(client: OkHttpClient, settingsDataStore: SettingsDataStore): Retrofit {
        // Fallback default if not set
        val baseUrl = runBlocking { settingsDataStore.backendUrl.first() }
        
        return Retrofit.Builder()
            .baseUrl(baseUrl.ifBlank { "http://10.0.2.2:8000/" })
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }

    @Provides
    @Singleton
    fun provideApiService(retrofit: Retrofit): GuardianApiService {
        return retrofit.create(GuardianApiService::class.java)
    }
}
