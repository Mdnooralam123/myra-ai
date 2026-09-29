import 'package:google_generative_ai/google_generative_ai.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class AiService {
  final _storage = const FlutterSecureStorage();
  GenerativeModel? _model;
  ChatSession? _chat;

  Future<String> getApiKey() async =>
      await _storage.read(key: 'gemini_api_key') ?? '';

  Future<void> _initModel() async {
    final apiKey = await getApiKey();
    if (apiKey.isEmpty) return;
    _model = GenerativeModel(
      model: 'gemini-1.5-flash',
      apiKey: apiKey,
      systemInstruction: Content.system(
        'Tum MYRA ho. Friendly, caring, playful AI girl assistant. Hinglish mein baat karo. Chhote natural jawab do.'
      ),
    );
    _chat = _model!.startChat();
  }

  Future<Map<String, dynamic>> sendMessage(String message) async {
    try {
      if (_chat == null) await _initModel();
      if (_chat == null) return {'error': 'API key set nahi hai'};
      final command = _parseCommand(message);
      final response = await _chat!.sendMessage(Content.text(message));
      final reply = response.text ?? 'Sorry, samajh nahi payi.';
      return {'reply': reply, 'command': command};
    } catch (e) {
      return {'error': 'Error: $e'};
    }
  }

  Map<String, dynamic> _parseCommand(String input) {
    final lower = input.toLowerCase();
    final apps = {
      'whatsapp': 'com.whatsapp',
      'youtube': 'com.google.android.youtube',
      'chrome': 'com.android.chrome',
      'instagram': 'com.instagram.android',
      'facebook': 'com.facebook.katana',
      'spotify': 'com.spotify.music',
      'telegram': 'org.telegram.messenger',
    };
    if (lower.contains('open') || lower.contains('kholo')) {
      for (var entry in apps.entries) {
        if (lower.contains(entry.key)) {
          return {'type': 'open_app', 'target': entry.value, 'params': {'app_name': entry.key}};
        }
      }
    }
    if (lower.contains('gaana') || lower.contains('gana') || lower.contains('song') || lower.contains('play')) {
      final song = input.replaceAll(RegExp(r'(gaana|gana|song|play|bajao|chalao|karo|do)', caseSensitive: false), '').trim();
      if (song.isNotEmpty) return {'type': 'play_music', 'params': {'song_name': song}};
    }
    if (lower.contains('pause') || lower.contains('rok')) return {'type': 'media_control', 'action': 'pause'};
    if (lower.contains('next') || lower.contains('agla')) return {'type': 'media_control', 'action': 'next'};
    if (lower.contains('previous') || lower.contains('pichla')) return {'type': 'media_control', 'action': 'previous'};
    if (lower.contains('home')) return {'type': 'system', 'action': 'home'};
    if (lower.contains('back')) return {'type': 'system', 'action': 'back'};
    return {'type': 'chat'};
  }

  Future<void> setApiKey(String apiKey) async {
    await _storage.write(key: 'gemini_api_key', value: apiKey);
    _model = null;
    _chat = null;
    await _initModel();
  }
}
