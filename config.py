"""
config.py — 런타임 설정값 제공

우선순위: atem.conf (있으면) > 기본값
conf 파일 관리는 conf_manager.py 참고.
"""

from conf_manager import load as _load_conf

import sys as _sys

_cp = _load_conf()

ATEM_IP                = _cp.get('atem',      'ip')
ATEM_PORT              = _cp.getint('atem',   'port')
API_HOST               = _cp.get('server',    'host')
API_PORT               = _cp.getint('server', 'port')
SIMULATOR_MODE         = _cp.getboolean('atem',      'simulator_mode')
TRANSITION_RATE_FRAMES = _cp.getint('switching', 'transition_rate_frames')
DEVICE_SYNC_INTERVAL   = _cp.getint('switching', 'device_sync_interval')
SHOW_CONSOLE           = _cp.getboolean('app', 'show_console')
SOURCE_NAMES           = [
    _cp.get('sources', 'name1'),
    _cp.get('sources', 'name2'),
    _cp.get('sources', 'name3'),
    _cp.get('sources', 'name4'),
]

# ── TCL TV ────────────────────────────────────────────────────
TCL_ENABLED        = _cp.getboolean('tcl', 'enabled')
TCL_PORT           = _cp.getint('tcl', 'port')
TCL_TVS            = [
    {"ip": _cp.get('tcl', f'tv{i}_ip'),   "name": _cp.get('tcl', f'tv{i}_name')}
    for i in range(1, 4)
]
TCL_INPUT_NAMES    = [_cp.get('tcl', f'input{i}_name') for i in range(1, 5)]
TCL_INPUT_COMMANDS = [_cp.get('tcl', f'input{i}_cmd')  for i in range(1, 5)]


def apply_console_visibility(show: bool) -> None:
    """EXE 실행 시 콘솔 창 표시/숨김 (Windows, frozen 환경에서만 동작)."""
    if _sys.platform != 'win32' or not getattr(_sys, 'frozen', False):
        return
    try:
        import ctypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 1 if show else 0)
    except Exception:
        pass


def reload() -> None:
    """atem.conf 변경 사항을 서버 재시작 없이 런타임에 반영.
    재시작 필요 항목: SIMULATOR_MODE, API_HOST, API_PORT"""
    global ATEM_IP, ATEM_PORT, TRANSITION_RATE_FRAMES, DEVICE_SYNC_INTERVAL, SHOW_CONSOLE, SOURCE_NAMES
    cp = _load_conf()
    ATEM_IP                = cp.get('atem',      'ip')
    ATEM_PORT              = cp.getint('atem',   'port')
    TRANSITION_RATE_FRAMES = cp.getint('switching', 'transition_rate_frames')
    DEVICE_SYNC_INTERVAL   = cp.getint('switching', 'device_sync_interval')
    SHOW_CONSOLE           = cp.getboolean('app', 'show_console')
    SOURCE_NAMES           = [
        cp.get('sources', 'name1'),
        cp.get('sources', 'name2'),
        cp.get('sources', 'name3'),
        cp.get('sources', 'name4'),
    ]
    global TCL_ENABLED, TCL_PORT, TCL_TVS, TCL_INPUT_NAMES, TCL_INPUT_COMMANDS
    TCL_ENABLED        = cp.getboolean('tcl', 'enabled')
    TCL_PORT           = cp.getint('tcl', 'port')
    TCL_TVS            = [
        {"ip": cp.get('tcl', f'tv{i}_ip'), "name": cp.get('tcl', f'tv{i}_name')}
        for i in range(1, 4)
    ]
    TCL_INPUT_NAMES    = [cp.get('tcl', f'input{i}_name') for i in range(1, 5)]
    TCL_INPUT_COMMANDS = [cp.get('tcl', f'input{i}_cmd')  for i in range(1, 5)]
    apply_console_visibility(SHOW_CONSOLE)
