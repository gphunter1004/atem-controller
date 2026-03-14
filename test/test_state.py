"""ATEMState 단위 테스트"""

from model.state import ATEMState


def test_defaults():
    """초기값: pgm=1, pvw=2, keyer_mode='off', transition_style='MIX', atem_connected=False"""
    s = ATEMState()
    assert s.pgm == 1
    assert s.pvw == 2
    assert s.keyer_mode == "off"
    assert s.transition_style == "MIX"
    assert s.atem_connected is False


def test_to_dict_has_all_keys():
    """to_dict() 반환값에 11개 필드 전부 존재하는지 확인"""
    s = ATEMState()
    d = s.to_dict()
    expected_keys = {
        "pgm", "pvw", "pip_src", "mode", "keyer_mode",
        "dve_size", "dve_pos_x", "dve_pos_y",
        "last_transition", "transition_style", "atem_connected",
    }
    assert expected_keys == set(d.keys())


def test_to_dict_reflects_current_values():
    """필드 변경 후 to_dict()가 변경된 값을 반환하는지 확인 (pgm=3, pvw=4, keyer_mode='keyup')"""
    s = ATEMState()
    s.pgm = 3
    s.pvw = 4
    s.keyer_mode = "keyup"
    s.pip_src = 2
    s.atem_connected = True
    d = s.to_dict()
    assert d["pgm"] == 3
    assert d["pvw"] == 4
    assert d["keyer_mode"] == "keyup"
    assert d["pip_src"] == 2
    assert d["atem_connected"] is True


def test_touch_suppresses_sync():
    """touch() 호출 후 sync_suppressed(window=1.0)가 True 반환하는지 확인"""
    s = ATEMState()
    assert not s.sync_suppressed()
    s.touch()
    assert s.sync_suppressed()


def test_sync_suppressed_zero_window_always_false():
    """window=0.0이면 touch() 직후에도 억제되지 않음 (이미 만료된 window)"""
    s = ATEMState()
    s.touch()
    assert not s.sync_suppressed(window=0.0)


def test_sync_suppressed_large_window_after_touch():
    """touch() 직후 window=60.0이면 억제 상태 유지"""
    s = ATEMState()
    s.touch()
    assert s.sync_suppressed(window=60.0)


def test_multiple_instances_are_independent():
    """인스턴스 a의 pgm=3 변경이 인스턴스 b에 영향 없음 (싱글톤 아닌 독립 인스턴스 확인)"""
    a = ATEMState()
    b = ATEMState()
    a.pgm = 3
    assert b.pgm == 1
