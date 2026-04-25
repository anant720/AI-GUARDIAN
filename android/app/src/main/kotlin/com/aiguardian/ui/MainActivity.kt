package com.aiguardian.ui

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.Settings
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.runtime.*
import kotlinx.coroutines.launch
import dagger.hilt.android.AndroidEntryPoint
import androidx.core.app.NotificationManagerCompat

@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    @javax.inject.Inject
    lateinit var scanRepository: com.aiguardian.data.repository.ScanRepository

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        setContent {
            MaterialTheme(colorScheme = darkColorScheme()) {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    DashboardScreen()
                }
            }
        }
    }
}

@Composable
fun DashboardScreen() {
    val context = LocalContext.current
    
    // Permission States
    var hasNotificationAccess by remember { 
        mutableStateOf(NotificationManagerCompat.getEnabledListenerPackages(context).contains(context.packageName)) 
    }
    var hasOverlayPermission by remember { 
        mutableStateOf(Settings.canDrawOverlays(context)) 
    }
    var hasSmsPermission by remember {
        mutableStateOf(androidx.core.content.ContextCompat.checkSelfPermission(context, android.Manifest.permission.RECEIVE_SMS) == android.content.pm.PackageManager.PERMISSION_GRANTED)
    }
    var isIgnoringBatteryOptimizations by remember {
        val powerManager = context.getSystemService(android.content.Context.POWER_SERVICE) as android.os.PowerManager
        mutableStateOf(powerManager.isIgnoringBatteryOptimizations(context.packageName))
    }

    val deviceId = remember { Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID) }
    val allGranted = hasNotificationAccess && hasOverlayPermission && hasSmsPermission && isIgnoringBatteryOptimizations

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Spacer(modifier = Modifier.height(40.dp))
        
        Text(
            text = "AI GUARDIAN",
            fontSize = 32.sp,
            fontWeight = FontWeight.ExtraBold,
            color = if (allGranted) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error
        )
        
        Text(
            text = if (allGranted) "🛡️ FULLY PROTECTED" else "⚠️ PROTECTION INCOMPLETE",
            fontSize = 14.sp,
            fontWeight = FontWeight.Bold,
            color = if (allGranted) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error
        )

        Spacer(modifier = Modifier.height(32.dp))

        // SMS Interception (New)
        PermissionCard(
            title = "SMS Scouter",
            description = "Intercepts raw scam texts at the system level.",
            isGranted = hasSmsPermission,
            onClick = {
                val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
                intent.data = Uri.fromParts("package", context.packageName, null)
                context.startActivity(intent)
            }
        )
        
        Spacer(modifier = Modifier.height(12.dp))

        // Notification Access
        PermissionCard(
            title = "Social Watcher",
            description = "Monitors WhatsApp, Telegram & Instagram.",
            isGranted = hasNotificationAccess,
            onClick = {
                context.startActivity(Intent("android.settings.ACTION_NOTIFICATION_LISTENER_SETTINGS"))
            }
        )
        
        Spacer(modifier = Modifier.height(12.dp))

        // Battery Optimization
        PermissionCard(
            title = "Background Life",
            description = "Required to keep protection alive 24/7.",
            isGranted = isIgnoringBatteryOptimizations,
            onClick = {
                val intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS)
                intent.data = Uri.parse("package:${context.packageName}")
                context.startActivity(intent)
            }
        )
        
        Spacer(modifier = Modifier.height(12.dp))

        // Overlay Permission
        PermissionCard(
            title = "Visual Alerts",
            description = "Draws Truecaller-style popups over scams.",
            isGranted = hasOverlayPermission,
            onClick = {
                val intent = Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:${context.packageName}"))
                context.startActivity(intent)
            }
        )
        
        Spacer(modifier = Modifier.height(32.dp))

        // Advanced Fix for Xiaomi/Battery killers
        if (com.aiguardian.util.OemHelper.isXiaomi()) {
            OutlinedButton(
                onClick = { com.aiguardian.util.OemHelper.openAutoStartSettings(context) },
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Xiaomi Fix: Enable Autostart")
            }
            Spacer(modifier = Modifier.height(8.dp))
        }

        Button(
            onClick = {
                hasNotificationAccess = NotificationManagerCompat.getEnabledListenerPackages(context).contains(context.packageName)
                hasOverlayPermission = Settings.canDrawOverlays(context)
                hasSmsPermission = androidx.core.content.ContextCompat.checkSelfPermission(context, android.Manifest.permission.RECEIVE_SMS) == android.content.pm.PackageManager.PERMISSION_GRANTED
                val pm = context.getSystemService(android.content.Context.POWER_SERVICE) as android.os.PowerManager
                isIgnoringBatteryOptimizations = pm.isIgnoringBatteryOptimizations(context.packageName)
                
                if (allGranted) {
                    android.widget.Toast.makeText(context, "AI Guardian Active: Monitoring all channels.", android.widget.Toast.LENGTH_LONG).show()
                }
            },
            modifier = Modifier.fillMaxWidth().height(56.dp)
        ) {
            Text(if (allGranted) "Locked & Protected" else "Refresh Status Check", fontSize = 18.sp)
        }

        Spacer(modifier = Modifier.height(12.dp))

        // Diagnostic Button
        val scope = rememberCoroutineScope()
        val scanRepository = (context as? MainActivity)?.scanRepository
        
        OutlinedButton(
            onClick = {
                scope.launch {
                    android.widget.Toast.makeText(context, "Testing Connection to Render...", android.widget.Toast.LENGTH_SHORT).show()
                    val result = scanRepository?.scan("Diagnostic Test Message", null, "com.aiguardian", "System Test")
                    if (result != null) {
                        android.widget.Toast.makeText(context, "✅ SERVER REACHED: Scan ${result.verdict}", android.widget.Toast.LENGTH_LONG).show()
                    } else {
                        android.widget.Toast.makeText(context, "❌ SERVER FAILED: No response from Render.", android.widget.Toast.LENGTH_LONG).show()
                    }
                }
            },
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.error)
        ) {
            Text("FORCE NETWORK TEST (Debug)")
        }
        
        Spacer(modifier = Modifier.weight(1f))

        Text(
            text = "Shield ID: ${deviceId.take(8).uppercase()}",
            fontSize = 11.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f)
        )
        Spacer(modifier = Modifier.height(16.dp))
    }
}

@Composable
fun PermissionCard(title: String, description: String, isGranted: Boolean, onClick: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = if (isGranted) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceVariant
        )
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(text = if (isGranted) "✅" else "❌", fontSize = 20.sp)
                Spacer(modifier = Modifier.width(12.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text(text = title, fontWeight = FontWeight.Bold, fontSize = 16.sp)
                    Text(text = description, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                if (!isGranted) {
                    TextButton(onClick = onClick) {
                        Text("FIX")
                    }
                }
            }
        }
    }
}
