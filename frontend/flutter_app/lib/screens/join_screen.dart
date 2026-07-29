import 'package:flutter/material.dart';

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
    return Column(
      key: const ValueKey(1),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _heading('STEP 02', '기본 정보를 알려주세요', '꼭 필요한 정보만 간단히 여쭤볼게요.'),
        const SizedBox(height: 25),
        const _Field(label: '이름', value: '지은'),
        const _Field(label: '생년월일', value: '1994.05.16'),
        const _Field(label: '아이디', value: 'jieun'),
        const _Field(label: '비밀번호', value: 'maeume123', obscure: true),
        const _Field(label: '비상 연락처 · 선택', hint: '010-0000-0000'),
        CheckboxListTile(
          contentPadding: EdgeInsets.zero,
          controlAffinity: ListTileControlAffinity.leading,
          value: true,
          onChanged: (_) {},
          title: const Text('1인 가구에 해당해요', style: TextStyle(fontSize: 13)),
        ),
        const SizedBox(height: 15),
        ElevatedButton(
            onPressed: () => setState(() => step = 2),
            child: const Text('회원가입 완료')),
      ],
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
        const Text('지은님, 반가워요!',
            textAlign: TextAlign.center,
            style: TextStyle(
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
                Text('Health Connect · Apple Health',
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
  const _Field(
      {required this.label, this.value, this.hint, this.obscure = false});
  final String label;
  final String? value;
  final String? hint;
  final bool obscure;

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
              initialValue: value,
              obscureText: obscure,
              decoration: InputDecoration(hintText: hint)),
        ],
      ),
    );
  }
}
