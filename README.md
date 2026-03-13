# 🌳 나무의사 MCP 서버

> 수목 병해충 진단 · 나무병원 찾기 · 수목 처방 DB · 관리 일정 관리
> 카카오 PlayMCP 등록용 MCP 서버

---

## 📁 파일 구조

```
tree_doctor_mcp/
│
├── server.py              ← 메인 실행 파일 (여기서 시작!)
├── requirements.txt       ← 설치할 패키지 목록
├── .env.example           ← 환경변수 예시 (복사해서 .env로 사용)
├── Dockerfile             ← 클라우드 배포용
│
├── tools/                 ← Tool 구현 파일 4개
│   ├── diagnosis.py       ← 🔬 병해충 진단 (Tool 1~4)
│   ├── hospital.py        ← 🏥 나무병원 찾기 (Tool 5~7)
│   ├── prescription.py    ← 💊 수목 처방 DB (Tool 8~10)
│   └── schedule.py        ← 📅 관리 일정 (Tool 11~13)
│
├── utils/
│   └── api_client.py      ← 공공데이터 API 공통 호출
│
└── data/
    └── pest_db.py         ← 병해충·수종 지식 베이스 데이터
```

---

## ⚡ 빠른 시작 (5단계)

### 1단계 — Python 설치 확인
```bash
python --version   # 3.10 이상 필요
```

### 2단계 — 패키지 설치
```bash
pip install -r requirements.txt
```

### 3단계 — 환경변수 설정
```bash
cp .env.example .env
# .env 파일을 열어서 API 키 입력
```

`.env` 파일에서 아래 값들을 채워 넣으세요:
| 키 이름 | 발급 위치 | 필수 여부 |
|--------|---------|---------|
| `PUBLIC_DATA_API_KEY` | [data.go.kr](https://www.data.go.kr) → 마이페이지 → 인증키 | 나무병원 검색 필수 |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) | 사진 진단 필수 |
| `KAKAO_REST_API_KEY` | [developers.kakao.com](https://developers.kakao.com) | 카카오 연동 시 |

### 4단계 — 로컬 실행 테스트
```bash
python server.py
```
→ 정상 실행 시 `나무의사 MCP 서버가 시작되었습니다` 출력

### 5단계 — PlayMCP 등록
1. [playmcp.kakao.com](https://playmcp.kakao.com) 접속 → 카카오 계정 로그인
2. `MCP 서버 등록` 클릭
3. 서버 URL 입력 (클라우드 배포 후 URL)
4. AI 채팅창에서 테스트 → "소나무 잎이 노랗게 변했어요" 입력

---

## ☁️ 클라우드 배포 (Google Cloud Run 예시)

```bash
# 1. Docker 이미지 빌드
docker build -t tree-doctor-mcp .

# 2. Google Artifact Registry에 업로드
docker tag tree-doctor-mcp gcr.io/[프로젝트ID]/tree-doctor-mcp
docker push gcr.io/[프로젝트ID]/tree-doctor-mcp

# 3. Cloud Run 배포
gcloud run deploy tree-doctor-mcp \
  --image gcr.io/[프로젝트ID]/tree-doctor-mcp \
  --platform managed \
  --region asia-northeast3 \
  --allow-unauthenticated \
  --set-env-vars PUBLIC_DATA_API_KEY=키값,ANTHROPIC_API_KEY=키값
```

> 💡 Railway(railway.app)를 사용하면 Git 연동만으로 자동 배포됩니다 — 비개발자에게 추천!

---

## 🔌 카카오 PlayMCP 도구함 연동

1. playmcp.kakao.com → 도구함 → `+ 도구 추가`
2. `카카오 톡캘린더 MCP` 추가 → 일정 자동 등록 활성화
3. `카카오톡 나와의 채팅방 MCP` 추가 → 알림 발송 활성화
4. Claude 설정 → 커스텀 커넥터 → PlayMCP 도구함 URL 등록

---

## 💬 테스트 대화 예시

AI에게 아래와 같이 말해보세요:

```
"소나무 잎이 갈색으로 변하고 끈적임이 생겼어요. 뭐가 문제일까요?"
→ diagnose_tree_disease 자동 실행

"서울 강남구에 나무병원 찾아줘"
→ find_tree_hospital_nearby 자동 실행

"이번 달에 주의해야 할 병해충 알려줘"
→ get_seasonal_pest_alert 자동 실행

"다음 주 화요일에 여의도공원 은행나무 방제 일정 등록해줘"
→ create_tree_care_schedule + 카카오 캘린더 연동
```

---

## 📞 문의 및 참고

- 산림청 산림병해충 신고: **042-481-4000**
- 소나무재선충병 신고: 가까운 시·군·구청 산림부서
- 공공데이터 API 문의: [data.go.kr 고객센터](https://www.data.go.kr)
- PlayMCP Discord: playmcp.kakao.com → 이용 가이드
