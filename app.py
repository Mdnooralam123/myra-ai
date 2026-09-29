#!/usr/bin/env python3
"""
MYRA AI - Self-Healing Auto Builder
Auto retry + Auto error fix + Complete build pipeline
"""

import os
import sys
import time
import shutil
import subprocess
import re
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.resolve()
FLUTTER_DIR = PROJECT_DIR / "myra_flutter"
ORG_NAME = "com.myra"
PROJECT_NAME = "myra_ai"
GITHUB_REPO = ""
GITHUB_TOKEN = ""
REPO_NAME = "myra-ai"
PREFIX = os.environ.get("PREFIX", "/data/data/com.termux/files/usr")
FLUTTER_BIN = f"{PREFIX}/opt/flutter/bin"

# Retry settings
MAX_RETRIES = 5
RETRY_DELAY = 10  # seconds


# ══════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════

def run(cmd, cwd=None, check=True):
    print(f"  ▶ {cmd[:120]}{'...' if len(cmd) > 120 else ''}")
    result = subprocess.run(cmd, shell=True, cwd=cwd or PROJECT_DIR,
                            capture_output=True, text=True)
    if result.stdout:
        print(f"  {result.stdout.strip()[:800]}")
    if result.stderr:
        print(f"  ⚠ {result.stderr.strip()[:500]}")
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd[:80]}")
    return result


def ask(prompt, secret=False):
    if secret:
        import getpass
        return getpass.getpass(prompt)
    return input(prompt).strip()


def github_api(method, endpoint, data=None, retries=MAX_RETRIES):
    """GitHub API call with auto-retry on network errors"""
    import requests

    url = f"https://api.github.com{endpoint}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    for attempt in range(1, retries + 1):
        try:
            if method == "GET":
                r = requests.get(url, headers=headers, timeout=30)
            elif method == "POST":
                r = requests.post(url, headers=headers, json=data, timeout=30)
            elif method == "PUT":
                r = requests.put(url, headers=headers, json=data, timeout=30)
            elif method == "DELETE":
                r = requests.delete(url, headers=headers, timeout=30)
            else:
                return None
            return r
        except Exception as e:
            print(f"  ⚠ Network error (attempt {attempt}/{retries}): {e}")
            if attempt < retries:
                print(f"  ⏳ {RETRY_DELAY}s wait...")
                time.sleep(RETRY_DELAY)
            else:
                print(f"  ❌ All {retries} attempts failed")
                raise
    return None


def get_github_username():
    r = github_api("GET", "/user")
    if r.status_code == 200:
        return r.json()["login"]
    raise RuntimeError("GitHub token invalid hai!")


# ══════════════════════════════════════════════
# FLUTTER PERMISSION FIX
# ══════════════════════════════════════════════

def fix_flutter_permission():
    print("\n🔧 Flutter check...")
    flutter_path = Path(FLUTTER_BIN) / "flutter"
    if not flutter_path.exists():
        print(f"  ⚠ Flutter nahi mila: {flutter_path}")
        return False
    if FLUTTER_BIN not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{os.environ.get('PATH', '')}:{FLUTTER_BIN}"
    result = run("flutter --version", check=False)
    if "Flutter" in result.stdout or "Flutter" in result.stderr:
        print("  ✅ Flutter working!")
        return True
    print("  ⚠ Flutter kaam nahi kar raha")
    return False


# ══════════════════════════════════════════════
# SETUP
# ══════════════════════════════════════════════

def setup():
    global GITHUB_TOKEN, GITHUB_REPO, REPO_NAME
    print("\n" + "=" * 60)
    print("  MYRA AI - Self-Healing Auto Builder")
    print("=" * 60)

    env_file = PROJECT_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()

    if os.environ.get("GITHUB_TOKEN"):
        GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
        REPO_NAME = os.environ.get("REPO_NAME", "myra-ai")
        username = get_github_username()
        GITHUB_REPO = f"{username}/{REPO_NAME}"
        print(f"\n✅ Config loaded: {GITHUB_REPO}")
        return

    print("\n📌 GitHub Token chahiye")
    print("   Scopes: repo, workflow, delete_repo")
    GITHUB_TOKEN = ask("   GitHub Token: ", secret=True)
    REPO_NAME = ask("   Repo name (default: myra-ai): ") or "myra-ai"
    username = get_github_username()
    GITHUB_REPO = f"{username}/{REPO_NAME}"

    env_content = f"GITHUB_TOKEN={GITHUB_TOKEN}\nREPO_NAME={REPO_NAME}\n"
    (PROJECT_DIR / ".env").write_text(env_content)
    print(f"\n✅ Config saved: {GITHUB_REPO}")


