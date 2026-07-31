import 'package:flutter/material.dart';

import '../models/auth_models.dart';
import '../services/app_services.dart';
import '../theme/app_theme.dart';
import '../widgets/common_widgets.dart';
import 'main_shell.dart';

class JoinScreen extends StatefulWidget {
  const JoinScreen({super.key});

  @override
  State<JoinScreen> createState() => _JoinScreenState();
}

class _JoinScreenState extends State<JoinScreen> {
  int step = 0;
  final checks = [false, false, false, false];
  final informationKey = GlobalKey<FormState>();
  final nameController = TextEditingController();
  final birthDateController = TextEditingController();
  final emailController = TextEditingController();
  final passwordController = TextEditingController();
  final heightController = TextEditingController();
  final phoneController = TextEditingController();
  String? gender;
  bool loading = false;
  bool? emailAvailable;
  String? errorMessage;

  @override
  void dispose() {
    nameController.dispose();
    birthDateController.dispose();
    emailController.dispose();
    passwordController.dispose();
    heightController.dispose();
    phoneController.dispose();
    super.dispose();
  }

  Future<void> checkEmail() async {
    final email = emailController.text.trim();
    if (!email.contains('@') || !email.contains('.')) {
      setState(() {
        emailAvailable = false;
        errorMessage = '올바른 이메일을 입력해주세요';
      });
      return;
    }
    await runRequest(() async {
      final available = await AppServices.auth.checkEmail(email);
      if (mounted) {
        setState(() => emailAvailable = available);
      }
    });
  }

