# ATEM Mini Controller — Release Notes

---

## v1.4.0 — 2026-02-22

### 개요
자동화 테스트 스위트 추가 릴리즈. 실제 ATEM 없이 시뮬레이터 모드만으로 96개 테스트 전량 실행 가능.
단위 테스트(state, preset_service)와 통합 테스트(API 전 엔드포인트)를 분리 구성.

### 새 기능

#### 자동화 테스트 스위트 (`test/`)

**테스트 파일 구성 (총 96개)**

| 파일 | 테스트 수 | 대상 |
|------|-----------|------|
| `test/test_state.py` | 7 | `ATEMState` 단위 — 초기값, `to_dict()`, `touch()` / `sync_suppressed()` |
| `test/test_preset_service.py` | 15 | `PresetService` 단위 — CRUD, 파일 영속성, hot reload, JSON 오류 복구, confirm/keyer 필드 |
| `test/test_api_switching.py` | 20 | `/switching/*` 통합 — pgm/pvw/cut/auto/style, 유효성 검사 (source 범위, style Literal) |
| `test/test_api_keyer.py` | 16 | `/key/*` 통합 — key/up, key/pip (4코너 위치), key/off, 기본값 적용, 유효성 검사 |
| `test/test_api_preset.py` | 20 | `/presets`, `/preset/{id}` 통합 — CRUD, keyup/pip/off 프리셋 실행, confirm, 404 처리 |
| `test/test_api_system.py` | 18 | `/status`, `/sources`, `/admin/reload`, `/sim/state` 통합 |

**픽스처 설계 (`test/conftest.py`)**

| 픽스처 | 스코프 | 역할 |
|--------|--------|------|
| `tmp_presets_file` | session | 임시 `presets.json` 경로 생성 |
| `_patch_presets_file` | session + autouse | `service.preset_service.PRESETS_FILE` 을 임시 경로로 교체 — 실제 파일 보호 |
| `client` | session | `TestClient(app)` — lifespan 포함, 앱 1회 기동 |
| `reset` | function + autouse | 매 테스트 전 `state` / 시뮬레이터 / 프리셋 초기화 + `state.touch()` 로 백그라운드 sync 루프 억제 |

**설계 원칙**
- `SIMULATOR_MODE = True` — 실제 ATEM 장비 불필요, CI/로컬 환경 모두 실행 가능
- 각 테스트 함수 docstring에 사용 값·기대 결과 명시 (예: `source=3 전송 → 응답 pgm=3, ok=True`)
- `test/test_preset_service.py` 의 `svc` 픽스처는 function 스코프 — 매 테스트 완전 독립 파일 사용
- `state.touch()` 로 2초 백그라운드 sync 루프를 테스트 시간 동안 억제하여 race condition 방지

#### pytest 설정 (`pytest.ini`)
```ini
[pytest]
pythonpath = .       # 프로젝트 루트를 Python 경로에 추가
testpaths = test     # 테스트 디렉토리
addopts = -v         # 테스트 이름 + docstring 상세 출력
```

### 실행 방법

```bash
# 테스트 의존성 설치 (최초 1회)
pip install pytest httpx anyio

# 전체 실행
python -m pytest

# 특정 파일만
python -m pytest test/test_api_keyer.py

# 실패 즉시 중단
python -m pytest -x
```

### 변경 파일

| 파일 | 유형 | 내용 |
|------|------|------|
| `pytest.ini` | 신규 | pytest 설정 (pythonpath, testpaths, addopts) |
| `test/requirements.txt` | 신규 | pytest, httpx, anyio |
| `test/conftest.py` | 신규 | 공통 픽스처 (session TestClient, autouse reset) |
| `test/test_state.py` | 신규 | ATEMState 단위 테스트 7개 |
| `test/test_preset_service.py` | 신규 | PresetService 단위 테스트 15개 |
| `test/test_api_switching.py` | 신규 | Switching API 통합 테스트 20개 |
| `test/test_api_keyer.py` | 신규 | Keyer API 통합 테스트 16개 |
| `test/test_api_preset.py` | 신규 | Preset API 통합 테스트 20개 |
| `test/test_api_system.py` | 신규 | System API 통합 테스트 18개 |
| `README.md` | 수정 | 자동화 테스트 섹션 추가, 프로젝트 구조 업데이트 |