# ══════════════════════════════════════════════
# DELETE / CREATE REPO
# ══════════════════════════════════════════════

def delete_old_repo():
    print(f"\n🗑  Purani repo check: {GITHUB_REPO}")
    r = github_api("GET", f"/repos/{GITHUB_REPO}")
    if r.status_code == 404:
        print("  ℹ️  Exist nahi karti")
        return True
    if r.status_code != 200:
        print(f"  ⚠ Check fail: {r.status_code}")
        return False

    print("  🗑  Delete kar raha hoon...")
    r = github_api("DELETE", f"/repos/{GITHUB_REPO}")
    if r.status_code == 204:
        print("  ✅ Delete ho gayi!")
        time.sleep(3)
        return True
    print(f"  ⚠ Delete fail: {r.status_code}")
    return False


def create_new_repo():
    print(f"\n📦 Nayi repo: {GITHUB_REPO}")
    r = github_api("POST", "/user/repos", {
        "name": REPO_NAME,
        "private": False,
        "auto_init": False,
        "description": "MYRA AI Assistant - Gemini + Flutter"
    })
    if r.status_code == 201:
        print("  ✅ Repo create ho gayi!")
        time.sleep(3)
        return True
    elif r.status_code == 422:
        print("  ℹ️  Already exists")
        return True
    print(f"  ⚠ Create fail: {r.status_code}")
    return False


# ══════════════════════════════════════════════
# FLUTTER CREATE
# ══════════════════════════════════════════════

def create_flutter_base():
    print("\n📁 Flutter base project bana raha hoon...")
    if FLUTTER_DIR.exists():
        shutil.rmtree(FLUTTER_DIR)
        print("  🗑 Purana delete kiya")
    flutter_cmd = f"{FLUTTER_BIN}/flutter"
    run(f"{flutter_cmd} create --org {ORG_NAME} "
        f"--project-name {PROJECT_NAME} "
        f"--platforms android "
        f"{FLUTTER_DIR}", cwd=PROJECT_DIR)
    print("  ✅ Flutter base ready!")


# ══════════════════════════════════════════════
# FIX BUILD.GRADLE (compileSdk, ndkVersion, minSdk)
# ══════════════════════════════════════════════

def fix_build_gradle():
    """build.gradle.kts me compileSdk=36, ndkVersion=27.x, minSdk=24 set karo"""
    print("\n🔧 build.gradle.kts fix kar raha hoon...")

    paths = [
        FLUTTER_DIR / "android" / "app" / "build.gradle.kts",
        FLUTTER_DIR / "android" / "app" / "build.gradle",
    ]

    fixed = False
    for gradle_path in paths:
        if not gradle_path.exists():
            continue

        content = gradle_path.read_text()

        if gradle_path.suffix == ".kts":
            content = content.replace(
                "compileSdk = flutter.compileSdkVersion", "compileSdk = 36")
            content = content.replace(
                "ndkVersion = flutter.ndkVersion",
                'ndkVersion = "27.0.12077973"')
            content = content.replace(
                "minSdk = flutter.minSdkVersion", "minSdk = 24")
        else:
            content = content.replace(
                "compileSdkVersion flutter.compileSdkVersion", "compileSdkVersion 36")
            content = content.replace(
                "ndkVersion flutter.ndkVersion",
                'ndkVersion "27.0.12077973"')
            content = content.replace(
                "minSdkVersion flutter.minSdkVersion", "minSdkVersion 24")

        gradle_path.write_text(content)
        print(f"  ✅ {gradle_path.name} fix ho gayi")
        fixed = True

    return fixed


# ══════════════════════════════════════════════
# AUTO ERROR FIX (Logs padh kar)
# ══════════════════════════════════════════════

