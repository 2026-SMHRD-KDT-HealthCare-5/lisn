import 'package:flutter/material.dart';

import '../models/auth_models.dart' show ApiException;
import '../models/settings_models.dart';
import '../services/app_services.dart';
import '../services/settings_service.dart';
import '../services/sync_worker.dart';
import '../theme/app_theme.dart';
import '../widgets/common_widgets.dart';
import 'login_screen.dart';

/// MAIN_SETTING_02 — 계정 관리·회원 탈퇴
///
/// ```
/// ❶ 계정 정보: 이메일, 이름, 가입일 표시
/// ❷ 비밀번호 변경: 현재 비밀번호 확인 후 변경
/// ❸ 회원 탈퇴: 탈퇴 절차 시작. 비밀번호 재입력 확인
/// ❹ 삭제 범위 안내: 라이프로그·체성분·대화·분석·기기
/// ❺ 최종 확인 후 탈퇴 처리, MAIN_LOGIN_01 복귀
/// ```
///
/// ⚠ **탈퇴는 설정 화면이 아니라 여기 있습니다.** 전에는 설정 「기타」 절에
///   탈퇴 버튼만 있었는데, 화면설계서는 `MAIN_SETTING_01` ❸ 이 이 화면으로
///   **이동**하도록 규정합니다. 되돌리면 문서와 어긋납니다.
class AccountScreen extends StatefulWidget {
  const AccountScreen({super.key, this.settingsService});

  /// 테스트 주입용. 평소에는 null 이고 AppServices.settings 를 씁니다.
  final SettingsService? settingsService;

  @override
  State<AccountScreen> createState() => _AccountScreenState();
}

class _AccountScreenState extends State<AccountScreen> {
  SettingsService get _service => widget.settingsService ?? AppServices.settings;

  UserProfile? profile;
  bool loading = true;
  bool busy = false;
  String? error;

  // ⚠ 컨트롤러를 **State 가 소유**합니다.
  //
  //   전에는 `showDialog` 가 끝나자마자 dispose 했는데, 그 시점에 다이얼로그는
  //   **아직 닫히는 중**이라 TextField 가 죽은 컨트롤러를 읽습니다.
  //       A TextEditingController was used after being disposed.
  //   릴리스 빌드에서는 assert 가 빠져 조용히 넘어가므로 더 나쁩니다.
  final _currentPw = TextEditingController();
  final _newPw = TextEditingController();
  final _confirmPw = TextEditingController();
  final _deletePw = TextEditingController();

