from fastapi import APIRouter
from model.request import SourceInput, PiPConfig, PiPMove
from model.state import state
from service.atem_service import atem_service
from service.ws_manager import ws_manager

router = APIRouter(prefix="/key", tags=["Keyer"])


@router.post("/up")
def key_up(body: SourceInput):
    """업스트림 키어 ON"""
    atem_service.key_up(body.source)
    result = {"ok": True, **state.to_dict()}
    ws_manager.notify()
    return result


@router.post("/pip")
def pip_on(body: PiPConfig):
    """PiP ON"""
    atem_service.pip_on(body.source, body.size, body.pos_x, body.pos_y)
    result = {"ok": True, **state.to_dict()}
    ws_manager.notify()
    return result


@router.post("/pip/move")
def pip_move(body: PiPMove):
    """PiP 위치만 변경 (이미 on-air 상태)"""
    atem_service.move_pip(body.pos_x, body.pos_y)
    result = {"ok": True, **state.to_dict()}
    ws_manager.notify()
    return result


@router.post("/off")
def key_off():
    """키어 OFF"""
    atem_service.key_off()
    result = {"ok": True, **state.to_dict()}
    ws_manager.notify()
    return result
