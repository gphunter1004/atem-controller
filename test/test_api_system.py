"""System API 통합 테스트 (GET /status · /sources · POST /admin/reload)"""


# ── GET /status ───────────────────────────────────────────────

def test_get_status_returns_200(client):
    """GET /status → 200 OK"""
    r = client.get("/status")
    assert r.status_code == 200


def test_get_status_has_all_fields(client):
    """GET /status → pgm/pvw/pip_src/mode/keyer_mode/dve_size/dve_pos_x/dve_pos_y/last_transition/transition_style/atem_connected 11개 필드 포함"""
    r = client.get("/status")
    data = r.json()
    expected_keys = {
        "pgm", "pvw", "pip_src", "mode", "keyer_mode",
        "dve_size", "dve_pos_x", "dve_pos_y",
        "last_transition", "transition_style", "atem_connected",
    }
    assert expected_keys == set(data.keys())


def test_get_status_reflects_state(client):
    """state.pgm=4, pvw=3, keyer_mode='keyup', pip_src=2 직접 설정 후 GET /status → 동일 값 반환"""
    from model.state import state
    state.pgm = 4
    state.pvw = 3
    state.keyer_mode = "keyup"
    state.pip_src = 2
    r = client.get("/status")
    data = r.json()
    assert data["pgm"] == 4
    assert data["pvw"] == 3
    assert data["keyer_mode"] == "keyup"
    assert data["pip_src"] == 2


def test_get_status_after_pgm_change(client):
    """POST /switching/pgm source=3 후 GET /status → pgm=3"""
    client.post("/switching/pgm", json={"source": 3})
    r = client.get("/status")
    assert r.json()["pgm"] == 3


def test_get_status_atem_connected_bool(client):
    """GET /status → atem_connected 값이 bool 타입"""
    data = client.get("/status").json()
    assert isinstance(data["atem_connected"], bool)


# ── GET /sources ──────────────────────────────────────────────

def test_get_sources_returns_200(client):
    """GET /sources → 200 OK"""
    r = client.get("/sources")
    assert r.status_code == 200


def test_get_sources_has_sources_key(client):
    """GET /sources → 'sources' 키 포함"""
    r = client.get("/sources")
    assert "sources" in r.json()


def test_get_sources_returns_four_items(client):
    """GET /sources → sources 배열 길이 4 (소스 1~4)"""
    data = client.get("/sources").json()
    assert isinstance(data["sources"], list)
    assert len(data["sources"]) == 4


def test_get_sources_matches_config(client):
    """GET /sources → config.SOURCE_NAMES와 동일한 값"""
    from config import SOURCE_NAMES
    data = client.get("/sources").json()
    assert data["sources"] == SOURCE_NAMES


# ── POST /admin/reload ────────────────────────────────────────

def test_admin_reload_returns_ok(client):
    """POST /admin/reload → ok=True"""
    r = client.post("/admin/reload")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_admin_reload_returns_count(client):
    """POST /admin/reload → 응답에 'count' 필드 포함"""
    r = client.post("/admin/reload")
    assert "count" in r.json()


def test_admin_reload_count_reflects_presets(client):
    """프리셋 A, B 추가 후 POST /admin/reload → count=2"""
    client.post("/presets", json={"name": "A", "label": "", "pgm": 1})
    client.post("/presets", json={"name": "B", "label": "", "pgm": 2})
    r = client.post("/admin/reload")
    assert r.json()["count"] == 2


def test_admin_reload_count_after_delete(client):
    """프리셋 추가 후 삭제, POST /admin/reload → count=0"""
    p = client.post("/presets", json={"name": "A", "label": "", "pgm": 1}).json()["preset"]
    client.delete(f"/presets/{p['id']}")
    r = client.post("/admin/reload")
    assert r.json()["count"] == 0


# ── 시뮬레이터 상태 (/status 통해 확인) ──────────────────────────

def test_sim_pgm_reflected_in_status(client):
    """POST /switching/pgm source=2 후 GET /status → pgm=2 (시뮬레이터 상태도 반영)"""
    client.post("/switching/pgm", json={"source": 2})
    assert client.get("/status").json()["pgm"] == 2


def test_sim_pvw_reflected_in_status(client):
    """POST /switching/pvw source=3 후 GET /status → pvw=3"""
    client.post("/switching/pvw", json={"source": 3})
    assert client.get("/status").json()["pvw"] == 3


def test_sim_cut_swaps_pgm_pvw(client):
    """PGM=1, PVW=2 설정 후 POST /switching/cut → pgm=2, pvw=1"""
    client.post("/switching/pgm", json={"source": 1})
    client.post("/switching/pvw", json={"source": 2})
    client.post("/switching/cut")
    data = client.get("/status").json()
    assert data["pgm"] == 2
    assert data["pvw"] == 1


def test_sim_state_direct_access(client):
    """model.state.pgm 직접 설정 후 GET /status → pgm 반영"""
    from model.state import state
    state.pgm = 4
    assert client.get("/status").json()["pgm"] == 4
