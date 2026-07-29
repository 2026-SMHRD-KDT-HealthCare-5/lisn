import 'package:flutter/material.dart';

import '../theme/app_theme.dart';
import '../widgets/common_widgets.dart';
import 'join_screen.dart';
import 'main_shell.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final idController = TextEditingController(text: 'jieun');
  final passwordController = TextEditingController(text: 'maeume123');

  @override
  void dispose() {
    idController.dispose();
    passwordController.dispose();
    super.dispose();
  }

  void login() {
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const MainShell()),
      (_) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        top: false,
        child: LayoutBuilder(
          builder: (context, constraints) {
            final desktop = constraints.maxWidth >= 800;
            return Row(
              children: [
                if (desktop) const Expanded(child: _DesktopLoginVisual()),
                Expanded(
                  child: SingleChildScrollView(
                    child: Column(
                      children: [
                        if (!desktop) const _MobileLoginHero(),
                        ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 480),
                          child: Padding(
                            padding: EdgeInsets.fromLTRB(desktop ? 50 : 30,
                                desktop ? 100 : 38, desktop ? 50 : 30, 70),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                Text('다시 만나 반가워요',
                                    style: Theme.of(context)
                                        .textTheme
                                        .headlineMedium
                                        ?.copyWith(
                                            fontSize: desktop ? 29 : 24)),
                                const SizedBox(height: 5),
                                const Text('마음이와 함께 오늘 하루를 돌아봐요.',
                                    style: TextStyle(
                                        color: AppColors.muted, fontSize: 12)),
                                const SizedBox(height: 28),
                                const Text('아이디',
                                    style: TextStyle(
                                        fontSize: 12,
                                        fontWeight: FontWeight.w700)),
                                const SizedBox(height: 9),
                                TextField(controller: idController),
                                const SizedBox(height: 20),
                                const Text('비밀번호',
                                    style: TextStyle(
                                        fontSize: 12,
                                        fontWeight: FontWeight.w700)),
                                const SizedBox(height: 9),
                                TextField(
                                    controller: passwordController,
                                    obscureText: true),
                                const SizedBox(height: 30),
                                ElevatedButton(
                                    onPressed: login, child: const Text('로그인')),
                                const SizedBox(height: 34),
                                FilledButton.tonal(
                                  onPressed: () => Navigator.push(
                                      context,
                                      MaterialPageRoute(
                                          builder: (_) => const JoinScreen())),
                                  style: FilledButton.styleFrom(
                                    minimumSize: const Size.fromHeight(48),
                                    backgroundColor: AppColors.soft,
                                    foregroundColor: AppColors.primary,
                                    shape: RoundedRectangleBorder(
                                        borderRadius:
                                            BorderRadius.circular(12)),
                                  ),
                                  child: const Text('처음 오셨나요? 회원가입'),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _MobileLoginHero extends StatelessWidget {
  const _MobileLoginHero();

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 228,
      width: double.infinity,
      child: Stack(
        clipBehavior: Clip.hardEdge,
        children: [
          const ColoredBox(color: Color(0xFFEDF2FF), child: SizedBox.expand()),
          const Positioned(left: 24, top: 25, child: MaeumeBrand(size: 22)),
          const Positioned(
            left: 25,
            top: 92,
            child: Text('오늘의 마음도\n포근히 안아줄게요',
                style: TextStyle(
                    fontSize: 25,
                    height: 1.2,
                    fontWeight: FontWeight.w800,
                    color: AppColors.navy)),
          ),
          Positioned(
            width: 226,
            height: 226,
            right: -26,
            top: 35,
            child: Image.asset('assets/images/login_mascot.png',
                fit: BoxFit.cover),
          ),
        ],
      ),
    );
  }
}

class _DesktopLoginVisual extends StatelessWidget {
  const _DesktopLoginVisual();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(52),
      decoration: const BoxDecoration(
          gradient: LinearGradient(
              colors: [Color(0xFFF7F9FF), Color(0xFFDCE9FA)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight)),
      child: Stack(
        children: [
          const Align(
              alignment: Alignment.topLeft, child: MaeumeBrand(size: 26)),
          const Align(
            alignment: Alignment(-.65, -.15),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('MY DAILY MIND CARE',
                    style: TextStyle(
                        color: AppColors.primary,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 1.8)),
                SizedBox(height: 18),
                Text('오늘의 마음도\n포근히 안아줄게요',
                    style: TextStyle(
                        fontSize: 48,
                        height: 1.25,
                        fontWeight: FontWeight.w900,
                        color: AppColors.navy)),
                SizedBox(height: 15),
                Text('라이프로그와 AI로 나의 감정을 이해하는 가장 다정한 방법',
                    style: TextStyle(color: AppColors.muted)),
              ],
            ),
          ),
          Align(
              alignment: const Alignment(.75, .7),
              child: ClipRRect(
                  borderRadius: BorderRadius.circular(40),
                  child: Image.asset('assets/images/login_mascot.png',
                      width: 330, height: 330, fit: BoxFit.cover))),
        ],
      ),
    );
  }
}