---

## v1.3.0 — 2026-02-22

### 개요
WebSocket 기능 강화 + UI/UX 개선 + 타이밍·flow 버그 전면 수정 릴리즈.
패널 페이지에 실행 로그·접속 정보·소스 바를 추가하고, 연결 상태 표시를 정확하게 개선.

### 새 기능

#### WebSocket 프로토콜 확장
- 연결 시 `welcome` 메시지 전송 — 클라이언트 IP, 8자리 랜덤 ID(`secrets.token_hex(4)`), 접속자 수 포함
- `log` 메시지 — 프리셋 실행·PGM·CUT·AUTO 시 실행자 IP 포함 액션 로그 실시간 전송
- `count` 메시지 — 클라이언트 접속/해제 시 접속자 수 즉시 브로드캐스트
- `reload` 메시지 — `POST /admin/reload` 시 패널·어드민 클라이언트에 프리셋 목록 자동 갱신 알림
- `ws_count` 필드 — `status` 브로드캐스트에 현재 접속자 수 포함

#### 패널 페이지 UI 개선
- **접속 정보 표시** — 헤더에 WS 상태 dot + ATEM 상태 dot + 클라이언트 IP·ID·접속자 수 표시
  - 각 dot에 `WS` / `ATEM` 텍스트 레이블 추가 (dot만으로는 의미 불명확)
  - 연결 시 초록, 끊김 시 빨강 (WS, ATEM 독립 표시)
- **실행 로그 패널** — 프리셋 바와 PGM 바 사이에 최근 5건 실행 이력 표시
- **PGM 소스 바** — 하단에 소스 이름 버튼 추가, 직접 PGM 전환 가능
- **소스 이름 커스터마이징** — `config.SOURCE_NAMES` → `GET /sources` → PGM 버튼에 반영
- 프리셋 버튼 **더블클릭 확인** 모드 (`confirm: true`) — 첫 클릭 시 노란 pulse 애니메이션, 2초 내 재클릭 시 실행
- 프리셋 바 : PGM 바 = **7:3 비율** 배치

#### 어드민 UI 개선
- WS / ATEM 연결 상태 dot + 접속자 수 헤더 표시 (`#admin-conn`)
- **핫 리로드 버튼** — `↺ 프리셋 목록 새로고침` 전체 너비 버튼으로 배치
- 키보드 단축키 제거 (의도치 않은 입력 방지)

#### 새 API 엔드포인트
- `GET /sources` — `config.SOURCE_NAMES` 반환
- `POST /admin/reload` — `presets.json` 즉시 재로드 + WS `reload` 브로드캐스트

#### 새 모델 필드
- `Preset.confirm: bool = False` — 더블클릭 확인 모드
- `ATEMState.atem_connected: bool` — 서버 ↔ ATEM 장비 연결 상태

### 버그 수정

| 위치 | 내용 |
|------|------|
| `panel.js` `loadSources()` | `renderPgmBar()` 재호출 후 PGM active 상태 소실 — `if (status) updatePgmActive()` 추가 |
| `router/ws.py` `notify_count()` | `welcome`/`status` 전송 전 count 브로드캐스트 → 신규 클라이언트에 `.ws-count` DOM 없어 무시됨 — `notify_count()` 를 `welcome`/`status` 전송 완료 후로 이동 |
| `service/atem_service.py` `sync_from_device()` | suppress 중 초기 `return False` 로 인해 `atem_connected` 미갱신 — 장비 읽기 및 연결 상태 갱신을 suppress 판단 이전으로 이동 |
| `service/atem_service.py` `sync_from_device()` | ATEM 끊김 시 `return False` 반환 → 루프가 `notify()` 미호출 — 연결 상태 변화 시 `True` 반환으로 수정 |
| `static/css/panel.css` `.pgm-btn:hover` | 호버 색상이 빨강(active 색상과 동일)으로 오인 가능 — 중성 색상으로 변경 |

