import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../models/auth_models.dart';
import '../services/app_services.dart';
import '../theme/app_theme.dart';
import '../widgets/common_widgets.dart';
import 'join_screen.dart';
import 'main_shell.dart';

/// MAIN_LOGIN_01
///
/// 입력란을 한 번에 다 보여주지 않고 **단계적으로 드러냅니다.**
///
///   0단계  마스코트와 문구가 화면을 온전히 씀 + [로그인] [회원가입]
///   1단계  이메일 입력란
///   2단계  비밀번호 입력란 + 「비밀번호를 잊으셨나요?」
///
/// 첫 화면에서 빈 입력란 두 개를 마주하는 것보다 부담이 덜합니다.
/// 회원가입 버튼은 0단계에서만 보입니다 — 로그인을 시작한 뒤에는
/// 지금 하려던 일에서 눈을 돌리게 하는 선택지입니다.
class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

enum _Step { intro, email, password }

class _LoginScreenState extends State<LoginScreen> {
  final formKey = GlobalKey<FormState>();
  final emailController = TextEditingController();
  final passwordController = TextEditingController();
  final emailFocus = FocusNode();
  final passwordFocus = FocusNode();

  _Step step = _Step.intro;
  bool loading = false;
  String? errorMessage;

  @override
  void initState() {
    super.initState();
    emailController.addListener(_onEmailChanged);
  }

  @override
  void dispose() {
    emailController.removeListener(_onEmailChanged);
    emailController.dispose();
    passwordController.dispose();
    emailFocus.dispose();
    passwordFocus.dispose();
    super.dispose();
  }

  /// 이메일이 형태를 갖추면 비밀번호 칸을 띄웁니다.
  ///
  /// 한 글자만 쳐도 나타나게 하면 화면이 계속 흔들립니다. 반대로 완벽한
  /// 검증을 요구하면 오타 하나에 다음 칸이 사라져 더 답답합니다.
  /// `@` 와 `.` 만 보는 이 기준은 로그인 버튼의 실제 검증과 같습니다.
  bool get _emailLooksReady {
    final email = emailController.text.trim();
    return email.contains('@') && email.contains('.');
  }

  void _onEmailChanged() {
    if (step == _Step.email && _emailLooksReady) {
      setState(() => step = _Step.password);
    }
    // ⚠ 한 번 나타난 비밀번호 칸은 다시 숨기지 않습니다. 이메일을 고치는
    //   중에 칸이 사라졌다 나타나면 입력하던 비밀번호까지 흔들립니다.
  }

  void _startLogin() {
    setState(() {
      step = _Step.email;
      errorMessage = null;
    });
    // 프레임이 그려진 뒤에 포커스를 줘야 키보드가 올라옵니다.
    WidgetsBinding.instance
        .addPostFrameCallback((_) => emailFocus.requestFocus());
  }

  void _backToIntro() {
    FocusScope.of(context).unfocus();
    setState(() {
      step = _Step.intro;
      errorMessage = null;
    });
  }