  Future<void> signup() async {
    if (!(informationKey.currentState?.validate() ?? false) || loading) {
      return;
    }
    await runRequest(() async {
      final available = await AppServices.auth.checkEmail(emailController.text);
      if (!available) {
        if (mounted) {
          setState(() {
            emailAvailable = false;
            errorMessage = '이미 가입된 이메일입니다';
          });
        }
        return;
      }

      final birthDate = birthDateController.text.trim().isEmpty
          ? null
          : DateTime.tryParse(birthDateController.text.trim());
      await AppServices.auth.signup(
        SignupInput(
          email: emailController.text.trim(),
          password: passwordController.text,
          name: nameController.text.trim(),
          birthDate: birthDate,
          gender: gender,
          heightCm: double.tryParse(heightController.text.trim()),
          phone: phoneController.text.trim().isEmpty
              ? null
              : phoneController.text.trim(),
          termsAgreed: checks[0] && checks[1],
          sensitiveAgreed: checks[2],
        ),
      );
      if (mounted) {
        setState(() => step = 2);
      }
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
            onPressed: () =>
                step == 0 ? Navigator.pop(context) : setState(() => step--),
            icon: const Icon(Icons.arrow_back_rounded)),
        title: Row(
            mainAxisSize: MainAxisSize.min,
            children: List.generate(
                3,
                (i) => Container(
                    width: 34,
                    height: 4,
                    margin: const EdgeInsets.symmetric(horizontal: 3),
                    decoration: BoxDecoration(
                        color: i <= step ? AppColors.primary : AppColors.line,
                        borderRadius: BorderRadius.circular(4))))),
        centerTitle: true,
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(25, 18, 25, 40),
          child: AnimatedSwitcher(
            duration: const Duration(milliseconds: 280),
            child: switch (step) {
              0 => _agreementStep(),
              1 => _informationStep(),
              _ => _completeStep(),
            },
          ),
        ),
      ),
    );
  }

  Widget _heading(String eyebrow, String title, String description) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(eyebrow,
            style: const TextStyle(
                fontSize: 11,
                color: AppColors.primary,
                fontWeight: FontWeight.w800,
                letterSpacing: 1.4)),
        const SizedBox(height: 12),
        Text(title,
            style: const TextStyle(
                fontSize: 27,
                fontWeight: FontWeight.w900,
                color: AppColors.navy)),
        const SizedBox(height: 7),
        Text(description,
            style: const TextStyle(color: AppColors.muted, height: 1.6)),
      ],
    );
  }

  Widget _agreementStep() {
    final labels = [
      '서비스 이용약관 동의',
      '개인정보 수집 및 이용 동의',
      '민감정보(생체·건강 데이터) 처리 동의',
      '맞춤 케어 알림 수신 동의'
    ];
    final requiredChecked = checks.take(3).every((value) => value);
    return Column(
      key: const ValueKey(0),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _heading('STEP 01', '마음이와 시작하기 전에', '안전하고 세심한 케어를 위해 약관을 확인해주세요.'),
        const SizedBox(height: 28),
        AppCard(
          color: const Color(0xFFF5F7FF),
          child: InkWell(
            onTap: () => setState(() {
              final next = !checks.every((value) => value);
              for (var i = 0; i < checks.length; i++) {
                checks[i] = next;
              }
            }),
            child: Row(children: [
              CircleAvatar(
                  radius: 15,
                  backgroundColor: checks.every((v) => v)
                      ? AppColors.primary
                      : AppColors.line,
                  child:
                      const Icon(Icons.check, color: Colors.white, size: 17)),
              const SizedBox(width: 13),
              const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('전체 동의하기',
                        style: TextStyle(fontWeight: FontWeight.w800)),
                    SizedBox(height: 3),
                    Text('선택 항목도 함께 포함됩니다.',
                        style: TextStyle(fontSize: 10, color: AppColors.muted))
                  ]),
            ]),
          ),
        ),
        const SizedBox(height: 12),
        ...List.generate(
            labels.length,
            (i) => ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Checkbox(
                      value: checks[i],
                      onChanged: (value) =>
                          setState(() => checks[i] = value ?? false)),
                  title: Text(labels[i],
                      style: const TextStyle(
                          fontSize: 13, fontWeight: FontWeight.w600)),
                  trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                    Text(i < 3 ? '필수' : '선택',
                        style: TextStyle(
                            fontSize: 10,
                            color:
                                i < 3 ? AppColors.primary : AppColors.muted)),
                    const Icon(Icons.chevron_right_rounded,
                        color: AppColors.muted)
                  ]),
                  onTap: () => setState(() => checks[i] = !checks[i]),
                )),
        const SizedBox(height: 22),
        ElevatedButton(
            onPressed: requiredChecked ? () => setState(() => step = 1) : null,
            child: const Text('다음')),
      ],
    );
  }

  Widget _informationStep() {
    return Form(
      key: informationKey,
      child: Column(
        key: const ValueKey(1),
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _heading('STEP 02', '기본 정보를 알려주세요', '꼭 필요한 정보만 간단히 여쭤볼게요.'),
          const SizedBox(height: 25),
          _Field(
            label: '이름',
            controller: nameController,
            textInputAction: TextInputAction.next,
            validator: (value) =>
                (value?.trim().isEmpty ?? true) ? '이름을 입력해주세요' : null,
          ),
          _Field(
            label: '생년월일 · 선택',
            controller: birthDateController,
            hint: '1994-05-16',
            keyboardType: TextInputType.datetime,
            textInputAction: TextInputAction.next,
            validator: (value) {
              if (value == null || value.trim().isEmpty) return null;
              return DateTime.tryParse(value.trim()) == null
                  ? 'YYYY-MM-DD 형식으로 입력해주세요'
                  : null;
            },
          ),
          _Field(
            label: '이메일',
            controller: emailController,
            hint: 'user@example.com',
            keyboardType: TextInputType.emailAddress,
            textInputAction: TextInputAction.next,
            validator: (value) {
              final email = value?.trim() ?? '';
              if (!email.contains('@') || !email.contains('.')) {
                return '올바른 이메일을 입력해주세요';
              }
              return null;
            },
          ),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(
              onPressed: loading ? null : checkEmail,
              child: Text(
                emailAvailable == true
                    ? '사용 가능한 이메일이에요'
                    : emailAvailable == false
                        ? '이미 사용 중인 이메일이에요'
                        : '이메일 중복 확인',
                style: const TextStyle(fontSize: 11),
              ),
            ),
          ),
          _Field(
            label: '비밀번호',
            controller: passwordController,
            obscure: true,
            textInputAction: TextInputAction.next,
            validator: (value) =>
                (value?.length ?? 0) < 8 ? '비밀번호는 8자 이상 입력해주세요' : null,
          ),
          const Text(
            '성별 · 선택',
            style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 8),
          DropdownButtonFormField<String>(
            initialValue: gender,
            decoration: const InputDecoration(hintText: '선택해주세요'),
            items: const [
              DropdownMenuItem(value: 'MALE', child: Text('남성')),
              DropdownMenuItem(value: 'FEMALE', child: Text('여성')),
              DropdownMenuItem(value: 'OTHER', child: Text('기타')),
            ],
            onChanged: (value) => setState(() => gender = value),
          ),
          const SizedBox(height: 18),
          _Field(
            label: '키(cm) · 선택',
            controller: heightController,
            hint: '예: 165.5',
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            textInputAction: TextInputAction.next,
            validator: (value) {
              if (value == null || value.trim().isEmpty) return null;
              final height = double.tryParse(value.trim());
              return height == null || height <= 0 || height > 300
                  ? '키는 0보다 크고 300 이하로 입력해주세요'
                  : null;
            },
          ),
          _Field(
            label: '연락처 · 선택',
            controller: phoneController,
            hint: '010-0000-0000',
            keyboardType: TextInputType.phone,
            textInputAction: TextInputAction.done,
          ),
          if (errorMessage != null) ...[
            Text(
              errorMessage!,
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: Color(0xFF69738F),
                fontSize: 11,
              ),
            ),
            const SizedBox(height: 12),
          ],
          ElevatedButton(
            onPressed: loading ? null : signup,
            child: loading
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Colors.white,
                    ),
                  )
                : const Text('회원가입 완료'),
          ),
        ],
      ),
    );
  }

  Widget _completeStep() {
    return Column(
      key: const ValueKey(2),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const SizedBox(height: 30),
        Center(
          child: Stack(
            children: [
              Container(
                  width: 155,
                  height: 155,
                  decoration: const BoxDecoration(
                      shape: BoxShape.circle, color: Color(0xFFEEF2FF)),
                  alignment: Alignment.center,
                  child: const MaeumeMascot(size: 95)),
              const Positioned(
                  right: 4,
                  bottom: 8,
                  child: CircleAvatar(
                      radius: 18,
                      backgroundColor: Color(0xFF63CFA7),
                      child: Icon(Icons.check, color: Colors.white))),
            ],
          ),
        ),
        const SizedBox(height: 28),
        const Text('WELCOME',
            textAlign: TextAlign.center,
            style: TextStyle(
                color: AppColors.primary,
                fontSize: 11,
                fontWeight: FontWeight.w800,
                letterSpacing: 1.5)),
        const SizedBox(height: 9),
        Text('${nameController.text.trim()}님, 반가워요!',
            textAlign: TextAlign.center,
            style: const TextStyle(
                fontSize: 28,
                fontWeight: FontWeight.w900,
                color: AppColors.navy)),
        const SizedBox(height: 10),
        const Text('가입이 완료되었어요.\n웨어러블을 연결하면 더 세심하게 마음을 살필 수 있어요.',
            textAlign: TextAlign.center,
            style: TextStyle(height: 1.7, color: AppColors.muted)),
        const SizedBox(height: 28),
        const AppCard(
            child: Row(children: [
          CircleAvatar(
              backgroundColor: Color(0xFFEEF1FF),
              child: Icon(Icons.watch_rounded, color: AppColors.primary)),
          SizedBox(width: 13),
          Expanded(
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                Text('웨어러블 연결하기',
                    style: TextStyle(fontWeight: FontWeight.w800)),
                Text('Health Connect',
                    style: TextStyle(fontSize: 10, color: AppColors.muted))
              ])),
          Icon(Icons.chevron_right_rounded)
        ])),
        const SizedBox(height: 18),
        ElevatedButton(
          onPressed: () => Navigator.of(context).pushAndRemoveUntil(
              MaterialPageRoute(builder: (_) => const MainShell()),
              (_) => false),
          child: const Text('마음이 시작하기'),
        ),
      ],
    );
  }
}

class _Field extends StatelessWidget {
  const _Field({
    required this.label,
    required this.controller,
    this.hint,
    this.obscure = false,
    this.keyboardType,
    this.textInputAction,
    this.validator,
  });

  final String label;
  final TextEditingController controller;
  final String? hint;
  final bool obscure;
  final TextInputType? keyboardType;
  final TextInputAction? textInputAction;
  final String? Function(String?)? validator;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label,
              style:
                  const TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          TextFormField(
            controller: controller,
            obscureText: obscure,
            keyboardType: keyboardType,
            textInputAction: textInputAction,
            validator: validator,
            decoration: InputDecoration(hintText: hint),
          ),
        ],
      ),
    );
  }
}
