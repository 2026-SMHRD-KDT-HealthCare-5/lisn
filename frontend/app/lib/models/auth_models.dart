class AuthUser {
  const AuthUser({
    required this.userId,
    required this.email,
    required this.name,
    required this.role,
    required this.personaType,
  });

  final String userId;
  final String email;
  final String name;
  final String role;
  final String personaType;

  factory AuthUser.fromJson(Map<String, dynamic> json) {
    return AuthUser(
      userId: json['user_id'] as String,
      email: json['email'] as String,
      name: json['name'] as String,
      role: json['role'] as String,
      personaType: json['persona_type'] as String,
    );
  }
}

class AuthSession {
  const AuthSession({
    required this.accessToken,
    required this.expiresAt,
    required this.user,
  });

  final String accessToken;
  final DateTime expiresAt;
  final AuthUser user;

  factory AuthSession.fromJson(Map<String, dynamic> json) {
    return AuthSession(
      accessToken: json['access_token'] as String,
      expiresAt: DateTime.parse(json['expires_at'] as String).toUtc(),
      user: AuthUser.fromJson(json['user'] as Map<String, dynamic>),
    );
  }
}

class SignupInput {
  const SignupInput({
    required this.email,
    required this.password,
    required this.name,
    required this.termsAgreed,
    required this.sensitiveAgreed,
    this.birthDate,
    this.gender,
    this.heightCm,
    this.phone,
  });

  final String email;
  final String password;
  final String name;
  final DateTime? birthDate;
  final String? gender;
  final double? heightCm;
  final String? phone;
  final bool termsAgreed;
  final bool sensitiveAgreed;

  Map<String, dynamic> toJson() => {
        'email': email,
        'password': password,
        'name': name,
        'birth_date': birthDate == null
            ? null
            : '${birthDate!.year.toString().padLeft(4, '0')}-'
                '${birthDate!.month.toString().padLeft(2, '0')}-'
                '${birthDate!.day.toString().padLeft(2, '0')}',
        'gender': gender,
        'height_cm': heightCm,
        'phone': phone,
        'terms_agreed': termsAgreed,
        'sensitive_agreed': sensitiveAgreed,
      };
}

class ApiException implements Exception {
  const ApiException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}
