import os
import sys
import socket
import asyncio
import logging
from logging.handlers import RotatingFileHandler
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import config as _config
from config import API_HOST, API_PORT, ATEM_PORT, SIMULATOR_MODE
_config.apply_console_visibility(_config.SHOW_CONSOLE)
from controller.atem_controller import atem
from router import switching, keyer, system, ws as ws_router
from router import config_router
from router import tcl_router
import uvicorn

logger = logging.getLogger("atem")



class _ConsoleTee:
    """sys.stdout/stderr를 원본 스트림 + 롤링 파일로 동시 출력."""

    def __init__(self, original, handler: RotatingFileHandler):
        self._original = original
        self._handler  = handler
        self._buf      = ""

    def write(self, data: str) -> None:
        self._original.write(data)
        self._buf += data
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            record = logging.makeLogRecord({"msg": line, "levelno": logging.INFO, "levelname": "INFO"})
            try:
                self._handler.emit(record)
            except Exception:
                pass

    def flush(self) -> None:
        self._original.flush()
        if self._buf.strip():
            record = logging.makeLogRecord({"msg": self._buf, "levelno": logging.INFO, "levelname": "INFO"})
            try:
                self._handler.emit(record)
            except Exception:
                pass
            self._buf = ""

    def __getattr__(self, name):
        return getattr(self._original, name)