def fetch_build_logs():
    """Latest build ke logs fetch karo"""
    print("\n📋 Build logs fetch kar raha hoon...")
    r = github_api("GET", f"/repos/{GITHUB_REPO}/actions/runs?per_page=1")
    data = r.json()

    if not data.get("workflow_runs"):
        return None, None

    run_info = data["workflow_runs"][0]
    run_id = run_info["id"]
    conclusion = run_info.get("conclusion")

    # Logs download URL
    logs_url = f"/repos/{GITHUB_REPO}/actions/runs/{run_id}/logs"
    return run_id, conclusion


def auto_fix_from_logs():
    """Build fail ke common causes ko fix karo"""
    print("\n🔍 Common errors check kar raha hoon...")

    fixes_applied = []

    # Fix 1: minSdk check
    gradle_path = FLUTTER_DIR / "android" / "app" / "build.gradle.kts"
    if gradle_path.exists():
        content = gradle_path.read_text()
        if "minSdk = 24" not in content and "minSdk = flutter" in content:
            content = content.replace("minSdk = flutter.minSdkVersion", "minSdk = 24")
            gradle_path.write_text(content)
            fixes_applied.append("minSdk = 24 set kiya")

        # Fix 2: compileSdk check
        if "compileSdk = 36" not in content and "compileSdk = flutter" in content:
            content = content.replace("compileSdk = flutter.compileSdkVersion", "compileSdk = 36")
            gradle_path.write_text(content)
            fixes_applied.append("compileSdk = 36 set kiya")

    # Fix 3: MainActivity.kt check
    main_activity = FLUTTER_DIR / "android" / "app" / "src" / "main" / "kotlin" / "com" / "myra" / "myra_ai" / "MainActivity.kt"
    if main_activity.exists():
        content = main_activity.read_text()
        # Agar performGlobalAction use ho raha hai toh hata do
        if "performGlobalAction" in content:
            content = re.sub(
                r'.*performGlobalAction.*\n',
                '',
                content
            )
            main_activity.write_text(content)
            fixes_applied.append("performGlobalAction hataya")

    if fixes_applied:
        print("  ✅ Fixes applied:")
        for fix in fixes_applied:
            print(f"     • {fix}")
        return True

    print("  ℹ️  Koi obvious error nahi mila")
    return False


# ══════════════════════════════════════════════
# GITIGNORE
# ══════════════════════════════════════════════

GITIGNORE = '''# Secrets
.env
*.env
secrets.json

# Flutter
myra_flutter/build/
myra_flutter/.dart_tool/
myra_flutter/.flutter-plugins
myra_flutter/.flutter-plugins-dependencies
myra_flutter/android/.gradle/
myra_flutter/android/local.properties
myra_flutter/.packages
myra_flutter/pubspec.lock

# Python
__pycache__/
*.pyc
venv/
.venv/

# IDE/OS
.vscode/
.idea/
*.iml
.DS_Store
Thumbs.db
'''


# ══════════════════════════════════════════════
# FLUTTER FILES
# ══════════════════════════════════════════════

FLUTTER_PUBSPEC = '''name: myra_ai
description: MYRA AI Assistant
publish_to: 'none'
version: 1.0.0+1

environment:
  sdk: '>=3.0.0 <4.0.0'

dependencies:
  flutter:
    sdk: flutter
  cupertino_icons: ^1.0.6
  http: ^1.2.0
  permission_handler: ^11.3.1
  flutter_accessibility_service: ^1.2.0
  speech_to_text: ^6.6.0
  audioplayers: ^6.0.0
  flutter_secure_storage: ^9.0.0
  android_intent_plus: ^5.0.0
  model_viewer_plus: ^1.8.0
  flutter_tts: ^4.0.2
  google_generative_ai: ^0.4.6

dependency_overrides:
  collection: ^1.19.1

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^3.0.0

flutter:
  uses-material-design: true
  assets:
    - assets/
'''

FLUTTER_MAIN = '''import 'package:flutter/material.dart';
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
'''