  @override
  void dispose() {
    _currentPw.dispose();
    _newPw.dispose();
    _confirmPw.dispose();
    _deletePw.dispose();
    super.dispose();
  }

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final p = await _service.profile();
      if (!mounted) return;
      setState(() {
        profile = p;
        loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        error = e is ApiException ? e.message : '계정 정보를 불러오지 못했습니다.';
        loading = false;
      });
    }
  }

  void _toast(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(message)));
  }

  // ─────────────────────────────────────────────────────────────
  //  ❷ 비밀번호 변경 — MLCM_101
  // ─────────────────────────────────────────────────────────────
  Future<void> _changePassword() async {
    final formKey = GlobalKey<FormState>();
    for (final c in [_currentPw, _newPw, _confirmPw]) {
      c.clear();
    }

    final ok = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('비밀번호 변경'),
        content: Form(
          key: formKey,
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            TextFormField(
              controller: _currentPw,
              obscureText: true,
              decoration: const InputDecoration(labelText: '현재 비밀번호'),
              validator: (v) =>
                  (v == null || v.isEmpty) ? '현재 비밀번호를 입력해주세요' : null,
            ),
            TextFormField(
              controller: _newPw,
              obscureText: true,
              decoration: const InputDecoration(labelText: '새 비밀번호 (8자 이상)'),
              // 서버도 8~64자를 검증합니다. 여기서 먼저 걸러 왕복을 줄입니다.
              validator: (v) =>
                  (v == null || v.length < 8) ? '8자 이상 입력해주세요' : null,
            ),
            TextFormField(
              controller: _confirmPw,
              obscureText: true,
              decoration: const InputDecoration(labelText: '새 비밀번호 확인'),
              validator: (v) => v != _newPw.text ? '새 비밀번호가 서로 다릅니다' : null,
            ),
          ]),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(false),
              child: const Text('취소')),
          TextButton(
              onPressed: () {
                if (formKey.currentState?.validate() ?? false) {
                  Navigator.of(dialogContext).pop(true);
                }
              },
              child: const Text('변경하기')),
        ],
      ),
    );

    if (ok != true || !mounted) return;
    final currentText = _currentPw.text;
    final nextText = _newPw.text;

    setState(() => busy = true);
    try {
      await _service.changePassword(
          currentPassword: currentText, newPassword: nextText);
      // ⚠ 성공해도 **로그아웃시키지 않습니다.** 서버가 기존 토큰을 무효화하지
      //   않으므로 세션은 그대로 유효하고, 여기서 쫓아내면 사용자만 놀랍니다.
      _toast('비밀번호를 바꿨어요.');
    } catch (e) {
      _toast(e is ApiException ? e.message : '비밀번호를 바꾸지 못했습니다.');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  // ─────────────────────────────────────────────────────────────
  //  ❸❹❺ 회원 탈퇴 — MLCM_103
  // ─────────────────────────────────────────────────────────────
  /// ⚠ CASCADE 로 라이프로그·대화기록이 **전부 지워지고 되돌릴 수 없습니다.**
  ///   삭제 범위를 먼저 알리는 것이 MLCM_103 3단계 요건입니다.
  Future<void> _deleteAccount() async {
    _deletePw.clear();
    final password = await showDialog<String>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('정말 탈퇴하시겠어요?'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          const Text(
            '탈퇴하면 아래 정보가 모두 삭제되고 되돌릴 수 없어요.\n\n'
            '· 라이프로그 측정 기록\n· 체성분 측정 기록\n· 대화 기록과 요약\n'
            '· 정서 분석 결과\n· 연동한 기기 정보',
            style: TextStyle(fontSize: 12, height: 1.7),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _deletePw,
            obscureText: true,
            decoration: const InputDecoration(
              labelText: '본인 확인을 위해 비밀번호를 입력해주세요',
              labelStyle: TextStyle(fontSize: 11),
            ),
          ),
        ]),
        actions: [
          TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text('취소')),
          TextButton(
              onPressed: () =>
                  Navigator.of(dialogContext).pop(_deletePw.text),
              child: const Text('탈퇴하기')),
        ],
      ),
    );
    if (password == null || password.isEmpty || !mounted) return;

    setState(() => busy = true);
    try {
      await _service.deleteAccount(password);
      await AppServices.tokenStore.clear();
      // 계정이 사라졌는데 워커가 남으면 없는 계정으로 전송을 계속 시도합니다.
      try {
        await cancelLifelogSync();
      } catch (_) {}
      if (!mounted) return;
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => const LoginScreen()),
        (_) => false,
      );
    } catch (e) {
      if (mounted) setState(() => busy = false);
      _toast(e is ApiException ? e.message : '탈퇴 처리에 실패했습니다.');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('계정 관리',
            style: TextStyle(fontSize: 17, fontWeight: FontWeight.w900)),
        centerTitle: true,
      ),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(15, 12, 15, 28),
            children: loading && profile == null
                ? [
                    const Padding(
                        padding: EdgeInsets.symmetric(vertical: 70),
                        child: Center(
                            child: CircularProgressIndicator(strokeWidth: 2.5)))
                  ]
                : error != null
                    ? [_errorCard()]
                    : _sections(),
          ),
        ),
      ),
    );
  }

  Widget _errorCard() => AppCard(
          child: Column(children: [
        Text(error!,
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 12, color: AppColors.muted)),
        const SizedBox(height: 12),
        TextButton(onPressed: _load, child: const Text('다시 시도')),
      ]));

  List<Widget> _sections() => [
        // ❶ 계정 정보
        AppCard(
            child: Column(children: [
          _InfoRow('이름', profile?.name ?? '–'),
          const Divider(height: 20, color: AppColors.line),
          _InfoRow('이메일', profile?.email ?? '–'),
          const Divider(height: 20, color: AppColors.line),
          _InfoRow('가입일', _joinedText),
        ])),
        const SizedBox(height: 16),

        // ❷❸ 동작
        AppCard(
            padding: EdgeInsets.zero,
            child: Column(children: [
              _ActionRow(
                  icon: Icons.lock_outline_rounded,
                  label: '비밀번호 변경',
                  onTap: busy ? null : _changePassword),
              _ActionRow(
                  icon: Icons.delete_outline_rounded,
                  label: '회원 탈퇴',
                  onTap: busy ? null : _deleteAccount),
            ])),
        const SizedBox(height: 14),

        // ❹ 삭제 범위 안내
        //
        // ⚠ **경고색을 쓰지 않습니다.** 탈퇴는 위기 화면은 아니지만 같은 계열의
        //   판단입니다 — 빨간 박스는 겁을 주고, 필요한 건 「무엇이 지워지는지」를
        //   정확히 아는 것입니다. 강조는 색이 아니라 구조로 합니다.
        const AppCard(
            child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
              Text('탈퇴하면 함께 삭제되는 것',
                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800)),
              SizedBox(height: 8),
              Text('라이프로그 · 체성분 · 대화 기록 · 정서 분석 결과 · 연동 기기',
                  style:
                      TextStyle(fontSize: 11, height: 1.7, color: AppColors.muted)),
              SizedBox(height: 6),
              Text('되돌릴 수 없어요.',
                  style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w800,
                      color: AppColors.muted)),
            ])),
      ];

  /// `USERS` 에 `created_at` 이 없어 약관 동의 시각을 씁니다 → `UserProfile.joinedAt`
  String get _joinedText {
    final d = profile?.joinedAt;
    if (d == null) return '–';
    return '${d.year}. ${d.month.toString().padLeft(2, '0')}. '
        '${d.day.toString().padLeft(2, '0')}';
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow(this.label, this.value);
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Row(children: [
        SizedBox(
            width: 68,
            child: Text(label,
                style: const TextStyle(fontSize: 12, color: AppColors.muted))),
        Expanded(
            child: Text(value,
                textAlign: TextAlign.right,
                style: const TextStyle(
                    fontSize: 13, fontWeight: FontWeight.w700))),
      ]);
}

class _ActionRow extends StatelessWidget {
  const _ActionRow({required this.icon, required this.label, this.onTap});
  final IconData icon;
  final String label;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 15),
          child: Row(children: [
            Icon(icon, size: 19, color: AppColors.muted),
            const SizedBox(width: 12),
            Expanded(
                child: Text(label,
                    style: const TextStyle(
                        fontSize: 13, fontWeight: FontWeight.w700))),
            const Icon(Icons.chevron_right_rounded,
                size: 20, color: AppColors.muted),
          ]),
        ),
      );
}
