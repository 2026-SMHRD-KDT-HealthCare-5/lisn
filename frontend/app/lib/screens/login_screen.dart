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

class _MobileLoginHero extends StatelessWidget {
  const _MobileLoginHero({this.expanded = false});

  /// _LoginScreenState._revealDuration 과 같은 길이여야 합니다.
  /// 다르면 히어로와 입력란이 따로 움직여 두 동작으로 보입니다.
  static const _duration = Duration(milliseconds: 520);

  /// 0단계에서 참. 마스코트와 문구가 화면을 더 크게 씁니다.
  final bool expanded;

  /// 헤드라인 전체.
  ///
  /// ⚠ **좌표와 글자 크기를 하나의 진행값(t)으로 함께 계산합니다.**
  ///   좌표는 expanded 로 즉시 정하고 크기만 AnimatedDefaultTextStyle 에
  ///   맡기면, 둘이 다른 시간축으로 움직여 전환 중간에 글자가 겹칩니다.
  ///   실제로 그렇게 만들었다가 '포근히' 위에 '안아줄게요'가 포개졌습니다.
  ///
  /// 이동은 직선입니다. 대신 **겹치는 구간에서만 잠깐 비웁니다.**
  ///
  /// ㄱ자로 꺾어 가는 방법도 써봤지만 움직임이 기계적으로 보였습니다.
  /// 경로는 자연스럽게 두고, '포근히' 를 지나는 동안만 사라졌다가
  /// 도착 지점 근처에서 다시 나타납니다. 출발과 도착이 모두 보이므로
  /// 같은 글자가 옮겨간 것으로 읽힙니다.
  ///
  ///   3줄(0단계)          2줄(입력 단계)
  ///   오늘의 마음도        오늘의 마음도
  ///   포근히              포근히 안아줄게요
  ///   안아줄게요           ↑ 세 번째 줄이 둘째 줄 끝으로 올라온다
  Widget _headlines() {
    return TweenAnimationBuilder<double>(
      // begin 을 주지 않으면 현재 값에서 이어집니다. 전환 도중에 되돌려도
      // 처음부터 다시 시작하지 않습니다.
      tween: Tween<double>(end: expanded ? 0.0 : 1.0),
      duration: _duration,
      curve: Curves.linear, // 구간별 곡선은 아래에서 직접 적용합니다.
      builder: (context, t, _) {
        const ease = Curves.easeOutCubic;
        final e = ease.transform(t);

        final fontSize = 29 + (25 - 29) * e;
        final lineHeight = fontSize * 1.2;
        final top0 = 104 + (92 - 104) * e;
        final style = TextStyle(
            fontSize: fontSize,
            height: 1.2,
            fontWeight: FontWeight.w800,
            color: AppColors.navy);

        // 지금 크기로 실측합니다. 눈대중으로 숫자를 박으면 글꼴이나 크기가
        // 바뀔 때 글자가 겹치거나 벌어집니다.
        final painter = TextPainter(
          text: TextSpan(text: '포근히 ', style: style),
          textDirection: TextDirection.ltr,
        )..layout();

        // 겹침을 피하는 투명도.
        //   0.00~0.12  제자리에서 온전히 보인다
        //   0.12~0.34  '포근히' 로 들어가기 전에 사라진다
        //   0.34~0.70  가려도 될 구간 — 비어 있다
        //   0.70~0.92  '포근히' 오른쪽으로 빠져나온 뒤 다시 나타난다
        final gone = const Interval(0.12, 0.34, curve: Curves.easeIn).transform(t);
        final back = const Interval(0.70, 0.92, curve: Curves.easeOut).transform(t);
        final opacity = ((1 - gone) + back).clamp(0.0, 1.0);

        Widget at(String text, double left, double line) => Positioned(
              left: left,
              top: top0 + lineHeight * line,
              child: Text(text, style: style),
            );

        return Stack(clipBehavior: Clip.none, children: [
          at('오늘의 마음도', 25, 0),
          at('포근히', 25, 1),
          Positioned(
            left: 25 + painter.width * e,
            top: top0 + lineHeight * (2 - e),
            child: Opacity(
              opacity: opacity,
              child: Text('안아줄게요', style: style),
            ),
          ),
        ]);
      },
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
          // 한 덩어리로 두고 줄바꿈만 바꾸면 '안아줄게요'가 사라졌다 다시
          // 나타나 보입니다. 쪼개서 위치를 움직이면 같은 글자가 자리를
          // 옮기는 것으로 읽힙니다.
          Positioned.fill(child: _headlines()),
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