### Flow / 타이밍 수정

| 위치 | 내용 |
|------|------|
| `service/ws_manager.py` `_schedule()` | `asyncio.ensure_future` deprecated → `loop.create_task` 교체 |
| `service/ws_manager.py` `notify_count()` | count를 스케줄 시점에 캡처 → 다중 이벤트 연속 시 stale count 브로드캐스트 가능 — `_broadcast_count()` 코루틴으로 실행 시점 캡처 |
| `panel.js` / `ui.js` `onclose` | WS 끊기면 ATEM dot이 마지막 상태(초록) 유지 → `setAtemOnline(false)` 추가 |
| `panel.js` / `ui.js` `fetchStatus()` | WS 활성 중에도 HTTP 폴링 실행 → `_wsLive` 플래그 도입, WS 수신 중엔 HTTP 폴링 건너뜀 |
| `ui.js` `savePreset()` | 저장 전 `GET /status` 요청 사이에 다른 클라이언트가 상태 변경 가능 — `lastStatus` 재사용으로 race 조건 최소화 |
| `router/system.py` `admin_reload()` | 리로드 후 패널 클라이언트가 10초 타이머까지 대기 — `notify_reload()` 브로드캐스트 추가 |

### 변경 파일

| 파일 | 유형 | 내용 |
|------|------|------|
| `config.py` | 수정 | `SOURCE_NAMES` 추가 |
| `model/preset.py` | 수정 | `confirm: bool = False` 필드 추가 |
| `model/state.py` | 수정 | `atem_connected: bool` 필드, `to_dict()` 포함 |
| `service/atem_service.py` | 수정 | `sync_from_device()` 연결 상태 처리 개선 |
| `service/ws_manager.py` | 수정 | `_broadcast()` 헬퍼, `notify_log()`, `notify_count()` (lazy), `notify_reload()`, `ensure_future`→`create_task` |
| `router/ws.py` | 수정 | 클라이언트 ID/IP, `welcome` 메시지, `notify_count()` 순서 조정 |
| `router/system.py` | 수정 | `GET /sources`, `POST /admin/reload` + `notify_reload()`, `notify_log()` |
| `router/switching.py` | 수정 | `notify_log()` (IP 포함) |
| `static/atem_ui.html` | 수정 | `#admin-conn` dot + count, `.btn.reload` |
| `static/css/ui.css` | 수정 | `#admin-conn` WS/ATEM dot 스타일, `.btn.reload` |
| `static/css/base.css` | 수정 | `.dot-label` 공통 스타일 추가 |
| `static/css/panel.css` | 수정 | `#conn-info` WS/ATEM dot, `#log-bar`, `#pgm-bar`, `confirm-pending` 애니메이션, `.pgm-btn:hover` 색상 |
| `static/js/ui.js` | 수정 | `_wsLive`, `onclose` ATEM dot, `savePreset()` lastStatus, `reload` 핸들링, WS 메시지 처리 |
| `static/js/panel.js` | 수정 | `_wsLive`, `onclose` ATEM dot, `loadSources()` PGM active 복원, `reload` 핸들링, confirm 로직, `renderPgmBar()`, 접속 정보 표시 |

---

## v1.2.0 — 2026-02-22

### 개요
WebSocket 실시간 상태 푸시 도입 + 안정성 보완 릴리즈.
HTTP 폴링 방식을 WebSocket 방식으로 교체하여 패널/UI 간 상태 지연을 제거.

### 새 기능

