import 'package:flutter/material.dart';

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
