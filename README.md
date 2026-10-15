# 🗓️ 스티커 메모 캘린더 (Sticky Note Calendar)

포스트잇 스타일의 **스티커 메모형 캘린더** 애플리케이션입니다.  
내 PC 로컬 환경과 **Docker 컨테이너 환경** 모두에서 즉시 실행 및 상호 연동되도록 구축되었습니다.

---

## 주요 기능

1. **파스텔톤 5색 테마**:
   - 🟡 노랑 (`#FEF9E7`) / 🔵 파랑 (`#EBF5FB`) / 🟢 초록 (`#EAFAF1`) / 🟠 주황 (`#FBEEE6`) / 🟣 보라 (`#F4ECF7`)
2. **자유로운 창 이동 & 크기 조절**:
   - 상단 헤더를 잡고 부드럽게 드래그하여 원하는 위치에 배치
   - 모서리 핸들을 잡고 드래그하여 자유로운 크기 조절
3. **실시간 자동 저장 & 복원 (Auto-Save)**:
   - 메모 내용, 날짜, 색상, 좌표(`pos_x, pos_y`), 크기(`width, height`), 핀 고정 상태가 SQLite(`sticky_notes.db`)에 실시간 동기화
4. **체크박스 / 투두(Todo) 모드 지원**:
   - `[ ]`, `[x]` 기반의 대화형 체크리스트 모드 지원 (완료 시 취소선 효과 및 체크 상태 저장)
5. **항상 위 핀(Pin) 고정 (📌/📍)**:
   - 핀을 켜면 최상단 레이어에 고정
6. **월별 캘린더 뷰 (Calendar View)**:
   - 날짜별 메모 등록 현황을 캘린더 인디케이터(도트)로 한눈에 파악
   - 특정 날짜 클릭 시 해당 날짜 메모 필터링 및 즉시 추가 기능
7. **자동 바둑판 정렬 (🗂️)**:
   - 흩어져 있는 메모들을 화면에 깔끔하게 자동 정렬
8. **시스템 트레이(Tray Icon) & 플로팅 독 (Dock Widget)**:
   - 로컬 앱: 작업표시줄 트레이 상주, 원클릭 전체 메모 숨기기/보이기, 트레이 우클릭 메뉴(새 메모, 정렬, 종료)
   - 웹 앱: 상단 `[👁️ 전체 숨기기/보이기]` 버튼, 개별 메모 `[➖]` 최소화, 하단 플로팅 독 위젯을 통한 원클릭 복원
9. **일정 시간 알람 & 사운드/토스트 알림 (Alarm Sound & Toast)**:
   - 각 포스트잇에 날짜 외에 **시간(HH:mm) 설정 및 알람 토글(🔔 / 🔕)** 지원
   - 로컬 앱: 지정 시간에 윈도우 비프/사운드 재생, 창 전면 활성화, 윈도우 트레이 풍선 알림 발송
   - 웹 앱: Web Audio API 기반 크리스탈 멜로디 차임벨 재생, 글래스모피즘 토스트 팝업 및 메모 포커스 펄스 하이라이트 효과, 데스크톱 브라우저 푸시 알림 연동

---

## Docker 컨테이너로 실행 (권장)

현재 Docker 컨테이너가 이미 빌드되어 포트 `8080`에서 실행 중입니다.

### 브라우저 접속 주소
**[http://localhost:8080](http://localhost:8080)**

### 실행 및 관리 명령어
```bash
# 1. 원클릭 실행 (Windows 배치 파일)
start.bat

# 2. 또는 Docker Compose 명령어
docker compose up -d

# 로그 실시간 확인
docker compose logs -f

# 컨테이너 중지
docker compose down
```

---

## 로컬 PC(PyQt6) 데스크톱 앱으로 실행

로컬 PC 파이썬 환경에서 창 형태로 직접 띄우고 싶을 때 사용합니다.

```bash
# 1. 패키지 설치
pip install PyQt6

# 2. 실행
python sticky_calendar.py
```

> **참고**: Docker 웹 버전과 로컬 PyQt6 버전은 동일한 `sticky_notes.db` 파일을 공유하므로 데이터가 상호 보존됩니다.

---

## 프로젝트 구조

```text
local-memo/
├── .gitignore             # Git 추적 제외 파일 목록 (DB, 캐시 등)
├── docker-compose.yml     # Docker 컨테이너 오케스트레이션 설정
├── Dockerfile             # Docker 이미지 빌드 파일
├── requirements.txt       # Python 의존성 목록 (FastAPI, Uvicorn 등)
├── server.py              # FastAPI 백엔드 API & SQLite 연동 서버
├── sticky_calendar.py     # 로컬 PC용 PyQt6 데스크톱 애플리케이션
├── sticky_notes.db        # 로컬 SQLite 데이터베이스 (공유)
├── start.bat              # Windows 원클릭 실행 배치 파일
└── static/                # 웹 애플리케이션 정적 파일
    ├── index.html         # 메인 HTML 구조
    ├── style.css          # 파스텔 테마 및 반응형 UI 스타일시트
    └── app.js             # 드래그앤드롭, 투두, 캘린더, 실시간 자동저장 로직
```
