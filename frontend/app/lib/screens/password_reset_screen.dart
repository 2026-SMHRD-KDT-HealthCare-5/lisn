import 'package:flutter/material.dart';

import '../models/auth_models.dart';
import '../services/app_services.dart';
import '../theme/app_theme.dart';
import '../widgets/common_widgets.dart';

class PasswordResetScreen extends StatefulWidget {
  const PasswordResetScreen({super.key});

  @override
  State<PasswordResetScreen> createState() => _PasswordResetScreenState();
}

class _PasswordResetScreenState extends State<PasswordResetScreen> {
  final emailKey = GlobalKey<FormState>();
  final resetKey = GlobalKey<FormState>();
  final emailController = TextEditingController();
  final tokenController = TextEditingController();
  final passwordController = TextEditingController();
  final confirmController = TextEditingController();

  bool requestSent = false;
  bool loading = false;
  String? errorMessage;

  @override
  void dispose() {
    emailController.dispose();
    tokenController.dispose();
    passwordController.dispose();
    confirmController.dispose();
    super.dispose();
  }

  Future<void> requestReset() async {
    if (!(emailKey.currentState?.validate() ?? false) || loading) return;
    await runRequest(() async {
      await AppServices.auth.requestPasswordReset(emailController.text);
      if (mounted) {
        setState(() => requestSent = true);
      }
    });
  }

  Future<void> confirmReset() async {
    if (!(resetKey.currentState?.validate() ?? false) || loading) return;
    await runRequest(() async {
      await AppServices.auth.confirmPasswordReset(
        token: tokenController.text,
        newPassword: passwordController.text,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('비밀번호가 변경됐어요. 다시 로그인해주세요.')),
      );
      Navigator.pop(context);
    });
  }

  Future<void> runRequest(Future<void> Function() request) async {
    setState(() {
      loading = true;
      errorMessage = null;
    });
    try {
      await request();
    } on ApiException catch (error) {
      if (mounted) {
        setState(() => errorMessage = error.message);
      }
    } finally {
      if (mounted) {
        setState(() => loading = false);
      }
    }
  }

  String? validateEmail(String? value) {
    final email = value?.trim() ?? '';
    if (!email.contains('@') || !email.contains('.')) {
      return '올바른 이메일을 입력해주세요';
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          onPressed: loading ? null : () => Navigator.pop(context),
          icon: const Icon(Icons.arrow_back_rounded),
        ),
        // AppBar 제목은 "여기가 어디인지"를 알려주는 자리입니다.
        // 브랜드를 넣으면 사용자가 어떤 작업 중인지 알 수 없습니다.
        title: const Text('비밀번호 재설정',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
        centerTitle: true,
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(22, 18, 22, 40),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                '비밀번호를\n다시 설정해요',
                style: TextStyle(
                  fontSize: 28,
                  height: 1.25,
                  fontWeight: FontWeight.w900,
                  color: AppColors.navy,
                ),
              ),
              const SizedBox(height: 9),
              const Text(
                '가입한 이메일을 확인한 뒤 안전하게 변경할 수 있어요.',
                style: TextStyle(color: AppColors.muted, height: 1.6),
              ),
              const SizedBox(height: 25),
              AppCard(
                child: Form(
                  key: emailKey,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      const _StepTitle(
                        number: '1',
                        title: '이메일 확인',
                        description: '가입할 때 사용한 이메일을 입력해주세요',
                      ),
                      const SizedBox(height: 18),
                      const Text(
                        '이메일',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 8),
                      TextFormField(
                        controller: emailController,
                        keyboardType: TextInputType.emailAddress,
                        validator: validateEmail,
                      ),
                      const SizedBox(height: 14),
                      ElevatedButton(
                        onPressed: loading ? null : requestReset,
                        child: const Text('인증 메일 보내기'),
                      ),
                    ],
                  ),
                ),
              ),
              if (requestSent) ...[
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(15),
                  decoration: BoxDecoration(
                    color: const Color(0xFFEAF8F4),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: const Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(
                        Icons.check_circle_rounded,
                        color: Color(0xFF63A295),
                        size: 20,
                      ),
                      SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          '재설정 안내를 보냈어요.\n가입 여부와 관계없이 동일한 안내가 표시됩니다.',
                          style: TextStyle(
                            color: Color(0xFF5E8C83),
                            fontSize: 11,
                            height: 1.55,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                AppCard(
                  child: Form(
                    key: resetKey,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        const _StepTitle(
                          number: '2',
                          title: '새 비밀번호 입력',
                          description: '메일로 받은 토큰과 새 비밀번호를 입력해주세요',
                        ),
                        const SizedBox(height: 16),
                        TextFormField(
                          controller: tokenController,
                          decoration: const InputDecoration(hintText: '재설정 토큰'),
                          validator: (value) => (value?.trim().isEmpty ?? true)
                              ? '재설정 토큰을 입력해주세요'
                              : null,
                        ),
                        const SizedBox(height: 11),
                        TextFormField(
                          controller: passwordController,
                          obscureText: true,
                          decoration: const InputDecoration(hintText: '새 비밀번호'),
                          validator: (value) => (value?.length ?? 0) < 8
                              ? '비밀번호는 8자 이상 입력해주세요'
                              : null,
                        ),
                        const SizedBox(height: 11),
                        TextFormField(
                          controller: confirmController,
                          obscureText: true,
                          decoration:
                              const InputDecoration(hintText: '새 비밀번호 확인'),
                          validator: (value) => value != passwordController.text
                              ? '비밀번호가 일치하지 않습니다'
                              : null,
                        ),
                        const SizedBox(height: 14),
                        ElevatedButton(
                          onPressed: loading ? null : confirmReset,
                          child: const Text('비밀번호 재설정 완료'),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
              if (errorMessage != null) ...[
                const SizedBox(height: 12),
                Text(
                  errorMessage!,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: Color(0xFF69738F),
                    fontSize: 11,
                  ),
                ),
              ],
              if (loading) ...[
                const SizedBox(height: 16),
                const Center(child: CircularProgressIndicator()),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _StepTitle extends StatelessWidget {
  const _StepTitle({
    required this.number,
    required this.title,
    required this.description,
  });

  final String number;
  final String title;
  final String description;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        CircleAvatar(
          radius: 17,
          backgroundColor: const Color(0xFFE7EDFF),
          child: Text(
            number,
            style: const TextStyle(
              color: AppColors.primary,
              fontWeight: FontWeight.w800,
            ),
          ),
        ),
        const SizedBox(width: 11),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: const TextStyle(fontWeight: FontWeight.w800)),
              const SizedBox(height: 2),
              Text(
                description,
                style: const TextStyle(fontSize: 10, color: AppColors.muted),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