def _setup_logging() -> tuple[str, str]:
    """로그 파일 2종 설정.
    1. atem.log         — logging 모듈 출력  (1 MB × 3 로테이션)
    2. atem_console.log — 콘솔 전체 출력     (5 MB × 5 로테이션)
    Returns: (log_file, console_log_file)
    """
    from conf_manager import BASE_DIR
    log_file         = os.path.join(BASE_DIR, "atem.log")
    console_log_file = os.path.join(BASE_DIR, "atem_console.log")

    # ── 1. atem.log (logging 모듈 핸들러) ────────────────────────
    try:
        fh = RotatingFileHandler(
            log_file,
            maxBytes=1 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        fh.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        root = logging.getLogger()
        root.setLevel(logging.INFO)
        root.addHandler(fh)
    except Exception as e:
        print(f"[LOG] 파일 로그 설정 실패 (콘솔 전용): {e}", flush=True)
        log_file = "(콘솔 전용)"

    # ── 2. atem_console.log (stdout/stderr tee) ──────────────────
    try:
        cfh = RotatingFileHandler(
            console_log_file,
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        cfh.setFormatter(logging.Formatter("%(message)s"))
        sys.stdout = _ConsoleTee(sys.__stdout__, cfh)
        sys.stderr = _ConsoleTee(sys.__stderr__, cfh)
    except Exception as e:
        print(f"[LOG] 콘솔 로그 설정 실패: {e}", flush=True)
        console_log_file = "(설정 실패)"

    return log_file, console_log_file


def _static_dir() -> str:
    """exe 모드: PyInstaller 번들 경로. 개발 모드: 상대 경로."""
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, 'static')
    return 'static'


def _static_file(name: str) -> str:
    return os.path.join(_static_dir(), name)


def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "unknown"

async def _device_sync_loop():
    """백그라운드에서 주기적으로 장비 상태를 state에 반영, 변경 시 WS 브로드캐스트"""
    from service.atem_service import atem_service
    from service.ws_manager import ws_manager
    loop = asyncio.get_running_loop()
    while True:
        await asyncio.sleep(_config.DEVICE_SYNC_INTERVAL)
        try:
            changed = await loop.run_in_executor(None, atem_service.sync_from_device)
            if changed:
                ws_manager.notify()
        except Exception as e:
            logger.error("[SYNC] 오류: %s", e)


async def _connect_and_init(loop: asyncio.AbstractEventLoop):
    """ATEM 장비 연결 시도 (최대 3회, 회당 10초 타임아웃).
    성공 시 기본값 설정 + 장비 상태 동기화 + 프리셋 1번 실행.
    3회 모두 실패하면 수동 연결(POST /admin/connect) 안내."""
    from service.atem_service import atem_service
    from service.preset_service import preset_service
    from model.state import state

    for attempt in range(1, 4):
        try:
            logger.info("ATEM 연결 시도 %d/3", attempt)
            print(f"[ATEM] 연결 시도 {attempt}/3 ...", flush=True)
            await asyncio.wait_for(
                loop.run_in_executor(None, atem.connect),
                timeout=10.0,
            )
            atem.init_defaults()
            state.transition_style = "MIX"
            atem_service.sync_from_device()
            p1 = preset_service.get_preset(1)
            if p1:
                preset_service.execute(p1)
            logger.info("ATEM 연결 성공")
            print("[ATEM] 연결 성공!", flush=True)
            return
        except asyncio.TimeoutError:
            logger.warning("ATEM 연결 타임아웃 (%d/3)", attempt)
            print(f"[ATEM] 타임아웃 ({attempt}/3)", flush=True)
        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.warning("ATEM 연결 실패 (%d/3): %s", attempt, e)
            print(f"[ATEM] 연결 실패 ({attempt}/3): {e}", flush=True)

    logger.error("ATEM 3회 연결 실패 — 수동 연결: POST /admin/connect")
    print("[ATEM] 연결 실패 — 수동 연결: POST /admin/connect", flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from conf_manager import init_conf_if_missing, init_presets_if_missing

    init_conf_if_missing()
    init_presets_if_missing()

    from service.ws_manager import ws_manager as _ws_manager
    loop = asyncio.get_running_loop()
    _ws_manager.setup(loop)

    # UDP 시뮬레이터 서버 시작 (simulator_mode=true 일 때만)
    udp_server = None
    if SIMULATOR_MODE:
        from simulator.atem_udp_server import ATEMUDPServer
        udp_server = ATEMUDPServer(atem.switcher)
        udp_server.start(ATEM_PORT)

    ip = get_local_ip()
    lines = [
        "=" * 40,
        "  ATEM Mini Controller",
        "=" * 40,
        f"  Home   : http://localhost:{API_PORT}",
        f"  Network: http://{ip}:{API_PORT}",
        f"  UI     : http://localhost:{API_PORT}/ui",
        f"  Panel  : http://localhost:{API_PORT}/panel",
        f"  Config : http://localhost:{API_PORT}/config",
        f"  Swagger: http://localhost:{API_PORT}/docs",
        "=" * 40,
        f"  장비 동기화: {_config.DEVICE_SYNC_INTERVAL}초마다",
    ]
    if SIMULATOR_MODE:
        lines.append(f"  ATEM UDP  : {ip}:{ATEM_PORT} (시뮬레이터)")
    lines += ["  종료: Ctrl+C", "=" * 40]
    for line in lines:
        print(line, flush=True)
    logger.info("서버 시작 — http://%s:%d", ip, API_PORT)

    # 백그라운드 태스크: 동기화 루프 + ATEM 연결 (웹 서버 기동 후 실행)
    sync_task    = asyncio.create_task(_device_sync_loop())
    connect_task = asyncio.create_task(_connect_and_init(loop))

    yield

    for task in (connect_task, sync_task):
        task.cancel()
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=1.5)
        except (asyncio.CancelledError, asyncio.TimeoutError, Exception):
            pass
    if udp_server:
        udp_server.stop()
    logger.info("서버 종료")
    print("종료됨", flush=True)

app = FastAPI(
    title="ATEM Mini Controller",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

app.mount("/static", StaticFiles(directory=_static_dir()), name="static")

# ── 루트 → UI 서빙 ─────────────────────────────
@app.get("/")
def root():
    return FileResponse(_static_file("preset_panel.html"))

@app.get("/menu")
def menu():
    return FileResponse(_static_file("index.html"))

@app.get("/ui")
def ui():
    return FileResponse(_static_file("atem_ui.html"))

@app.get("/panel")
def panel():
    return FileResponse(_static_file("preset_panel.html"))

@app.get("/config")
def config_page():
    return FileResponse(_static_file("config.html"))

# ── 라우터 등록 ────────────────────────────────
app.include_router(switching.router)
app.include_router(keyer.router)
app.include_router(system.router)
app.include_router(ws_router.router)
app.include_router(config_router.router)
app.include_router(tcl_router.router)

async def main():
    log_file, console_log_file = _setup_logging()
    print(f"  Log    : {log_file}", flush=True)
    print(f"  Console: {console_log_file}", flush=True)

    app_ref = app if getattr(sys, 'frozen', False) else "main:app"
    config = uvicorn.Config(
        app_ref,
        host=API_HOST,
        port=API_PORT,
        reload=False,
    )
    server = uvicorn.Server(config)

    # Windows: Ctrl+C 시 uvicorn에 종료 신호 전달.
    # lifespan 정리가 3초 내 완료 안 되면 강제 종료.
    if sys.platform == "win32":
        import signal, threading, os

        def _sigint(sig, frame):
            server.should_exit = True
            def _force():
                import time
                time.sleep(3)
                os._exit(0)
            threading.Thread(target=_force, daemon=True).start()

        signal.signal(signal.SIGINT, _sigint)

    try:
        await server.serve()
    except KeyboardInterrupt:
        print("종료됨", flush=True)

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("종료됨", flush=True)
