from fastapi import APIRouter, Request
from model.request import SourceInput, TransitionStyleInput
from model.state import state
from service.atem_service import atem_service
from service.ws_manager import ws_manager

router = APIRouter(prefix="/switching", tags=["Switching"])


@router.post("/pgm")
def direct_pgm(body: SourceInput, req: Request):
    """PGM 직접 CUT 출력"""
    atem_service.direct_pgm(body.source)
    result = {"ok": True, **state.to_dict()}
    ws_manager.notify()
    ws_manager.notify_log(f"소스{body.source} PGM  [{req.client.host}]")
    return result


@router.post("/pvw")
def set_pvw(body: SourceInput):
    """PVW 소스 선택"""
    atem_service.set_pvw(body.source)
    result = {"ok": True, **state.to_dict()}
    ws_manager.notify()
    return result


@router.post("/cut")
def do_cut(req: Request):
    """CUT 전환"""
    atem_service.cut()
    result = {"ok": True, **state.to_dict()}
    ws_manager.notify()
    ws_manager.notify_log(f"CUT 전환  [{req.client.host}]")
    return result


@router.post("/auto")
def do_auto(req: Request):
    """AUTO 전환"""
    atem_service.auto()
    result = {"ok": True, **state.to_dict()}
    ws_manager.notify()
    ws_manager.notify_log(f"AUTO 전환  [{req.client.host}]")
    return result


@router.post("/style")
def set_style(body: TransitionStyleInput):
    """트랜지션 스타일 설정"""
    atem_service.set_transition_style(body.style)
    result = {"ok": True, **state.to_dict()}
    ws_manager.notify()
    return result
