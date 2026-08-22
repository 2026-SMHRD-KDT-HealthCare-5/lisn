import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../theme/app_theme.dart';
import '../widgets/common_widgets.dart';

typedef EmergencyCallLauncher = Future<bool> Function();

class EmergencyScreen extends StatefulWidget {
  const EmergencyScreen({super.key, this.callLauncher});

  final EmergencyCallLauncher? callLauncher;

  @override
  State<EmergencyScreen> createState() => _EmergencyScreenState();
}

class _EmergencyScreenState extends State<EmergencyScreen> {
  bool launchingCall = false;

  Future<bool> _launch109() {
    final customLauncher = widget.callLauncher;
    if (customLauncher != null) return customLauncher();
    return launchUrl(
      Uri(scheme: 'tel', path: '109'),
      mode: LaunchMode.externalApplication,
    );
  }

  Future<void> call109() async {
    if (launchingCall) return;
    setState(() => launchingCall = true);

    var launched = false;
    try {
      launched = await _launch109();
    } catch (_) {
      launched = false;
    }

    if (!mounted) return;
    setState(() => launchingCall = false);
    if (!launched) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('전화 앱을 열 수 없어요. 직접 109로 전화해 주세요.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFEDF2FF),
      body: SafeArea(
        child: Column(
          children: [
            // 브랜드를 두지 않습니다. 위기 상황에서 서비스명은 잡음이고,
            // 상담 연결 화면 맨 위에 로고가 있으면 우리가 상담 제공자인 것처럼
            // 읽힙니다. 실제 연결 대상은 외부 전문 기관입니다.
            const SizedBox(height: 12),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(20, 16, 20, 20),
                child: Column(
                  // 카드 세 장의 너비를 맞춥니다.
                  //
                  // ⚠ **기본값(center)이면 카드마다 너비가 달라집니다.**
                  //   느슨한 제약이 내려가 각자 내용 너비로 줄어들기 때문에,
                  //   버튼이 있는 카드는 넓고 글자만 있는 카드는 좁아집니다.
                  //   실제로 「지금 많이 힘드신 것 같아요」만 눈에 띄게
                  //   좁았습니다(2026.08.22 시연영상에서 발견).
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    _NoticeCard(),
                    const SizedBox(height: 14),
                    _CallCard(
                      launching: launchingCall,
                      onCall: call109,
                    ),
                    const SizedBox(height: 14),
                    const _PrivacyCard(),
                  ],
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 4, 20, 22),
              child: TextButton(
                onPressed: () => Navigator.of(context).maybePop(),
                child: const Text(
                  '나중에 볼게요',
                  style: TextStyle(
                    color: AppColors.muted,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _NoticeCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return const AppCard(
      padding: EdgeInsets.fromLTRB(24, 30, 24, 28),
      child: Column(
        children: [
          CircleAvatar(
            radius: 31,
            backgroundColor: Color(0xFFE7EDFF),
            child: Icon(
              Icons.favorite_rounded,
              size: 30,
              color: Color(0xFF8A9CF0),
            ),
          ),
          SizedBox(height: 16),
          Text(
            '지금 많이 힘드신 것 같아요',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: AppColors.navy,
              fontSize: 19,
              height: 1.45,
              fontWeight: FontWeight.w900,
            ),
          ),
          SizedBox(height: 10),
          Text(
            '최근 정서 상태에서 도움이 필요한 신호가 보였어요.\n'
            '혼자 견디지 않으셔도 괜찮아요.',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: AppColors.muted,
              fontSize: 13,
              height: 1.7,
            ),
          ),
        ],
      ),
    );
  }
}

class _CallCard extends StatelessWidget {
  const _CallCard({required this.launching, required this.onCall});

  final bool launching;
  final VoidCallback onCall;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        children: [
          const Row(
            children: [
              CircleAvatar(
                radius: 23,
                backgroundColor: Color(0xFFEAF1FF),
                child: Icon(
                  Icons.phone_in_talk_rounded,
                  color: Color(0xFF5A6BE0),
                ),
              ),
              SizedBox(width: 13),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '109',
                    style: TextStyle(
                      color: AppColors.navy,
                      fontSize: 21,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  Text(
                    '자살예방 상담전화 · 24시간 무료',
                    style: TextStyle(fontSize: 11, color: AppColors.muted),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 16),
          ElevatedButton.icon(
            key: const ValueKey('emergency-call-button'),
            onPressed: launching ? null : onCall,
            icon: launching
                ? const SizedBox.square(
                    dimension: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Colors.white,
                    ),
                  )
                : const Icon(Icons.phone_rounded),
            label: Text(launching ? '전화 앱 여는 중...' : '지금 상담원과 연결하기'),
            style: ElevatedButton.styleFrom(
              elevation: 7,
              shadowColor: const Color(0x475A6BE0),
              backgroundColor: const Color(0xFF5A6BE0),
            ),
          ),
        ],
      ),
    );
  }
}

class _PrivacyCard extends StatelessWidget {
  const _PrivacyCard();

  @override
  Widget build(BuildContext context) {
    return const AppCard(
      color: Color(0xFFF8FAFF),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.shield_outlined, size: 20, color: AppColors.primary),
          SizedBox(width: 10),
          Expanded(
            child: Text(
              '버튼을 누르면 전화 앱만 열립니다. 마음이에 저장된 정서 분석 데이터는 '
              '상담기관으로 전송되지 않아요.',
              style: TextStyle(
                color: AppColors.muted,
                fontSize: 12,
                height: 1.65,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
