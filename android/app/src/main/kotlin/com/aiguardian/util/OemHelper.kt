package com.aiguardian.util

import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings

object OemHelper {

    /**
     * Attempts to open the AutoStart settings for the current device manufacturer.
     */
    fun openAutoStartSettings(context: Context) {
        val manufacturer = Build.MANUFACTURER.lowercase()
        val intent = Intent()
        
        when {
            manufacturer.contains("xiaomi") -> {
                intent.component = ComponentName(
                    "com.miui.securitycenter",
                    "com.miui.permcenter.autostart.AutoStartManagementActivity"
                )
            }
            manufacturer.contains("oppo") -> {
                intent.component = ComponentName(
                    "com.coloros.safecenter",
                    "com.coloros.safecenter.permission.startup.StartupAppListActivity"
                )
            }
            manufacturer.contains("vivo") -> {
                intent.component = ComponentName(
                    "com.vivo.permissionmanager",
                    "com.vivo.permissionmanager.activity.BgStartUpManagerActivity"
                )
            }
            manufacturer.contains("huawei") -> {
                intent.component = ComponentName(
                    "com.huawei.systemmanager",
                    "com.huawei.systemmanager.optimize.process.ProtectActivity"
                )
            }
            else -> {
                // Fallback to general app details
                intent.action = Settings.ACTION_APPLICATION_DETAILS_SETTINGS
                intent.data = Uri.fromParts("package", context.packageName, null)
            }
        }
        
        try {
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            context.startActivity(intent)
        } catch (e: Exception) {
            // Last resort: Open Battery Optimization page
            try {
                val batteryIntent = Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS)
                batteryIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(batteryIntent)
            } catch (ex: Exception) {
                // Open app details if even battery optimization fails
                val detailsIntent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
                detailsIntent.data = Uri.fromParts("package", context.packageName, null)
                detailsIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(detailsIntent)
            }
        }
    }

    /**
     * Checks if the device is a Xiaomi/MIUI device which requires the hidden
     * "Display pop-up windows while running in background" permission.
     */
    fun isXiaomi(): Boolean = Build.MANUFACTURER.lowercase().contains("xiaomi")

    fun openXiaomiSpecificPermissions(context: Context) {
        try {
            val intent = Intent("miui.intent.action.APP_PERM_EDITOR")
            intent.setClassName("com.miui.securitycenter", "com.miui.permcenter.permissions.PermissionsEditorActivity")
            intent.putExtra("extra_pkgname", context.packageName)
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            context.startActivity(intent)
        } catch (e: Exception) {
            val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
            intent.data = Uri.fromParts("package", context.packageName, null)
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            context.startActivity(intent)
        }
    }
}
