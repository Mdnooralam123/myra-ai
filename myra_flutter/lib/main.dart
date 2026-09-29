import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:flutter_accessibility_service/flutter_accessibility_service.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'screens/home_screen.dart';
import 'screens/api_key_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await _requestAllPermissions();
  await _enableAccessibility();
  final storage = FlutterSecureStorage();
  final apiKey = await storage.read(key: 'gemini_api_key');
  runApp(MyraApp(hasApiKey: apiKey != null));
}

Future<void> _requestAllPermissions() async {
  List<Permission> permissions = [
    Permission.microphone, Permission.storage, Permission.phone,
    Permission.contacts, Permission.camera, Permission.notification,
    Permission.location, Permission.bluetooth, Permission.sms,
  ];
  await permissions.request();
}

Future<void> _enableAccessibility() async {
  final bool isEnabled = await FlutterAccessibilityService.isAccessibilityPermissionEnabled();
  if (!isEnabled) await FlutterAccessibilityService.requestAccessibilityPermission();
}

class MyraApp extends StatelessWidget {
  final bool hasApiKey;
  const MyraApp({super.key, required this.hasApiKey});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'MYRA AI',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        primarySwatch: Colors.purple,
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF0D0D1A),
      ),
      home: hasApiKey ? const HomeScreen() : const ApiKeyScreen(),
    );
  }
}
