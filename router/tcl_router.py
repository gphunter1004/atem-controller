# router/tcl_router.py
"""TCL TV 입력 전환 + 페어링 API"""

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from service.tcl_service import tcl_service
from service.ws_manager import ws_manager

router = APIRouter(prefix="/tcl", tags=["TCL TV"])


class InputBody(BaseModel):
    tv:    int = Field(ge=1, description="TV 번호 (1-based)")
    input: int = Field(ge=1, description="입력 번호 (1-based)")

class InputAllBody(BaseModel):
    input: int = Field(ge=1, description="입력 번호 (1-based)")

class PairStartBody(BaseModel):
    tv: int = Field(ge=1, description="TV 번호 (1-based)")

class PairFinishBody(BaseModel):
    tv:  int = Field(ge=1)
    pin: str = Field(min_length=1)


@router.post("/input")
async def switch_input(body: InputBody, req: Request):
    """특정 TV 입력 소스 전환"""
    result = await tcl_service.switch_input(body.tv, body.input)
    _log(result, req.client.host)
    return result


@router.post("/input/all")
async def switch_input_all(body: InputAllBody, req: Request):
    """전체 TV 입력 소스 동시 전환"""
    result = await tcl_service.switch_input_all(body.input)
    for r in result.get("results", []):
        _log(r, req.client.host)
    return result


@router.get("/status")
async def get_status():
    """TCL TV 연결 상태 및 설정 조회"""
    return await tcl_service.get_status()


@router.post("/pair/start")
async def pair_start(body: PairStartBody):
    """페어링 시작 — TV 화면에 PIN 표시"""
    result = await tcl_service.start_pairing(body.tv)
    ws_manager.notify_log(f"[TCL] 페어링 시작: {result.get('tv','?')}")
    return result


@router.post("/pair/finish")
async def pair_finish(body: PairFinishBody):
    """PIN 입력으로 페어링 완료"""
    result = await tcl_service.finish_pairing(body.tv, body.pin)
    icon = "✓" if result.get("ok") else "✗"
    ws_manager.notify_log(f"[TCL] {icon} 페어링: {result.get('tv','?')} — {result.get('message','')}")
    return result


def _log(result: dict, client_ip: str):
    ok     = result.get("ok", False)
    tv     = result.get("tv", "?")
    inp    = result.get("input", "?")
    detail = result.get("detail", "")
    icon   = "✓" if ok else "✗"
    msg    = f"[TCL] {icon} {tv} → {inp}"
    if not ok and detail:
        msg += f"  {detail}"
    msg += f"  [{client_ip}]"
    ws_manager.notify_log(msg)
