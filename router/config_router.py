"""설정 파일(atem.conf) 조회 / 저장 / 삭제 API"""

import os
from typing import List
from fastapi import APIRouter
from pydantic import BaseModel, Field
from conf_manager import load, save_conf, delete_conf, CONF_PATH

router = APIRouter(prefix="/api/config", tags=["Config"])


class ConfigBody(BaseModel):
    atem_ip:                str
    atem_port:              int   = Field(ge=1,   le=65535)
    simulator_mode:         bool
    api_port:               int   = Field(ge=1,   le=65535)
    transition_rate_frames: int   = Field(ge=1,   le=300)
    device_sync_interval:   int   = Field(ge=1,   le=60)
    show_console:           bool  = True
    source_names:           List[str]


# ── 현재 설정 조회 ────────────────────────────────────────────────
@router.get("")
def get_config():
    """현재 적용 중인 설정값 반환 (conf 파일 없으면 기본값)."""
    cp = load()
    return {
        "atem_ip":                cp.get('atem',      'ip'),
        "atem_port":              cp.getint('atem',   'port'),
        "simulator_mode":         cp.getboolean('atem', 'simulator_mode'),
        "api_port":               cp.getint('server', 'port'),
        "transition_rate_frames": cp.getint('switching', 'transition_rate_frames'),
        "device_sync_interval":   cp.getint('switching', 'device_sync_interval'),
        "show_console":           cp.getboolean('app', 'show_console'),
        "source_names": [
            cp.get('sources', 'name1'),
            cp.get('sources', 'name2'),
            cp.get('sources', 'name3'),
            cp.get('sources', 'name4'),
        ],
        "conf_file":   CONF_PATH,
        "conf_exists": os.path.exists(CONF_PATH),
    }


# ── 설정 저장 ────────────────────────────────────────────────────
@router.post("")
def post_config(body: ConfigBody):
    """설정값을 atem.conf에 저장. 대부분 즉시 반영됨 (simulator_mode/api_port는 재시작 필요)."""
    save_conf({
        'atem': {
            'ip':             body.atem_ip,
            'port':           str(body.atem_port),
            'simulator_mode': str(body.simulator_mode).lower(),
        },
        'server': {
            'host': '0.0.0.0',
            'port': str(body.api_port),
        },
        'switching': {
            'transition_rate_frames': str(body.transition_rate_frames),
            'device_sync_interval':   str(body.device_sync_interval),
        },
        'app': {
            'show_console': str(body.show_console).lower(),
        },
        'sources': {f'name{i + 1}': body.source_names[i] for i in range(4)},
    })
    import config as _config
    _config.reload()
    return {"ok": True, "conf_file": CONF_PATH}


# ── 설정 파일 삭제 (기본값 복원) ──────────────────────────────────
@router.delete("")
def del_config():
    """atem.conf 삭제. 재시작 후 기본값이 적용됨."""
    delete_conf()
    return {"ok": True}
