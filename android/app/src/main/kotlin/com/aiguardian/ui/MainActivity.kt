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
import dagger.hilt.android.AndroidEntryPoint
import androidx.core.app.NotificationManagerCompat

@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        setContent {
            MaterialTheme(colorScheme = darkColorScheme()) {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    PermissionsScreen()
                }
            }
        }
    }
}

@Composable
fun PermissionsScreen() {
    val context = LocalContext.current
    
    // Check permissions
    var hasNotificationAccess by remember { 
        mutableStateOf(NotificationManagerCompat.getEnabledListenerPackages(context).contains(context.packageName)) 
    }
    
    var hasOverlayPermission by remember { 
        mutableStateOf(Settings.canDrawOverlays(context)) 
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(
            text = "AI Guardian Setup",
            fontSize = 28.sp,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.primary
        )
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            text = "To protect against scams, we need two permissions.",
            fontSize = 16.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        
        Spacer(modifier = Modifier.height(48.dp))

        // Notification Access
        PermissionCard(
            title = "Notification Access",
            description = "Allows us to scan incoming messages.",
            isGranted = hasNotificationAccess,
            onClick = {
                context.startActivity(Intent("android.settings.ACTION_NOTIFICATION_LISTENER_SETTINGS"))
            }
        )
        
        Spacer(modifier = Modifier.height(16.dp))

        // Overlay Permission
        PermissionCard(
            title = "Display over other apps",
            description = "Allows us to show the Truecaller-style alert popup.",
            isGranted = hasOverlayPermission,
            onClick = {
                val intent = Intent(
                    Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                    Uri.parse("package:${context.packageName}")
                )
                context.startActivity(intent)
            }
        )
        
        Spacer(modifier = Modifier.height(48.dp))
        
        Button(
            onClick = {
                hasNotificationAccess = NotificationManagerCompat.getEnabledListenerPackages(context).contains(context.packageName)
                hasOverlayPermission = Settings.canDrawOverlays(context)
            },
            modifier = Modifier.fillMaxWidth().height(56.dp)
        ) {
            Text(if (hasNotificationAccess && hasOverlayPermission) "Ready & Active!" else "Check Permissions", fontSize = 18.sp)
        }
        
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
                Text(text = if (isGranted) "✅" else "⚠️", fontSize = 24.sp)
                Spacer(modifier = Modifier.width(12.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text(text = title, fontWeight = FontWeight.Bold)
                    Text(text = description, style = MaterialTheme.typography.bodySmall)
                }
                if (!isGranted) {
                    Button(onClick = onClick) {
                        Text("Grant")
                    }
                }
            }
        }
    }
}
