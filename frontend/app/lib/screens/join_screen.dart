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
  final passwordConfirmController = TextEditingController();
  final heightController = TextEditingController();
  final phoneController = TextEditingController();
  String? gender;

  /// 선택 입력 묶음이 펼쳐졌는지. 접혀 있어도 첫 칸이 살짝 보입니다.
  bool optionalOpen = false;

  bool loading = false;
  bool? emailAvailable;
  String? errorMessage;

  @override
  void initState() {
    super.initState();
    emailController.addListener(_resetEmailCheck);
  }

  /// 이메일을 고치면 이전 확인 결과를 지웁니다.
  ///
  /// ⚠ 그대로 두면 A 로 확인해 '사용 가능' 을 받은 뒤 B 로 고쳐도 그 문구가
  ///   남습니다. 확인하지 않은 주소를 확인된 것으로 오인하게 됩니다.
  void _resetEmailCheck() {
    if (emailAvailable != null) {
      setState(() => emailAvailable = null);
    }
  }

  @override
  void dispose() {
    emailController.removeListener(_resetEmailCheck);
    nameController.dispose();
    birthDateController.dispose();
    emailController.dispose();
    passwordController.dispose();
    passwordConfirmController.dispose();
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
          // ⚠ 버튼 라벨이 결과 표시를 겸하고 있었습니다. 확인을 마치면
          //   '사용 가능한 이메일이에요' 로 바뀌어, 여전히 누를 수 있는
          //   요소인지 알 수 없었습니다. 버튼과 결과를 분리합니다.
          Row(children: [
            Expanded(
              child: OutlinedButton(
                onPressed: loading ? null : checkEmail,
                style: OutlinedButton.styleFrom(
                  minimumSize: const Size.fromHeight(44),
                  side: const BorderSide(color: AppColors.line),
                  foregroundColor: AppColors.primary,
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12)),
                ),
                child: const Text('이메일 중복 확인',
                    style: TextStyle(
                        fontSize: 12, fontWeight: FontWeight.w700)),
              ),
            ),
          ]),
          if (emailAvailable != null) ...[
            const SizedBox(height: 8),
            Row(children: [
              Icon(
                  emailAvailable!
                      ? Icons.check_circle_outline_rounded
                      : Icons.info_outline_rounded,
                  size: 14,
                  color: emailAvailable! ? AppColors.teal : AppColors.muted),
              const SizedBox(width: 5),
              Text(
                emailAvailable! ? '사용할 수 있는 이메일이에요' : '이미 사용 중인 이메일이에요',
                style: TextStyle(
                    fontSize: 11,
                    color: emailAvailable! ? AppColors.teal : AppColors.muted),
              ),
            ]),
          ],
          const SizedBox(height: 18),
          _Field(
            label: '비밀번호',
            controller: passwordController,
            obscure: true,
            textInputAction: TextInputAction.next,
            validator: (value) =>
                (value?.length ?? 0) < 8 ? '비밀번호는 8자 이상 입력해주세요' : null,
          ),
          // 화면설계서 ❷ 가 '비밀번호/비밀번호 확인' 을 규정합니다.
          // 서버는 확인값을 받지 않으므로 여기서만 대조합니다.
          _Field(
            label: '비밀번호 확인',
            controller: passwordConfirmController,
            obscure: true,
            textInputAction: TextInputAction.next,
            validator: (value) => value != passwordController.text
                ? '비밀번호가 일치하지 않습니다'
                : null,
          ),
          // ❹~❻ 사용자 인적사항 — 문서에 선택 표기가 없으므로 필수입니다.
          // ⚠ schema.sql 은 birth_date·gender 를 NULL 허용으로 두지만,
          //   그건 저장 가능 여부고 화면 요건과는 별개입니다.
          _Field(
            label: '생년월일',
            controller: birthDateController,
            hint: '1994-05-16',
            keyboardType: TextInputType.datetime,
            textInputAction: TextInputAction.next,
            validator: (value) {
              final text = value?.trim() ?? '';
              if (text.isEmpty) return '생년월일을 입력해주세요';
              return DateTime.tryParse(text) == null
                  ? 'YYYY-MM-DD 형식으로 입력해주세요'
                  : null;
            },
          ),
          const Text('성별',
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
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
            validator: (value) => value == null ? '성별을 선택해주세요' : null,
          ),
          const SizedBox(height: 22),
          _optionalSection(),
          const SizedBox(height: 22),
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

  /// 선택 입력 묶음 — MAIN_JOIN_02
  ///
  /// 접어서 완전히 감추지 않습니다. **윗부분이 살짝 보이게 잘라두고**
  /// 아래를 흐리게 덮어, 더 있다는 걸 알아채고 스스로 펼치게 합니다.
  /// 완전히 접혀 있으면 대부분 그냥 지나칩니다.
  ///
  /// 필수와 섞어두면 어디까지 채워야 하는지 알 수 없어 중간에 막힙니다.
  /// 화면설계서도 비상 연락처를 「선택사항」으로 적고 있는데 화면만
  /// 구분이 없던 상태였습니다.
  Widget _optionalSection() {
    final fields = Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _Field(
          label: '비상 연락처',
          controller: phoneController,
          hint: '010-0000-0000',
          keyboardType: TextInputType.phone,
          textInputAction: TextInputAction.done,
          // ⚠ 문구를 담담하게 씁니다. 가입 첫날에 위기 상황을 설명하면
          //   불안을 심어 오히려 입력을 피하게 됩니다.
          //   '자동으로 연락이 가지 않는다'는 반드시 넣습니다. 그 말이 없으면
          //   내 상태가 남에게 알려진다고 여겨 아예 적지 않습니다.
          //   실제로도 그런 기능이 없습니다 — FR-MN-002 는 본인이 109 에
          //   거는 구조입니다.
          onWhy: () => _why(
            '비상 연락처는 왜 필요한가요?',
            const [
              '혼자 감당하기 어려운 상황이 생겼을 때 도움을 요청할 수 있는 연락처예요.',
              '평소에는 쓰지 않고, 자동으로 연락이 가지도 않아요.',
              '입력하지 않아도 모든 기능을 쓸 수 있어요.',
              '저장할 때 암호화되고, 설정에서 언제든 지울 수 있어요.',
            ],
          ),
        ),
        _Field(
          label: '키(cm)',
          controller: heightController,
          hint: '예: 165.5',
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          textInputAction: TextInputAction.next,
          onWhy: () => _why(
            '키는 왜 필요한가요?',
            const [
              '체성분 수치를 해석할 때 씁니다. 같은 근육량이라도 키에 따라 의미가 달라져요.',
              '입력하지 않아도 모든 기능을 쓸 수 있어요.',
              '나중에 설정에서 추가하거나 지울 수 있어요.',
            ],
          ),
          validator: (value) {
            if (value == null || value.trim().isEmpty) return null;
            final height = double.tryParse(value.trim());
            return height == null || height <= 0 || height > 300
                ? '키는 0보다 크고 300 이하로 입력해주세요'
                : null;
          },
        ),
      ],
    );

    return Container(
      decoration: BoxDecoration(
        color: AppColors.soft,
        borderRadius: BorderRadius.circular(14),
      ),
      padding: const EdgeInsets.fromLTRB(15, 14, 15, 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('선택 입력',
                    style:
                        TextStyle(fontSize: 12, fontWeight: FontWeight.w800)),
                SizedBox(height: 3),
                Text('건너뛰어도 가입할 수 있어요',
                    style: TextStyle(fontSize: 10, color: AppColors.muted)),
              ]),
          const SizedBox(height: 12),
          AnimatedSize(
            duration: const Duration(milliseconds: 420),
            curve: Curves.easeOutCubic,
            alignment: Alignment.topCenter,
            child: optionalOpen
                // 펼친 뒤에는 같은 자리에 ^ 를 둡니다. 열고 닫는 손잡이가
                // 한 곳에 있어야 어디를 눌러야 할지 헤매지 않습니다.
                ? Column(children: [
                    fields,
                    GestureDetector(
                      onTap: () => setState(() => optionalOpen = false),
                      behavior: HitTestBehavior.opaque,
                      child: const SizedBox(
                        height: 34,
                        width: double.infinity,
                        child: Icon(Icons.keyboard_arrow_up_rounded,
                            size: 26, color: AppColors.primary),
                      ),
                    ),
                  ])
                // 접힌 상태 — 첫 칸의 라벨과 입력창 윗부분만 보입니다.
                //
                // ⚠ ConstrainedBox 로 자르면 자식이 더 크다고 오버플로 경고가
                //   납니다. SizedBox 로 **자리만** 잡고 OverflowBox 로 자식이
                //   제 크기를 갖게 둔 뒤 ClipRect 로 잘라야 경고가 없습니다.
                : SizedBox(
                    height: 74,
                    child: ClipRect(
                      child: Stack(children: [
                        OverflowBox(
                          alignment: Alignment.topCenter,
                          minHeight: 0,
                          maxHeight: double.infinity,
                          child: fields,
                        ),
                        // 잘린 자리를 흐리게 덮고 그 위에 v 를 얹습니다.
                        // 흐려지는 것만으로는 눌러야 한다는 게 전해지지 않습니다.
                        Positioned(
                          left: 0,
                          right: 0,
                          bottom: 0,
                          height: 44,
                          child: GestureDetector(
                            onTap: () => setState(() => optionalOpen = true),
                            child: DecoratedBox(
                              decoration: BoxDecoration(
                                gradient: LinearGradient(
                                  begin: Alignment.topCenter,
                                  end: Alignment.bottomCenter,
                                  colors: [
                                    AppColors.soft.withValues(alpha: 0),
                                    AppColors.soft,
                                  ],
                                ),
                              ),
                              child: const Align(
                                alignment: Alignment.bottomCenter,
                                child: Icon(Icons.keyboard_arrow_down_rounded,
                                    size: 26, color: AppColors.primary),
                              ),
                            ),
                          ),
                        ),
                      ]),
                    ),
                  ),
          ),
        ],
      ),
    );
  }

  /// 선택 항목이 왜 필요한지 알려주는 바텀시트.
  ///
  /// 툴팁으로는 담기지 않습니다. 비상 연락처 설명은 네 줄이고,
  /// 그중 한 줄이라도 빠지면 오해를 부릅니다.
  void _why(String title, List<String> lines) {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (sheetContext) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(24, 4, 24, 26),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title,
                  style: const TextStyle(
                      fontSize: 16, fontWeight: FontWeight.w800)),
              const SizedBox(height: 16),
              for (final line in lines)
                Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('· ',
                            style: TextStyle(color: AppColors.muted)),
                        Expanded(
                          child: Text(line,
                              style: const TextStyle(
                                  fontSize: 12,
                                  height: 1.7,
                                  color: AppColors.muted)),
                        ),
                      ]),
                ),
            ],
          ),
        ),
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
    this.onWhy,
  });

  final String label;
  final TextEditingController controller;
  final String? hint;
  final bool obscure;
  final TextInputType? keyboardType;
  final TextInputAction? textInputAction;
  final String? Function(String?)? validator;

  /// 주면 라벨 옆에 `?` 가 붙습니다. 왜 필요한지 설명할 항목에만 씁니다.
  final VoidCallback? onWhy;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Text(label,
                style: const TextStyle(
                    fontSize: 12, fontWeight: FontWeight.w700)),
            if (onWhy != null) ...[
              // 오른쪽 끝에 붙입니다. 라벨 옆에 바짝 두면 글자와 뭉쳐
              // 라벨의 일부처럼 보입니다. 입력란 폭에 맞춰 떨어뜨리면
              // 누를 수 있는 것으로 읽힙니다.
              const Spacer(),
              IconButton(
                onPressed: onWhy,
                icon: const Icon(Icons.help_outline_rounded, size: 16),
                color: AppColors.muted,
                visualDensity: VisualDensity.compact,
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(),
                tooltip: '왜 필요한가요?',
              ),
            ],
          ]),
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
