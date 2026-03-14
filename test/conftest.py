"""
공통 픽스처

실행 방법 (프로젝트 루트에서):
    pytest test/

픽스처 구조:
  session scope  : _patch_presets_file, client
  function scope : reset (autouse=True)  ← 매 테스트마다 state/시뮬레이터/프리셋 초기화
"""

import json
import pytest
import service.preset_service as ps_module


# ── 임시 presets 파일 ────────────────────────────────────────

@pytest.fixture(scope="session")
def tmp_presets_file(tmp_path_factory):
    p = tmp_path_factory.mktemp("presets") / "presets.json"
    p.write_text('{"presets": []}', encoding="utf-8")
    return str(p)


# ── PRESETS_FILE 패치 (session 전체 유효) ────────────────────

@pytest.fixture(scope="session", autouse=True)
def _patch_presets_file(tmp_presets_file):
    """테스트 중 preset_service 가 실제 presets.json 을 건드리지 않도록 임시 파일로 교체."""
    original = ps_module.PRESETS_FILE
    ps_module.PRESETS_FILE = tmp_presets_file
    yield
    ps_module.PRESETS_FILE = original


# ── TestClient (lifespan 포함, 세션 전체 공유) ───────────────

@pytest.fixture(scope="session")
def client(_patch_presets_file):
    from main import app
    from starlette.testclient import TestClient
    with TestClient(app) as c:
        yield c


# ── 각 테스트 전 초기화 ──────────────────────────────────────

@pytest.fixture(autouse=True)
def reset(client, tmp_presets_file):
    """
    매 테스트 전에 state / 시뮬레이터 / 프리셋을 깨끗한 초기값으로 되돌린다.
    state.touch() 로 백그라운드 sync 루프를 1초간 억제해 race condition 방지.
    """
    from model.state import state
    from service.preset_service import preset_service
    from controller.atem_controller import atem
    from simulator.atem_simulator import SimulatorState

    # ── state 초기화
    state.pgm              = 1
    state.pvw              = 2
    state.pip_src          = 1
    state.mode             = "대기중"
    state.keyer_mode       = "off"
    state.dve_size         = 0.25
    state.dve_pos_x        = 0.62
    state.dve_pos_y        = 0.35
    state.last_transition  = ""
    state.transition_style = "MIX"
    state.atem_connected   = True
    state.touch()  # 백그라운드 sync 루프 억제 (1초간)

    # ── 시뮬레이터 상태 초기화
    atem.switcher.state = SimulatorState(
        pgm=1, pvw=2, pip_src=1,
        keyer_on=False, keyer_type="none",
        dve_size=0.25, dve_pos_x=0.62, dve_pos_y=0.35,
        transition_style="MIX", transition_rate=15,
    )

    # ── 프리셋 파일 비우기 + 재로드
    with open(tmp_presets_file, "w", encoding="utf-8") as f:
        json.dump({"presets": []}, f)
    preset_service._load()

    yield