#### WebSocket 실시간 상태 동기화
- `/ws` 엔드포인트 신규 추가 (`router/ws.py`)
- 연결 즉시 현재 상태 1회 전송
- 상태 변경 시 서버 → 모든 클라이언트 즉시 브로드캐스트 (패널/UI 공통)
- WebSocket 불가 시 자동 폴링 폴백 (3초 간격)
- 재연결 지수 백오프: 3s → 6s → 12s → 최대 30s

#### 브로드캐스트 아키텍처 최적화
- `WSManager` 도입 (`service/ws_manager.py`)
  - `asyncio.gather()` — 모든 클라이언트에 병렬 전송 (느린 클라이언트가 다른 클라이언트에 영향 없음)
  - `notify()` — `loop.call_soon_threadsafe` 기반, HTTP 응답을 블로킹하지 않음
  - 스레드풀 + 이벤트루프 양쪽에서 안전하게 호출 가능
- 라우터 핸들러 비동기 의존성 제거: `async def` → `def`, `await ws_manager.broadcast()` → `ws_manager.notify()`
- 브로드캐스트 시점에 `state` 싱글톤에서 직접 읽어 직렬화 중복 제거

### 안정성 보완

#### 스레드 안전성 강화
- `model/state.py` — `threading.RLock` 추가
  - `to_dict()`: 락 보호로 다중 필드 torn read 방지
  - `touch()` / `sync_suppressed()`: 락 보호

#### 프리셋 실행 중 중간 상태 브로드캐스트 방지
- `preset_service.execute()` 시작 시 `state.touch()` 호출
- 다단계 명령(pgm → pvw → keyer) 실행 중 sync loop가 중간 상태를 클라이언트에 전송하는 문제 해결

#### 서버 종료 안정화
- `main.py` lifespan — `sync_task.cancel()` 후 `await sync_task` + `CancelledError` 처리로 graceful shutdown 보장

#### WebSocket 에러 로깅
- `router/ws.py` — non-disconnect 예외 시 오류 메시지 콘솔 출력

### 버그 수정

| 위치 | 내용 |
|------|------|
| WebSocket 연결 실패 | `uvicorn[standard]` (websockets) 미설치 시 `/ws` 404 반환 — `python3 -m pip install` 가이드 README 추가 |
| `fire_and_forget()` | 스레드풀에서 `asyncio.create_task()` 호출 시 `RuntimeError: no running event loop` — `run_coroutine_threadsafe` → `call_soon_threadsafe` 패턴으로 교체 |

### 변경 파일

| 파일 | 유형 | 내용 |
|------|------|------|
| `service/ws_manager.py` | 신규 | WebSocket 클라이언트 관리, 병렬 브로드캐스트, `notify()` |
| `router/ws.py` | 신규 | `/ws` WebSocket 엔드포인트, 에러 로깅 |
| `model/state.py` | 수정 | `threading.RLock` 추가, `to_dict()` / `touch()` / `sync_suppressed()` 락 보호 |
| `service/preset_service.py` | 수정 | `execute()` 시작 시 `state.touch()` 추가 |
| `router/switching.py` | 수정 | `async def` → `def`, `await broadcast` → `notify()` |
| `router/keyer.py` | 수정 | 동일 |
| `router/system.py` | 수정 | `run_preset` 동일 |
| `main.py` | 수정 | WS 라우터 등록, `ws_manager.setup(loop)`, graceful shutdown |
| `static/js/ui.js` | 수정 | WebSocket 클라이언트, 지수 백오프, 페이지 오픈 시 HTTP 즉시 조회 |
| `static/js/panel.js` | 수정 | 동일 |
| `README.md` | 수정 | WebSocket 섹션 추가, 설치 주의사항, 파일 구조 업데이트 |

---

## v1.1.0 — 2026-02-22

### 개요
코드 전반 감사(audit) 및 UI/UX 개선, 안정성 보완 릴리즈.

### 새 기능

