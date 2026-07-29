import 'package:flutter/material.dart';

import '../theme/app_theme.dart';
import '../widgets/common_widgets.dart';
import 'login_screen.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  bool healthConnect = true;
  final notifications = [true, true, false];

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Column(children: [
        SizedBox(
            height: 68,
            child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  IconButton(
                      onPressed: () {}, icon: const Icon(Icons.menu_rounded)),
                  const Text('설정',
                      style:
                          TextStyle(fontSize: 18, fontWeight: FontWeight.w900)),
                  IconButton(
                      onPressed: () {},
                      icon: const Icon(Icons.notifications_none_rounded))
                ])),
        Expanded(
            child: ListView(
                padding: const EdgeInsets.fromLTRB(15, 8, 15, 25),
                children: [
              const AppCard(
                  child: Row(children: [
                MaeumeMascot(size: 50),
                SizedBox(width: 13),
                Expanded(
                    child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                      Text('지은님',
                          style: TextStyle(fontWeight: FontWeight.w800)),
                      Text('jieun@email.com',
                          style:
                              TextStyle(fontSize: 10, color: AppColors.muted))
                    ])),
                Icon(Icons.chevron_right_rounded)
              ])),
              const _SettingsTitle('연결된 기기'),
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
                      Text('스마트워치',
                          style: TextStyle(
                              fontSize: 12, fontWeight: FontWeight.w800)),
                      Text('Galaxy Watch 6 · 방금 동기화',
                          style: TextStyle(fontSize: 9, color: AppColors.muted))
                    ])),
                Text('연결됨',
                    style: TextStyle(
                        fontSize: 10,
                        color: Color(0xFF43B58E),
                        fontWeight: FontWeight.w800))
              ])),
              const _SettingsTitle('데이터 연동'),
              AppCard(
                  child: SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      secondary: const CircleAvatar(
                          backgroundColor: Color(0xFFEEF1FF),
                          child: Icon(Icons.smartphone_rounded,
                              color: AppColors.primary)),
                      title: const Text('Health Connect',
                          style: TextStyle(
                              fontSize: 12, fontWeight: FontWeight.w800)),
                      subtitle: const Text('수면 · 걸음 · 심박수 · 스트레스',
                          style: TextStyle(fontSize: 9)),
                      value: healthConnect,
                      onChanged: (value) =>
                          setState(() => healthConnect = value))),
              const _SettingsTitle('알림 설정'),
              AppCard(
                  padding: EdgeInsets.zero,
                  child: Column(
                      children: List.generate(
                          3,
                          (i) => SwitchListTile(
                              secondary: Icon(
                                  [
                                    Icons.favorite_border_rounded,
                                    Icons.auto_awesome_rounded,
                                    Icons.monitor_heart_outlined
                                  ][i],
                                  color: AppColors.primary),
                              title: Text(['감정 알림', '추천 콘텐츠 알림', '리포트 알림'][i],
                                  style: const TextStyle(
                                      fontSize: 12,
                                      fontWeight: FontWeight.w700)),
                              value: notifications[i],
                              onChanged: (value) =>
                                  setState(() => notifications[i] = value))))),
              const _SettingsTitle('기타'),
              AppCard(
                  padding: EdgeInsets.zero,
                  child: Column(children: [
                    const _SettingsRow(
                        icon: Icons.dark_mode_outlined, label: '테마 설정'),
                    const _SettingsRow(
                        icon: Icons.account_circle_outlined, label: '계정 관리'),
                    const _SettingsRow(
                        icon: Icons.help_outline_rounded, label: '도움말 및 문의'),
                    _SettingsRow(
                        icon: Icons.logout_rounded,
                        label: '로그아웃',
                        onTap: () => Navigator.of(context).pushAndRemoveUntil(
                            MaterialPageRoute(
                                builder: (_) => const LoginScreen()),
                            (_) => false)),
                  ])),
            ])),
      ]),
    );
  }
}

class _SettingsTitle extends StatelessWidget {
  const _SettingsTitle(this.label);
  final String label;

  @override
  Widget build(BuildContext context) => Padding(
      padding: const EdgeInsets.fromLTRB(4, 22, 4, 9),
      child: Text(label,
          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800)));
}

class _SettingsRow extends StatelessWidget {
  const _SettingsRow({required this.icon, required this.label, this.onTap});
  final IconData icon;
  final String label;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => ListTile(
      onTap: onTap,
      leading: Icon(icon, color: AppColors.primary),
      title: Text(label,
          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
      trailing: const Icon(Icons.chevron_right_rounded, size: 19));
}
