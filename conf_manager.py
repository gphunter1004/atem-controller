"""
conf_manager.py — 설정 파일(atem.conf) 읽기/쓰기 관리

우선순위:
  1. exe/스크립트와 같은 디렉토리의 atem.conf
  2. 없으면 아래 _DEFAULTS 기본값 사용

런타임 경로:
  BASE_DIR     — exe 모드: exe와 같은 디렉토리 / 개발 모드: 프로젝트 루트
  CONF_PATH    — atem.conf 전체 경로
  PRESETS_FILE — presets.json 전체 경로 (preset_service가 사용)
"""

import sys
import os
import configparser


def _exe_dir() -> str:
    """exe 모드: exe 파일 디렉토리. 개발 모드: 스크립트 디렉토리."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _base_dir() -> str:
    """conf/presets 파일 위치 결정.
    1. CWD에 atem.conf가 있으면 → CWD 사용 (수동 실행 시 오버라이드 가능)
    2. 없으면 → exe/스크립트 디렉토리 (기본, 최초 실행 시 여기에 생성)
    """
    exe_dir = _exe_dir()
    cwd = os.getcwd()
    if cwd != exe_dir and os.path.exists(os.path.join(cwd, 'atem.conf')):
        return cwd
    return exe_dir


BASE_DIR     = _base_dir()
CONF_PATH    = os.path.join(BASE_DIR, 'atem.conf')
PRESETS_FILE = os.path.join(BASE_DIR, 'presets.json')

# ── 기본값 ────────────────────────────────────────────────────────
_DEFAULTS: dict[str, dict[str, str]] = {
    'atem': {
        'ip':             '192.168.0.240',
        'port':           '9910',
        'simulator_mode': 'false',
    },
    'server': {
        'host': '0.0.0.0',
        'port': '8000',
    },
    'switching': {
        'transition_rate_frames': '15',
        'device_sync_interval':   '1',
    },
    'app': {
        'show_console': 'false',
    },
    'sources': {
        'name1': '소스1(Camera)',
        'name2': '소스2(PPT)',
        'name3': '소스3(없음)',
        'name4': '소스4(없음)',
    },
    'tcl': {
        'enabled':      'false',
        'port':         '6466',
        'tv1_ip':       '',
        'tv1_name':     'TV 1',
        'tv2_ip':       '',
        'tv2_name':     'TV 2',
        'tv3_ip':       '',
        'tv3_name':     'TV 3',
        'input1_name':  'HDMI 1',
        'input1_cmd':   'KEYCODE_TV_INPUT_HDMI_1',
        'input2_name':  'HDMI 2',
        'input2_cmd':   'KEYCODE_TV_INPUT_HDMI_2',
        'input3_name':  'HDMI 3',
        'input3_cmd':   'KEYCODE_TV_INPUT_HDMI_3',
        'input4_name':  'HDMI 4',
        'input4_cmd':   'KEYCODE_TV_INPUT_HDMI_4',
    },
}


def _make_parser() -> configparser.ConfigParser:
    """기본값이 채워진 ConfigParser 생성."""
    cp = configparser.ConfigParser()
    for section, values in _DEFAULTS.items():
        cp[section] = dict(values)
    return cp


def load() -> configparser.ConfigParser:
    """기본값 로드 후 atem.conf가 있으면 오버라이드."""
    cp = _make_parser()
    if os.path.exists(CONF_PATH):
        cp.read(CONF_PATH, encoding='utf-8')
    return cp


def save_conf(body: dict) -> None:
    """설정 딕셔너리를 atem.conf에 저장."""
    cp = _make_parser()
    for section, kv in body.items():
        if section not in cp:
            cp.add_section(section)
        for k, v in kv.items():
            cp[section][k] = str(v)
    with open(CONF_PATH, 'w', encoding='utf-8') as f:
        cp.write(f)


def delete_conf() -> bool:
    """atem.conf 삭제 (기본값으로 복원). 삭제 성공 시 True."""
    if os.path.exists(CONF_PATH):
        os.remove(CONF_PATH)
        return True
    return False


def init_conf_if_missing() -> None:
    """conf 파일이 없으면 기본값으로 atem.conf 생성 (최초 실행 시 1회)."""
    if not os.path.exists(CONF_PATH):
        save_conf({})


def init_presets_if_missing() -> None:
    """번들에 포함된 presets.json을 BASE_DIR에 복사 (없는 경우에만)."""
    if os.path.exists(PRESETS_FILE):
        return
    if getattr(sys, 'frozen', False):
        bundled = os.path.join(sys._MEIPASS, 'presets.json')
        if os.path.exists(bundled):
            import shutil
            shutil.copy2(bundled, PRESETS_FILE)
