"""Switching API 통합 테스트 (/switching/pgm · pvw · cut · auto · style)"""


# ── POST /switching/pgm ───────────────────────────────────────

def test_pgm_changes_state(client):
    """source=3 전송 → 응답 pgm=3, ok=True"""
    r = client.post("/switching/pgm", json={"source": 3})
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["pgm"] == 3


def test_pgm_response_includes_all_state_fields(client):
    """source=2 전송 → 응답에 pgm/pvw/keyer_mode/transition_style/atem_connected/ok 필드 포함"""
    r = client.post("/switching/pgm", json={"source": 2})
    data = r.json()
    for key in ("pgm", "pvw", "keyer_mode", "transition_style", "atem_connected", "ok"):
        assert key in data, f"응답에 '{key}' 필드 없음"


def test_pgm_all_valid_sources(client):
    """source=1,2,3,4 모두 200 응답, 각각 pgm 값 일치"""
    for src in (1, 2, 3, 4):
        r = client.post("/switching/pgm", json={"source": src})
        assert r.status_code == 200
        assert r.json()["pgm"] == src


# ── POST /switching/pvw ───────────────────────────────────────

def test_pvw_changes_state(client):
    """source=4 전송 → 응답 pvw=4"""
    r = client.post("/switching/pvw", json={"source": 4})
    assert r.status_code == 200
    assert r.json()["pvw"] == 4


def test_pvw_does_not_change_pgm(client):
    """pgm=1 고정 후 pvw=3 변경 → pgm은 여전히 1, pvw=3"""
    client.post("/switching/pgm", json={"source": 1})
    r = client.post("/switching/pvw", json={"source": 3})
    assert r.json()["pgm"] == 1
    assert r.json()["pvw"] == 3


# ── POST /switching/cut ───────────────────────────────────────

def test_cut_swaps_pgm_and_pvw(client):
    """초기(pgm=1, pvw=2) 상태에서 CUT → pgm=2, pvw=1로 교체"""
    r = client.post("/switching/cut")
    assert r.status_code == 200
    data = r.json()
    assert data["pgm"] == 2
    assert data["pvw"] == 1


def test_cut_sets_last_transition(client):
    """CUT 후 last_transition='CUT'"""
    r = client.post("/switching/cut")
    assert r.json()["last_transition"] == "CUT"


def test_cut_twice_restores_original(client):
    """CUT 두 번 → pgm=1, pvw=2로 원복"""
    client.post("/switching/cut")
    r = client.post("/switching/cut")
    data = r.json()
    assert data["pgm"] == 1
    assert data["pvw"] == 2


# ── POST /switching/auto ──────────────────────────────────────

def test_auto_swaps_pgm_and_pvw(client):
    """초기(pgm=1, pvw=2) 상태에서 AUTO → pgm=2, pvw=1로 교체"""
    r = client.post("/switching/auto")
    assert r.status_code == 200
    data = r.json()
    assert data["pgm"] == 2
    assert data["pvw"] == 1


def test_auto_sets_last_transition(client):
    """AUTO 후 last_transition='AUTO'"""
    r = client.post("/switching/auto")
    assert r.json()["last_transition"] == "AUTO"


# ── POST /switching/style ─────────────────────────────────────

def test_style_mix(client):
    """style='MIX' 전송 → transition_style='MIX'"""
    r = client.post("/switching/style", json={"style": "MIX"})
    assert r.status_code == 200
    assert r.json()["transition_style"] == "MIX"


def test_style_dip(client):
    """style='DIP' 전송 → transition_style='DIP'"""
    r = client.post("/switching/style", json={"style": "DIP"})
    assert r.status_code == 200
    assert r.json()["transition_style"] == "DIP"


def test_style_wipe(client):
    """style='WIPE' 전송 → transition_style='WIPE'"""
    r = client.post("/switching/style", json={"style": "WIPE"})
    assert r.status_code == 200
    assert r.json()["transition_style"] == "WIPE"


def test_style_sting(client):
    """style='STING' 전송 → transition_style='STING'"""
    r = client.post("/switching/style", json={"style": "STING"})
    assert r.status_code == 200
    assert r.json()["transition_style"] == "STING"


# ── 유효성 검사 ───────────────────────────────────────────────

def test_pgm_source_too_low_rejected(client):
    """source=0 (범위 1~4 미만) → 422 Unprocessable Entity"""
    r = client.post("/switching/pgm", json={"source": 0})
    assert r.status_code == 422


def test_pgm_source_too_high_rejected(client):
    """source=5 (범위 1~4 초과) → 422 Unprocessable Entity"""
    r = client.post("/switching/pgm", json={"source": 5})
    assert r.status_code == 422


def test_pvw_source_out_of_range_rejected(client):
    """source=99 → 422 Unprocessable Entity"""
    r = client.post("/switching/pvw", json={"source": 99})
    assert r.status_code == 422


def test_invalid_style_rejected(client):
    """style='DISSOLVE' (허용값: MIX/DIP/WIPE/STING 아님) → 422 Unprocessable Entity"""
    r = client.post("/switching/style", json={"style": "DISSOLVE"})
    assert r.status_code == 422


def test_missing_source_field_rejected(client):
    """body에 source 필드 없음 → 422 Unprocessable Entity"""
    r = client.post("/switching/pgm", json={})
    assert r.status_code == 422
