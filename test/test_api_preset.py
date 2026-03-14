"""Preset CRUD + 실행 API 통합 테스트"""


# ── 헬퍼 ─────────────────────────────────────────────────────

def _body(**kw):
    defaults = {"name": "테스트프리셋", "label": "", "pgm": 1}
    defaults.update(kw)
    return defaults


def _create(client, **kw):
    """프리셋 생성 후 preset dict 반환"""
    return client.post("/presets", json=_body(**kw)).json()["preset"]


# ── GET /presets ──────────────────────────────────────────────

def test_list_empty(client):
    """프리셋 없을 때 GET /presets → {"presets": []}"""
    r = client.get("/presets")
    assert r.status_code == 200
    assert r.json() == {"presets": []}


# ── POST /presets ─────────────────────────────────────────────

def test_create_returns_ok(client):
    """name='크로마키', pgm=2 생성 → ok=True, preset.name='크로마키', preset.pgm=2, id>=1"""
    r = client.post("/presets", json=_body(name="크로마키", pgm=2))
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["preset"]["name"] == "크로마키"
    assert data["preset"]["pgm"] == 2
    assert data["preset"]["id"] >= 1


def test_create_auto_assigns_id(client):
    """두 번 생성 시 두 번째 id = 첫 번째 id + 1"""
    p1 = _create(client, name="A")
    p2 = _create(client, name="B")
    assert p2["id"] == p1["id"] + 1


def test_create_and_list(client):
    """A, B 생성 후 GET /presets → 목록에 'A', 'B' 모두 포함"""
    _create(client, name="A")
    _create(client, name="B")
    presets = client.get("/presets").json()["presets"]
    names = [p["name"] for p in presets]
    assert "A" in names
    assert "B" in names


def test_create_with_keyer_keyup(client):
    """keyer={mode='keyup', source=3} 생성 → preset.keyer.mode='keyup', source=3"""
    body = _body(name="키업", pgm=2, keyer={"mode": "keyup", "source": 3})
    r = client.post("/presets", json=body)
    assert r.status_code == 200
    p = r.json()["preset"]
    assert p["keyer"]["mode"] == "keyup"
    assert p["keyer"]["source"] == 3


def test_create_with_keyer_pip(client):
    """keyer={mode='pip', source=2, size=0.3, pos_x=-0.62, pos_y=0.35} 생성 → 각 값 반영"""
    body = _body(
        name="PiP",
        pgm=1,
        keyer={"mode": "pip", "source": 2, "size": 0.3, "pos_x": -0.62, "pos_y": 0.35},
    )
    r = client.post("/presets", json=body)
    assert r.status_code == 200
    p = r.json()["preset"]
    assert p["keyer"]["mode"] == "pip"
    assert abs(p["keyer"]["size"] - 0.3) < 0.001


def test_create_with_confirm_true(client):
    """confirm=True 생성 → preset.confirm=True"""
    p = _create(client, confirm=True)
    assert p["confirm"] is True


def test_create_with_confirm_default_false(client):
    """confirm 미지정 생성 → preset.confirm=False (기본값)"""
    p = _create(client)
    assert p["confirm"] is False


def test_create_with_pvw(client):
    """pgm=1, pvw=3 생성 → preset.pvw=3"""
    p = _create(client, pgm=1, pvw=3)
    assert p["pvw"] == 3


def test_create_invalid_pgm_too_low(client):
    """pgm=0 (범위 1~4 미만) → 422 Unprocessable Entity"""
    r = client.post("/presets", json=_body(pgm=0))
    assert r.status_code == 422


def test_create_invalid_pgm_too_high(client):
    """pgm=5 (범위 1~4 초과) → 422 Unprocessable Entity"""
    r = client.post("/presets", json=_body(pgm=5))
    assert r.status_code == 422


def test_create_missing_name_rejected(client):
    """name 필드 없음 → 422 Unprocessable Entity"""
    r = client.post("/presets", json={"pgm": 1})
    assert r.status_code == 422


def test_create_missing_pgm_rejected(client):
    """pgm 필드 없음 → 422 Unprocessable Entity"""
    r = client.post("/presets", json={"name": "이름만"})
    assert r.status_code == 422


# ── DELETE /presets/{id} ──────────────────────────────────────

def test_delete_preset(client):
    """생성 후 DELETE /presets/{id} → ok=True, 이후 목록에서 해당 id 사라짐"""
    p = _create(client)
    r = client.delete(f"/presets/{p['id']}")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    ids = [x["id"] for x in client.get("/presets").json()["presets"]]
    assert p["id"] not in ids


def test_delete_notfound(client):
    """존재하지 않는 id=99999 삭제 → 404 Not Found"""
    r = client.delete("/presets/99999")
    assert r.status_code == 404


def test_delete_only_target(client):
    """A 삭제 후 B는 목록에 유지, A는 목록에서 사라짐"""
    p1 = _create(client, name="A")
    p2 = _create(client, name="B")
    client.delete(f"/presets/{p1['id']}")
    ids = [x["id"] for x in client.get("/presets").json()["presets"]]
    assert p1["id"] not in ids
    assert p2["id"] in ids


# ── POST /preset/{id} (실행) ──────────────────────────────────

def test_run_preset_changes_pgm(client):
    """pgm=3 프리셋 실행 → 응답 pgm=3, ok=True"""
    p = _create(client, name="PGM3", pgm=3)
    r = client.post(f"/preset/{p['id']}")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["pgm"] == 3


def test_run_preset_with_keyer_keyup(client):
    """pgm=2, keyer={mode='keyup', source=3} 프리셋 실행 → pgm=2, keyer_mode='keyup', pip_src=3"""
    body = _body(name="키업실행", pgm=2, keyer={"mode": "keyup", "source": 3})
    p = client.post("/presets", json=body).json()["preset"]
    r = client.post(f"/preset/{p['id']}")
    assert r.status_code == 200
    data = r.json()
    assert data["keyer_mode"] == "keyup"
    assert data["pip_src"] == 3
    assert data["pgm"] == 2


def test_run_preset_with_keyer_pip(client):
    """pgm=1, keyer={mode='pip', source=2} 프리셋 실행 → pgm=1, keyer_mode='pip'"""
    body = _body(
        name="PiP실행",
        pgm=1,
        keyer={"mode": "pip", "source": 2, "size": 0.25, "pos_x": 0.62, "pos_y": 0.35},
    )
    p = client.post("/presets", json=body).json()["preset"]
    r = client.post(f"/preset/{p['id']}")
    assert r.status_code == 200
    data = r.json()
    assert data["keyer_mode"] == "pip"
    assert data["pgm"] == 1


def test_run_preset_with_keyer_off(client):
    """key/up 설정 후 keyer=off 프리셋 실행 → keyer_mode='off'"""
    client.post("/key/up", json={"source": 2})
    body = _body(name="키어OFF", pgm=1, keyer={"mode": "off"})
    p = client.post("/presets", json=body).json()["preset"]
    r = client.post(f"/preset/{p['id']}")
    assert r.json()["keyer_mode"] == "off"


def test_run_preset_notfound(client):
    """존재하지 않는 id=99999 실행 → 404 Not Found"""
    r = client.post("/preset/99999")
    assert r.status_code == 404


def test_run_preset_response_has_state_fields(client):
    """프리셋 실행 응답에 pgm/pvw/keyer_mode/transition_style/atem_connected/ok 필드 포함"""
    p = _create(client, pgm=1)
    r = client.post(f"/preset/{p['id']}")
    data = r.json()
    for key in ("pgm", "pvw", "keyer_mode", "transition_style", "atem_connected", "ok"):
        assert key in data
