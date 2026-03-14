import os
import sys
import asyncio
import subprocess
import threading
import time
from fastapi import APIRouter, HTTPException, Request
from model.state import state
from model.preset import PresetCreate
from service.preset_service import preset_service
from service.ws_manager import ws_manager

router = APIRouter(tags=["System"])


# ── 소스 이름 ───────────────────────────────────
@router.get("/sources")
def get_sources():
    import config
    return {"sources": config.SOURCE_NAMES}


# ── 프리셋 목록 ────────────────────────────────
@router.get("/presets")
def list_presets():
    return {"presets": preset_service.list_presets()}


# ── 프리셋 추가 ────────────────────────────────
@router.post("/presets")
def add_preset(body: PresetCreate):
    preset = preset_service.add_preset(body)
    return {"ok": True, "preset": preset}


# ── 프리셋 삭제 ────────────────────────────────
@router.delete("/presets/{preset_id}")
def delete_preset(preset_id: int):
    if not preset_service.delete_preset(preset_id):
        raise HTTPException(status_code=404, detail="존재하지 않는 프리셋")
    return {"ok": True}


# ── 프리셋 실행 ────────────────────────────────
@router.post("/preset/{preset_id}")
def run_preset(preset_id: int, req: Request):
    preset = preset_service.get_preset(preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail="존재하지 않는 프리셋")
    try:
        preset_service.execute(preset)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"프리셋 실행 실패: {e}")
    result = {"ok": True, **state.to_dict()}
    ws_manager.notify()
    ws_manager.notify_log(f"{preset.name} 실행  [{req.client.host}]")
    return result


# ── 상태 조회 ──────────────────────────────────
@router.get("/status")
def get_status():
    return state.to_dict()


# ── 서버 재시작 ────────────────────────────────
@router.post("/admin/restart")
def admin_restart():
    def _do_restart():
        time.sleep(0.5)
        args = [sys.executable] if getattr(sys, 'frozen', False) else [sys.executable] + sys.argv
        subprocess.Popen(args)
        os._exit(0)
    threading.Thread(target=_do_restart, daemon=True).start()
    return {"ok": True}


# ── 프리셋 핫리로드 ────────────────────────────
@router.post("/admin/reload")
def admin_reload():
    preset_service._load()
    ws_manager.notify_reload()
    return {"ok": True, "count": len(preset_service.list_presets())}



# ── ATEM 수동 재연결 ────────────────────────────
@router.post("/admin/connect")
async def admin_connect():
    """ATEM 장비에 수동 재연결 (10초 타임아웃 1회 시도).
    실패 시 ok=False와 error 메시지 반환."""
    from controller.atem_controller import atem
    from service.atem_service import atem_service

    loop = asyncio.get_running_loop()
    try:
        await asyncio.wait_for(
            loop.run_in_executor(None, atem.connect),
            timeout=10.0,
        )
        atem.init_defaults()
        state.transition_style = "MIX"
        atem_service.sync_from_device()
        ws_manager.notify()
        return {"ok": True, **state.to_dict()}
    except asyncio.TimeoutError:
        return {"ok": False, "error": "연결 타임아웃 (10초)", **state.to_dict()}
    except Exception as e:
        return {"ok": False, "error": str(e), **state.to_dict()}

