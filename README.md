# ATEM Mini Controller

FastAPI 기반 ATEM Mini 제어 서버 + 웹 UI

---

## 프로젝트 구조

```
atem-controller/
├── main.py                      # FastAPI 앱, 라우터 등록, 기동 로직
├── config.py                    # 런타임 설정값 제공 (atem.conf 우선, 없으면 기본값)
├── conf_manager.py              # 설정 파일(atem.conf) 읽기/쓰기/삭제
├── requirements.txt
├── pytest.ini                   # pytest 설정 (pythonpath, testpaths)
├── presets.json                 # 프리셋 데이터 (런타임 파일)
├── atem.conf.example            # 설정 파일 예시 (실제 atem.conf는 gitignore)
├── build.bat                    # PyInstaller EXE 빌드 스크립트
├── work-log.md                  # 작업 로그
├── README.md
├── model/
│   ├── state.py                 # 내부 상태 싱글톤 (ATEMState, RLock 포함)
│   ├── preset.py                # Preset / PresetCreate / KeyerConfig Pydantic 모델
│   └── request.py               # SourceInput / PiPConfig / TransitionStyleInput 요청 스키마
├── service/
│   ├── atem_service.py          # 비즈니스 로직 + 상태 관리 (ATEMService 싱글톤)
│   ├── preset_service.py        # 프리셋 CRUD + 실행 (mtime 기반 hot reload)
│   └── ws_manager.py            # WebSocket 클라이언트 관리 + 브로드캐스트
├── controller/
│   └── atem_controller.py       # PyATEMMax SDK 하드웨어 추상화
├── simulator/
│   ├── atem_simulator.py        # PyATEMMax ATEMSimulator 래퍼 (명령 실행 + 상태 관리)
│   ├── atem_udp_server.py       # ATEM Binary UDP 프로토콜 서버 (포트 9910, 시뮬레이터 모드 전용)
│   └── simulator_config.py      # 시뮬레이터 초기값 설정
├── router/
│   ├── switching.py             # PGM / PVW / CUT / AUTO / 트랜지션 스타일
│   ├── keyer.py                 # KEY UP / PiP / KEY OFF
│   ├── system.py                # 프리셋 CRUD·실행 / 상태 조회 / 관리 API
│   ├── config_router.py         # 설정 파일 조회·저장·삭제 (/api/config)
│   └── ws.py                    # WebSocket 엔드포인트 (/ws)
├── static/
│   ├── index.html               # 메뉴 페이지
│   ├── atem_ui.html             # 메인 컨트롤 UI
│   ├── preset_panel.html        # 프리셋 전용 패널 (기본 화면)
│   ├── config.html              # 설정 페이지 (ATEM IP, 소스 이름 등)
│   ├── css/
│   │   ├── base.css             # 공통: 변수, 리셋, 폰트, 네비 버튼, 구분선
│   │   ├── ui.css               # 메인 컨트롤러 전용 스타일
│   │   ├── panel.css            # 프리셋 패널 전용 스타일
│   │   ├── config.css           # 설정 페이지 전용 스타일
│   │   └── index.css            # 메뉴 페이지 전용 스타일
│   └── js/
│       ├── ui.js                # 메인 컨트롤러 클라이언트 로직
│       ├── panel.js             # 프리셋 패널 클라이언트 로직
│       ├── header.js            # 공통 헤더/네비게이션 로직
│       ├── index.js             # 메뉴 페이지 로직
│       └── config.js            # 설정 페이지 로직
└── test/
    ├── requirements.txt         # 테스트 의존성 (pytest, httpx, anyio)
    ├── conftest.py              # 공통 픽스처 (TestClient, state/프리셋 초기화)
    ├── test_state.py            # ATEMState 단위 테스트 (7개)
    ├── test_preset_service.py   # PresetService 단위 테스트 (15개)
    ├── test_api_switching.py    # Switching API 통합 테스트 (19개)
    ├── test_api_keyer.py        # Keyer API 통합 테스트 (16개)
    ├── test_api_preset.py       # Preset CRUD + 실행 통합 테스트 (22개)
    ├── test_api_system.py       # System API 통합 테스트 (17개)
    ├── test_conf_manager.py     # conf_manager 단위 테스트 (15개)
    └── test_api_config.py       # Config API + 페이지 라우트 통합 테스트 (29개)
```

---

## 레이어 역할

| 레이어 | 역할 |
|---|---|
| `router/` | HTTP 요청/응답 처리 |
| `service/` | 비즈니스 로직 + 상태 관리 + WebSocket 브로드캐스트 |
| `controller/` | ATEM SDK 하드웨어 추상화 |
| `model/` | 데이터 구조 정의 |
| `simulator/` | 하드웨어 없이 테스트 가능한 ATEM 모의 구현 (UDP 프로토콜 포함) |
| `test/` | 자동화 테스트 (단위 + 통합, 140개) |

