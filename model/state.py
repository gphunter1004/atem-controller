import time as _time
import threading

class ATEMState:
    def __init__(self):
        self._lock = threading.RLock()
        self.pgm:        int   = 1
        self.pvw:        int   = 2
        self.pip_src:    int   = 1
        self.mode:       str   = "대기중"
        self.keyer_mode:      str   = "off"   # off / keyup / pip
        self.dve_size:        float = 0.25
        self.dve_pos_x:       float = 12.0
        self.dve_pos_y:       float = 7.0
        self.last_transition:   str   = ""      # "" / "CUT" / "AUTO"
        self.transition_style:  str   = "MIX"   # MIX / DIP / WIPE / STING
        self.atem_connected:    bool  = False
        self._last_write: float = 0.0

    def touch(self):
        """마지막 쓰기 시각 갱신 — sync 억제용"""
        with self._lock:
            self._last_write = _time.monotonic()

    def sync_suppressed(self, window: float = 1.0) -> bool:
        """마지막 쓰기 후 window초 이내면 sync 건너뜀"""
        with self._lock:
            return (_time.monotonic() - self._last_write) < window

    def to_dict(self):
        """일관된 스냅샷 반환 (다중 필드 읽기 중 torn read 방지)"""
        with self._lock:
            return {
                "pgm":             self.pgm,
                "pvw":             self.pvw,
                "pip_src":         self.pip_src,
                "mode":            self.mode,
                "keyer_mode":      self.keyer_mode,
                "dve_size":        self.dve_size,
                "dve_pos_x":       self.dve_pos_x,
                "dve_pos_y":       self.dve_pos_y,
                "last_transition":  self.last_transition,
                "transition_style": self.transition_style,
                "atem_connected":   self.atem_connected,
            }

# 싱글톤
state = ATEMState()
