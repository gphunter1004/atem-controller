# ATEM Mini Controller — Work Log

---

## 2026-03-08 (세션 7 — PyATEMMax 분석 + Flying Key 수정 + 패널 PiP 위치 버튼)

### 개요
PyATEMMax 라이브러리 내부 분석을 통해 Flying Key 트랜지션 버그를 수정하고,
패널 화면에 PiP 위치 버튼 4개(↖↗↙↘ + KEY OFF)를 추가.

---

### 1. PyATEMMax 라이브러리 내부 분석

#### DVE 좌표계 확인

| 항목 | 방식 | Signed | 범위 | Scale |
|------|------|--------|------|-------|
| Position X/Y (Setter) | `int(float * 1000)` → 32-bit 전송 | Yes | ±16 / ±9 | 1000 |
| Position X/Y (Handler) | `getFloat(offset, True, 32, 1000)` | Yes | ±16 / ±9 | 1000 |
| Size X/Y | `int(float * 1000)` / `getFloat(…, False, …)` | No | 0.0 ~ 1.0 | 1000 |

- **Position은 Signed** → 음수값(좌/하) 지원
- 문서의 `0.0-1.0` 표기는 잘못된 것으로, 실제 프로토콜은 signed 32-bit

#### Flying Key 메커니즘

| 메서드 | 프로토콜 명령 | 기능 |
|--------|-------------|------|
| `setKeyerOnAirEnabled` | CKOn | KEY LED ON/OFF — 단독으로 충분 |
| `setKeyerFlyEnabled` | CKTp | Flying Key 애니메이션 활성화 (LED와 무관) |
| `setRunFlyingKeyKeyFrame` | RFlK | 키프레임 A/B 위치로 트랜지션 이동 |

- **KEY LED는 `setKeyerOnAirEnabled(True)` 만으로 충분**, `setKeyerFlyEnabled`는 불필요
- `setKeyerFlyEnabled(True)` 활성화 시 키프레임 A 위치(초기값 0,0)로 트랜지션 발생

#### 물리 위치 버튼 관련
- 라이브러리에 4코너 좌표 상수 없음 (topLeftBox 등은 Wipe 트랜지션 패턴용, DVE 무관)
- 물리 버튼 눌렀을 때 `/status` → `dve_pos_x/y`로 실제 좌표 확인 필요
- `_handleKeDV` 핸들러가 실시간으로 position X/Y 수신

---

### 2. `setKeyerFlyEnabled` 제거

**문제**: `set_keyer_type_dve()`에서 `setKeyerFlyEnabled(True)` 호출 → Flying Key 애니메이션 활성화 → 키프레임 A 위치(초기값 0,0)로 트랜지션 발생 → PiP가 중앙으로 이동

**수정** (`controller/atem_controller.py`):
```python
# Before
def set_keyer_type_dve(self):
    keyer_type = "dve" if _is_simulator else PyATEMMax.ATEMKeyerTypes.dVE
    self._cmd(lambda: self.switcher.setKeyerType(0, 0, keyer_type))
    if not _is_simulator:
        self._cmd(lambda: self.switcher.setKeyerFlyEnabled(0, 0, True))  # ← 제거

# After
def set_keyer_type_dve(self):
    keyer_type = "dve" if _is_simulator else PyATEMMax.ATEMKeyerTypes.dVE
    self._cmd(lambda: self.switcher.setKeyerType(0, 0, keyer_type))
```

---

### 3. 패널 PiP 위치 버튼 4개 추가

**요구사항**: 패널 화면에서 PiP를 4개 코너 위치로 즉시 이동하는 독립 버튼

**좌표 (추정값, 물리키 테스트 후 보정 필요)**:
| 버튼 | pos_x | pos_y |
|------|-------|-------|
| ↖ 좌상 | -12.0 | 7.0 |
| ↗ 우상 | 12.0 | 7.0 |
| ↙ 좌하 | -12.0 | -7.0 |
| ↘ 우하 | 12.0 | -7.0 |

**구현**:

`static/preset_panel.html` — `#pip-bar` div 추가 (log-bar와 pgm-bar 사이)

`static/js/panel.js`:
- `_pipPos` 상수: tl/tr/bl/br 좌표 정의
- `renderPipBar()`: ↖↗↙↘ + KEY OFF 버튼 생성
- `activatePip(posKey)`: `POST /key/pip` 호출 (source = 현재 `status.pip_src` 또는 1, size = 0.25)
- `keyOff()`: `POST /key/off` 호출
- `updatePipActive()`: `dve_pos_x/y` 비교(오차 ±0.5)로 활성 버튼 노란색 하이라이트
- WS status / HTTP 폴링 수신 시 `updatePipActive()` 자동 호출

`static/css/panel.css`:
- `#pip-bar`: `flex: 2`
- `.pip-btn.pip-active`: 노란색 하이라이트 + glow
- `.pip-btn.pip-off-active`: KEY OFF 활성 표시
- `#pgm-bar` flex: 3 → 2
- 레이아웃 비율: preset:7 / pip:2 / pgm:2

**미확인 사항**: 물리 위치 버튼의 실제 DVE 좌표값. 장비 연결 후 물리키 누를 때 `/status`의 `dve_pos_x/y` 값 확인하여 `_pipPos` 보정 필요.

---

### 변경 파일 요약

| 파일 | 유형 | 내용 |
|------|------|------|
| `controller/atem_controller.py` | 수정 | `set_keyer_type_dve()`에서 `setKeyerFlyEnabled` 제거 |
| `static/preset_panel.html` | 수정 | `#pip-bar` div 추가 |
| `static/js/panel.js` | 수정 | PiP 위치 바 렌더링, activatePip, keyOff, updatePipActive |
| `static/css/panel.css` | 수정 | `#pip-bar` 스타일, `.pip-btn` 스타일, `#pgm-bar` flex 조정 |

---

## 2026-03-08 (세션 6 — 공통 헤더 / conf 핫리로드 / config UI / EXE 빌드)

### 개요
공통 헤더 JS 리팩토링, conf 핫리로드, config 페이지 개선, 시작 프로그램 등록,
EXE 빌드 및 setup.ps1 강화.

---

