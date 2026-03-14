# controller/tcl_controller.py
"""TCL TV Android TV Remote 프로토콜 제어 컨트롤러.

androidtvremote2 라이브러리 사용 (포트 6466/6467).
개발자 옵션 불필요 — TV에 PIN 입력으로 1회 페어링 후 자동 연결.

연결은 서버 세션 동안 유지됩니다 (매 명령마다 재연결하지 않음).

페어링 흐름:
  1. POST /tcl/pair/start {"tv": 1}  →  TV 화면에 PIN 표시
  2. POST /tcl/pair/finish {"tv": 1, "pin": "123456"}  →  페어링 완료
"""

import asyncio
import os
import logging
from conf_manager import BASE_DIR

logger      = logging.getLogger("atem.tcl")
CERT_FILE   = os.path.join(BASE_DIR, 'tcl_cert.pem')
KEY_FILE    = os.path.join(BASE_DIR, 'tcl_key.pem')
CLIENT_NAME = "ATEM Controller"

# TV별 persistent 연결 풀 (ip → AndroidTVRemote)
_pool:   dict[str, object]         = {}
_ready:  dict[str, asyncio.Event]  = {}

# 진행 중인 페어링 세션 (ip → AndroidTVRemote)
_pairing_sessions: dict[str, object] = {}


def _make_remote(ip: str, api_port: int = 6466, pair_port: int = 6467):
    from androidtvremote2 import AndroidTVRemote
    return AndroidTVRemote(
        CLIENT_NAME, CERT_FILE, KEY_FILE, ip,
        api_port=api_port, pair_port=pair_port,
    )


async def _ensure_cert():
    r = _make_remote("0.0.0.0")
    await r.async_generate_cert_if_missing()


async def _connect(ip: str, port: int):
    """TV에 persistent 연결 수립. 이미 연결되어 있으면 재사용."""
    if ip in _pool:
        return _pool[ip], _ready[ip]

    print(f"[TCL] 연결 중... ({ip}:{port})", flush=True)
    remote = _make_remote(ip, api_port=port)
    await remote.async_generate_cert_if_missing()

    ev = asyncio.Event()
    _ready[ip] = ev

    def _on_available(available: bool):
        if available:
            ev.set()
            print(f"[TCL] TV 준비 완료 ({ip})", flush=True)
        else:
            ev.clear()
            print(f"[TCL] TV 연결 끊김 ({ip})", flush=True)

    remote.add_is_available_updated_callback(_on_available)

    await remote.async_connect()
    _pool[ip] = remote
    print(f"[TCL] 연결 성공 ({ip})", flush=True)
    ev.set()  # 초기 연결 성공 → 즉시 available 표시
    remote.keep_reconnecting()  # 끊기면 자동 재연결 (메서드 호출)
    return remote, ev


def _drop(ip: str):
    """연결 풀에서 제거."""
    remote = _pool.pop(ip, None)
    _ready.pop(ip, None)
    if remote:
        try:
            remote.disconnect()
        except Exception:
            pass


async def send_command(ip: str, port: int, keycode: str) -> tuple[bool, str]:
    """Android TV Remote 프로토콜로 키 이벤트 전송."""
    try:
        remote, ev = await _connect(ip, port)
        print(f"[TCL] TV 준비 대기 중... TV 화면에 '연결 허용?' 팝업이 표시되면 허용하세요 ({ip})", flush=True)
        await asyncio.wait_for(ev.wait(), timeout=30.0)
        print(f"[TCL] 키 전송: {keycode} → {ip}", flush=True)
        remote.send_key_command(keycode)
        await asyncio.sleep(0.4)
        print(f"[TCL] OK → {keycode} ({ip})", flush=True)
        logger.info("[TCL] OK → %r (%s)", keycode, ip)
        return True, "OK"
    except asyncio.TimeoutError:
        detail = f"TV 준비 타임아웃 ({ip}) — TV 화면에서 연결 허용 팝업을 확인하세요"
        print(f"[TCL] ERROR: {detail}", flush=True)
        logger.error("[TCL] %s", detail)
        _drop(ip)
        return False, detail
    except Exception as e:
        detail = f"{type(e).__name__}: {e}"
        print(f"[TCL] ERROR: {detail}", flush=True)
        logger.error("[TCL] 실패 (%s) %r: %s", ip, keycode, detail)
        _drop(ip)
        return False, detail


async def start_pairing(ip: str, pair_port: int = 6467) -> None:
    """페어링 시작 — TV 화면에 PIN이 표시됨."""
    _pairing_sessions.pop(ip, None)
    _drop(ip)   # 기존 연결 정리
    remote = _make_remote(ip, pair_port=pair_port)
    await remote.async_generate_cert_if_missing()
    await remote.async_start_pairing()
    _pairing_sessions[ip] = remote
    print(f"[TCL] 페어링 시작: {ip}", flush=True)


async def finish_pairing(ip: str, pin: str) -> None:
    """PIN 입력으로 페어링 완료."""
    remote = _pairing_sessions.get(ip)
    if not remote:
        raise ValueError("페어링 세션 없음. 먼저 시작하세요.")
    try:
        await remote.async_finish_pairing(pin)
        print(f"[TCL] 페어링 완료: {ip}", flush=True)
        logger.info("[TCL] 페어링 완료: %s", ip)
    finally:
        try:
            remote.disconnect()
        except Exception:
            pass
        _pairing_sessions.pop(ip, None)


async def ping(ip: str, port: int = 6466) -> bool:
    """TCP 포트 응답 확인."""
    import socket
    loop = asyncio.get_event_loop()
    def _check():
        try:
            with socket.create_connection((ip, port), timeout=2.0):
                return True
        except OSError:
            return False
    return await loop.run_in_executor(None, _check)
