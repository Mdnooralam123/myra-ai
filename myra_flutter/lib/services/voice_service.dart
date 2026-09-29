import 'package:speech_to_text/speech_to_text.dart';
import 'package:flutter_tts/flutter_tts.dart';

class VoiceService {
  final SpeechToText _speech = SpeechToText();
  final FlutterTts _tts = FlutterTts();
  bool _isListening = false;

  Future<bool> init() async {
    await _tts.setLanguage('hi-IN');
    await _tts.setPitch(1.1);
    await _tts.setSpeechRate(0.9);
    return await _speech.initialize(
      onError: (error) => print('Speech error: $error'),
      onStatus: (status) => print('Speech status: $status'),
    );
  }

  Future<void> listen() async {
    if (!_isListening) {
      _isListening = true;
      await _speech.listen(
        localeId: 'hi_IN',
        onResult: (result) {
          if (result.finalResult) _isListening = false;
        },
      );
    }
  }

  Future<void> speak(String text) async {
    await _tts.speak(text);
  }

  void stopListening() {
    _isListening = false;
    _speech.stop();
  }
}