### 1. 공통 헤더 리팩토링

`static/js/header.js` 신규 생성 — 두 UI(`panel.js`, `ui.js`)에서 공통으로 사용하는 함수 분리:
- `BASE`, `updateConnInfo`, `setWsOnline`, `setAtemOnline`, `updateWsCount`, `reconnect`, `loadAtemAddr`
- `_onReconnectSuccess` 콜백 패턴으로 각 페이지별 재연결 후 처리 위임
- `atem_ui.html`, `preset_panel.html`에 `header.js` 로드 추가
- `ui.css`에서 `#admin-conn` 블록 제거 → `base.css`의 `#conn-info`로 통합

---

### 2. conf 핫리로드

`POST /api/config` 저장 후 서버 재시작 없이 즉시 설정 반영:
- `config.reload()` 호출 — `atem.conf` 재파싱 후 모듈 전역 변수 갱신
- `atem_controller.py`: `from config import X` → `import config` + `config.X` 접근으로 변경 (동적 참조)
- `main.py`: `DEVICE_SYNC_INTERVAL` 루프에서 `_config.DEVICE_SYNC_INTERVAL` 동적 참조

---

### 3. config 페이지 개선

- 재시작 필요 항목 🔄 / 즉시 적용 항목 ⚡ 이모지 배지로 구분 표시
- 콘솔 창 표시 옵션 추가 (`show_console`, 기본값 OFF)
  - Windows EXE 환경에서 `ctypes`로 콘솔 창 show/hide
- HOME 버튼 우측 배치
- `conf_manager.py`: `device_sync_interval` 기본값 2→1초, `[app]` 섹션 추가

---

### 4. `/admin/startup` 추가 후 제거

- `router/system.py`에 `GET/POST/DELETE /admin/startup` 구현 (atem.exe 시작 프로그램 등록)
- config 페이지에 UI 추가 (`config.html`, `config.css`, `config.js`)
- **사용자 요청으로 전체 제거** — 서버(atem.exe) 자동실행이 아니라 웹 페이지(Edge) 자동실행이 원래 의도였음

---

### 5. setup.ps1 강화