  Future<void> login() async {
    if (!(formKey.currentState?.validate() ?? false) || loading) {
      return;
    }
    setState(() {
      loading = true;
      errorMessage = null;
    });
    try {
      await AppServices.auth.login(
        email: emailController.text,
        password: passwordController.text,
      );
      if (!mounted) return;
      // 비밀번호 관리자가 저장 여부를 물어볼 수 있게 알려줍니다.
      TextInput.finishAutofillContext();
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => const MainShell()),
        (_) => false,
      );
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
    final intro = step == _Step.intro;

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
                        // 0단계에서는 히어로가 더 큽니다. 마스코트가 화면을
                        // 온전히 쓰도록 두고, 입력이 시작되면 자리를 내줍니다.
                        if (!desktop) _MobileLoginHero(expanded: intro),
                        ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 480),
                          child: Padding(
                            padding: EdgeInsets.fromLTRB(
                                desktop ? 50 : 30,
                                desktop ? 100 : (intro ? 30 : 38),
                                desktop ? 50 : 30,
                                intro ? 40 : 70),
                            child: AutofillGroup(
                              child: Form(
                                key: formKey,
                                child: AnimatedSize(
                                  duration: const Duration(milliseconds: 260),
                                  curve: Curves.easeOutCubic,
                                  alignment: Alignment.topCenter,
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.stretch,
                                    children: _formChildren(desktop, intro),
                                  ),
                                ),
                              ),
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

  List<Widget> _formChildren(bool desktop, bool intro) {
    return [
      Row(children: [
        if (!intro)
          Padding(
            padding: const EdgeInsets.only(right: 6),
            child: IconButton(
              onPressed: loading ? null : _backToIntro,
              icon: const Icon(Icons.arrow_back_rounded, size: 20),
              visualDensity: VisualDensity.compact,
              padding: EdgeInsets.zero,
              constraints: const BoxConstraints(),
              tooltip: '처음으로',
            ),
          ),
        Expanded(
          child: Text('다시 만나 반가워요',
              style: Theme.of(context)
                  .textTheme
                  .headlineMedium
                  ?.copyWith(fontSize: desktop ? 29 : 24)),
        ),
      ]),
      const SizedBox(height: 5),
      const Text('마음이와 함께 오늘 하루를 돌아봐요.',
          style: TextStyle(color: AppColors.muted, fontSize: 12)),
      const SizedBox(height: 28),

      // ---- 1단계 이후: 이메일 ----
      if (step != _Step.intro) ...[
        const Text('이메일',
            style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
        const SizedBox(height: 9),
        TextFormField(
          controller: emailController,
          focusNode: emailFocus,
          keyboardType: TextInputType.emailAddress,
          textInputAction: TextInputAction.next,
          autofillHints: const [AutofillHints.email],
          onFieldSubmitted: (_) {
            if (_emailLooksReady) passwordFocus.requestFocus();
          },
          validator: (value) {
            final email = value?.trim() ?? '';
            if (!email.contains('@') || !email.contains('.')) {
              return '올바른 이메일을 입력해주세요';
            }
            return null;
          },
        ),
      ],

      // ---- 2단계: 비밀번호 ----
      if (step == _Step.password) ...[
        const SizedBox(height: 20),
        const Text('비밀번호',
            style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
        const SizedBox(height: 9),
        TextFormField(
          controller: passwordController,
          focusNode: passwordFocus,
          obscureText: true,
          textInputAction: TextInputAction.done,
          autofillHints: const [AutofillHints.password],
          onFieldSubmitted: (_) => login(),
          validator: (value) =>
              (value?.length ?? 0) < 8 ? '비밀번호는 8자 이상 입력해주세요' : null,
        ),
        // 비밀번호 칸과 함께 나타납니다. 이메일만 있는 단계에서는
        // 아직 필요 없는 선택지입니다.
        Align(
          alignment: Alignment.centerRight,
          child: TextButton(
            onPressed: loading
                ? null
                : () => Navigator.pushNamed(context, '/password-reset'),
            child:
                const Text('비밀번호를 잊으셨나요?', style: TextStyle(fontSize: 11)),
          ),
        ),
      ],

      if (errorMessage != null) ...[
        const SizedBox(height: 6),
        Text(errorMessage!,
            textAlign: TextAlign.center,
            style: const TextStyle(color: Color(0xFF69738F), fontSize: 11)),
        const SizedBox(height: 12),
      ],

      if (step != _Step.password) const SizedBox(height: 22),

      ElevatedButton(
        onPressed: loading ? null : (intro ? _startLogin : login),
        child: loading
            ? const SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(
                    strokeWidth: 2, color: Colors.white),
              )
            : const Text('로그인'),
      ),

      // 회원가입은 0단계에서만 보입니다.
      if (intro) ...[
        const SizedBox(height: 24),
        FilledButton.tonal(
          onPressed: loading
              ? null
              : () => Navigator.push(context,
                  MaterialPageRoute(builder: (_) => const JoinScreen())),
          style: FilledButton.styleFrom(
            minimumSize: const Size.fromHeight(48),
            backgroundColor: AppColors.soft,
            foregroundColor: AppColors.primary,
            shape:
                RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          ),
          child: const Text('처음 오셨나요? 회원가입'),
        ),
      ],
    ];
  }
}

class _MobileLoginHero extends StatelessWidget {
  const _MobileLoginHero({this.expanded = false});

  /// 0단계에서 참. 마스코트와 문구가 화면을 더 크게 씁니다.
  final bool expanded;

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 260),
      curve: Curves.easeOutCubic,
      height: expanded ? 330 : 228,
      width: double.infinity,
      child: Stack(
        clipBehavior: Clip.hardEdge,
        children: [
          const ColoredBox(color: Color(0xFFEDF2FF), child: SizedBox.expand()),
          const Positioned(left: 24, top: 25, child: LisnBrand(size: 22)),
          AnimatedPositioned(
            duration: const Duration(milliseconds: 260),
            curve: Curves.easeOutCubic,
            left: 25,
            top: expanded ? 104 : 92,
            child: Text(
                expanded ? '오늘의 마음도\n포근히\n안아줄게요' : '오늘의 마음도\n포근히 안아줄게요',
                style: const TextStyle(
                    fontSize: 25,
                    height: 1.2,
                    fontWeight: FontWeight.w800,
                    color: AppColors.navy)),
          ),
          AnimatedPositioned(
            duration: const Duration(milliseconds: 260),
            curve: Curves.easeOutCubic,
            width: expanded ? 300 : 226,
            height: expanded ? 300 : 226,
            right: expanded ? -34 : -26,
            top: expanded ? 62 : 35,
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
              alignment: Alignment.topLeft, child: LisnBrand(size: 26)),
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
