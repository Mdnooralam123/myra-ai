import 'package:flutter/material.dart';
import '../services/ai_service.dart';
import '../services/device_service.dart';
import '../services/voice_service.dart';
import '../widgets/avatar_3d_widget.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _aiService = AiService();
  final _deviceService = DeviceService();
  final _voiceService = VoiceService();
  final _textController = TextEditingController();
  final _scrollController = ScrollController();
  final List<Map<String, String>> _messages = [];
  bool _isListening = false;
  bool _isProcessing = false;

  @override
  void initState() {
    super.initState();
    _initServices();
    _messages.add({'role': 'myra', 'text': 'Hi! Main MYRA hoon. Kya help chahiye? 🎀'});
  }

  Future<void> _initServices() async {
    await _voiceService.init();
  }

  Future<void> _sendMessage(String text) async {
    if (text.trim().isEmpty) return;
    setState(() {
      _messages.add({'role': 'user', 'text': text});
      _isProcessing = true;
    });
    _scrollToBottom();
    final response = await _aiService.sendMessage(text);
    if (response.containsKey('error')) {
      setState(() {
        _messages.add({'role': 'myra', 'text': 'Error: ${response['error']}'});
        _isProcessing = false;
      });
      return;
    }
    final reply = response['reply'] ?? 'Sorry, samajh nahi payi.';
    final command = response['command'] as Map<String, dynamic>?;
    setState(() {
      _messages.add({'role': 'myra', 'text': reply});
      _isProcessing = false;
    });
    _scrollToBottom();
    if (command != null) await _executeCommand(command);
    await _voiceService.speak(reply);
  }

  Future<void> _executeCommand(Map<String, dynamic> command) async {
    final type = command['type'] as String?;
    final action = command['action'] as String?;
    final target = command['target'] as String?;
    final params = command['params'] as Map<String, dynamic>? ?? {};
    switch (type) {
      case 'open_app': await _deviceService.openApp(target ?? ''); break;
      case 'play_music': await _deviceService.playSong(params['song_name'] ?? ''); break;
      case 'media_control':
        if (action == 'pause') await _deviceService.playPauseMusic();
        else if (action == 'next') await _deviceService.nextTrack();
        else if (action == 'previous') await _deviceService.prevTrack();
        break;
      case 'system':
        if (action == 'home') await _deviceService.goHome();
        else if (action == 'back') await _deviceService.goBack();
        break;
    }
  }

  void _scrollToBottom() {
    Future.delayed(const Duration(milliseconds: 100), () {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('MYRA AI', style: TextStyle(fontWeight: FontWeight.bold)),
        backgroundColor: const Color(0xFF1A1A2E),
        elevation: 0,
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: () => setState(() => _messages.clear())),
        ],
      ),
      body: Column(
        children: [
          Container(
            height: 280,
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [Color(0xFF1A1A2E), Color(0xFF0D0D1A)],
              ),
            ),
            child: const Avatar3DWidget(),
          ),
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.all(16),
              itemCount: _messages.length,
              itemBuilder: (context, index) {
                final msg = _messages[index];
                final isUser = msg['role'] == 'user';
                return Align(
                  alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                  child: Container(
                    margin: const EdgeInsets.only(bottom: 12),
                    padding: const EdgeInsets.all(14),
                    constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.75),
                    decoration: BoxDecoration(
                      color: isUser ? const Color(0xFF6C3FC5) : const Color(0xFF1E1E32),
                      borderRadius: BorderRadius.only(
                        topLeft: const Radius.circular(18),
                        topRight: const Radius.circular(18),
                        bottomLeft: isUser ? const Radius.circular(18) : const Radius.circular(4),
                        bottomRight: isUser ? const Radius.circular(4) : const Radius.circular(18),
                      ),
                    ),
                    child: Text(msg['text'] ?? '', style: const TextStyle(color: Colors.white, fontSize: 15)),
                  ),
                );
              },
            ),
          ),
          if (_isProcessing)
            const Padding(padding: EdgeInsets.all(8), child: CircularProgressIndicator(color: Colors.purple)),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: const BoxDecoration(
              color: Color(0xFF1A1A2E),
              border: Border(top: BorderSide(color: Color(0xFF2A2A4A))),
            ),
            child: Row(
              children: [
                IconButton(
                  icon: Icon(_isListening ? Icons.mic : Icons.mic_none),
                  color: _isListening ? Colors.red : Colors.white,
                  onPressed: () async {
                    if (_isListening) {
                      _voiceService.stopListening();
                      setState(() => _isListening = false);
                    } else {
                      setState(() => _isListening = true);
                      await _voiceService.listen();
                    }
                  },
                ),
                Expanded(
                  child: TextField(
                    controller: _textController,
                    style: const TextStyle(color: Colors.white),
                    decoration: InputDecoration(
                      hintText: 'Kuch bolo ya likho...',
                      hintStyle: const TextStyle(color: Colors.grey),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(24),
                        borderSide: BorderSide.none,
                      ),
                      filled: true,
                      fillColor: const Color(0xFF0D0D1A),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    ),
                    onSubmitted: (text) { _sendMessage(text); _textController.clear(); },
                  ),
                ),
                const SizedBox(width: 8),
                IconButton(
                  icon: const Icon(Icons.send, color: Color(0xFF6C3FC5)),
                  onPressed: () { _sendMessage(_textController.text); _textController.clear(); },
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