FLUTTER_API_KEY_SCREEN = '''import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'home_screen.dart';

class ApiKeyScreen extends StatefulWidget {
  const ApiKeyScreen({super.key});
  @override
  State<ApiKeyScreen> createState() => _ApiKeyScreenState();
}

class _ApiKeyScreenState extends State<ApiKeyScreen> {
  final _controller = TextEditingController();
  final _storage = const FlutterSecureStorage();
  bool _isLoading = false;

  Future<void> _saveKey() async {
    final key = _controller.text.trim();
    if (key.isEmpty) return;
    setState(() => _isLoading = true);
    await _storage.write(key: 'gemini_api_key', value: key);
    if (mounted) {
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => const HomeScreen()),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.smart_toy, size: 80, color: Colors.purple),
            const SizedBox(height: 16),
            const Text('MYRA AI',
              style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold, color: Colors.white)),
            const SizedBox(height: 8),
            const Text('Gemini API Key Daalo',
              style: TextStyle(fontSize: 16, color: Colors.grey)),
            const SizedBox(height: 32),
            TextField(
              controller: _controller,
              decoration: InputDecoration(
                labelText: 'API Key',
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                prefixIcon: const Icon(Icons.key),
              ),
              obscureText: true,
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _isLoading ? null : _saveKey,
              style: ElevatedButton.styleFrom(
                minimumSize: const Size(double.infinity, 50),
                backgroundColor: Colors.purple,
              ),
              child: _isLoading
                  ? const CircularProgressIndicator(color: Colors.white)
                  : const Text('Save & Start'),
            ),
          ],
        ),
      ),
    );
  }
}
'''

FLUTTER_HOME = '''import 'package:flutter/material.dart';
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
'''

FLUTTER_3D_WIDGET = '''import 'package:flutter/material.dart';

class Avatar3DWidget extends StatefulWidget {
  const Avatar3DWidget({super.key});
  @override
  State<Avatar3DWidget> createState() => _Avatar3DWidgetState();
}

class _Avatar3DWidgetState extends State<Avatar3DWidget>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      alignment: Alignment.center,
      children: [
        AnimatedBuilder(
          animation: _controller,
          builder: (context, child) {
            return Container(
              width: 200 + (_controller.value * 30),
              height: 200 + (_controller.value * 30),
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    const Color(0xFF6C3FC5).withOpacity(0.4),
                    Colors.transparent,
                  ],
                ),
              ),
            );
          },
        ),
        Container(
          width: 180,
          height: 180,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: const LinearGradient(
              colors: [Color(0xFF6C3FC5), Color(0xFF9B6FE8)],
            ),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFF6C3FC5).withOpacity(0.5),
                blurRadius: 40,
                spreadRadius: 10,
              ),
            ],
          ),
          child: const Icon(Icons.face_retouching_natural, size: 120, color: Colors.white),
        ),
        Positioned(
          bottom: 10,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
            decoration: BoxDecoration(
              color: const Color(0xFF6C3FC5),
              borderRadius: BorderRadius.circular(20),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF6C3FC5).withOpacity(0.6),
                  blurRadius: 15,
                ),
              ],
            ),
            child: const Text(
              'MYRA',
              style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, letterSpacing: 3, fontSize: 16),
            ),
          ),
        ),
      ],
    );
  }
}
'''

FLUTTER_AI_SERVICE = '''import 'package:google_generative_ai/google_generative_ai.dart';
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
'''

FLUTTER_VOICE_SERVICE = '''import 'package:speech_to_text/speech_to_text.dart';
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
'''

FLUTTER_DEVICE_SERVICE = '''import 'package:flutter/services.dart';
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
'''

MAIN_ACTIVITY = '''package com.myra.myra_ai

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
}'''

MANIFEST = '''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.RECORD_AUDIO" />
    <uses-permission android:name="android.permission.READ_CONTACTS" />
    <uses-permission android:name="android.permission.CALL_PHONE" />
    <uses-permission android:name="android.permission.CAMERA" />
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
    <uses-permission android:name="android.permission.SYSTEM_ALERT_WINDOW" />
    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
    <uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />
    <uses-permission android:name="android.permission.SEND_SMS" />
    <uses-permission android:name="android.permission.INTERNET" />

    <application
        android:label="MYRA AI"
        android:name="${applicationName}"
        android:icon="@mipmap/ic_launcher"
        android:usesCleartextTraffic="true">
        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:launchMode="singleTop"
            android:taskAffinity=""
            android:theme="@style/LaunchTheme"
            android:configChanges="orientation|keyboardHidden|keyboard|screenSize|smallestScreenSize|locale|layoutDirection|fontScale|screenLayout|density|uiMode"
            android:hardwareAccelerated="true"
            android:windowSoftInputMode="adjustResize">
            <meta-data
                android:name="io.flutter.embedding.android.NormalTheme"
                android:resource="@style/NormalTheme" />
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>

        <meta-data
            android:name="flutterEmbedding"
            android:value="2" />

        <service
            android:name="slayer.accessibility.service.flutter_accessibility_service.AccessibilityListener"
            android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE"
            android:exported="false">
            <intent-filter>
                <action android:name="android.accessibilityservice.AccessibilityService" />
            </intent-filter>
            <meta-data
                android:name="android.accessibilityservice"
                android:resource="@xml/accessibilityservice" />
        </service>
    </application>

    <queries>
        <intent>
            <action android:name="android.intent.action.PROCESS_TEXT" />
            <data android:mimeType="text/plain" />
        </intent>
    </queries>
</manifest>'''

