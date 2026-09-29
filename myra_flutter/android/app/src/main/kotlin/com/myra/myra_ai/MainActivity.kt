package com.myra.myra_ai

import android.content.Context
import android.content.Intent
import android.media.AudioManager
import android.view.KeyEvent
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private val CHANNEL = "com.myra.assistant/device"

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL)
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "openApp" -> { openApp(call.argument<String>("packageName")); result.success(true) }
                    "playPauseMusic" -> { sendMediaButton(KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE); result.success(true) }
                    "nextTrack" -> { sendMediaButton(KeyEvent.KEYCODE_MEDIA_NEXT); result.success(true) }
                    "prevTrack" -> { sendMediaButton(KeyEvent.KEYCODE_MEDIA_PREVIOUS); result.success(true) }
                    else -> result.notImplemented()
                }
            }
    }

    private fun openApp(packageName: String?) {
        val intent = packageManager.getLaunchIntentForPackage(packageName ?: "")
        if (intent != null) {
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            startActivity(intent)
        }
    }

    private fun sendMediaButton(keyCode: Int) {
        val audioManager = getSystemService(Context.AUDIO_SERVICE) as AudioManager
        var keyEvent = KeyEvent(KeyEvent.ACTION_DOWN, keyCode)
        audioManager.dispatchMediaKeyEvent(keyEvent)
        keyEvent = KeyEvent(KeyEvent.ACTION_UP, keyCode)
        audioManager.dispatchMediaKeyEvent(keyEvent)
    }
}