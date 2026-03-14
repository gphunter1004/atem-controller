"""conf_manager 단위 테스트 — load / save_conf / delete_conf"""

import os
import pytest
import conf_manager as cm


# ── 테스트마다 독립된 CONF_PATH 사용 ─────────────────────────

@pytest.fixture()
def conf_path(tmp_path, monkeypatch):
    """각 테스트 전용 임시 conf 파일 경로로 CONF_PATH 교체."""
    p = str(tmp_path / "atem_test.conf")
    monkeypatch.setattr(cm, "CONF_PATH", p)
    yield p


# ── 기본값 검증 ────────────────────────────────────────────────

def test_load_returns_defaults_when_no_file(conf_path):
    """conf 파일 없을 때 load() → 기본값 반환 (ip=192.168.0.240, port=9910)"""
    assert not os.path.exists(conf_path)
    cp = cm.load()
    assert cp.get("atem", "ip") == "192.168.0.240"
    assert cp.getint("atem", "port") == 9910


def test_load_simulator_mode_default_false(conf_path):
    """conf 파일 없을 때 simulator_mode 기본값 = False"""
    cp = cm.load()
    assert cp.getboolean("atem", "simulator_mode") is False


def test_load_server_defaults(conf_path):
    """conf 파일 없을 때 server 기본값: host=0.0.0.0, port=8000"""
    cp = cm.load()
    assert cp.get("server", "host") == "0.0.0.0"
    assert cp.getint("server", "port") == 8000


def test_load_switching_defaults(conf_path):
    """conf 파일 없을 때 switching 기본값: transition_rate_frames=15, device_sync_interval=2"""
    cp = cm.load()
    assert cp.getint("switching", "transition_rate_frames") == 15
    assert cp.getint("switching", "device_sync_interval") == 2


def test_load_sources_defaults(conf_path):
    """conf 파일 없을 때 sources 기본값: name1~name4 모두 존재"""
    cp = cm.load()
    for i in range(1, 5):
        assert cp.get("sources", f"name{i}")


# ── 파일 오버라이드 ─────────────────────────────────────────────

def test_load_overrides_ip_from_file(conf_path):
    """conf 파일에 ip=10.0.0.1 저장 후 load() → ip=10.0.0.1"""
    cm.save_conf({"atem": {"ip": "10.0.0.1", "port": "9910", "simulator_mode": "false"}})
    cp = cm.load()
    assert cp.get("atem", "ip") == "10.0.0.1"


def test_load_partial_override_keeps_other_defaults(conf_path):
    """atem 섹션만 저장 → server 섹션은 기본값 유지"""
    cm.save_conf({"atem": {"ip": "10.0.0.99", "port": "9910", "simulator_mode": "false"}})
    cp = cm.load()
    assert cp.getint("server", "port") == 8000


# ── save_conf ──────────────────────────────────────────────────

def test_save_conf_creates_file(conf_path):
    """save_conf() 호출 후 conf 파일이 생성됨"""
    cm.save_conf({"atem": {"ip": "1.2.3.4", "port": "9910", "simulator_mode": "false"}})
    assert os.path.exists(conf_path)


def test_save_conf_roundtrip(conf_path):
    """저장한 값을 다시 load() 하면 동일한 값 반환"""
    body = {
        "atem":      {"ip": "172.16.0.1", "port": "9911", "simulator_mode": "true"},
        "server":    {"host": "127.0.0.1", "port": "9000"},
        "switching": {"transition_rate_frames": "30", "device_sync_interval": "5"},
        "sources":   {"name1": "카메라", "name2": "PPT", "name3": "화면", "name4": "없음"},
    }
    cm.save_conf(body)
    cp = cm.load()
    assert cp.get("atem", "ip") == "172.16.0.1"
    assert cp.getint("atem", "port") == 9911
    assert cp.getboolean("atem", "simulator_mode") is True
    assert cp.get("server", "host") == "127.0.0.1"
    assert cp.getint("server", "port") == 9000
    assert cp.getint("switching", "transition_rate_frames") == 30
    assert cp.get("sources", "name1") == "카메라"


def test_save_conf_updates_existing(conf_path):
    """두 번 save_conf() 호출 시 두 번째 값이 반영됨"""
    cm.save_conf({"atem": {"ip": "1.1.1.1", "port": "9910", "simulator_mode": "false"}})
    cm.save_conf({"atem": {"ip": "2.2.2.2", "port": "9910", "simulator_mode": "false"}})
    cp = cm.load()
    assert cp.get("atem", "ip") == "2.2.2.2"


# ── delete_conf ────────────────────────────────────────────────

def test_delete_conf_removes_file(conf_path):
    """파일 생성 후 delete_conf() → 파일 삭제됨, True 반환"""
    cm.save_conf({"atem": {"ip": "1.2.3.4", "port": "9910", "simulator_mode": "false"}})
    assert os.path.exists(conf_path)
    result = cm.delete_conf()
    assert result is True
    assert not os.path.exists(conf_path)


def test_delete_conf_returns_false_when_no_file(conf_path):
    """파일 없을 때 delete_conf() → False 반환"""
    assert not os.path.exists(conf_path)
    result = cm.delete_conf()
    assert result is False


def test_delete_then_load_returns_defaults(conf_path):
    """save → delete → load() 시 기본값 반환"""
    cm.save_conf({"atem": {"ip": "9.9.9.9", "port": "9910", "simulator_mode": "true"}})
    cm.delete_conf()
    cp = cm.load()
    assert cp.get("atem", "ip") == "192.168.0.240"
    assert cp.getboolean("atem", "simulator_mode") is False


# ── 모듈 상수 ──────────────────────────────────────────────────

def test_base_dir_is_nonempty_string():
    """BASE_DIR 은 비어있지 않은 문자열"""
    assert isinstance(cm.BASE_DIR, str)
    assert len(cm.BASE_DIR) > 0


def test_presets_file_ends_with_presets_json():
    """PRESETS_FILE 상수는 'presets.json'으로 끝남"""
    assert cm.PRESETS_FILE.endswith("presets.json")