#### 페이지 구성 개편
- **랜딩 페이지** (`/`) 추가 — 메인 컨트롤러와 프리셋 패널 선택 화면
- **메인 UI** 경로 변경: `/` → `/ui`
- **프리셋 전용 패널** (`/panel`) 신규 — 프리셋 버튼만 전체 화면에 표시, 실행 전용
- 각 페이지 헤더에 **HOME 버튼** 추가

#### 프리셋 기능 강화
- `description` 필드 추가 — 버튼에 `이름 (설명)` 형식으로 표시, hover 시 `label` 툴팁
- **현재 활성 프리셋 하이라이트** — 초록색 테두리 + glow + 상태 dot (메인 UI / 패널 공통)
  - 판단 기준: `pgm` + `keyer_mode` + `pip_src` 3가지 일치
- `presets.json` **실시간 반영** — 파일 mtime 감지, 서버 재시작 없이 즉시 적용
- 프리셋 버튼 **중복 클릭 방지** — 요청 중 disabled 처리, finally에서 복원

#### 상태 관리 안정화
- **Race Condition 방지**: `state.touch()` / `state.sync_suppressed()` 패턴 도입
  - 모든 쓰기 동작 후 1초간 백그라운드 sync 억제
- `asyncio.get_running_loop()` 적용 (deprecated `get_event_loop()` 교체)
- `state.mode` 가 백그라운드 sync에 의해 덮어써지는 문제 수정

### 버그 수정

| 위치 | 내용 |
|------|------|
| `atem_ui.js` `buildKeyerConfig()` | PiP 저장 시 전역 `pipSrc` 대신 `status.pip_src` 사용하도록 수정 |
| `atem_service.py` `sync_from_device()` | 2초마다 콘솔 출력 범람 제거 |
| `atem_service.py` | `state.mode` 덮어쓰기 제거 |
| `atem_ui.js` `fetchStatus()` | `updateStatus()` 이중 호출 제거 |
| `atem_ui.js` preset 렌더링 | `innerHTML` XSS 취약점 → `createElement` + `textContent` DOM 방식으로 교체 |
| `preset_service.py` | 손상된 `presets.json` 로드 시 예외 전파로 서버 크래시 → `try/except` 안전 처리 |
| `simulator/atem_simulator.py` | `performAutoME()` 스레드 경쟁 조건 — 상태 스냅샷 + `threading.Lock` 도입 |
| `simulator/atem_simulator.py` | `setKeyerDVESizeY()` 가 `state.dve_size` 에 저장하지 않는 버그 수정 |
| `controller/atem_controller.py` | 실제 장비에서 `transition_style` 을 읽지 않던 문제 수정 |

### 변경 파일

| 파일 | 유형 |
|------|------|
| `static/index.html` | 신규 |
| `static/preset_panel.html` | 신규 |
| `model/state.py` | 수정 |
| `model/preset.py` | 수정 |
| `service/atem_service.py` | 수정 |
| `service/preset_service.py` | 수정 |
| `controller/atem_controller.py` | 수정 |
| `simulator/atem_simulator.py` | 수정 |
| `main.py` | 수정 |
| `static/atem_ui.html` | 수정 |
| `static/atem_ui.js` | 수정 |
| `static/atem_ui.css` | 수정 |
| `presets.json` | 수정 |

---

## v1.0.0 — 2026-02-21

### 개요
ATEM Mini 제어 서버 최초 구현. PyATEMMax SDK 기반 FastAPI 서버 + 웹 UI 완성.

### 구현된 기능

#### 아키텍처
- FastAPI 기반 REST API 서버 (uvicorn)
- 레이어 분리: `router` → `service` → `controller` → ATEM SDK
- 내부 상태 싱글톤 `ATEMState` 분리
- **시뮬레이터 모드**: 실제 ATEM 없이 로직 테스트 가능 (`SIMULATOR_MODE = True`)
- `simulator_config.py` — 시뮬레이터 초기값 자유 설정

