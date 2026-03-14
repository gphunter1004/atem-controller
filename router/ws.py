import secrets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from model.state import state
from service.ws_manager import ws_manager

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    client_id = secrets.token_hex(4)
    client_ip = ws.client.host if ws.client else "unknown"
    await ws_manager.connect(ws, client_id)
    print(f"[WS] 연결 ({ws_manager.count}명) id={client_id} ip={client_ip}", flush=True)
    try:
        # 연결 즉시 ID/IP/접속자 수 전송 후 현재 상태 전송
        await ws.send_json({
            "type":     "welcome",
            "id":       client_id,
            "ip":       client_ip,
            "ws_count": ws_manager.count,
        })
        await ws.send_json({
            "type":     "status",
            "data":     state.to_dict(),
            "ws_count": ws_manager.count,
        })
        # welcome/status 전송 완료 후 다른 클라이언트에 접속자 수 변경 알림
        ws_manager.notify_count()
        while True:
            # 클라이언트 ping / 메시지 수신 대기 (연결 유지)
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)
        ws_manager.notify_count()
        print(f"[WS] 연결 해제 ({ws_manager.count}명) id={client_id}", flush=True)
    except Exception as e:
        ws_manager.disconnect(ws)
        ws_manager.notify_count()
        print(f"[WS] 오류로 연결 해제 ({ws_manager.count}명) id={client_id}: {e}", flush=True)
