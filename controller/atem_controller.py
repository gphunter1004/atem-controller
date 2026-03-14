# controller/atem_controller.py
import time
import config
from config import SIMULATOR_MODE

# PyATEMMax가 없으면 시뮬레이터로 자동 전환
_is_simulator = SIMULATOR_MODE
if not _is_simulator:
    try:
        import PyATEMMax
        ATEMMax = PyATEMMax.ATEMMax
    except ImportError:
        print("[경고] PyATEMMax 없음 → 시뮬레이터 모드로 전환합니다.", flush=True)
        _is_simulator = True

if _is_simulator:
    from simulator.atem_simulator import ATEMSimulator as ATEMMax

class ATEMController:
    def __init__(self):
        self.switcher   = ATEMMax()
        self._connected = False

    def connect(self):
        self._connected = False
        if _is_simulator:
            print("ATEM 연결 중... (시뮬레이터)", flush=True)
            self.switcher.connect(config.ATEM_IP)
        else:
            print(f"ATEM 연결 중... ({config.ATEM_IP}:{config.ATEM_PORT})", flush=True)
            self.switcher.connect(config.ATEM_IP, config.ATEM_PORT)
        self.switcher.waitForConnection()
        self._connected = True
        print("ATEM 연결 성공!", flush=True)

    def _cmd(self, fn):
        """연결된 경우에만 명령 실행. 미연결 시 조용히 무시."""
        if not self._connected:
            return
        try:
            fn()
        except Exception as e:
            print(f"[ATEM] 명령 실패: {e}", flush=True)

    def set_program_input(self, source: int):
        self._cmd(lambda: self.switcher.setProgramInputVideoSource(0, source))

    def set_preview_input(self, source: int):
        self._cmd(lambda: self.switcher.setPreviewInputVideoSource(0, source))

    def cut(self):
        self._cmd(lambda: self.switcher.execCutME(0))

    def auto(self):
        self._cmd(lambda: self.switcher.execAutoME(0))

    def set_keyer_source(self, source: int):
        self._cmd(lambda: self.switcher.setKeyerFillSource(0, 0, source))

    def set_keyer_on_air(self, on: bool):
        self._cmd(lambda: self.switcher.setKeyerOnAirEnabled(0, 0, on))

    def set_keyer_type_chroma(self):
        keyer_type = "chroma" if _is_simulator else PyATEMMax.ATEMKeyerTypes.chroma
        self._cmd(lambda: self.switcher.setKeyerType(0, 0, keyer_type))

    def set_keyer_type_dve(self):
        keyer_type = "dve" if _is_simulator else PyATEMMax.ATEMKeyerTypes.dVE
        self._cmd(lambda: self.switcher.setKeyerType(0, 0, keyer_type))

    def set_dve_size(self, size: float):
        self._cmd(lambda: self.switcher.setKeyDVESizeX(0, 0, size))
        self._cmd(lambda: self.switcher.setKeyDVESizeY(0, 0, size))

    def set_dve_position(self, pos_x: float, pos_y: float):
        self._cmd(lambda: self.switcher.setKeyDVEPositionX(0, 0, pos_x))
        self._cmd(lambda: self.switcher.setKeyDVEPositionY(0, 0, pos_y))

    def read_key_frame_position(self, key_frame: str) -> tuple:
        """키프레임 A/B에 저장된 위치 좌표 반환. 미설정/읽기 실패 시 기본값 반환."""
        default = (12.0, 7.0)
        if not self._connected or _is_simulator:
            return default
        try:
            is_set = getattr(self.switcher.keyer[0][0].fly, f"is{key_frame.upper()}Set", None)
            if is_set is False:
                print(f"[ATEM] 키프레임 {key_frame.upper()} 미설정 → 기본값 {default} 사용", flush=True)
                return default
            kf = getattr(PyATEMMax.ATEMKeyFrames, key_frame)
            pos_x = self.switcher.keyer[0][0].fly.keyFrame[kf].position.x
            pos_y = self.switcher.keyer[0][0].fly.keyFrame[kf].position.y
            print(f"[ATEM] 키프레임 {key_frame.upper()} 위치: ({pos_x}, {pos_y})", flush=True)
            if abs(pos_x) < 1.0 and abs(pos_y) < 1.0:
                print(f"[ATEM] 키프레임 좌표 비정상 → 기본값 {default} 사용", flush=True)
                return default
            return (pos_x, pos_y)
        except Exception as e:
            print(f"[ATEM] 키프레임 읽기 실패: {e}", flush=True)
            return default

    def set_transition_style(self, style: str):
        if _is_simulator:
            s = style
        else:
            mapping = {
                "MIX":   PyATEMMax.ATEMTransitionStyles.mix,
                "DIP":   PyATEMMax.ATEMTransitionStyles.dip,
                "WIPE":  PyATEMMax.ATEMTransitionStyles.wipe,
                "STING": PyATEMMax.ATEMTransitionStyles.sting,
            }
            s = mapping.get(style.upper(), PyATEMMax.ATEMTransitionStyles.mix)
        self._cmd(lambda: self.switcher.setTransitionStyle(0, s))

    def init_defaults(self):
        """서버 시작 시 기본값 설정: AUTO(MIX) 전환 + 설정 속도"""
        if _is_simulator:
            style = "MIX"
        else:
            style = PyATEMMax.ATEMTransitionStyles.mix
        self.switcher.setTransitionStyle(0, style)
        self.switcher.setTransitionMixRate(0, config.TRANSITION_RATE_FRAMES)

    def read_device_state(self) -> dict:
        """현재 장비 상태를 읽어 반환. 미연결 시 빈 dict 반환."""
        if not self._connected:
            return {}
        if _is_simulator:
            return self.switcher.get_state()
        try:
            keyer_type       = self.switcher.keyer[0][0].type.name
            transition_style = self.switcher.transition[0].style.name.upper()
            return {
                "pgm":              self.switcher.programInput[0].videoSource.value,
                "pvw":              self.switcher.previewInput[0].videoSource.value,
                "pip_src":          self.switcher.keyer[0][0].fillSource.value,
                "keyer_on":         self.switcher.keyer[0][0].onAir.enabled,
                "keyer_type":       keyer_type,
                "dve_size":         self.switcher.key[0][0].dVE.size.x,
                "dve_pos_x":        self.switcher.key[0][0].dVE.position.x,
                "dve_pos_y":        self.switcher.key[0][0].dVE.position.y,
                "transition_style": transition_style,
            }
        except Exception as e:
            self._connected = False
            print(f"[ATEM] 상태 읽기 실패 (연결 끊김): {e}", flush=True)
            return {}

# 싱글톤
atem = ATEMController()