**시작 프로그램 바로가기 추가**:
- 설치 시 바탕화면 + 시작 프로그램 폴더(`%APPDATA%\...\Startup\`) 두 곳에 동시 바로가기 생성
- 바로가기 대상: Edge `--app=http://...` (웹 UI 런처)
- 제거 시 두 바로가기 모두 삭제

**스케줄러 등록 후 즉시 실행**:
- `schtasks /run` / `Start-ScheduledTask` 추가
- 설치 완료 직후 atem.exe 즉시 기동 (재로그인 불필요)

적용 파일: `setup.ps1` (루트), `dist/setup.ps1`

---

### 6. EXE 빌드

```bash
python -m PyInstaller --noconfirm atem.spec
```
`dist/atem.exe` 정상 생성 확인.

---

### 변경 파일 요약

| 파일 | 유형 | 내용 |
|------|------|------|
| `static/js/header.js` | 신규 | 공통 헤더 함수 분리 |
| `static/js/panel.js` | 수정 | header.js 의존, 중복 제거 |
| `static/js/ui.js` | 수정 | header.js 의존, 중복 제거 |
| `static/atem_ui.html` | 수정 | header.js 로드 추가 |
| `static/preset_panel.html` | 수정 | header.js 로드 추가 |
| `static/css/base.css` | 수정 | `#conn-info` 통합 |
| `static/css/ui.css` | 수정 | `#admin-conn` 제거 |
| `config.py` | 수정 | `reload()` 함수 추가 |
| `controller/atem_controller.py` | 수정 | `import config` 방식으로 변경 |
| `conf_manager.py` | 수정 | `[app]` 섹션, `device_sync_interval` 기본값 변경 |
| `main.py` | 수정 | 동적 DEVICE_SYNC_INTERVAL 참조 |
| `setup.ps1` | 수정 | 시작 프로그램 바로가기, 즉시 실행 |
| `dist/setup.ps1` | 수정 | 동일 |

---

## 2026-03-08 (세션 5 — Config API 테스트 + 페이지 라우트 테스트 + EXE 빌드)

### 개요
세션 4 이후 추가된 기능(Config API, `/menu` 라우트, EXE 빌드/배포)에 대한 테스트를 보강하고,
`conf_manager` 단위 테스트를 신규 작성. 페이지 라우트 커버리지도 추가. 총 54개 테스트 추가.

---

### 1. 신규 테스트 파일

#### `test/test_conf_manager.py` (19개)

conf_manager.py 단위 테스트. 각 테스트마다 `monkeypatch`로 `CONF_PATH`를 임시 경로로 교체해 실제 `atem.conf`를 건드리지 않음.

| 그룹 | 테스트 수 | 내용 |
|------|-----------|------|
| 기본값 검증 | 5 | conf 파일 없을 때 ip/port/simulator_mode/server/switching/sources 기본값 |
| 파일 오버라이드 | 2 | ip 오버라이드, 부분 저장 시 나머지 기본값 유지 |
| save_conf | 3 | 파일 생성, 전체 라운드트립, 두 번 저장 시 덮어씌워짐 |
| delete_conf | 3 | 삭제 후 파일 없음/True 반환, 파일 없을 때 False, 삭제 후 기본값 복원 |
| 모듈 상수 | 2 | BASE_DIR 비어있지 않음, PRESETS_FILE 접미사 확인 |

#### `test/test_api_config.py` (35개)

Config API 통합 테스트 + 페이지 라우트 테스트. `conf_path` 픽스처로 `conf_manager.CONF_PATH`와 `router.config_router.CONF_PATH` 를 모두 임시 경로로 패치.

**GET /api/config (8개)**
- 200 OK
- 필수 키 9개 전체 포함 (atem_ip, atem_port, simulator_mode, api_port, transition_rate_frames, device_sync_interval, source_names, conf_file, conf_exists)
- conf 파일 없을 때 기본값: ip, simulator_mode=False, api_port
- source_names 배열 길이 4
- conf_exists=False (파일 없음), bool 타입 확인

**POST /api/config (12개)**
- ok=True, conf_file 필드 포함
- 저장 후 GET에서 반영: conf_exists=True, ip, transition_rate_frames, source_names
- 유효성 검사 (422): atem_port=0/99999, api_port=0, transition_rate_frames=0/301, device_sync_interval=61

**DELETE /api/config (4개)**
- ok=True, 파일 없어도 ok=True (idempotent)
- 삭제 후 conf_exists=False, 삭제 후 기본 ip 복원

**페이지 라우트 (5개)**
- GET `/` `/menu` `/ui` `/panel` `/config` → 200, Content-Type: text/html

---

### 2. 설계 포인트

#### `conf_path` 픽스처 (function 스코프)

```python
@pytest.fixture()
def conf_path(tmp_path, monkeypatch):
    p = str(tmp_path / "atem_test.conf")
    monkeypatch.setattr(cm, "CONF_PATH", p)   # load/save/delete 함수 영향
    monkeypatch.setattr(cr, "CONF_PATH", p)   # 응답 conf_file 필드 영향
    yield p
```

**두 모듈을 모두 패치해야 하는 이유**:
- `conf_manager.CONF_PATH` → `load()`, `save_conf()`, `delete_conf()` 가 모듈 전역 `CONF_PATH`를 런타임에 참조
- `router.config_router.CONF_PATH` → `from conf_manager import CONF_PATH` 로 임포트 시점에 값을 복사 → 별도 패치 필요

#### `DELETE /api/config` idempotent 설계

`conf_manager.delete_conf()` 는 파일 없으면 `False` 반환. 그러나 router 레이어는 항상 `{"ok": True}` 반환(파일 유무 무관). 클라이언트 입장에서 멱등성 유지.

---

### 3. 세션 4 이후 추가된 기능

| 기능 | 파일 | 내용 |
|------|------|------|
| Config API | `router/config_router.py` | `GET/POST/DELETE /api/config` — atem.conf 읽기/쓰기/삭제 |
| conf_manager | `conf_manager.py` | 설정 파일 파서, 기본값 관리 |
| `/menu` 라우트 | `main.py` | `index.html` 서빙 |
| 기본 화면 변경 | `main.py` | `/` → `preset_panel.html` (이전: `index.html`) |
| EXE 빌드 | `atem.spec`, `build.bat` | PyInstaller one-file, console=True |
| 배포 스크립트 | `dist/setup.ps1` | 설치/제거, Task Scheduler + Edge 바로가기 |
| simulator_mode 기본값 | `conf_manager.py` | `'true'` → `'false'` |

---

### 변경 파일 요약

| 파일 | 유형 | 내용 |
|------|------|------|
| `test/test_conf_manager.py` | 신규 | conf_manager 단위 테스트 19개 |
| `test/test_api_config.py` | 신규 | Config API 통합 테스트 30개 + 페이지 라우트 5개 |
| `README.md` | 수정 | 테스트 수 업데이트, Config API 섹션 추가, 프로젝트 구조 업데이트 |

---

## 2026-02-22 (세션 4 — 자동화 테스트 작성)

### 개요
실제 ATEM 장비 없이 시뮬레이터 모드만으로 전체 기능을 검증하는 pytest 자동화 테스트 스위트를 작성.
단위 테스트와 통합 테스트를 분리 구성, 96개 테스트 전량 통과 (3초 내 완료).

---

### 1. 설계 결정

#### 픽스처 스코프 전략

**session 스코프 (`client`)**
- `TestClient(app)` 을 1회만 생성해 lifespan 오버헤드 최소화
- lifespan 실행 시 `atem.connect()` → `init_defaults()` → `sync_from_device()` → 프리셋 1번 실행(없으면 skip)

**autouse function 스코프 (`reset`)**
- 매 테스트 직전 `state` / 시뮬레이터 / 프리셋 파일을 초기값으로 되돌림
- 초기값: `pgm=1, pvw=2, keyer_mode='off', transition_style='MIX', atem_connected=True`
- `state.touch()` 로 백그라운드 sync 루프(2초 주기)를 1초간 억제 → 테스트 중 race condition 방지

**PRESETS_FILE 패치 (`_patch_presets_file`)**

핵심 문제: `preset_service = PresetService()` 싱글톤은 conftest.py 임포트 시점에 이미 생성됨.
하지만 `_load()`, `_save()` 등 메서드는 `PRESETS_FILE` 를 런타임에 모듈 전역에서 조회.
따라서 `ps_module.PRESETS_FILE = tmp_path` 패치 후의 모든 파일 I/O는 임시 경로를 사용.

```python
import service.preset_service as ps_module

@pytest.fixture(scope="session", autouse=True)
def _patch_presets_file(tmp_presets_file):
    original = ps_module.PRESETS_FILE
    ps_module.PRESETS_FILE = tmp_presets_file  # 이후 _load()/_save() 모두 tmp 경로 사용
    yield
    ps_module.PRESETS_FILE = original
```

실제 `presets.json` 은 테스트 중 절대 변경되지 않음.

---

### 2. 파일별 테스트 내용

#### `test/test_state.py` (7개)
- 초기값 검증 (pgm=1, pvw=2, keyer_mode='off', atem_connected=False 등)
- `to_dict()` 11개 필드 키/값 검증
- `touch()` → `sync_suppressed()` = True, window=0.0이면 False
- 독립 인스턴스 간 격리 확인

#### `test/test_preset_service.py` (15개)
각 테스트마다 `svc` 픽스처로 독립 파일 사용 (function 스코프):
- CRUD: add, list, get, delete, 존재하지 않는 id
- 파일 영속성: JSON 파일에 실제 저장됐는지 확인
- 새 인스턴스 로드: 같은 파일 경로의 새 인스턴스가 기존 데이터 읽는지 확인
- Hot reload: 외부에서 파일 수정 후 mtime 변경 → `list_presets()` 자동 재로드
- 오류 복구: 손상된 JSON → `_load()` 후 빈 목록
- 필드: confirm 기본값/True, keyer={mode='keyup', source=2}

#### `test/test_api_switching.py` (20개)
- pgm/pvw: 1~4 전체 소스, 응답 필드 검증
- cut: pgm↔pvw 교체, last_transition='CUT', 두 번 CUT으로 원복
- auto: 동일 구조, last_transition='AUTO'
- style: MIX/DIP/WIPE/STING 각각 검증
- 유효성: source=0/5 → 422, style='DISSOLVE' → 422, body 없음 → 422

#### `test/test_api_keyer.py` (16개)
- key/up: source=1~4 전체, pgm 불변 확인, 응답 필드
- key/pip: 커스텀 size/pos, 기본값 적용, 4코너 좌표 정밀 검증 (오차 0.001)
- key/off: keyup/pip 이후 → 'off', 이미 off 상태에서 재호출 idempotent
- 유효성: source=0/5 → 422, size=1.5/-0.1 → 422, pos_x=1.5 → 422
- source 미지정 → 기본값 1 적용 (200)

#### `test/test_api_preset.py` (20개)
- 빈 목록, 생성 응답, id 자동 증가, A/B 동시 목록 조회
- keyer keyup/pip/confirm/pvw 있는 프리셋 생성
- 유효성: pgm=0/5 → 422, name 없음 → 422, pgm 없음 → 422
- 삭제: ok=True, 목록에서 사라짐, 대상만 삭제(나머지 유지), 없는 id → 404
- 실행: pgm=3 변경, keyer keyup/pip 상태 반영, keyer off 전환, 없는 id → 404

#### `test/test_api_system.py` (18개)
- `/status`: 200, 11개 필드, state 직접 변경 후 반영, pgm API 호출 후 반영, bool 타입 확인
- `/sources`: 200, sources 키, 4개 항목, `config.SOURCE_NAMES` 일치
- `/admin/reload`: ok=True, count 필드, 프리셋 2개 후 count=2, 삭제 후 count=0
- `/sim/state`: 200, pgm/pvw 필드, 시뮬레이터 직접 수정 반영, API 호출 후 반영

---

### 3. 트러블슈팅

#### `./pytest` PowerShell 실행 오류
```
'./pytest' 용어가 cmdlet, 함수... 인식되지 않습니다.
```
PowerShell에서 Unix 방식 `./script` 실행 불가.
**해결**: `python -m pytest` 사용.

#### `python3 -m pytest` 모듈 없음
```
No module named pytest
```
Windows에서 `python3`(Microsoft Store 별칭)과 `python`(설치 Python)이 서로 다른 환경.
pytest가 `python` 환경에 설치됨.
**해결**: `python -m pytest` 사용.

#### 테스트 내용 파악 어려움
`-v` 옵션만으로는 테스트 이름은 보이나 무슨 값을 사용하는지 불명확.
**해결**:
1. `pytest.ini`에 `addopts = -v` 추가
2. 각 테스트 함수에 docstring으로 사용 값·기대 결과 명시
   ```python
   def test_pgm_changes_state(client):
       """source=3 전송 → 응답 pgm=3, ok=True"""
   ```

---

### 변경 파일 요약

| 파일 | 유형 | 내용 |
|------|------|------|
| `pytest.ini` | 신규 | `pythonpath=.`, `testpaths=test`, `addopts=-v` |
| `test/requirements.txt` | 신규 | `pytest>=7.4`, `httpx>=0.23`, `anyio[trio]>=3.6` |
| `test/conftest.py` | 신규 | session TestClient, PRESETS_FILE 패치, autouse reset 픽스처 |
| `test/test_state.py` | 신규 | ATEMState 단위 테스트 7개 |
| `test/test_preset_service.py` | 신규 | PresetService 단위 테스트 15개 (독립 svc 픽스처) |
| `test/test_api_switching.py` | 신규 | Switching API 통합 테스트 20개 |
| `test/test_api_keyer.py` | 신규 | Keyer API 통합 테스트 16개 |
| `test/test_api_preset.py` | 신규 | Preset API 통합 테스트 20개 |
| `test/test_api_system.py` | 신규 | System API 통합 테스트 18개 |
| `README.md` | 수정 | 자동화 테스트 섹션 추가, 프로젝트 구조 업데이트 |
| `RELEASE_NOTES.md` | 수정 | v1.4.0 추가 |

---

## 2026-02-22 (세션 3 — WebSocket 강화 + UI/UX + 타이밍 버그 수정)

### 개요
패널/어드민 UI에 연결 상태 표시·실행 로그·소스 바를 추가하고,
WebSocket 프로토콜을 확장(welcome / log / count / reload 메시지).
전반적인 타이밍·flow 이슈를 발견하고 전면 수정.

---

### 1. WebSocket 프로토콜 확장

#### 배경
연결 즉시 클라이언트 식별 정보를 전달하고 싶었으며,
실행 로그·접속자 수·프리셋 리로드를 별도 채널 없이 WS로 처리하고 싶었음.

#### 구현

**`router/ws.py`**
- `secrets.token_hex(4)` — 연결 시 8자리 랜덤 클라이언트 ID 생성
- `welcome` 메시지 — 클라이언트 자신의 IP, ID, 현재 접속자 수 전송
- `status` 전송 완료 후 `notify_count()` 호출 (기존: connect() 직후)

**`service/ws_manager.py`**
```python
async def _broadcast_count(self):
    await self._broadcast({"type": "count", "n": self.count})  # 실행 시점 캡처

def notify_count(self):
    self._schedule(self._broadcast_count())  # 스케줄 시점이 아닌 실행 시점 count 사용

def notify_log(self, msg: str):
    data = {"type": "log", "msg": msg, "ts": _time.strftime("%H:%M:%S")}
    self._schedule(self._broadcast(data))

def notify_reload(self):
    self._schedule(self._broadcast({"type": "reload"}))

# asyncio.ensure_future (deprecated) → loop.create_task 교체
self._loop.call_soon_threadsafe(self._loop.create_task, coro)
```

**`router/switching.py`, `router/system.py`**
- `Request` 주입 → 실행자 IP를 `notify_log()` 메시지에 포함
- `POST /admin/reload` — `notify_reload()` 브로드캐스트 추가

---

### 2. 패널·어드민 UI 개선

#### 패널 (`preset_panel.html`, `panel.css`, `panel.js`)

| 추가 요소 | 위치 | 설명 |
|---|---|---|
| WS/ATEM 상태 dot | 헤더 | 텍스트 레이블 `WS` / `ATEM` + 색상 dot (연결=초록, 끊김=빨강) |
| 클라이언트 IP·ID | 헤더 | `welcome` 메시지 수신 후 표시 |
| 접속자 수 | 헤더 | `· N명` 형식, count/status 수신 시 갱신 |
| 실행 로그 바 | 중단 | 최근 5건 액션 로그, WS `log` 메시지 수신 시 표시 |
| PGM 소스 바 | 하단 | 소스 이름 버튼 4개, 직접 PGM 전환 |
| 프리셋:PGM 비율 | — | 7:3 flex 비율 |

**소스 이름** — `GET /sources` 호출 후 `renderPgmBar()` 재실행. `config.SOURCE_NAMES` 로 커스터마이징.

**confirm 모드** — `Preset.confirm = true` 시 첫 클릭에서 노란 pulse 애니메이션(`confirm-pending`), 2초 내 재클릭 시 실행.

#### 어드민 (`atem_ui.html`, `ui.css`, `ui.js`)
- `#admin-conn` — WS/ATEM dot + 접속자 수, `ws-online` / `atem-online` CSS 클래스로 상태 전환
- `↺ 프리셋 목록 새로고침` — 기존 패널 타이틀 내 숨겨진 버튼 → 전체 너비 `.btn.reload` 버튼으로 재배치
- 키보드 단축키 제거 (의도치 않은 입력 오작동 방지)
- WS `log`, `count`, `reload` 메시지 핸들링 추가

---

### 3. 버그 발견 및 수정

#### 3-1. PGM active 상태 소실 (`panel.js`)

**문제**:
`loadSources()` 완료 후 `renderPgmBar()` 를 재호출하면 DOM을 새로 생성하므로
기존 `.pgm-active` 클래스가 사라짐.

**수정**:
```javascript
async function loadSources() {
  ...
  renderPgmBar();
  if (status) updatePgmActive();  // 추가
}
```

#### 3-2. `notify_count()` 타이밍 (`router/ws.py`)

**문제**:
`connect()` → `notify_count()` 예약 → `welcome` 전송 순서로 처리.
신규 클라이언트가 `welcome` 이전에 `count` 메시지를 받으면 `.ws-count` DOM 없어 무시됨.

**수정**: `welcome` / `status` 전송 완료 후 `notify_count()` 호출.

#### 3-3. `atem_connected` suppress 중 미갱신 (`atem_service.py`)

**문제**:
`sync_from_device()` 에서 `sync_suppressed()` True 이면 즉시 `return False` →
`atem_connected` 를 갱신하지 않고 종료 → 서버 시작 후 `execute(p1)` 직후 짧은 suppress 구간 동안
첫 WS 클라이언트에 `atem_connected: false` 전달.

**수정**: 장비 읽기 및 `atem_connected` 갱신을 suppress 판단 이전에 수행.

#### 3-4. ATEM 끊김 시 WS 브로드캐스트 없음 (`atem_service.py`)

**문제**: 장비 읽기 실패(예외 또는 빈 응답) 시 `return False` → sync 루프가 `notify()` 미호출 →
ATEM 끊김을 WS 클라이언트가 인지하지 못함.

**수정**: `prev_connected` 저장 후 연결 상태 변화 여부를 반환값에 반영:
```python
prev_connected = state.atem_connected
...
state.atem_connected = False
return prev_connected          # 이전이 True면 True 반환 → 브로드캐스트

state.atem_connected = True
if state.sync_suppressed():
    return not prev_connected  # 연결 상태 바뀐 경우만 True
```

#### 3-5. 패널 PGM 버튼 hover 색상 (`panel.css`)

**문제**: `.pgm-btn:hover` 가 빨강 → active 상태(빨강)와 구분 불가.

**수정**: hover 시 중성 색상(`var(--text)`, 연한 회청색)으로 변경.

---

### 4. Flow / 타이밍 보완

#### 4-1. `_wsLive` 플래그 — HTTP 폴링 중복 제거

**문제**: WS가 활성 상태인데도 `_wsFallback` 인터벌이 `fetchStatus()` 를 계속 호출.
페이지 오픈 시 HTTP + WS가 동시에 status를 가져와 나중 응답이 앞 응답을 덮어씀(last-write-wins).

**해결**:
```javascript
let _wsLive = false;  // WS status 수신 후 true

async function fetchStatus() {
  if (_wsLive) return;  // WS 활성 중 HTTP 폴링 건너뜀
  ...
}

// onmessage status:  _wsLive = true;
// onclose:           _wsLive = false; setAtemOnline(false);
```

#### 4-2. ATEM dot — WS 끊김 시 stale 표시

**문제**: WS `onclose` 시 WS dot만 빨강, ATEM dot은 마지막 상태(초록) 유지.
서버/ATEM 모두 알 수 없는 상황인데 ATEM dot이 정상처럼 보임.

**해결**: `onclose` 에 `setAtemOnline(false)` / `setAdminAtemOnline(false)` 추가.

#### 4-3. `savePreset()` race 조건 최소화 (`ui.js`)

**문제**: `GET /status` → (네트워크 왕복) → `POST /presets` 사이에 다른 클라이언트가 상태 변경 가능.

**해결**: WS로 이미 최신 상태를 받아 `lastStatus` 에 캐시되어 있으므로 HTTP 요청 없이 재사용.
```javascript
const status = lastStatus ?? await call('GET', '/status');
```

#### 4-4. `admin/reload` — 패널 즉시 갱신

**문제**: `POST /admin/reload` 후 패널 클라이언트가 10초 타이머까지 프리셋 목록 미갱신.

**해결**: `notify_reload()` 브로드캐스트 → 클라이언트 `reload` 핸들러에서 `loadPresets()` 즉시 호출.

---

### 변경 파일 요약

| 파일 | 유형 | 내용 |
|------|------|------|
| `config.py` | 수정 | `SOURCE_NAMES` 추가 |
| `model/preset.py` | 수정 | `confirm: bool = False` |
| `model/state.py` | 수정 | `atem_connected: bool`, `to_dict()` 포함 |
| `service/atem_service.py` | 수정 | `sync_from_device()` 연결 상태 개선, `prev_connected` 패턴 |
| `service/ws_manager.py` | 수정 | `_broadcast()` 헬퍼, `notify_log()`, `notify_count()` lazy, `notify_reload()`, `create_task` |
| `router/ws.py` | 수정 | 클라이언트 ID/IP, `welcome`, `notify_count()` 순서 |
| `router/system.py` | 수정 | `GET /sources`, `POST /admin/reload`, `notify_log()` |
| `router/switching.py` | 수정 | `notify_log()` IP 포함 |
| `static/atem_ui.html` | 수정 | `#admin-conn`, `.btn.reload` |
| `static/css/ui.css` | 수정 | `#admin-conn` dot, `.btn.reload` |
| `static/css/base.css` | 수정 | `.dot-label` |
| `static/css/panel.css` | 수정 | `#conn-info`, `#log-bar`, `#pgm-bar`, `confirm-pending`, `.pgm-btn:hover` |
| `static/js/ui.js` | 수정 | `_wsLive`, ATEM dot onclose, `savePreset()` lastStatus, reload |
| `static/js/panel.js` | 수정 | `_wsLive`, ATEM dot onclose, PGM active 복원, confirm, `renderPgmBar()`, reload |
| `README.md` | 수정 | SOURCE_NAMES, /sources, /admin/reload, WS 메시지, confirm, atem_connected |
| `RELEASE_NOTES.md` | 수정 | v1.3.0 추가 |

---

## 2026-02-22 (세션 2 — WebSocket + 안정성)

### 개요
WebSocket 실시간 상태 동기화 도입 및 코드 전반 안정성 보완 세션.

---

### 1. WebSocket 도입

#### 배경
패널 페이지에서 프리셋을 실행해도 메인 UI에 상태가 최대 3초 뒤에 반영되는 문제.
HTTP 폴링 주기(3초) 한계.

#### 구현

**`service/ws_manager.py` (신규)**
```python
class WSManager:
    async def _broadcast_state(self):
        from model.state import state
        data = {"type": "status", "data": state.to_dict()}
        await asyncio.gather(*[self._send_one(ws, data) for ws in list(self._clients)],
                             return_exceptions=True)

    def notify(self):
        if not self._loop or not self._loop.is_running():
            return
        self._loop.call_soon_threadsafe(
            asyncio.ensure_future, self._broadcast_state()
        )
```
- `asyncio.gather()`: 모든 클라이언트에 병렬 전송 → 느린 클라이언트가 다른 클라이언트에 영향 없음
- `call_soon_threadsafe`: FastAPI 스레드풀에서도 안전하게 이벤트루프에 작업 예약
- 브로드캐스트 시점에 `state` 싱글톤에서 직접 읽어 데이터 전달 불필요

**`router/ws.py` (신규)**
- `/ws` WebSocket 엔드포인트
- 연결 즉시 현재 상태 전송, `receive_text()` 루프로 연결 유지

**라우터 변경 (`switching.py`, `keyer.py`, `system.py`)**
- `async def` → `def` (await 불필요)
- `await ws_manager.broadcast(...)` → `ws_manager.notify()`

**`main.py`**
- `ws_router` 등록
- lifespan에서 `ws_manager.setup(loop)` 호출 (이벤트루프 캐시)
- sync loop에서도 `ws_manager.notify()` 호출

**클라이언트 (`ui.js`, `panel.js`)**
- 페이지 오픈 시 HTTP로 즉시 상태 조회
- 이후 WebSocket으로 상태 변경 수신
- WebSocket 끊김 시 3초 폴링 폴백 자동 전환

---

### 2. 트러블슈팅: WebSocket 연결 실패

#### 증상
```
WARNING: No supported WebSocket library detected.
INFO:     "GET /ws HTTP/1.1" 404 Not Found
```

#### 원인
Windows에서 `python3`(Microsoft Store)와 `python`(설치된 Python)이 서로 다른 환경.
`pip install uvicorn[standard]`이 `python` 환경에 설치됨.
서버는 `python3`으로 실행 → websockets 없음.

#### 해결
```bash
python3 -m pip install "uvicorn[standard]"
```
항상 `python3 -m pip`를 사용해 실행 환경과 동일한 곳에 설치.

---

### 3. 트러블슈팅: RuntimeError no running event loop

#### 증상
```
RuntimeError: no running event loop
  File "service/ws_manager.py", fire_and_forget()
    asyncio.create_task(self.broadcast(data))
```

#### 원인
FastAPI가 sync 핸들러를 스레드풀에서 실행하므로 그 스레드에는 이벤트루프가 없음.
`asyncio.create_task()`는 현재 실행 중인 루프에서만 호출 가능.

#### 해결 과정
1. 1차: `run_coroutine_threadsafe(coro, loop)` — lifespan에서 루프 캐시
2. 최종: `call_soon_threadsafe(ensure_future, coro)` + state에서 직접 읽는 `notify()` 패턴으로 단순화

---

### 4. 코드 감사 및 안정성 보완

#### 4-1. state.py 스레드 안전성
**문제**: `to_dict()`가 10개 필드를 연속 읽는 도중 다른 스레드가 값을 변경하면 불일치 스냅샷 반환 가능.

**해결**: `threading.RLock` 추가, `to_dict()` / `touch()` / `sync_suppressed()` 락 보호.

#### 4-2. 프리셋 실행 중 중간 상태 브로드캐스트
**문제**: `execute()`가 pgm → pvw → keyer 순서로 여러 명령을 실행하는 동안 sync loop가 중간 상태를 브로드캐스트 가능.

**해결**: `execute()` 진입 시 `state.touch()` 호출해 sync 억제 갱신.

#### 4-3. main.py graceful shutdown
**문제**: `sync_task.cancel()` 후 `await sync_task` 없어 태스크가 완전히 종료되기 전에 프로세스 종료.

**해결**:
```python
sync_task.cancel()
try:
    await sync_task
except asyncio.CancelledError:
    pass
```

#### 4-4. ws.py 에러 로깅
non-disconnect 예외 발생 시 원인을 콘솔에 출력하도록 수정.

#### 4-5. WebSocket 재연결 지수 백오프
**문제**: 서버 장애 시 3초마다 무한 재시도.

**해결** (panel.js, ui.js 공통):
재연결 간격 3s → 6s → 12s → 24s → 최대 30s, 연결 성공 시 초기화.

---

### 변경 파일 요약

| 파일 | 유형 | 내용 |
|------|------|------|
| `service/ws_manager.py` | 신규 | WebSocket 클라이언트 관리, 병렬 브로드캐스트, `notify()` |
| `router/ws.py` | 신규 | `/ws` WebSocket 엔드포인트, 에러 로깅 |
| `model/state.py` | 수정 | `threading.RLock`, `to_dict()` / `touch()` / `sync_suppressed()` 락 보호 |
| `service/preset_service.py` | 수정 | `execute()` 시작 시 `state.touch()` |
| `router/switching.py` | 수정 | `async def` → `def`, `notify()` |
| `router/keyer.py` | 수정 | 동일 |
| `router/system.py` | 수정 | `run_preset` 동일 |
| `main.py` | 수정 | WS 라우터, `ws_manager.setup(loop)`, graceful shutdown |
| `static/js/ui.js` | 수정 | WebSocket 클라이언트, 지수 백오프 |
| `static/js/panel.js` | 수정 | 동일 |
| `README.md` | 수정 | WebSocket 섹션, 설치 주의사항, 파일 구조 |
| `RELEASE_NOTES.md` | 수정 | v1.2.0 추가 |

---

## 2026-02-22 (세션 1 — 초기 감사 및 기능 추가)

### 개요
FastAPI 기반 ATEM Mini 비디오 스위처 컨트롤러의 코드 전반에 대한 감사(audit)와 기능 추가, 버그 수정을 진행한 세션.

---

### 1. 코드 감사 및 초기 버그 수정

#### 이슈
최초 감사에서 발견된 5개 문제:

| # | 위치 | 문제 |
|---|------|------|
| 1 | `static/atem_ui.js` `buildKeyerConfig()` | PiP 저장 시 전역 변수 `pipSrc` 사용 → 실제 장비 상태 `status.pip_src` 와 불일치 |
| 2 | `service/atem_service.py` `sync_from_device()` | 2초마다 콘솔에 디버그 출력 범람 |
| 3 | `service/preset_service.py` `execute()` | `state.mode` 를 `{preset.name} 실행` 으로 덮어써 이후 sync가 이를 다시 장비 상태로 덮어씀 |
| 4 | 루트에 잘못 위치한 `simulator_config.py` | `simulator/` 폴더 내에만 있어야 하는 파일이 루트에 중복 존재 |
| 5 | `controller/atem_controller.py` | 실제 장비에서 `transition_style` 을 읽지 않아 상태 미반영 |

#### 해결
- `buildKeyerConfig()`: `pipSrc` → `status.pip_src` 로 변경
- `sync_from_device()`: 불필요한 `print` 제거, `state.mode` 덮어쓰기 제거
- `atem_controller.py`: `read_device_state()` 에 `transition_style` 조회 추가
- 루트 `simulator_config.py`: 수동 삭제 안내

---

### 2. presets.json 실시간 반영 (Hot Reload)

#### 이슈
`presets.json` 파일을 직접 편집해도 서버 재시작 없이는 UI에 반영되지 않았음.

#### 원인
`PresetService` 가 초기화 시 한 번만 파일을 읽고 이후 메모리 캐시만 사용.

#### 해결 — `service/preset_service.py`
파일 수정 시각(mtime) 기반 hot reload 구현:

```python
def _reload_if_changed(self):
    if os.path.exists(PRESETS_FILE) and os.path.getmtime(PRESETS_FILE) != self._mtime:
        self._load()

def list_presets(self):
    self._reload_if_changed()
    return self._presets

def get_preset(self, preset_id):
    self._reload_if_changed()
    ...
```

`_save()` 후에도 `self._mtime` 을 갱신하여 자체 저장으로 인한 불필요한 재로드 방지.

---

### 3. 프리셋 description 필드 추가

#### 변경 내용
- `model/preset.py`: `Preset`, `PresetCreate` 에 `description: Optional[str] = None` 추가
- `presets.json`: 기존 데이터에 `"description"` 키 추가
- `static/atem_ui.html`: 프리셋 저장 폼에 description 입력 필드 추가
- `static/atem_ui.js`:
  - `savePreset()` 에 `description` 포함
  - 버튼 표시: `name (description)` 형식, hover 시 `label` 툴팁

---

### 4. 프리셋 전용 패널 페이지 (`/panel`)

#### 요구사항
프리셋 버튼만 전체 화면에 1줄로 표시하는 별도 페이지. 수정 기능 없이 실행만 가능.

#### 구현 — `static/preset_panel.html` (신규)
- 전체 화면(`100vh`) flex 레이아웃으로 버튼 균등 배치
- 현재 활성 프리셋 초록색 하이라이트 + glow + 상태 dot
- 3초마다 `/status` 폴링, 10초마다 `/presets` 폴링
- 활성 판단 로직: `pgm` + `keyer_mode` + `pip_src` 3가지 일치 여부

```javascript
function isMatch(p, s) {
  if (p.pgm !== s.pgm) return false;
  const km = p.keyer?.mode ?? 'off';
  if (km !== s.keyer_mode) return false;
  if (km !== 'off' && p.keyer?.source !== s.pip_src) return false;
  return true;
}
```

- `main.py` 에 `/panel` 라우트 추가

---

### 5. 인덱스 페이지 및 홈 버튼

#### 변경 내용
- `static/index.html` (신규): 메인 컨트롤러(`/ui`)와 프리셋 패널(`/panel`) 선택 랜딩 페이지
- `main.py`: `/` 를 `index.html`, `/ui` 를 기존 메인 UI로 라우팅 변경
- 각 페이지 헤더에 HOME 버튼(`<a href="/">HOME</a>`) 추가

---

### 6. 상태 관리 / 타이밍 이슈 보완

#### 발견된 문제들

**① Race Condition — sync vs API 핸들러**
- 배경: 백그라운드 sync가 2초마다 장비 상태를 `state` 에 덮어씀
- 문제: API 핸들러가 `state` 를 변경한 직후 sync가 이를 되돌릴 수 있음

**해결** — `model/state.py`에 억제(suppression) 패턴 추가:
```python
def touch(self):
    """마지막 쓰기 시각 갱신"""
    self._last_write = _time.monotonic()

def sync_suppressed(self, window: float = 1.0) -> bool:
    """마지막 쓰기 후 1초 이내면 sync 건너뜀"""
    return (_time.monotonic() - self._last_write) < window
```
모든 쓰기 서비스 메서드 진입 시 `state.touch()` 호출, `sync_from_device()` 는 `sync_suppressed()` 확인 후 진행.

**② `asyncio.get_event_loop()` deprecated 경고**
- `main.py` 의 `_device_sync_loop()` 에서 `get_event_loop()` 사용
- **해결**: `get_running_loop()` 으로 교체

**③ 프리셋 활성 상태 표시 지연**
- `loadPresets()` 완료 후 `updateStatus()` 가 아직 호출되지 않아 active 상태 미표시
- **해결**: `lastStatus` 변수에 마지막 상태 캐시, `loadPresets()` 후 즉시 `updateActivePreset(lastStatus)` 호출

**④ `fetchStatus()` 에서 `updateStatus()` 이중 호출**
- `call()` 내부에서 이미 `pgm` 필드 감지 시 `updateStatus()` 자동 호출
- `fetchStatus()` 가 추가로 한 번 더 호출하던 문제
- **해결**: `fetchStatus()` 에서 중복 호출 제거

---

### 7. 2차 전반적 보완

#### 발견 및 수정 항목 4가지

**① `preset_service.py` — JSON 파싱 오류 미처리**
- 손상된 `presets.json` 로드 시 예외 전파로 서버 크래시 가능
- **해결**: `try/except` 추가, 오류 시 `self._presets = []` 로 안전 복구

**② `simulator/atem_simulator.py` — 스레드 경쟁 조건 + DVE 버그**

문제 1: `performAutoME()` 에서 상태 스냅샷 없이 스레드 생성
```python
# Before (버그)
def performAutoME(self, me):
    self.state.in_transition = True
    def finish():
        time.sleep(...)
        self.state.pgm = self.state.pvw  # 클로저로 가변 참조
```
문제 2: `setKeyerDVESizeY()` 가 `self.state.dve_size` 에 저장하지 않음 (log만 출력)

**해결**:
```python
def performAutoME(self, me):
    with self._lock:
        self.state.in_transition = True
        rate   = self.state.transition_rate
        src_pg = self.state.pgm       # 진입 시 스냅샷
        src_pv = self.state.pvw

    def finish():
        time.sleep(rate / 30.0)
        with self._lock:
            self.state.pgm = src_pv   # 스냅샷 사용
            self.state.pvw = src_pg
            self.state.in_transition = False

def setKeyerDVESizeY(self, me, keyer, size):
    self.state.dve_size = size        # 누락된 저장 추가
    self._log(f"[DVE SIZE Y] {size}")
```

**③ `atem_ui.js` — innerHTML XSS 취약점**
- 프리셋 목록 렌더링 시 `innerHTML` 에 `p.name`, `p.description` 직접 삽입
- 프리셋 이름에 `<script>` 등 HTML 포함 시 실행 가능
- **해결**: `createElement` + `textContent` 기반 DOM 직접 생성으로 교체

```javascript
// Before (취약)
btn.innerHTML = `<span>${p.name}</span>`;

// After (안전)
const nameEl = document.createElement('span');
nameEl.textContent = p.name;
btn.appendChild(nameEl);
```

**④ `preset_panel.html` — 버튼 중복 클릭 방지 미구현**
- 요청 진행 중 동일 버튼 다중 클릭 시 중복 요청 발생
- **해결**: `runPreset()` 에 guard + `finally` 패턴 추가

```javascript
async function runPreset(id, btn) {
  if (btn.disabled) return;       // 이중 진입 차단
  btn.disabled = true;
  try {
    const res = await fetch(BASE + `/preset/${id}`, { method: 'POST' });
    ...
    flash(btn, res.ok ? 'flash-ok' : 'flash-err');
  } catch (_) {
    flash(btn, 'flash-err');
  } finally {
    btn.disabled = false;         // 성공/실패 모두 복원
  }
}
```
CSS `.p-btn:disabled { opacity: 0.6; cursor: not-allowed; pointer-events: none; }` 추가.

---

### 변경 파일 요약

| 파일 | 변경 유형 | 내용 |
|------|-----------|------|
| `model/state.py` | 수정 | `touch()`, `sync_suppressed()` 추가 |
| `model/preset.py` | 수정 | `description` 필드 추가 |
| `service/atem_service.py` | 수정 | `state.touch()` 호출, sync 억제, `print` 제거 |
| `service/preset_service.py` | 수정 | mtime hot reload, JSON 오류 처리 |
| `controller/atem_controller.py` | 수정 | `transition_style` 읽기 추가 |
| `simulator/atem_simulator.py` | 수정 | `threading.Lock`, DVE Size Y 버그 수정 |
| `main.py` | 수정 | `/` `/ui` `/panel` 라우트, `get_running_loop()`, 기동 로그 |
| `static/atem_ui.html` | 수정 | HOME 버튼, description 입력 필드 |
| `static/atem_ui.js` | 수정 | `lastStatus`, `presets` 캐시, DOM 렌더링, `updateActivePreset()` |
| `static/atem_ui.css` | 수정 | `.btn.preset.active`, `.refresh-btn` 스타일 |
| `static/index.html` | 신규 | 랜딩 페이지 |
| `static/preset_panel.html` | 신규 | 프리셋 전용 패널, 활성 상태 표시, 중복 클릭 방지 |
| `presets.json` | 수정 | `description`, `pvw` 필드 추가 |

---

### 잔여 사항

- 루트 `simulator_config.py` 파일 수동 삭제 필요 (`del i:\dev\atem\simulator_config.py`)
- 실제 ATEM 장비 연결 시 `PyATEMMax.ATEMConst.ATEMKeyerType.luma` 상수명 확인 필요
