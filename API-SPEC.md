# ATEM Controller — API 명세

Base URL: `http://<host>:8000`

---

## 공통

### StatusObject (상태 응답 공통 구조)

대부분의 POST 요청은 처리 후 현재 상태를 함께 반환합니다.

```json
{
  "ok": true,
  "pgm": 1,
  "pvw": 2,
  "pip_src": 1,
  "mode": "대기중",
  "keyer_mode": "off",
  "dve_size": 0.25,
  "dve_pos_x": 12.0,
  "dve_pos_y": 7.0,
  "last_transition": "",
  "transition_style": "MIX",
  "atem_connected": false
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `pgm` | int | 현재 PGM 소스 (1~4) |
| `pvw` | int | 현재 PVW 소스 (1~4) |
| `pip_src` | int | 키어/PiP 소스 (1~4) |
| `mode` | string | 마지막 동작 설명 |
| `keyer_mode` | `"off"` \| `"keyup"` \| `"pip"` | 키어 상태 |
| `dve_size` | float (0~1) | DVE 크기 |
| `dve_pos_x` | float (-16~16) | DVE X 위치 |
| `dve_pos_y` | float (-9~9) | DVE Y 위치 |
| `last_transition` | `""` \| `"CUT"` \| `"AUTO"` | 마지막 전환 방식 |
| `transition_style` | `"MIX"` \| `"DIP"` \| `"WIPE"` \| `"STING"` | 트랜지션 스타일 |
| `atem_connected` | bool | ATEM 장비 연결 여부 |

> ATEM 미연결 상태에서도 명령은 정상 응답합니다. 내부 상태만 업데이트되고 장비 명령은 무시됩니다.

---

## 상태 조회

### `GET /status`

현재 상태 조회.

**응답:** StatusObject (`ok` 필드 제외)

---

## 소스

### `GET /sources`

소스 이름 목록 조회.

**응답:**
```json
{ "sources": ["소스1(Camera)", "소스2(PPT)", "소스3(없음)", "소스4(없음)"] }
```

---

## 전환 (Switching)

### `POST /switching/pgm`

PGM 소스 직접 CUT 출력.

**요청:**
```json
{ "source": 2 }
```

| 필드 | 타입 | 제약 |
|------|------|------|
| `source` | int | 1~4 |

**응답:** StatusObject

---

### `POST /switching/pvw`

PVW 소스 선택.

**요청:**
```json
{ "source": 1 }
```

**응답:** StatusObject

---

### `POST /switching/cut`

CUT 전환 (PGM ↔ PVW 교환).

**요청:** 없음

**응답:** StatusObject

---

### `POST /switching/auto`

AUTO 전환 (설정된 스타일/속도로 PGM ↔ PVW 전환).

**요청:** 없음

**응답:** StatusObject

---

### `POST /switching/style`

트랜지션 스타일 변경.

**요청:**
```json
{ "style": "WIPE" }
```

| 값 | 설명 |
|----|------|
| `"MIX"` | 믹스 |
| `"DIP"` | 딥 |
| `"WIPE"` | 와이프 |
| `"STING"` | 스팅 |

**응답:** StatusObject

---

## 키어 (Keyer)

### `POST /key/up`

업스트림 키어 ON (루마키, 풀사이즈 오버레이).

**요청:**
```json
{ "source": 2 }
```

| 필드 | 타입 | 제약 |
|------|------|------|
| `source` | int | 1~4 |

**응답:** StatusObject

---

### `POST /key/pip`

PiP (DVE 키어) ON.

**요청:**
```json
{
  "source": 1,
  "size": 0.25,
  "pos_x": 12.0,
  "pos_y": 7.0
}
```

| 필드 | 타입 | 기본값 | 제약 |
|------|------|--------|------|
| `source` | int | — | 1~4 |
| `size` | float | `0.25` | 0.0~1.0 |
| `pos_x` | float | `12.0` | -16.0~16.0 |
| `pos_y` | float | `7.0` | -9.0~9.0 |

**응답:** StatusObject

---

### `POST /key/pip/move`

PiP 위치만 이동 (소스 및 크기 변경 없음).

**요청:**
```json
{
  "pos_x": -12.0,
  "pos_y": 7.0
}
```

| 필드 | 타입 | 제약 |
|------|------|------|
| `pos_x` | float | -16.0~16.0 |
| `pos_y` | float | -9.0~9.0 |

**응답:** StatusObject

---

### `POST /key/off`

키어 OFF.

**요청:** 없음

**응답:** StatusObject

---

## 프리셋

### `GET /presets`

프리셋 목록 조회.

**응답:**
```json
{
  "presets": [
    {
      "id": 1,
      "name": "크로마키",
      "label": "PGM:소스1 / KEY UP:소스2",
      "description": "기본 사용",
      "pgm": 1,
      "pvw": 2,
      "keyer": {
        "mode": "keyup",
        "source": 2,
        "size": 0.25,
        "pos_x": 12.0,
        "pos_y": 7.0
      },
      "confirm": false
    }
  ]
}
```

---

### `POST /presets`

프리셋 저장.

**요청:**
```json
{
  "name": "내 프리셋",
  "label": "PGM:소스1 / KEY:소스2",
  "description": "설명 (선택)",
  "pgm": 1,
  "pvw": 2,
  "keyer": {
    "mode": "keyup",
    "source": 2
  },
  "confirm": false
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `name` | string | ✅ | 표시 이름 |
| `label` | string | — | 요약 레이블 |
| `description` | string \| null | — | 부가 설명 |
| `pgm` | int (1~4) | ✅ | PGM 소스 |
| `pvw` | int (1~4) | — | PVW 소스 |
| `keyer.mode` | `"keyup"` \| `"pip"` \| `"off"` | — | 키어 모드 |
| `keyer.source` | int (1~4) | — | 키어 소스 |
| `keyer.size` | float (0~1) | — | DVE 크기 (pip 전용) |
| `keyer.pos_x` | float (-16~16) | — | DVE X 위치 (pip 전용) |
| `keyer.pos_y` | float (-9~9) | — | DVE Y 위치 (pip 전용) |
| `confirm` | bool | — | true = 두 번 클릭 필요 |

**응답:**
```json
{ "ok": true, "preset": { ...Preset } }
```

---

### `DELETE /presets/{preset_id}`

프리셋 삭제.

**응답:**
```json
{ "ok": true }
```

**오류:** `404` — 존재하지 않는 프리셋

---

### `POST /preset/{preset_id}`

프리셋 실행 (PGM/키어 상태 적용).

**응답:** StatusObject

**오류:** `404` — 존재하지 않는 프리셋, `500` — 실행 실패

---

## 관리 (Admin)

### `POST /admin/connect`

ATEM 장비 수동 재연결 (10초 타임아웃 1회 시도).

**응답 (성공):** StatusObject + `"ok": true`

**응답 (실패):**
```json
{ "ok": false, "error": "연결 타임아웃 (10초)", ...StatusObject }
```

---

### `POST /admin/restart`

서버 프로세스 재시작 (0.5초 후 실행).

**응답:**
```json
{ "ok": true }
```

---

### `POST /admin/reload`

프리셋 파일 핫리로드 + WebSocket 클라이언트에 reload 이벤트 전송.

**응답:**
```json
{ "ok": true, "count": 2 }
```

---

## TCL TV 제어

TCL TV 입력 소스 전환 및 페어링.

> `TCL_ENABLED = True`일 때만 동작합니다.

> **모델 호환성 — 65P635 / 75P635**
> 이 모델은 Google TV 기반으로 `androidtvremote2` 프로토콜이 홈 화면 이동만 지원합니다.
> `KEYCODE_TV_INPUT_HDMI_*` 키코드는 **동작하지 않으며**, API 응답은 성공(`ok: true`)으로
> 오지만 TV 화면이 변경되지 않습니다. 입력 전환이 필요하면 다른 모델을 사용하세요.

### `POST /tcl/input`

특정 TV 입력 소스 전환.

**요청:**
```json
{ "tv": 1, "input": 2 }
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `tv` | int (1-based) | TV 번호 |
| `input` | int (1-based) | 입력 소스 번호 |

**응답:**
```json
{ "ok": true, "tv": 1, "input": 2 }
```

**응답 (실패):**
```json
{ "ok": false, "tv": 1, "input": 2, "detail": "연결 실패 메시지" }
```

---

### `POST /tcl/input/all`

전체 TV 입력 소스 일괄 전환.

**요청:**
```json
{ "input": 2 }
```

**응답:**
```json
{
  "results": [
    { "ok": true, "tv": 1, "input": 2 },
    { "ok": false, "tv": 2, "input": 2, "detail": "..." }
  ]
}
```

---

### `GET /tcl/status`

TCL TV 상태 및 설정 조회.

---

### `POST /tcl/pair/start`

TV 페어링 시작 (TV 화면에 PIN 표시).

**요청:**
```json
{ "tv": 1 }
```

**응답:**
```json
{ "ok": true, "tv": 1, "message": "TV 화면의 PIN을 입력하세요" }
```

---

### `POST /tcl/pair/finish`

TV 페어링 완료 (PIN 입력).

**요청:**
```json
{ "tv": 1, "pin": "123456" }
```

**응답:**
```json
{ "ok": true, "tv": 1 }
```

---

## 설정 (Config)

### `GET /api/config`

현재 설정값 조회.

**응답:**
```json
{
  "atem_ip": "192.168.0.240",
  "atem_port": 9910,
  "simulator_mode": false,
  "api_port": 8000,
  "transition_rate_frames": 15,
  "device_sync_interval": 1,
  "show_console": false,
  "source_names": ["소스1(Camera)", "소스2(PPT)", "소스3(없음)", "소스4(없음)"],
  "tcl_enabled": false,
  "tcl_port": 6466,
  "tcl_tvs": [
    { "ip": "", "name": "TV 1" },
    { "ip": "", "name": "TV 2" },
    { "ip": "", "name": "TV 3" }
  ],
  "tcl_input_names": ["HDMI 1", "HDMI 2", "HDMI 3", "HDMI 4"],
  "tcl_input_cmds": [
    "KEYCODE_TV_INPUT_HDMI_1",
    "KEYCODE_TV_INPUT_HDMI_2",
    "KEYCODE_TV_INPUT_HDMI_3",
    "KEYCODE_TV_INPUT_HDMI_4"
  ],
  "conf_file": "C:\\Program Files\\Atem Controller\\atem.conf",
  "conf_exists": true
}
```

---

### `POST /api/config`

설정 저장 및 즉시 반영 가능한 항목 적용.

| 필드 | 즉시 반영 | 제약 | 설명 |
|------|-----------|------|------|
| `atem_ip` | ⚡ | — | ATEM IP 주소 |
| `atem_port` | ⚡ | 1~65535 | ATEM UDP 포트 |
| `transition_rate_frames` | ⚡ | 1~300 | AUTO 전환 속도 (프레임) |
| `device_sync_interval` | ⚡ | 1~60 | 장비 상태 동기화 주기 (초) |
| `show_console` | ⚡ | — | 콘솔 창 표시 (EXE 환경만) |
| `source_names` | ⚡ | 4개 배열 | 소스 이름 |
| `tcl_enabled` | ⚡ | — | TCL TV 제어 활성화 |
| `tcl_port` | ⚡ | 1~65535 | TCL TLS 포트 |
| `tcl_tvs` | ⚡ | 배열 | TV 목록 (ip, name) |
| `tcl_input_names` | ⚡ | 4개 배열 | 입력 소스 이름 |
| `tcl_input_cmds` | ⚡ | 4개 배열 | 입력 전환 키코드 |
| `simulator_mode` | 🔄 재시작 필요 | — | 시뮬레이터 모드 |
| `api_port` | 🔄 재시작 필요 | 1~65535 | 서버 포트 |

**응답:**
```json
{ "ok": true, "conf_file": "..." }
```

---

### `DELETE /api/config`

설정 파일(`atem.conf`) 삭제. 재시작 후 기본값 적용.

**응답:**
```json
{ "ok": true }
```

---

## WebSocket

### `WS /ws`

실시간 상태 스트림.

**수신 메시지 타입:**

#### `welcome` — 연결 시 1회
```json
{
  "type": "welcome",
  "ip": "192.168.10.5",
  "id": "a1b2c3",
  "ws_count": 2
}
```

#### `status` — 상태 변경 시
```json
{
  "type": "status",
  "data": { ...StatusObject },
  "ws_count": 2
}
```

#### `log` — 동작 로그
```json
{
  "type": "log",
  "ts": "12:34:56",
  "msg": "소스2 PGM  [192.168.10.5]"
}
```

#### `count` — 접속자 수 변경
```json
{ "type": "count", "n": 3 }
```

#### `reload` — 프리셋 핫리로드 알림
```json
{ "type": "reload" }
```

---

## 페이지 라우트

| URL | 파일 | 설명 |
|-----|------|------|
| `GET /` | `preset_panel.html` | 프리셋 패널 (기본 화면) |
| `GET /ui` | `atem_ui.html` | 메인 컨트롤 UI |
| `GET /panel` | `preset_panel.html` | 프리셋 패널 |
| `GET /config` | `config.html` | 설정 페이지 |
| `GET /menu` | `index.html` | 메뉴 페이지 |
