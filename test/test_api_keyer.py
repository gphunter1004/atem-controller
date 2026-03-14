"""Keyer API 통합 테스트 (/key/up · /key/pip · /key/off)"""


# ── POST /key/up ──────────────────────────────────────────────

def test_key_up_sets_keyer_mode(client):
    """source=2 전송 → keyer_mode='keyup', pip_src=2, ok=True"""
    r = client.post("/key/up", json={"source": 2})
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["keyer_mode"] == "keyup"
    assert data["pip_src"] == 2


def test_key_up_response_has_state_fields(client):
    """source=1 전송 → 응답에 pgm/pvw/keyer_mode/pip_src/ok 필드 포함"""
    r = client.post("/key/up", json={"source": 1})
    data = r.json()
    for key in ("pgm", "pvw", "keyer_mode", "pip_src", "ok"):
        assert key in data


def test_key_up_does_not_change_pgm(client):
    """pgm=3 설정 후 key/up source=2 → pgm은 여전히 3"""
    client.post("/switching/pgm", json={"source": 3})
    r = client.post("/key/up", json={"source": 2})
    assert r.json()["pgm"] == 3


def test_key_up_all_valid_sources(client):
    """source=1,2,3,4 모두 200 응답, 각각 pip_src 값 일치"""
    for src in (1, 2, 3, 4):
        r = client.post("/key/up", json={"source": src})
        assert r.status_code == 200
        assert r.json()["pip_src"] == src


# ── POST /key/pip ─────────────────────────────────────────────

def test_pip_on_sets_keyer_mode(client):
    """source=3, size=0.3, pos_x=-0.62, pos_y=0.35 → keyer_mode='pip', 각 값 반영"""
    r = client.post("/key/pip", json={
        "source": 3,
        "size": 0.3,
        "pos_x": -0.62,
        "pos_y": 0.35,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["keyer_mode"] == "pip"
    assert data["pip_src"] == 3
    assert abs(data["dve_size"] - 0.3) < 0.001
    assert abs(data["dve_pos_x"] - (-0.62)) < 0.001
    assert abs(data["dve_pos_y"] - 0.35) < 0.001


def test_pip_default_values_applied(client):
    """source만 보내면 size=0.25, pos_x=0.62, pos_y=0.35 기본값 적용"""
    r = client.post("/key/pip", json={"source": 2})
    assert r.status_code == 200
    data = r.json()
    assert data["keyer_mode"] == "pip"
    assert abs(data["dve_size"] - 0.25) < 0.001
    assert abs(data["dve_pos_x"] - 0.62) < 0.001
    assert abs(data["dve_pos_y"] - 0.35) < 0.001


def test_pip_four_corner_positions(client):
    """4개 코너 좌표(좌상/우상/좌하/우하) 각각 전송 → dve_pos_x/y 정확히 반영"""
    corners = [
        (-0.62,  0.35),   # 좌상단
        ( 0.62,  0.35),   # 우상단
        (-0.62, -0.35),   # 좌하단
        ( 0.62, -0.35),   # 우하단
    ]
    for px, py in corners:
        r = client.post("/key/pip", json={"source": 1, "pos_x": px, "pos_y": py})
        assert r.status_code == 200
        data = r.json()
        assert abs(data["dve_pos_x"] - px) < 0.001
        assert abs(data["dve_pos_y"] - py) < 0.001


# ── POST /key/off ─────────────────────────────────────────────

def test_key_off_after_key_up(client):
    """key/up 설정 후 key/off → keyer_mode='off'"""
    client.post("/key/up", json={"source": 2})
    r = client.post("/key/off")
    assert r.status_code == 200
    assert r.json()["keyer_mode"] == "off"


def test_key_off_after_pip(client):
    """key/pip 설정 후 key/off → keyer_mode='off'"""
    client.post("/key/pip", json={"source": 1})
    r = client.post("/key/off")
    assert r.status_code == 200
    assert r.json()["keyer_mode"] == "off"


def test_key_off_idempotent(client):
    """초기(keyer_mode='off') 상태에서 key/off 재호출 → 200, keyer_mode='off' 유지"""
    r = client.post("/key/off")
    assert r.status_code == 200
    assert r.json()["keyer_mode"] == "off"


# ── 유효성 검사 ───────────────────────────────────────────────

def test_key_up_source_too_low(client):
    """source=0 (범위 1~4 미만) → 422 Unprocessable Entity"""
    r = client.post("/key/up", json={"source": 0})
    assert r.status_code == 422


def test_key_up_source_too_high(client):
    """source=5 (범위 1~4 초과) → 422 Unprocessable Entity"""
    r = client.post("/key/up", json={"source": 5})
    assert r.status_code == 422


def test_pip_size_too_large(client):
    """size=1.5 (범위 0.0~1.0 초과) → 422 Unprocessable Entity"""
    r = client.post("/key/pip", json={"source": 1, "size": 1.5})
    assert r.status_code == 422


def test_pip_size_negative(client):
    """size=-0.1 (범위 0.0~1.0 미만) → 422 Unprocessable Entity"""
    r = client.post("/key/pip", json={"source": 1, "size": -0.1})
    assert r.status_code == 422


def test_pip_pos_x_out_of_range(client):
    """pos_x=1.5 (범위 -1.0~1.0 초과) → 422 Unprocessable Entity"""
    r = client.post("/key/pip", json={"source": 1, "pos_x": 1.5})
    assert r.status_code == 422


def test_pip_source_missing(client):
    """body 비어있어도 source 기본값=1 적용 → 200, pip_src=1"""
    r = client.post("/key/pip", json={})
    assert r.status_code == 200
    assert r.json()["pip_src"] == 1