ACCESSIBILITY_XML = '''<?xml version="1.0" encoding="utf-8"?>
<accessibility-service xmlns:android="http://schemas.android.com/apk/res/android"
    android:accessibilityEventTypes="typeWindowsChanged|typeWindowStateChanged|typeWindowContentChanged"
    android:accessibilityFeedbackType="feedbackVisual"
    android:notificationTimeout="300"
    android:accessibilityFlags="flagDefault|flagIncludeNotImportantViews|flagRequestTouchExplorationMode|flagRequestEnhancedWebAccessibility|flagReportViewIds|flagRetrieveInteractiveWindows"
    android:canRetrieveWindowContent="true"
    android:canPerformGestures="true" />'''

GITHUB_WORKFLOW = '''name: Build MYRA AI APK
on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Java
        uses: actions/setup-java@v4
        with:
          distribution: 'zulu'
          java-version: '17'

      - name: Setup Flutter
        uses: subosito/flutter-action@v2
        with:
          flutter-version: '3.24.0'
          channel: 'stable'

      - name: Install dependencies
        run: cd myra_flutter && flutter pub get

      - name: Build APK
        run: cd myra_flutter && flutter build apk --release

      - name: Upload APK
        uses: actions/upload-artifact@v4
        with:
          name: myra-ai-apk
          path: myra_flutter/build/app/outputs/flutter-apk/app-release.apk
'''


# ══════════════════════════════════════════════
# OVERWRITE FILES
# ══════════════════════════════════════════════

