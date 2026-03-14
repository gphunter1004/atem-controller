import json
import os
from typing import Optional
from model.preset import Preset, PresetCreate
from model.state import state
from conf_manager import PRESETS_FILE  # exe/개발 모드 모두 올바른 경로 사용


class PresetService:

    def __init__(self):
        self._presets: list[Preset] = []
        self._mtime: float = 0.0
        self._load()

    # ── 파일 I/O ──────────────────────────────────
    def _load(self):
        if not os.path.exists(PRESETS_FILE):
            self._presets = []
            return
        self._mtime = os.path.getmtime(PRESETS_FILE)
        try:
            with open(PRESETS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._presets = [Preset(**p) for p in data.get("presets", [])]
        except Exception as e:
            print(f"[PRESET] 파일 로드 오류: {e}", flush=True)
            self._presets = []

    def _reload_if_changed(self):
        if os.path.exists(PRESETS_FILE) and os.path.getmtime(PRESETS_FILE) != self._mtime:
            self._load()

    def _save(self):
        data = {"presets": [p.model_dump() for p in self._presets]}
        with open(PRESETS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self._mtime = os.path.getmtime(PRESETS_FILE)

    # ── CRUD ──────────────────────────────────────
    def list_presets(self) -> list[Preset]:
        self._reload_if_changed()
        return self._presets

    def get_preset(self, preset_id: int) -> Optional[Preset]:
        self._reload_if_changed()
        for p in self._presets:
            if p.id == preset_id:
                return p
        return None

    def add_preset(self, data: PresetCreate) -> Preset:
        new_id = max((p.id for p in self._presets), default=0) + 1
        preset = Preset(id=new_id, **data.model_dump())
        self._presets.append(preset)
        self._save()
        return preset

    def delete_preset(self, preset_id: int) -> bool:
        before = len(self._presets)
        self._presets = [p for p in self._presets if p.id != preset_id]
        if len(self._presets) < before:
            self._save()
            return True
        return False

    # ── 실행 ──────────────────────────────────────
    def execute(self, preset: Preset):
        from service.atem_service import atem_service

        state.touch()  # 실행 시작 시 sync 억제 갱신 (다단계 명령 중 중간 상태 브로드캐스트 방지)
        state.mode = f"{preset.name} 실행"
        atem_service.direct_pgm(preset.pgm)

        if preset.pvw is not None:
            atem_service.set_pvw(preset.pvw)

        if preset.keyer is None or preset.keyer.mode == "off":
            atem_service.key_off()
        elif preset.keyer.mode == "keyup":
            atem_service.key_up(preset.keyer.source or 1)
        elif preset.keyer.mode == "pip":
            atem_service.pip_on(
                source=preset.keyer.source or 1,
                size=preset.keyer.size if preset.keyer.size is not None else 0.25,
                pos_x=preset.keyer.pos_x if preset.keyer.pos_x is not None else 12.0,
                pos_y=preset.keyer.pos_y if preset.keyer.pos_y is not None else 7.0,
            )


# 싱글톤
preset_service = PresetService()
