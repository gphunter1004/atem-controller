"""PresetService 단위 테스트 (각 테스트마다 독립 파일 사용)"""

import json
import time
import pytest
import service.preset_service as ps_module
from service.preset_service import PresetService
from model.preset import PresetCreate


# ── 독립 PresetService 픽스처 ────────────────────────────────

@pytest.fixture()
def svc(tmp_path):
    """각 테스트 전용 PresetService — 독립된 임시 파일 사용."""
    f = tmp_path / "presets.json"
    f.write_text('{"presets": []}', encoding="utf-8")
    original = ps_module.PRESETS_FILE
    ps_module.PRESETS_FILE = str(f)
    s = PresetService()
    yield s, str(f)
    ps_module.PRESETS_FILE = original


def _new(name="테스트", pgm=1, **kw):
    return PresetCreate(name=name, label="", pgm=pgm, **kw)


# ── CRUD ──────────────────────────────────────────────────────

def test_add_and_list(svc):
    """프리셋 추가(name='A', pgm=1) 후 list_presets()에 1개 포함, id=1 할당"""
    s, _ = svc
    p = s.add_preset(_new("A"))
    assert p.id == 1
    assert p.name == "A"
    assert len(s.list_presets()) == 1


def test_add_increments_id(svc):
    """두 번 추가 시 두 번째 id = 첫 번째 id + 1"""
    s, _ = svc
    p1 = s.add_preset(_new("A"))
    p2 = s.add_preset(_new("B"))
    assert p2.id == p1.id + 1


def test_get_preset_returns_correct(svc):
    """name='X', pgm=3으로 추가한 프리셋을 id로 조회하면 동일 값 반환"""
    s, _ = svc
    p = s.add_preset(_new("X", pgm=3))
    found = s.get_preset(p.id)
    assert found is not None
    assert found.pgm == 3
    assert found.name == "X"


def test_get_preset_missing_returns_none(svc):
    """존재하지 않는 id=999 조회 시 None 반환"""
    s, _ = svc
    assert s.get_preset(999) is None


def test_delete_existing(svc):
    """추가한 프리셋 삭제 시 True 반환, 이후 list_presets() 빈 목록"""
    s, _ = svc
    p = s.add_preset(_new())
    assert s.delete_preset(p.id) is True
    assert s.get_preset(p.id) is None
    assert len(s.list_presets()) == 0


def test_delete_nonexistent_returns_false(svc):
    """존재하지 않는 id=999 삭제 시 False 반환"""
    s, _ = svc
    assert s.delete_preset(999) is False


def test_delete_only_target(svc):
    """id=p1 삭제 후 id=p2는 목록에 유지됨"""
    s, _ = svc
    p1 = s.add_preset(_new("A"))
    p2 = s.add_preset(_new("B"))
    s.delete_preset(p1.id)
    remaining = s.list_presets()
    assert len(remaining) == 1
    assert remaining[0].id == p2.id


# ── 파일 영속성 ───────────────────────────────────────────────

def test_persists_to_file(svc):
    """add_preset() 후 JSON 파일에 name='저장테스트' 데이터가 기록됐는지 확인"""
    s, path = svc
    s.add_preset(_new("저장테스트"))
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    assert len(raw["presets"]) == 1
    assert raw["presets"][0]["name"] == "저장테스트"


def test_new_instance_reads_existing_file(svc):
    """같은 파일을 가리키는 새 PresetService 인스턴스가 기존 데이터를 자동 로드"""
    s, _ = svc
    s.add_preset(_new("기존데이터"))
    s2 = PresetService()
    names = [p.name for p in s2.list_presets()]
    assert "기존데이터" in names


# ── Hot reload ────────────────────────────────────────────────

def test_hot_reload_on_external_change(svc):
    """파일 mtime이 바뀌면 list_presets() 호출 시 id=99 데이터를 자동 재로드"""
    s, path = svc
    time.sleep(0.05)  # mtime 차이 확보
    data = {
        "presets": [
            {"id": 99, "name": "외부추가", "label": "", "pgm": 2, "confirm": False}
        ]
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    result = s.list_presets()
    assert any(p.id == 99 for p in result)


# ── 오류 복구 ─────────────────────────────────────────────────

def test_invalid_json_recovery(svc):
    """파일 내용이 유효하지 않은 JSON일 때 _load() 후 빈 목록으로 복구"""
    s, path = svc
    with open(path, "w", encoding="utf-8") as f:
        f.write("이것은 JSON이 아닙니다!!!")
    s._load()
    assert s.list_presets() == []


def test_missing_file_returns_empty(tmp_path):
    """PRESETS_FILE 경로에 파일이 없으면 list_presets()가 빈 목록 반환"""
    original = ps_module.PRESETS_FILE
    ps_module.PRESETS_FILE = str(tmp_path / "nonexistent.json")
    try:
        s = PresetService()
        assert s.list_presets() == []
    finally:
        ps_module.PRESETS_FILE = original


# ── 필드 검증 ─────────────────────────────────────────────────

def test_confirm_field_default_false(svc):
    """confirm 미지정 시 기본값 False"""
    s, _ = svc
    p = s.add_preset(_new())
    assert p.confirm is False


def test_confirm_field_true(svc):
    """confirm=True 로 생성 시 저장/조회 후에도 True 유지"""
    s, _ = svc
    p = s.add_preset(_new(confirm=True))
    assert p.confirm is True


def test_keyer_keyup(svc):
    """keyer={mode='keyup', source=2} 로 생성 시 keyer 필드 정상 저장"""
    from model.preset import KeyerConfig
    s, _ = svc
    keyer = KeyerConfig(mode="keyup", source=2)
    p = s.add_preset(_new(keyer=keyer))
    assert p.keyer is not None
    assert p.keyer.mode == "keyup"
    assert p.keyer.source == 2
