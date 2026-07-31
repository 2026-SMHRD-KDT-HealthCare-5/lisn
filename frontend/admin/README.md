# 관리자 관제 웹

React + Vite 기반 관리자 로그인과 관제 대시보드 셸입니다.

```powershell
npm install
npm run dev
```

기본 API 주소는 `http://localhost:8000/api/v1`입니다. 다른 주소는 환경변수로 지정합니다.

```powershell
$env:VITE_API_BASE_URL='http://localhost:8000/api/v1'
npm run dev
```

로그인은 Flutter 앱과 같은 `POST /auth/login`을 사용하며 응답의 `user.role`이 `ADMIN`인 계정만 통과합니다. 토큰은 브라우저 탭을 닫으면 사라지는 `sessionStorage`에 보관합니다.

관제 대시보드 데이터 API는 아직 구현되지 않아 로그인 이후에는 연결 대기 상태를 표시합니다.
