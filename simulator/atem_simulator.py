import time
import threading
from dataclasses import dataclass, field
from typing import Optional
from simulator.simulator_config import (
    SIM_PGM, SIM_PVW, SIM_PIP_SRC,
    SIM_KEYER_ON, SIM_KEYER_TYPE,
    SIM_DVE_SIZE, SIM_DVE_POS_X, SIM_DVE_POS_Y,
    SIM_TRANSITION_STYLE, SIM_TRANSITION_RATE,
)

@dataclass
class SimulatorState:
    pgm:      int   = 1
    pvw:      int   = 2
    pip_src:  int   = 1
    keyer_on: bool  = False
    keyer_type: str = "none"   # none / key / dve
    dve_size:  float = 0.25
    dve_pos_x: float = 0.62
    dve_pos_y: float = 0.35
    in_transition:    bool  = False
    transition_style: str   = "MIX"
    transition_rate:  int   = 15    # 프레임 (30fps 기준 500ms)

class ATEMSimulator:
    """
    PyATEMMax ATEMMax 클래스를 흉내내는 시뮬레이터
    실제 ATEM 없이 로직 테스트용
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._state_change_cb = None   # 외부 콜백 (ATEMUDPServer 등록용)
        self.state = SimulatorState(
            pgm             = SIM_PGM,
            pvw             = SIM_PVW,
            pip_src         = SIM_PIP_SRC,
            keyer_on        = SIM_KEYER_ON,
            keyer_type      = SIM_KEYER_TYPE,
            dve_size        = SIM_DVE_SIZE,
            dve_pos_x       = SIM_DVE_POS_X,
            dve_pos_y       = SIM_DVE_POS_Y,
            transition_style= SIM_TRANSITION_STYLE,
            transition_rate = SIM_TRANSITION_RATE,
        )
        self._log("ATEM 시뮬레이터 초기화")

    # ── 연결 ──────────────────────────────────────
    def connect(self, ip: str, port: int = 9910):
        self._log(f"[연결 시도] {ip}:{port} (시뮬레이터)")

    def waitForConnection(self):
        time.sleep(0.3)  # 연결 지연 흉내
        self._log("[연결 성공] 시뮬레이터 모드")

    # ── PGM / PVW ─────────────────────────────────
    def setProgramInputVideoSource(self, me: int, source: int):
        self.state.pgm = source
        self._log(f"[PGM] ME{me} → 소스{source}")

    def setPreviewInputVideoSource(self, me: int, source: int):
        self.state.pvw = source
        self._log(f"[PVW] ME{me} → 소스{source}")

    # ── 전환 ──────────────────────────────────────
    def execCutME(self, me: int):
        prev = self.state.pgm
        self.state.pgm = self.state.pvw
        self.state.pvw = prev
        self._log(f"[CUT] ME{me} | 소스{prev} → 소스{self.state.pgm}")

    def execAutoME(self, me: int):
        with self._lock:
            self.state.in_transition = True
            rate   = self.state.transition_rate
            src_pg = self.state.pgm
            src_pv = self.state.pvw
        duration_ms = rate / 30.0 * 1000
        self._log(f"[AUTO 시작] ME{me} | 소스{src_pg} → 소스{src_pv} ({duration_ms:.0f}ms)")

        def finish():
            time.sleep(rate / 30.0)
            with self._lock:
                self.state.pgm = src_pv
                self.state.pvw = src_pg
                self.state.in_transition = False
            self._log(f"[AUTO 완료] → 소스{src_pv}")
            if self._state_change_cb:
                try:
                    self._state_change_cb(["pgm", "pvw"])
                except Exception:
                    pass

        threading.Thread(target=finish, daemon=True).start()

    def setTransitionStyle(self, me: int, style):
        style_name = str(style).split(".")[-1]
        self.state.transition_style = style_name
        self._log(f"[TRANSITION STYLE] ME{me} → {style_name}")

    def setTransitionMixRate(self, me: int, rate: int):
        self.state.transition_rate = rate
        self._log(f"[MIX RATE] ME{me} → {rate}프레임 ({rate / 30 * 1000:.0f}ms)")

    # ── 키어 ──────────────────────────────────────
    def setKeyerOnAirEnabled(self, me: int, keyer: int, on: bool):
        self.state.keyer_on = on
        self._log(f"[KEYER] ME{me} Keyer{keyer} → {'ON' if on else 'OFF'}")

    def setKeyerFillSource(self, me: int, keyer: int, source: int):
        self.state.pip_src = source
        self._log(f"[KEYER FILL] ME{me} Keyer{keyer} → 소스{source}")

    def setKeyerType(self, me: int, keyer: int, keyer_type):
        type_name = str(keyer_type).split(".")[-1]
        self.state.keyer_type = type_name
        self._log(f"[KEYER TYPE] ME{me} Keyer{keyer} → {type_name}")

    # ── DVE ───────────────────────────────────────
    def setKeyDVESizeX(self, me: int, keyer: int, size: float):
        self.state.dve_size = size
        self._log(f"[DVE SIZE X] {size}")

    def setKeyDVESizeY(self, me: int, keyer: int, size: float):
        self.state.dve_size = size
        self._log(f"[DVE SIZE Y] {size}")

    def setKeyDVEPositionX(self, me: int, keyer: int, pos: float):
        self.state.dve_pos_x = pos
        self._log(f"[DVE POS X] {pos}")

    def setKeyDVEPositionY(self, me: int, keyer: int, pos: float):
        self.state.dve_pos_y = pos
        self._log(f"[DVE POS Y] {pos}")

    # ── Flying Key ────────────────────────────────
    def setRunFlyingKeyKeyFrame(self, me: int, keyer: int, key_frame):
        """키프레임으로 PiP 위치 이동 (a=우상단, b=좌상단)"""
        kf = str(key_frame).split(".")[-1].lower()
        key_frame_pos = {
            "a":    ( 12.0,  7.0),
            "b":    (-12.0,  7.0),
            "full": (  0.0,  0.0),
        }
        if kf in key_frame_pos:
            self.state.dve_pos_x, self.state.dve_pos_y = key_frame_pos[kf]
        self._log(f"[FLY KEY] ME{me} Keyer{keyer} → 키프레임 {kf.upper()}")
        if self._state_change_cb:
            try:
                self._state_change_cb(["dve_pos_x", "dve_pos_y"])
            except Exception:
                pass

    # ── 상태 조회 ─────────────────────────────────
    def get_state(self) -> dict:
        return {
            "pgm":           self.state.pgm,
            "pvw":           self.state.pvw,
            "pip_src":       self.state.pip_src,
            "keyer_on":      self.state.keyer_on,
            "keyer_type":    self.state.keyer_type,
            "dve_size":      self.state.dve_size,
            "dve_pos_x":     self.state.dve_pos_x,
            "dve_pos_y":     self.state.dve_pos_y,
            "in_transition":    self.state.in_transition,
            "transition_style": self.state.transition_style,
            "transition_rate":  self.state.transition_rate,
        }

    # ── 로그 ──────────────────────────────────────
    def _log(self, msg: str):
        print(f"[ATEM SIM] {msg}", flush=True)