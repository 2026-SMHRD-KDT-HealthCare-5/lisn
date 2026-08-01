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

  // 단계 전환 애니메이션. 짧으면 화면이 튀는 것처럼 보입니다.
  // 520ms 는 히어로 축소와 입력란 펼침이 한 동작으로 읽히는 길이입니다.
  static const _revealDuration = Duration(milliseconds: 520);

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
                  child: Container(
                    // 히어로와 입력 영역 사이의 흰색 경계를 없앱니다.
                    // 위에서 아래로 옅어지는 한 장의 배경이라 화면이 끊기지
                    // 않고, 입력 영역은 아래쪽이라 여전히 밝게 유지됩니다.
                    decoration: desktop
                        ? null
                        : const BoxDecoration(
                            gradient: LinearGradient(
                              begin: Alignment.topCenter,
                              end: Alignment.bottomCenter,
                              colors: [Color(0xFFEDF2FF), Color(0xFFFFFFFF)],
                              // 화면 중간을 조금 지난 지점부터 옅어집니다.
                              // 위쪽이 단색으로 충분히 유지돼야 마스코트가
                              // 배경에 얹힌 것처럼 보이지 않습니다.
                              stops: [0.58, 1.0],
                            ),
                          ),
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
                                    duration: _revealDuration,
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
      if (step != _Step.intro)
        _Reveal(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
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
          ),
        ),

      // ---- 2단계: 비밀번호 ----
      if (step == _Step.password)
        _Reveal(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
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
                  child: const Text('비밀번호를 잊으셨나요?',
                      style: TextStyle(fontSize: 11)),
                ),
              ),
            ],
          ),
        ),

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
      //
      // 테두리도 배경도 두지 않고 글자만 둡니다. 버튼 두 개가 나란히 있으면
      // 어느 쪽이 주된 행동인지 흐려집니다. 로그인이 주고, 회원가입은
      // 그 아래 놓인 안내에 가깝습니다.
      if (intro) ...[
        const SizedBox(height: 18),
        TextButton(
          onPressed: loading
              ? null
              : () => Navigator.push(context,
                  MaterialPageRoute(builder: (_) => const JoinScreen())),
          style: TextButton.styleFrom(
            minimumSize: const Size.fromHeight(44),
            foregroundColor: AppColors.muted,
            overlayColor: AppColors.primary,
          ),
          child: const Text.rich(
            TextSpan(children: [
              TextSpan(
                  text: '처음 오셨나요?  ',
                  style: TextStyle(fontSize: 13, color: AppColors.muted)),
              TextSpan(
                  text: '회원가입',
                  style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w800,
                      color: AppColors.primary)),
            ]),
          ),
        ),
      ],
    ];
  }
}

/// 새로 나타나는 입력란을 흐릿하게 띄우며 살짝 밀어 올립니다.
///
/// `AnimatedSize` 는 **자리(높이)만** 부드럽게 늘려줍니다. 그 안의 위젯은
/// 첫 프레임부터 완전히 보여서, 칸이 열리는 동안 글자가 툭 나타나 보입니다.
///
/// 위젯이 트리에 붙는 순간이 곧 등장 시점이라 상태를 따로 두지 않습니다.
class _Reveal extends StatelessWidget {
  const _Reveal({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return TweenAnimationBuilder<double>(
      tween: Tween<double>(begin: 0, end: 1),
      duration: _LoginScreenState._revealDuration,
      // 자리가 어느 정도 열린 뒤에 나타납니다. 처음부터 같이 시작하면
      // 아직 좁은 칸에서 글자가 잘려 보입니다.
      curve: const Interval(0.35, 1.0, curve: Curves.easeOut),
      builder: (context, t, child) => Opacity(
        opacity: t,
        child: Transform.translate(offset: Offset(0, 10 * (1 - t)), child: child),
      ),
      child: child,
    );
  }
}

class _MobileLoginHero extends StatelessWidget {
  const _MobileLoginHero({this.expanded = false});

  /// _LoginScreenState._revealDuration 과 같은 길이여야 합니다.
  /// 다르면 히어로와 입력란이 따로 움직여 두 동작으로 보입니다.
  static const _duration = Duration(milliseconds: 520);

  /// 0단계에서 참. 마스코트와 문구가 화면을 더 크게 씁니다.
  final bool expanded;

  /// 헤드라인.
  ///
  /// 3줄 ↔ 2줄은 서로 다른 문자열이라 글자를 이어붙일 수 없습니다.
  /// 겹쳐 놓고 **교차 페이드**로 넘깁니다.
  ///
  /// ⚠ 두 문구를 **동시에** 흐리게 하면 반투명끼리 포개져 글자가 뭉갭니다.
  ///   switchOutCurve·switchInCurve 로 구간을 갈라 **나가는 쪽이 완전히
  ///   사라진 뒤 들어오는 쪽이 나타나게** 합니다.
  ///
  ///   3줄(0단계)          2줄(입력 단계)
  ///   오늘의 마음도        오늘의 마음도
  ///   포근히              포근히 안아줄게요
  ///   안아줄게요
  Widget _headline() {
    final style = TextStyle(
        fontSize: expanded ? 29 : 25,
        height: 1.2,
        fontWeight: FontWeight.w800,
        color: AppColors.navy);

    return AnimatedPositioned(
      duration: _duration,
      curve: Curves.easeOutCubic,
      left: 25,
      top: expanded ? 104 : 92,
      child: AnimatedDefaultTextStyle(
        duration: _duration,
        curve: Curves.easeOutCubic,
        style: style,
        child: AnimatedSwitcher(
          duration: _duration,
          // 앞 절반은 나가는 쪽만, 뒤 절반은 들어오는 쪽만.
          switchOutCurve: const Interval(0.0, 0.5, curve: Curves.easeIn),
          switchInCurve: const Interval(0.5, 1.0, curve: Curves.easeOut),
          transitionBuilder: (child, animation) =>
              FadeTransition(opacity: animation, child: child),
          layoutBuilder: (current, previous) => Stack(
            alignment: Alignment.topLeft,
            children: [...previous, if (current != null) current],
          ),
          child: Text(
            expanded ? '오늘의 마음도\n포근히\n안아줄게요' : '오늘의 마음도\n포근히 안아줄게요',
            // 키가 바뀌어야 AnimatedSwitcher 가 교체를 감지합니다.
            key: ValueKey(expanded),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: _duration,
      curve: Curves.easeOutCubic,
      height: expanded ? 330 : 228,
      width: double.infinity,
      child: Stack(
        clipBehavior: Clip.hardEdge,
        children: [
          // 자체 배경을 칠하지 않습니다. 바깥 그라데이션이 화면 전체를
          // 덮으므로, 여기서 단색을 깔면 경계가 다시 생깁니다.
          const Positioned(left: 24, top: 25, child: LisnBrand(size: 22)),
          _headline(),
          AnimatedPositioned(
            duration: _duration,
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
