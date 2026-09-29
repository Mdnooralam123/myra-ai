import 'package:flutter/services.dart';
import 'package:android_intent_plus/android_intent.dart';
import 'package:flutter_accessibility_service/flutter_accessibility_service.dart';

class DeviceService {
  static const _channel = MethodChannel('com.myra.assistant/device');

  Future<void> openApp(String packageName) async {
    try {
      await _channel.invokeMethod('openApp', {'packageName': packageName});
    } catch (e) {
      final intent = AndroidIntent(
        action: 'android.intent.action.MAIN',
        package: packageName,
      );
      await intent.launch();
    }
  }

  Future<void> playSong(String songName) async {
    final intent = AndroidIntent(
      action: 'android.intent.action.VIEW',
      data: 'https://www.youtube.com/results?search_query=${Uri.encodeComponent(songName)}',
    );
    await intent.launch();
  }

  Future<void> goHome() async {
    await FlutterAccessibilityService.performGlobalAction(GlobalAction.globalActionHome);
  }

  Future<void> goBack() async {
    await FlutterAccessibilityService.performGlobalAction(GlobalAction.globalActionBack);
  }

  Future<void> playPauseMusic() async => await _channel.invokeMethod('playPauseMusic');
  Future<void> nextTrack() async => await _channel.invokeMethod('nextTrack');
  Future<void> prevTrack() async => await _channel.invokeMethod('prevTrack');
}
