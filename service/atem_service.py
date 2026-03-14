import time
from model.state import state
from controller.atem_controller import atem

class ATEMService:

    # ── PGM ──────────────────────────────────────
    def direct_pgm(self, source: int):
        state.touch()
        state.pgm        = source
        state.keyer_mode = "off"
        state.mode       = f"직접출력 CUT → 소스{source}"
        atem.set_keyer_on_air(False)
        atem.set_program_input(source)

    # ── PVW ──────────────────────────────────────
    def set_pvw(self, source: int):
        state.touch()
        state.pvw  = source
        state.mode = f"PVW 선택 → 소스{source}"
        atem.set_preview_input(source)

    # ── 전환 ─────────────────────────────────────
    def cut(self):
        state.touch()
        prev_pgm              = state.pgm
        state.pgm             = state.pvw
        state.pvw             = prev_pgm
        state.mode            = f"CUT → 소스{state.pgm}"
        state.last_transition = "CUT"
        atem.cut()

    def auto(self):
        state.touch()
        prev_pgm              = state.pgm
        state.pgm             = state.pvw
        state.pvw             = prev_pgm
        state.mode            = f"AUTO → 소스{state.pgm}"
        state.last_transition = "AUTO"
        atem.auto()

    # ── 키어 ─────────────────────────────────────
    def key_up(self, source: int):
        state.touch()
        state.keyer_mode = "keyup"
        state.pip_src    = source
        state.mode       = f"KEY UP → 소스{source}"
        atem.set_keyer_on_air(False)
        time.sleep(0.05)
        atem.set_keyer_type_chroma()
        atem.set_keyer_source(source)
        atem.set_keyer_on_air(True)

    def pip_on(self, source: int, size: float, pos_x: float, pos_y: float):
        state.touch()
        state.keyer_mode = "pip"
        state.pip_src    = source
        state.dve_size   = size
        state.dve_pos_x  = pos_x
        state.dve_pos_y  = pos_y
        state.mode       = f"PiP ON → 소스{source}"
        atem.set_keyer_on_air(False)
        time.sleep(0.05)
        atem.set_keyer_type_dve()
        atem.set_keyer_source(source)
        atem.set_dve_size(size)
        pos_x, pos_y = atem.read_key_frame_position('a')
        atem.set_dve_position(pos_x, pos_y)
        state.dve_pos_x = pos_x
        state.dve_pos_y = pos_y
        atem.set_keyer_on_air(True)

    def set_transition_style(self, style: str):
        state.touch()
        state.transition_style = style.upper()
        state.mode             = f"트랜지션 스타일 → {style}"
        atem.set_transition_style(style)

    def key_off(self):
        state.touch()
        state.keyer_mode = "off"
        state.mode       = "키어 OFF"
        atem.set_keyer_on_air(False)

    # ── 초기화 ───────────────────────────────────
    def sync_from_device(self) -> bool:
        """장비 현재 상태를 프로그램 state에 반영 (명령 없이 읽기만).
        상태가 실제로 갱신된 경우 True 반환."""
        prev_connected = state.atem_connected

        try:
            raw = atem.read_device_state()
        except Exception:
            state.atem_connected = False
            return prev_connected          # 연결 상태가 바뀌었으면 broadcast 필요

        if not raw:
            state.atem_connected = False
            return prev_connected          # 연결 상태가 바뀌었으면 broadcast 필요

        # 연결 상태는 suppress와 무관하게 항상 갱신
        state.atem_connected = True

        if state.sync_suppressed():
            return not prev_connected      # 연결 상태가 바뀐 경우만 broadcast

        state.pgm              = raw.get("pgm",              state.pgm)
        state.pvw              = raw.get("pvw",              state.pvw)
        state.pip_src          = raw.get("pip_src",          state.pip_src)
        state.transition_style = raw.get("transition_style", state.transition_style)

        keyer_on   = raw.get("keyer_on",   False)
        keyer_type = raw.get("keyer_type", "none").lower()

        if not keyer_on:
            state.keyer_mode = "off"
        elif keyer_type == "dve":
            state.keyer_mode = "pip"
            state.dve_size   = raw.get("dve_size",  state.dve_size)
            state.dve_pos_x  = raw.get("dve_pos_x", state.dve_pos_x)
            state.dve_pos_y  = raw.get("dve_pos_y", state.dve_pos_y)
        else:
            state.keyer_mode = "keyup"

        return True

# 싱글톤
atem_service = ATEMService()