---

## 자동화 테스트

### 설치

```bash
pip install pytest httpx anyio
```

### 실행 (프로젝트 루트에서)

```bash
python -m pytest
```

> Windows에서 `python3`과 `python`이 다른 환경일 수 있습니다. `python -m pytest`를 권장합니다.

### 테스트 구성

| 파일 | 테스트 수 | 내용 |
|---|---|---|
| `test/test_state.py` | 7 | ATEMState 초기값, to_dict(), touch()/sync_suppressed(), 인스턴스 독립성 |
| `test/test_preset_service.py` | 15 | CRUD, 파일 영속성, hot reload, 오류 복구, confirm/keyer 필드 |
| `test/test_api_switching.py` | 19 | pgm/pvw/cut/auto/style 엔드포인트 + 유효성 검사 |
| `test/test_api_keyer.py` | 16 | key/up, key/pip (4코너 포함), key/off + 유효성 검사 |
| `test/test_api_preset.py` | 22 | 프리셋 CRUD, 실행(keyup/pip/off), 404 처리 |
| `test/test_api_system.py` | 17 | /status, /sources, /admin/reload, /admin/restart |
| `test/test_conf_manager.py` | 15 | load 기본값·오버라이드, save_conf 라운드트립, delete_conf |
| `test/test_api_config.py` | 29 | GET/POST/DELETE /api/config, 유효성 검사, 페이지 라우트 5개 |

**합계: 140개 테스트**

### 픽스처 설계

| 픽스처 | 스코프 | 역할 |
|---|---|---|
| `_patch_presets_file` | session + autouse | `PRESETS_FILE`을 임시 경로로 교체 — 실제 `presets.json` 보호 |
| `client` | session | `TestClient(app)` — lifespan 포함, 앱 1회 기동 |
| `reset` | function + autouse | 매 테스트 전 state / 시뮬레이터 / 프리셋 초기화 + `state.touch()`로 백그라운드 sync 억제 |

- **실제 ATEM 불필요** — `SIMULATOR_MODE = True`로 하드웨어 없이 완전 실행
- **독립성 보장** — 매 테스트 전 state.pgm=1, pvw=2, keyer_mode='off' 등 초기값으로 리셋

---

## 설치 및 실행

```bash
python -m pip install -r requirements.txt
python main.py
```

> **주의**: Windows에서 `python3`과 `python`이 다른 환경을 가리킬 수 있습니다.
> 반드시 실행에 사용하는 인터프리터와 동일한 것으로 패키지를 설치하세요.
> WebSocket 지원을 위해 `uvicorn[standard]` (websockets 포함)이 필요합니다.

기동 후 콘솔에 접속 URL 출력:

```
========================================
  ATEM Mini Controller
========================================
  Home   : http://localhost:8000
  Network: http://192.168.x.x:8000
  UI     : http://localhost:8000/ui
  Panel  : http://localhost:8000/panel
  Config : http://localhost:8000/config
  Swagger: http://localhost:8000/docs
========================================
```

---

## 페이지 구성

| URL | 파일 | 설명 |
|---|---|---|
| `/` | `preset_panel.html` | 프리셋 패널 (기본 화면, 기본 접속 URL) |
| `/ui` | `atem_ui.html` | 메인 컨트롤러 (전환, 키어, 프리셋 관리 포함) |
| `/panel` | `preset_panel.html` | 프리셋 전용 패널 (버튼 전체 화면, 실행 전용) |
| `/config` | `config.html` | 설정 페이지 (ATEM IP, 소스 이름, 포트, 전환 속도) |
| `/menu` | `index.html` | 메뉴 페이지 (페이지 선택) |
| `/docs` | — | Swagger API 문서 |

---

## 설정 (config.py / atem.conf)

설정 우선순위: `atem.conf` (있으면) > 기본값

| 항목 | 기본값 | 설명 |
|---|---|---|
| `ATEM_IP` | `192.168.0.240` | ATEM Mini IP 주소 |
| `ATEM_PORT` | `9910` | ATEM UDP 포트 |
| `API_HOST` | `0.0.0.0` | 서버 바인드 주소 |
| `API_PORT` | `8000` | 서버 포트 |
| `SIMULATOR_MODE` | `False` | True = 시뮬레이터 / False = 실제 ATEM |
| `TRANSITION_RATE_FRAMES` | `15` | AUTO 전환 속도 (15프레임 ≈ 500ms) |
| `DEVICE_SYNC_INTERVAL` | `2` | 장비 상태 동기화 주기 (초) |
| `SHOW_CONSOLE` | `False` | EXE 실행 시 콘솔 창 표시 여부 |
| `SOURCE_NAMES` | `["소스1(Camera)", ...]` | PGM 버튼 표시 이름 (4개) |