def overwrite_flutter_files():
    print("\n📝 Flutter files overwrite kar raha hoon...")
    dirs = [
        FLUTTER_DIR / "lib" / "screens",
        FLUTTER_DIR / "lib" / "services",
        FLUTTER_DIR / "lib" / "widgets",
        FLUTTER_DIR / "assets",
        FLUTTER_DIR / "android" / "app" / "src" / "main" / "res" / "xml",
        PROJECT_DIR / ".github" / "workflows",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    kotlin_dir = FLUTTER_DIR / "android" / "app" / "src" / "main" / "kotlin" / "com" / "myra" / "myra_ai"
    kotlin_dir.mkdir(parents=True, exist_ok=True)

    wrong_dir = FLUTTER_DIR / "android" / "app" / "src" / "main" / "kotlin" / "com" / "myra" / "assistant"
    if wrong_dir.exists():
        shutil.rmtree(wrong_dir)

    files = {
        PROJECT_DIR / ".gitignore": GITIGNORE,
        FLUTTER_DIR / "pubspec.yaml": FLUTTER_PUBSPEC,
        FLUTTER_DIR / "lib" / "main.dart": FLUTTER_MAIN,
        FLUTTER_DIR / "lib" / "screens" / "home_screen.dart": FLUTTER_HOME,
        FLUTTER_DIR / "lib" / "screens" / "api_key_screen.dart": FLUTTER_API_KEY_SCREEN,
        FLUTTER_DIR / "lib" / "widgets" / "avatar_3d_widget.dart": FLUTTER_3D_WIDGET,
        FLUTTER_DIR / "lib" / "services" / "ai_service.dart": FLUTTER_AI_SERVICE,
        FLUTTER_DIR / "lib" / "services" / "voice_service.dart": FLUTTER_VOICE_SERVICE,
        FLUTTER_DIR / "lib" / "services" / "device_service.dart": FLUTTER_DEVICE_SERVICE,
        PROJECT_DIR / ".github" / "workflows" / "build.yml": GITHUB_WORKFLOW,
        FLUTTER_DIR / "android" / "app" / "src" / "main" / "AndroidManifest.xml": MANIFEST,
        FLUTTER_DIR / "android" / "app" / "src" / "main" / "res" / "xml" / "accessibilityservice.xml": ACCESSIBILITY_XML,
        kotlin_dir / "MainActivity.kt": MAIN_ACTIVITY,
    }

    for path, content in files.items():
        path.write_text(content)

    placeholder = FLUTTER_DIR / "assets" / "myra_model.glb"
    placeholder.write_bytes(b"")
    print("  ✅ Saari files ready!")


# ══════════════════════════════════════════════
# PUSH
# ══════════════════════════════════════════════

def push_to_github():
    print("\n📤 GitHub par push kar raha hoon...")
    os.chdir(PROJECT_DIR)
    if (PROJECT_DIR / ".git").exists():
        shutil.rmtree(PROJECT_DIR / ".git")
    run("git init")
    run("git branch -M main")
    run(f"git remote add origin https://{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git")
    run("git add -A")
    run(f'git commit -m "MYRA AI: Build {datetime.now().strftime("%Y-%m-%d %H:%M")}"', check=False)

    # Push with retry
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            run("git push -u origin main --force")
            print(f"\n✅ Push ho gaya!")
            return True
        except Exception as e:
            print(f"  ⚠ Push fail (attempt {attempt}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
    return False


# ══════════════════════════════════════════════
# TRIGGER BUILD
# ══════════════════════════════════════════════

def trigger_build():
    print("\n🔨 Build trigger kar raha hoon...")
    time.sleep(8)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = github_api("POST",
                          f"/repos/{GITHUB_REPO}/actions/workflows/build.yml/dispatches",
                          {"ref": "main"})
            if r.status_code == 204:
                print("  ✅ Build trigger ho gayi!")
                print(f"  📱 https://github.com/{GITHUB_REPO}/actions")
                return True
            else:
                print(f"  ⚠ Status {r.status_code}: {r.text[:200]}")
        except Exception as e:
            print(f"  ⚠ Trigger fail (attempt {attempt}/{MAX_RETRIES}): {e}")

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY)

    print("\n  💡 Manually trigger karo:")
    print(f"     https://github.com/{GITHUB_REPO}/actions")
    return False


def wait_and_watch():
    """Build ko watch karo, fail ho toh auto-fix karo"""
    print("\n⏳ Build watch kar raha hoon...")

    for i in range(90):
        time.sleep(10)
        try:
            r = github_api("GET", f"/repos/{GITHUB_REPO}/actions/runs?per_page=1")
            data = r.json()
            if not data.get("workflow_runs"):
                continue

            info = data["workflow_runs"][0]
            status = info.get("status")
            conclusion = info.get("conclusion")
            print(f"  ⏱ [{i*10}s] {status}")

            if status == "completed":
                if conclusion == "success":
                    print(f"\n✅ BUILD SUCCESSFUL!")
                    print(f"📥 APK: https://github.com/{GITHUB_REPO}/actions")
                    return True
                else:
                    print(f"\n❌ FAILED: {conclusion}")
                    print(f"   Logs: https://github.com/{GITHUB_REPO}/actions")
                    # Try auto-fix
                    print("\n🔧 Auto-fix try kar raha hoon...")
                    if auto_fix_from_logs():
                        print("\n🔄 Fixed! Dobara push + build...")
                        push_to_github()
                        trigger_build()
                        continue
                    return False
        except Exception as e:
            print(f"  ⚠ Check error: {e}")

    print(f"\n⚠ Timeout. Check: https://github.com/{GITHUB_REPO}/actions")
    return False


# ══════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════

def main():
    print("""
    ╔══════════════════════════════════════════╗
    ║   MYRA AI - Self-Healing Auto Builder    ║
    ║   Auto Retry + Auto Fix + Complete       ║
    ╚══════════════════════════════════════════╝
    """)

    if not fix_flutter_permission():
        print("\n❌ Flutter fix karo pehle")
        return

    setup()

    if not delete_old_repo():
        print("\n❌ Repo delete fail")
        return

    if not create_new_repo():
        print("\n❌ Repo create fail")
        return

    create_flutter_base()
    fix_build_gradle()
    overwrite_flutter_files()
    push_to_github()
    trigger_build()
    wait_and_watch()

    print(f"\n🎉 Done! APK: https://github.com/{GITHUB_REPO}/actions")


if __name__ == "__main__":
    main()