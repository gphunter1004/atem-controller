"""Config API 통합 테스트 (GET/POST/DELETE /api/config) + 페이지 라우트"""

import pytest
import conf_manager as cm
import router.config_router as cr


# ── 테스트마다 독립된 conf 파일 경로 ──────────────────────────

@pytest.fixture()
def conf_path(tmp_path, monkeypatch):
    """각 테스트 전용 임시 conf 경로로 CONF_PATH 패치.
    conf_manager 의 파일 I/O 함수(load/save_conf/delete_conf)와
    config_router 의 응답 필드(conf_file)가 모두 임시 경로를 사용한다.
    """
    p = str(tmp_path / "atem_test.conf")
    monkeypatch.setattr(cm, "CONF_PATH", p)
    monkeypatch.setattr(cr, "CONF_PATH", p)
    yield p


# ── GET /api/config ────────────────────────────────────────────

def test_get_config_returns_200(client, conf_path):
    """GET /api/config → 200 OK"""
    r = client.get("/api/config")
    assert r.status_code == 200


def test_get_config_has_all_fields(client, conf_path):
    """GET /api/config → 필수 키 전체 포함"""
    data = client.get("/api/config").json()
    expected = {
        "atem_ip", "atem_port", "simulator_mode", "api_port",
        "transition_rate_frames", "device_sync_interval",
        "source_names", "conf_file", "conf_exists",
    }
    assert expected == set(data.keys())


def test_get_config_default_ip(client, conf_path):
    """conf 파일 없을 때 GET /api/config → atem_ip 기본값 192.168.0.240"""
    data = client.get("/api/config").json()
    assert data["atem_ip"] == "192.168.0.240"


def test_get_config_default_simulator_mode_false(client, conf_path):
    """conf 파일 없을 때 GET /api/config → simulator_mode=False"""
    data = client.get("/api/config").json()
    assert data["simulator_mode"] is False


def test_get_config_default_api_port(client, conf_path):
    """conf 파일 없을 때 GET /api/config → api_port=8000"""
    data = client.get("/api/config").json()
    assert data["api_port"] == 8000


def test_get_config_source_names_count(client, conf_path):
    """GET /api/config → source_names 배열 길이 4"""
    data = client.get("/api/config").json()
    assert isinstance(data["source_names"], list)
    assert len(data["source_names"]) == 4


def test_get_config_conf_exists_false_initially(client, conf_path):
    """conf 파일 없을 때 conf_exists=False"""
    data = client.get("/api/config").json()
    assert data["conf_exists"] is False


def test_get_config_conf_exists_is_bool(client, conf_path):
    """conf_exists 값이 bool 타입"""
    data = client.get("/api/config").json()
    assert isinstance(data["conf_exists"], bool)


# ── POST /api/config ───────────────────────────────────────────

_VALID_BODY = {
    "atem_ip":                "10.0.0.5",
    "atem_port":              9910,
    "simulator_mode":         False,
    "api_port":               8000,
    "transition_rate_frames": 20,
    "device_sync_interval":   3,
    "source_names":           ["카메라", "PPT", "화면", "없음"],
}


def test_post_config_returns_ok(client, conf_path):
    """POST /api/config (유효한 바디) → ok=True"""
    r = client.post("/api/config", json=_VALID_BODY)
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_post_config_returns_conf_file(client, conf_path):
    """POST /api/config → conf_file 필드 포함"""
    r = client.post("/api/config", json=_VALID_BODY)
    assert "conf_file" in r.json()


def test_post_config_conf_exists_after_save(client, conf_path):
    """POST /api/config 후 GET → conf_exists=True"""
    client.post("/api/config", json=_VALID_BODY)
    data = client.get("/api/config").json()
    assert data["conf_exists"] is True


def test_post_config_get_reflects_saved_ip(client, conf_path):
    """POST ip=10.0.0.5 후 GET /api/config → atem_ip=10.0.0.5"""
    client.post("/api/config", json=_VALID_BODY)
    data = client.get("/api/config").json()
    assert data["atem_ip"] == "10.0.0.5"


