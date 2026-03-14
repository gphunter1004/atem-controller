# simulator/simulator_config.py
# 시뮬레이터 초기 상태 설정
# SIMULATOR_MODE = True 일 때만 적용됨

# ── 입력 소스 ─────────────────────────────────
SIM_PGM     = 3       # 초기 PGM 소스 (1~4)
SIM_PVW     = 2       # 초기 PVW 소스 (1~4)
SIM_PIP_SRC = 1       # 초기 키어 소스 (1~4)

# ── 키어 ──────────────────────────────────────
SIM_KEYER_ON   = False   # 키어 초기 ON/OFF
SIM_KEYER_TYPE = "none"  # 키어 타입: "none" / "key" / "dve"

# ── DVE (PiP) ─────────────────────────────────
SIM_DVE_SIZE  = 0.25    # PiP 크기 (0.0 ~ 1.0)
SIM_DVE_POS_X = 12.0    # PiP X 위치 (-16.0 ~ 16.0)
SIM_DVE_POS_Y = 7.0     # PiP Y 위치 (-9.0 ~ 9.0)

# ── 전환 ──────────────────────────────────────
SIM_TRANSITION_STYLE = "MIX"  # 전환 스타일: "MIX" / "DIP" / "WIPE" / "STING"
SIM_TRANSITION_RATE  = 15     # 전환 속도 (프레임, 30fps 기준 15 = 500ms)
