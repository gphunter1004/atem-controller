# service/tcl_service.py
"""TCL TV 입력 전환 비즈니스 로직 (멀티 TV, async)."""

import logging
import config as _config
import controller.tcl_controller as _ctrl

logger = logging.getLogger("atem.tcl")


class TCLService:

    def _tvs(self):      return _config.TCL_TVS
    def _port(self):     return _config.TCL_PORT
    def _commands(self): return _config.TCL_INPUT_COMMANDS
    def _names(self):    return _config.TCL_INPUT_NAMES

    # ── 단일 TV 입력 전환 ──────────────────────────────────────
    async def switch_input(self, tv_index: int, input_index: int) -> dict:
        tvs      = self._tvs()
        commands = self._commands()
        names    = self._names()

        if tv_index < 1 or tv_index > len(tvs):
            return {"ok": False, "message": f"잘못된 TV 번호: {tv_index}"}
        if input_index < 1 or input_index > len(commands):
            return {"ok": False, "message": f"잘못된 입력 번호: {input_index}"}

        tv    = tvs[tv_index - 1]
        cmd   = commands[input_index - 1]
        iname = names[input_index - 1] if input_index <= len(names) else f"입력{input_index}"

        if not cmd:
            return {"ok": False, "message": f"입력{input_index} 명령 미설정"}
        if not tv["ip"]:
            return {"ok": False, "message": f"TV{tv_index} IP 미설정"}

        ok, detail = await _ctrl.send_command(tv["ip"], self._port(), cmd)
        msg = f"{tv['name']} → {iname} {'성공' if ok else '실패'}"
        if not ok:
            msg += f" ({detail})"
        return {
            "ok":     ok,
            "tv":     tv["name"],
            "input":  iname,
            "detail": detail,
            "message": msg,
        }

    # ── 전체 TV 입력 전환 ──────────────────────────────────────
    async def switch_input_all(self, input_index: int) -> dict:
        import asyncio
        tvs = self._tvs()
        tasks = [
            self.switch_input(i + 1, input_index)
            for i in range(len(tvs))
            if tvs[i]["ip"]
        ]
        results = await asyncio.gather(*tasks)
        return {"ok": all(r["ok"] for r in results), "results": list(results)}

    # ── 페어링 ────────────────────────────────────────────────
    async def start_pairing(self, tv_index: int) -> dict:
        tvs = self._tvs()
        if tv_index < 1 or tv_index > len(tvs):
            return {"ok": False, "message": f"잘못된 TV 번호: {tv_index}"}
        tv = tvs[tv_index - 1]
        if not tv["ip"]:
            return {"ok": False, "message": f"TV{tv_index} IP 미설정"}
        try:
            await _ctrl.start_pairing(tv["ip"])
            return {"ok": True, "tv": tv["name"], "message": f"{tv['name']} TV 화면에서 PIN을 확인하세요."}
        except Exception as e:
            return {"ok": False, "tv": tv["name"], "message": f"페어링 시작 실패: {e}"}

    async def finish_pairing(self, tv_index: int, pin: str) -> dict:
        tvs = self._tvs()
        if tv_index < 1 or tv_index > len(tvs):
            return {"ok": False, "message": f"잘못된 TV 번호: {tv_index}"}
        tv = tvs[tv_index - 1]
        if not tv["ip"]:
            return {"ok": False, "message": f"TV{tv_index} IP 미설정"}
        try:
            await _ctrl.finish_pairing(tv["ip"], pin)
            return {"ok": True, "tv": tv["name"], "message": f"{tv['name']} 페어링 완료!"}
        except Exception as e:
            return {"ok": False, "tv": tv["name"], "message": f"페어링 실패: {e}"}

    # ── 상태 조회 ─────────────────────────────────────────────
    async def get_status(self) -> dict:
        import asyncio

        async def _false(): return False

        tvs  = self._tvs()
        port = self._port()
        reachable = await asyncio.gather(*[
            _ctrl.ping(tv["ip"], port) if tv["ip"] else _false()
            for tv in tvs
        ])
        tv_status = [
            {"index": i+1, "name": tv["name"], "ip": tv["ip"], "reachable": reachable[i]}
            for i, tv in enumerate(tvs)
        ]
        return {
            "enabled":     _config.TCL_ENABLED,
            "port":        port,
            "tvs":         tv_status,
            "input_names": self._names(),
            "input_cmds":  self._commands(),
        }


# 싱글톤
tcl_service = TCLService()