#### 전환 (Switching)
- PGM 직접 출력 (`/switching/pgm`) — CUT 효과 즉시 적용
- PVW 소스 선택 (`/switching/pvw`)
- CUT 전환 (`/switching/cut`)
- AUTO 전환 (`/switching/auto`) — 기본 15프레임(≈500ms, 30fps 기준)
- 트랜지션 스타일 선택 (`/switching/style`): MIX / DIP / WIPE / STING

#### 키어 (Keyer)
- KEY UP (`/key/up`) — 지정 소스 풀사이즈 오버레이 합성
- PiP ON (`/key/pip`) — 지정 소스 코너 축소 표시 (크기 + 위치 지정)
- KEY OFF (`/key/off`) — 키어 해제

#### 프리셋 (Preset)
- JSON 기반 프리셋 시스템 (`presets.json`)
- 프리셋 CRUD API (`GET/POST/DELETE /presets`, `POST /preset/{id}`)
- 프리셋 실행: PGM, PVW(선택), 키어 모드(keyup/pip/off) 일괄 적용
- 서버 기동 시 **프리셋 1번 자동 적용**

#### 상태 관리
- 서버 기동 시 장비 현재 상태 → `state` 반영 후 프리셋 1번 적용
- **백그라운드 장비 동기화**: 2초 주기로 장비 ↔ `state` 동기화
- UI는 3초마다 `/status` 폴링으로 상태 표시 갱신

#### 웹 UI (`/ui`)
- HTML / CSS / JS 파일 분리 (`atem_ui.html` / `atem_ui.css` / `atem_ui.js`)
- 4컬럼 그리드 레이아웃: PGM | 프리셋+트랜지션 | 키어 | PiP
- **PGM 소스 버튼** — 활성 소스 빨간색 하이라이트
- **PVW 소스 버튼** — 활성 소스 초록색 하이라이트
- **CUT / AUTO 버튼** — 마지막 사용 전환 방식 하이라이트
- **트랜지션 스타일** 선택 버튼 4개 (MIX/DIP/WIPE/STING) — 활성 스타일 하이라이트
- **키어 소스 선택** 버튼 (KEY UP용), **PiP 소스 선택** 버튼 (PiP용) 별도 분리
- **KEY UP / PiP / KEY OFF** 버튼 — 현재 키어 상태 하이라이트
- **PiP 위치** 선택 (4코너 버튼), **PiP 크기** 슬라이더 (%)
- **상태 표시 바**: PGM, PVW, 트랜지션 종류, 키어 상태 실시간 표시
- **프리셋 목록** — 웹에서 저장/삭제/실행 가능
- **API 로그** — 최근 100건 요청/응답 인라인 표시

#### 기타
- CORS 미들웨어 (`allow_origins: *`)
- Swagger 자동 문서 (`/docs`)
- `/sim/state` — 시뮬레이터 내부 원시 상태 조회 (시뮬레이터 모드 전용)
- 기동 시 콘솔에 접속 URL 출력 (localhost / 네트워크 IP)
- `README.md` 작성

### 수정 이력 (v1.0.0 개발 중)

| 내용 |
|------|
| POST `/preset/2` 에서 `Unexpected token 'I'` JSON 파싱 오류 수정 |
| 트랜지션 CUT/AUTO 버튼 2행 → 1행 동등 분할로 변경 |
| 트랜지션 스타일 섹션 디바이더 추가 |
| 키어 소스 선택 UI 추가 (KEY UP / PiP 각각 분리) |
| 소스 선택 영역과 액션 버튼 간격 조정 |
| 서비스 재기동 시 `TRAN` 상태가 `—` 로 표시되는 문제 수정 |
| PVW 필드를 프리셋에서 선택 항목으로 처리 (미지정 시 현재값 유지) |
| `simulator_config.py` → `simulator/` 디렉토리로 이동 |

---

## 참고

- [README.md](README.md) — 설치, 설정, API 전체 레퍼런스
- [work-log.md](work-log.md) — 개발 과정 상세 기록 (이슈 및 해결 방법)
