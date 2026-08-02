import 'package:flutter/material.dart';

import '../models/auth_models.dart' show ApiException;
import '../models/settings_models.dart';
import '../services/app_services.dart';
import '../services/settings_service.dart';
import '../theme/app_theme.dart';
import '../widgets/common_widgets.dart';
import 'login_screen.dart';

/// MAIN_SETTING_01
class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key, this.settingsService});

  /// 테스트 주입용. 평소에는 null 이고 AppServices.settings 를 씁니다.
  final SettingsService? settingsService;

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  SettingsService get _service => widget.settingsService ?? AppServices.settings;

  UserProfile? profile;
  List<DeviceConnection> connections = const [];
  bool loading = true;
  bool loggingOut = false;
  bool busy = false;
  String? error;

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
      // 둘은 서로 독립이라 함께 기다립니다.
      final results = await Future.wait([
        _service.profile(),
        _service.connections(),
      ]);
      if (!mounted) return;
      setState(() {
        profile = results[0] as UserProfile;
        connections = results[1] as List<DeviceConnection>;
        loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        error = e is ApiException ? e.message : '설정을 불러오지 못했습니다.';
        loading = false;
      });
    }
  }

  void _toast(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _toggleConnection(DeviceConnection c, bool value) async {
    if (busy) return;
    setState(() => busy = true);
    try {
      final updated = await _service.updateConnection(c.connectionId,
          permissionGranted: value);
      if (!mounted) return;
      setState(() {
        connections = [
          for (final item in connections)
            item.connectionId == updated.connectionId ? updated : item
        ];
      });
    } catch (e) {
      _toast(e is ApiException ? e.message : '변경하지 못했습니다.');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> logout() async {
    if (loggingOut) return;
    setState(() => loggingOut = true);
    try {
      await AppServices.auth.logout();
    } catch (_) {
      // 서버가 응답하지 않아도 로컬 토큰은 AuthService에서 반드시 폐기한다.
    }
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const LoginScreen()),
      (_) => false,
    );
  }

  /// 회원 탈퇴 — MLCM_103.
  ///
  /// ⚠ CASCADE 로 라이프로그·대화기록이 **전부 지워지고 되돌릴 수 없습니다.**
  ///   삭제 범위를 먼저 알리는 것이 MLCM_103 3단계 요건입니다.
  Future<void> _deleteAccount() async {
    // MLCM_103 2단계 — 비밀번호 재확인(본인 확인). 서버도 본문 없이 오면 거절한다.
    final passwordController = TextEditingController();
    final password = await showDialog<String>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('정말 탈퇴하시겠어요?'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          const Text(
            '탈퇴하면 아래 정보가 모두 삭제되고 되돌릴 수 없어요.\n\n'
            '· 라이프로그 측정 기록\n· 대화 기록과 요약\n· 정서 분석 결과\n· 계정 정보',
            style: TextStyle(fontSize: 12, height: 1.7),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: passwordController,
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
                  Navigator.of(dialogContext).pop(passwordController.text),
              child: const Text('탈퇴하기')),
        ],
      ),
    );
    passwordController.dispose();
    if (password == null || password.isEmpty || !mounted) return;

    try {
      await _service.deleteAccount(password);
      await AppServices.tokenStore.clear();
      if (!mounted) return;
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => const LoginScreen()),
        (_) => false,
      );
    } catch (e) {
      _toast(e is ApiException ? e.message : '탈퇴 처리에 실패했습니다.');
    }
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Column(children: [
        const SizedBox(
            height: 68,
            child: Center(
                child: Text('설정',
                    style:
                        TextStyle(fontSize: 18, fontWeight: FontWeight.w900)))),
        Expanded(
          child: RefreshIndicator(
            onRefresh: _load,
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(15, 8, 15, 25),
              // 당겨서 새로고침할 때 본문을 스피너로 갈아치우지 않습니다.
              // RefreshIndicator 가 이미 위에서 진행을 알리고 있고, 보고 있던
              // 프로필·기기 목록이 사라졌다 돌아오면 화면이 크게 튑니다.
              children: (loading && profile == null)
                  ? [
                      const Padding(
                          padding: EdgeInsets.symmetric(vertical: 70),
                          child: Center(
                              child:
                                  CircularProgressIndicator(strokeWidth: 2.5)))
                    ]
                  : error != null
                      ? [
                          AppCard(
                              child: Column(children: [
                            Text(error!,
                                textAlign: TextAlign.center,
                                style: const TextStyle(
                                    fontSize: 12, color: AppColors.muted)),
                            const SizedBox(height: 12),
                            TextButton(
                                onPressed: _load, child: const Text('다시 시도')),
                          ]))
                        ]
                      : loading
                          // 갱신 중임은 흐리게 알립니다. 이 사이 토글을 누르면
                          // 곧 덮어써질 값을 바꾸게 되므로 조작도 막습니다.
                          ? [StaleContent(child: Column(children: _sections()))]
                          : _sections(),
            ),
          ),
        ),
      ]),
    );
  }

  List<Widget> _sections() => [
        _profileCard(),
        // 「대화 성격」 절은 없습니다 — 챗봇 탭이 확인·변경 화면입니다(SD-A⑥).
        const _SettingsTitle('데이터 연동'),
        ..._connectionCards(),
        const _SettingsTitle('알림 설정'),
        _notificationsCard(),
        const _SettingsTitle('기타'),
        AppCard(
            padding: EdgeInsets.zero,
            child: Column(children: [
              _SettingsRow(
                  icon: Icons.delete_outline_rounded,
                  label: '회원 탈퇴',
                  onTap: busy ? null : _deleteAccount),
              _SettingsRow(
                  icon: Icons.logout_rounded,
                  label: loggingOut ? '로그아웃 중...' : '로그아웃',
                  onTap: loggingOut ? null : logout),
            ])),
      ];

  Widget _profileCard() {
    final p = profile;
    return AppCard(
        child: Row(children: [
      const MaeumeMascot(size: 50),
      const SizedBox(width: 13),
      Expanded(
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('${p?.name ?? ''}님',
            style: const TextStyle(fontWeight: FontWeight.w800)),
        Text(p?.email ?? '',
            style: const TextStyle(fontSize: 10, color: AppColors.muted)),
      ])),
      if (p?.role == 'ADMIN')
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
          decoration: BoxDecoration(
              color: AppColors.soft, borderRadius: BorderRadius.circular(9)),
          child: const Text('관리자',
              style: TextStyle(fontSize: 9, color: AppColors.primary)),
        ),
    ]));
  }

  // ❸ 페르소나 항목은 **설정에서 뺐습니다.**
  //
  // 이 앱은 성격 선택과 대화 시작이 한 동작입니다(카드 버튼이 「이 성격으로
  // 대화하기」). 그래서 설정에서 「바꾸기」를 누르면 결국 대화가 시작돼,
  // 설정 변경치고는 이상한 흐름이 됩니다.
  //
  // 대신 **챗봇 탭이 확인 화면 역할을 합니다** — 열면 최근에 고른 성격 카드가
  // 먼저 뜨고 「최근 대화」 표시가 붙습니다. 확인도 변경도 거기서 됩니다.
  // 설정에 같은 것을 또 두면 어느 쪽이 실제로 적용되는지 알 수 없습니다.
  //
  // 화면설계서 `MAIN_SETTING_01` ❸ 삭제 → 체크리스트 `SD-A⑥`

  List<Widget> _connectionCards() {
    if (connections.isEmpty) {
      return [
        const AppCard(
            child: Column(children: [
          Text('연동된 기기가 없어요',
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800)),
          SizedBox(height: 7),
          Text('Health Connect 를 연동하면 걸음·수면·심박수가\n자동으로 기록됩니다.',
              textAlign: TextAlign.center,
              style:
                  TextStyle(fontSize: 10, height: 1.6, color: AppColors.muted)),
        ]))
      ];
    }

    return [
      for (final c in connections)
        AppCard(
            child: Column(children: [
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            secondary: const CircleAvatar(
                backgroundColor: Color(0xFFEEF1FF),
                child:
                    Icon(Icons.smartphone_rounded, color: AppColors.primary)),
            title: Text(c.deviceName ?? _platformLabel(c.platformType),
                style:
                    const TextStyle(fontSize: 12, fontWeight: FontWeight.w800)),
            subtitle: Text(_scopeText(c),
                style: const TextStyle(fontSize: 9, color: AppColors.muted)),
            value: c.permissionGranted,
            onChanged: busy ? null : (v) => _toggleConnection(c, v),
          ),
          // ⚠ 연동을 꺼도 이미 수집된 기록은 지워지지 않습니다(MLCM_110 종료조건).
          //   이 말을 빼면 "끄면 다 사라진다"고 오해합니다.
          const Align(
            alignment: Alignment.centerLeft,
            child: Text('연동을 꺼도 지금까지 쌓인 기록은 그대로 남아요.',
                style: TextStyle(fontSize: 9, color: AppColors.muted)),
          ),
        ])),
    ];
  }

  String _platformLabel(String type) =>
      type == 'APPLE_HEALTH' ? 'Apple 건강' : 'Health Connect';

  String _scopeText(DeviceConnection c) {
    final on = [
      if (c.consentScopes.activity) '활동',
      if (c.consentScopes.sleep) '수면',
      if (c.consentScopes.bodyComposition) '체성분',
    ];
    final synced = c.lastSyncedAt == null
        ? '아직 수신 없음'
        : '마지막 수신 ${c.lastSyncedAt!.month}.${c.lastSyncedAt!.day}';
    return '${on.isEmpty ? '수집 항목 없음' : on.join(' · ')}  ·  $synced';
  }

  /// ⚠ 알림은 **아직 서버에 저장되지 않습니다.** 켜지는 것처럼 보이게 두면
  ///   시연에서 껐다 켜도 아무 일이 없어 그대로 드러납니다.
  ///   FCM 토큰 필드는 있지만 알림 설정 저장 API 가 없습니다.
  Widget _notificationsCard() {
    return AppCard(
        child: Column(children: [
      for (final label in const ['감정 알림', '추천 콘텐츠 알림', '리포트 알림'])
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: Text(label,
              style: const TextStyle(fontSize: 12, color: AppColors.muted)),
          value: false,
          onChanged: null,
        ),
      const Align(
        alignment: Alignment.centerLeft,
        child: Text('알림 기능은 준비 중이에요.',
            style: TextStyle(fontSize: 9, color: AppColors.muted)),
      ),
    ]));
  }
}

class _SettingsTitle extends StatelessWidget {
  const _SettingsTitle(this.label);
  final String label;

  @override
  Widget build(BuildContext context) => Padding(
      padding: const EdgeInsets.fromLTRB(4, 20, 4, 9),
      child: Text(label,
          style: const TextStyle(
              fontSize: 10,
              color: AppColors.muted,
              fontWeight: FontWeight.w800)));
}

class _SettingsRow extends StatelessWidget {
  const _SettingsRow({required this.icon, required this.label, this.onTap});
  final IconData icon;
  final String label;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => ListTile(
      leading: Icon(icon, color: AppColors.primary, size: 20),
      title: Text(label,
          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
      trailing: const Icon(Icons.chevron_right_rounded, size: 19),
      onTap: onTap);
}
