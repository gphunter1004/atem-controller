import asyncio
import time as _time
from fastapi import WebSocket


class WSManager:
    def __init__(self):
        self._clients: dict[WebSocket, str] = {}  # ws → client_id
        self._loop: asyncio.AbstractEventLoop | None = None

    def setup(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    async def connect(self, ws: WebSocket, client_id: str):
        await ws.accept()
        self._clients[ws] = client_id

    def disconnect(self, ws: WebSocket):
        self._clients.pop(ws, None)

    async def _send_one(self, ws: WebSocket, data: dict):
        try:
            await ws.send_json(data)
        except Exception:
            self._clients.pop(ws, None)

    async def _broadcast(self, data: dict):
        """지정 데이터를 모든 클라이언트에 병렬 전송."""
        if not self._clients:
            return
        await asyncio.gather(
            *[self._send_one(ws, data) for ws in list(self._clients.keys())],
            return_exceptions=True
        )

    async def _broadcast_state(self):
        """현재 state를 메모리에서 읽어 모든 클라이언트에 병렬 전송."""
        from model.state import state
        await self._broadcast({
            "type":     "status",
            "data":     state.to_dict(),
            "ws_count": self.count,
        })

    def _schedule(self, coro):
        """이벤트 루프에 코루틴 예약 (스레드 / 비동기 컨텍스트 모두 안전)."""
        if not self._loop or not self._loop.is_running():
            return
        self._loop.call_soon_threadsafe(self._loop.create_task, coro)

    def notify(self):
        """상태 변경 알림 — 브로드캐스트 예약."""
        self._schedule(self._broadcast_state())

    def notify_log(self, msg: str):
        """실행 로그를 모든 클라이언트에 브로드캐스트."""
        data = {"type": "log", "msg": msg, "ts": _time.strftime("%H:%M:%S")}
        self._schedule(self._broadcast(data))

    async def _broadcast_count(self):
        """실행 시점의 접속자 수를 브로드캐스트."""
        await self._broadcast({"type": "count", "n": self.count})

    def notify_count(self):
        """현재 접속자 수를 모든 클라이언트에 브로드캐스트."""
        self._schedule(self._broadcast_count())

    def notify_reload(self):
        """프리셋 목록 갱신을 모든 클라이언트에 알림."""
        self._schedule(self._broadcast({"type": "reload"}))

    @property
    def count(self) -> int:
        return len(self._clients)

    def get_id(self, ws: WebSocket) -> str | None:
        return self._clients.get(ws)


# 싱글톤
ws_manager = WSManager()