def test_post_config_get_reflects_transition_rate(client, conf_path):
    """POST transition_rate_frames=20 후 GET → transition_rate_frames=20"""
    client.post("/api/config", json=_VALID_BODY)
    data = client.get("/api/config").json()
    assert data["transition_rate_frames"] == 20


def test_post_config_get_reflects_source_names(client, conf_path):
    """POST source_names=['카메라','PPT','화면','없음'] 후 GET → 동일 배열 반환"""
    client.post("/api/config", json=_VALID_BODY)
    data = client.get("/api/config").json()
    assert data["source_names"] == ["카메라", "PPT", "화면", "없음"]


# 유효성 검사

def test_post_config_port_too_low(client, conf_path):
    """atem_port=0 (1 미만) → 422 Unprocessable Entity"""
    body = {**_VALID_BODY, "atem_port": 0}
    r = client.post("/api/config", json=body)
    assert r.status_code == 422


def test_post_config_port_too_high(client, conf_path):
    """atem_port=99999 (65535 초과) → 422 Unprocessable Entity"""
    body = {**_VALID_BODY, "atem_port": 99999}
    r = client.post("/api/config", json=body)
    assert r.status_code == 422


def test_post_config_api_port_out_of_range(client, conf_path):
    """api_port=0 (1 미만) → 422 Unprocessable Entity"""
    body = {**_VALID_BODY, "api_port": 0}
    r = client.post("/api/config", json=body)
    assert r.status_code == 422


def test_post_config_transition_rate_too_high(client, conf_path):
    """transition_rate_frames=301 (300 초과) → 422 Unprocessable Entity"""
    body = {**_VALID_BODY, "transition_rate_frames": 301}
    r = client.post("/api/config", json=body)
    assert r.status_code == 422


def test_post_config_transition_rate_too_low(client, conf_path):
    """transition_rate_frames=0 (1 미만) → 422 Unprocessable Entity"""
    body = {**_VALID_BODY, "transition_rate_frames": 0}
    r = client.post("/api/config", json=body)
    assert r.status_code == 422


def test_post_config_device_sync_too_high(client, conf_path):
    """device_sync_interval=61 (60 초과) → 422 Unprocessable Entity"""
    body = {**_VALID_BODY, "device_sync_interval": 61}
    r = client.post("/api/config", json=body)
    assert r.status_code == 422


# ── DELETE /api/config ─────────────────────────────────────────

def test_delete_config_returns_ok(client, conf_path):
    """DELETE /api/config → ok=True"""
    r = client.delete("/api/config")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_delete_config_no_file_still_returns_ok(client, conf_path):
    """파일 없는 상태에서 DELETE /api/config → 200 ok=True (idempotent)"""
    r = client.delete("/api/config")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_delete_config_conf_exists_false_after_delete(client, conf_path):
    """POST 후 DELETE → GET /api/config → conf_exists=False"""
    client.post("/api/config", json=_VALID_BODY)
    client.delete("/api/config")
    data = client.get("/api/config").json()
    assert data["conf_exists"] is False


def test_post_then_delete_restores_default_ip(client, conf_path):
    """ip 저장 후 DELETE → GET 에서 기본 ip 반환"""
    body = {**_VALID_BODY, "atem_ip": "9.9.9.9"}
    client.post("/api/config", json=body)
    client.delete("/api/config")
    data = client.get("/api/config").json()
    assert data["atem_ip"] == "192.168.0.240"


# ── 페이지 라우트 ─────────────────────────────────────────────

def test_root_returns_html(client):
    """GET / → 200, HTML 응답"""
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")


def test_menu_returns_html(client):
    """GET /menu → 200, HTML 응답"""
    r = client.get("/menu")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")


def test_ui_returns_html(client):
    """GET /ui → 200, HTML 응답"""
    r = client.get("/ui")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")


def test_panel_returns_html(client):
    """GET /panel → 200, HTML 응답"""
    r = client.get("/panel")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")


def test_config_page_returns_html(client):
    """GET /config → 200, HTML 응답"""
    r = client.get("/config")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