`config.reload()` 호출 시 재시작 없이 즉시 반영 가능한 항목: `ATEM_IP`, `ATEM_PORT`, `TRANSITION_RATE_FRAMES`, `DEVICE_SYNC_INTERVAL`, `SHOW_CONSOLE`, `SOURCE_NAMES`

재시작 필요 항목: `SIMULATOR_MODE`, `API_HOST`, `API_PORT`

---

## API 엔드포인트

### Switching

| 메서드 | 경로 | Body | 동작 |
|---|---|---|---|
| `POST` | `/switching/pgm` | `{ "source": 1 }` | PGM 직접 CUT 출력 |
| `POST` | `/switching/pvw` | `{ "source": 2 }` | PVW 소스 선택 |
| `POST` | `/switching/cut` | — | CUT 전환 (PGM ↔ PVW) |
| `POST` | `/switching/auto` | — | AUTO 전환 |
| `POST` | `/switching/style` | `{ "style": "MIX" }` | 트랜지션 스타일 설정 |

트랜지션 스타일: `MIX` / `DIP` / `WIPE` / `STING`

### Keyer

| 메서드 | 경로 | Body | 동작 |
|---|---|---|---|
| `POST` | `/key/up` | `{ "source": 2 }` | 업스트림 키어 ON (루마키, 풀사이즈 오버레이) |
| `POST` | `/key/pip` | `{ "source": 2, "size": 0.25, "pos_x": 0.62, "pos_y": 0.35 }` | PiP ON (DVE 키어) |
| `POST` | `/key/off` | — | 키어 OFF |

### 프리셋

| 메서드 | 경로 | Body | 동작 |
|---|---|---|---|
| `GET`    | `/presets` | — | 프리셋 목록 조회 |
| `POST`   | `/presets` | `PresetCreate` | 프리셋 저장 |
| `DELETE` | `/presets/{id}` | — | 프리셋 삭제 |
| `POST`   | `/preset/{id}` | — | 프리셋 실행 |

### 시스템

| 메서드 | 경로 | 동작 |
|---|---|---|
| `GET` | `/status` | 현재 상태 조회 |
| `GET` | `/sources` | 소스 이름 목록 조회 |
| `POST` | `/admin/reload` | `presets.json` 즉시 재로드 + WS 클라이언트에 `reload` 브로드캐스트 |
| `POST` | `/admin/restart` | 서버 프로세스 재시작 (0.5초 후 실행) |
| `POST` | `/admin/connect` | ATEM 장비 수동 재연결 (10초 타임아웃) |

모든 쓰기 API는 응답 시 현재 `state`를 함께 반환합니다.

### 설정 (Config)

| 메서드 | 경로 | Body | 동작 |
|---|---|---|---|
| `GET` | `/api/config` | — | 현재 설정값 조회 (conf 파일 없으면 기본값) |
| `POST` | `/api/config` | `ConfigBody` | 설정값을 `atem.conf`에 저장 |
| `DELETE` | `/api/config` | — | `atem.conf` 삭제 (재시작 후 기본값 복원) |

`ConfigBody` 필드: `atem_ip`, `atem_port` (1–65535), `simulator_mode`, `api_port` (1–65535), `transition_rate_frames` (1–300), `device_sync_interval` (1–60), `show_console`, `source_names` (4개 배열)

---

## WebSocket

| URL | 프로토콜 | 설명 |
|---|---|---|
| `/ws` | `ws://` / `wss://` | 실시간 상태 푸시 |

### 동작 방식
- 연결 즉시 `welcome` → `status` 순서로 전송
- 이후 상태 변경 시 서버에서 모든 클라이언트에 자동 브로드캐스트
- WebSocket 연결 불가 시 자동으로 3초 폴링 폴백 전환
- 재연결 시 지수 백오프 적용 (3s → 6s → 12s → 최대 30s)

### 메시지 포맷

| type | 방향 | 내용 |
|---|---|---|
| `welcome` | 서버 → 클라이언트 | 연결 확인 + 클라이언트 정보 |
| `status` | 서버 → 전체 | 현재 상태 스냅샷 |
| `log` | 서버 → 전체 | 액션 실행 로그 (실행자 IP 포함) |
| `count` | 서버 → 전체 | 접속자 수 변경 알림 |
| `reload` | 서버 → 전체 | 프리셋 목록 갱신 알림 |

```json
{ "type": "welcome", "id": "a1b2c3d4", "ip": "192.168.0.10", "ws_count": 2 }
{ "type": "status",  "data": { ...상태 필드... }, "ws_count": 2 }
{ "type": "log",     "msg": "INTRO 실행  [192.168.0.10]", "ts": "14:32:01" }
{ "type": "count",   "n": 3 }
{ "type": "reload" }
```

---

## 프리셋 데이터 구조

```json
{
  "id": 1,
  "name": "크로마키",
  "label": "PGM:소스1 / KEY UP:소스2",
  "description": "기본 사용",
  "confirm": false,
  "pgm": 1,
  "pvw": 2,
  "keyer": {
    "mode": "keyup",
    "source": 2
  }
}
```

| 필드 | 설명 |
|---|---|
| `name` | 버튼에 표시되는 이름 |
| `label` | 마우스 hover 시 툴팁 |
| `description` | 이름 옆 부가 설명 (선택) |
| `confirm` | `true` 이면 더블클릭 확인 필요 (실수 방지, 기본 `false`) |
| `pgm` | 실행할 PGM 소스 (1–4) |
| `pvw` | 실행할 PVW 소스 (선택) |
| `keyer.mode` | `keyup` / `pip` / `off` |
| `keyer.source` | 키어 소스 |
| `keyer.size` | PiP 크기 (0.0–1.0, pip 모드 전용) |
| `keyer.pos_x` | PiP 수평 위치 (-1.0–1.0, pip 모드 전용) |
| `keyer.pos_y` | PiP 수직 위치 (-1.0–1.0, pip 모드 전용) |

> `presets.json`을 직접 편집해도 서버 재시작 없이 즉시 반영됩니다 (mtime 감지).
> `POST /admin/reload`로 즉시 강제 재로드도 가능합니다.

---

## PiP 위치 좌표

```
pos_x: -1.0(좌) ~ +1.0(우)
pos_y: -1.0(하) ~ +1.0(상)

좌상단: pos_x=-0.62, pos_y= 0.35
우상단: pos_x= 0.62, pos_y= 0.35  ← 기본값
좌하단: pos_x=-0.62, pos_y=-0.35
우하단: pos_x= 0.62, pos_y=-0.35
```

> 실제 좌표는 장비 연결 후 물리 버튼 조작 시 `/status`의 `dve_pos_x/y` 값으로 확인 가능.

---

## 키어 동작 설명

| 기능 | 설명 |
|---|---|
| KEY UP | PGM 위에 지정 소스를 풀사이즈 오버레이 합성 (루마키) |
| PiP ON | PGM 위에 지정 소스를 축소해서 코너에 표시 (DVE 키어) |
| KEY OFF | 합성 제거, PGM 단독 출력 |

> **주의**: ATEM Mini 기본형은 업스트림 키어가 1개뿐이므로
> KEY UP과 PiP는 동시 사용 불가. 나중에 설정한 것이 덮어씌워짐.
> 동시 사용은 ATEM Mini Extreme (키어 4개) 이상 필요.

---

## 모델별 키어 개수

| 모델 | 업스트림 키어 | KEY UP + PiP 동시 사용 |
|---|---|---|
| ATEM Mini | 1개 | ❌ |
| ATEM Mini Pro | 1개 | ❌ |
| ATEM Mini Extreme | 4개 | ✅ |
| ATEM Mini Extreme ISO | 4개 | ✅ |

---

## 상태 응답 구조 (/status)

```json
{
  "pgm": 1,
  "pvw": 2,
  "pip_src": 2,
  "mode": "대기중",
  "keyer_mode": "keyup",
  "dve_size": 0.25,
  "dve_pos_x": 0.62,
  "dve_pos_y": 0.35,
  "last_transition": "AUTO",
  "transition_style": "MIX",
  "atem_connected": true
}
```

| 필드 | 값 |
|---|---|
| `pgm` | 현재 PGM 소스 (1~4) |
| `pvw` | 현재 PVW 소스 (1~4) |
| `pip_src` | 키어/PiP 소스 (1~4) |
| `mode` | 마지막 동작 설명 문자열 |
| `keyer_mode` | `off` / `keyup` / `pip` |
| `dve_size` | DVE 크기 (0.0~1.0) |
| `dve_pos_x` | DVE X 위치 (-1.0~1.0) |
| `dve_pos_y` | DVE Y 위치 (-1.0~1.0) |
| `last_transition` | `""` / `"CUT"` / `"AUTO"` |
| `transition_style` | `MIX` / `DIP` / `WIPE` / `STING` |
| `atem_connected` | `true` = 서버 ↔ ATEM 장비 연결 정상 |
