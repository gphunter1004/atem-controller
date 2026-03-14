"""
simulator/atem_udp_server.py — ATEM Binary UDP 프로토콜 서버

simulator_mode=true 일 때 포트 9910 (설정 가능) 에서 BlackMagic ATEM UDP 프로토콜을
구현해 PC-B 의 PyATEMMax 클라이언트가 실제 장비처럼 연결할 수 있게 한다.

ATEM UDP 패킷 헤더 (12 bytes, big-endian):
  [0-1]   (flags<<11) | total_length
  [2-3]   session_id
  [4-5]   ack'd remote packet ID
  [6-7]   resend packet ID (보통 0)
  [8-9]   0x0000
  [10-11] local packet ID (송신 카운터)

플래그 (5-bit field, bits 15-11):
  0x01 = ackRequest     0x02 = helloPacket
  0x04 = resend         0x08 = requestNextAfter
  0x10 = ack

명령 블록 (패킷 헤더 뒤에 연속):
  [0-1] 블록 전체 길이   [2-3] 0x0000   [4-7] 4문자 명령코드   [8+] 데이터
"""
import struct
import socket
import threading
import time
import logging
from typing import Callable, Dict, List, Optional, Tuple

log = logging.getLogger("ATEMUDPServer")

# ── 프로토콜 상수 ────────────────────────────────────────────────
HDR_LEN     = 12
CMD_HDR_LEN = 8

FLAG_ACK_REQ  = 0x01   # ackRequest
FLAG_HELLO    = 0x02   # helloPacket
FLAG_RESEND   = 0x04
FLAG_REQ_NEXT = 0x08   # requestNextAfter
FLAG_ACK      = 0x10   # ack

STYLE_MAP    = {"MIX": 0, "DIP": 1, "WIPE": 2, "DVE": 3, "STING": 4}
KTYPE_MAP    = {"luma": 0, "chroma": 1, "pattern": 2, "dve": 3}
STYLE_NAMES  = ["MIX", "DIP", "WIPE", "DVE", "STING"]
KTYPE_NAMES  = ["luma", "chroma", "pattern", "dve"]


# ── 패킷 빌더 헬퍼 ───────────────────────────────────────────────
def _hdr(flags: int, length: int, session: int,
         ack_id: int = 0, resend_id: int = 0, pkt_id: int = 0) -> bytes:
    word0 = (flags << 11) | (length & 0x7FF)
    return struct.pack(">HHHHHH", word0, session, ack_id, resend_id, 0, pkt_id)


def _cmd(code: str, data: bytes) -> bytes:
    """ATEM 명령 블록 생성 (8-byte 헤더 + 데이터)"""
    block_len = CMD_HDR_LEN + len(data)
    return struct.pack(">HH4s", block_len, 0, code.encode("ascii")) + data


# ── 세션 ─────────────────────────────────────────────────────────
class _Session:
    __slots__ = ("session_id", "addr", "pkt_counter", "last_remote", "init_done")

    def __init__(self, session_id: int, addr: Tuple[str, int]):
        self.session_id  = session_id
        self.addr        = addr
        self.pkt_counter = 0
        self.last_remote = 0
        self.init_done   = False

    def next_pkt_id(self) -> int:
        self.pkt_counter += 1
        return self.pkt_counter


# ── 메인 서버 클래스 ──────────────────────────────────────────────
class ATEMUDPServer:
    """
    ATEM Mini UDP 프로토콜 서버.
    ATEMSimulator 인스턴스를 래핑해 ATEM 장비처럼 동작한다.
    """

    def __init__(self, sim):
        self._sim = sim
        self._sock: Optional[socket.socket] = None
        self._running  = False
        self._thread:  Optional[threading.Thread] = None
        self._lock     = threading.Lock()
        self._sessions:       Dict[int, _Session]              = {}
        self._addr_to_sid:    Dict[Tuple[str, int], int]       = {}
        self._next_session    = 0x9AC0

        # ATEMSimulator 의 상태 변경 콜백 등록 (auto 전환 완료 알림용)
        if hasattr(sim, '_state_change_cb'):
            sim._state_change_cb = self._on_sim_change

    # ── 공개 API ──────────────────────────────────────────────────
    def start(self, port: int = 9910):
        if self._running:
            return
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("0.0.0.0", port))
            sock.settimeout(0.5)
            self._sock = sock
        except OSError as e:
            print(f"[ATEM UDP] 포트 바인드 실패 {port}: {e}", flush=True)
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="ATEMUDPServer")
        self._thread.start()
        print(f"[ATEM UDP] 시뮬레이터 UDP 서버 시작 포트:{port}", flush=True)

    def stop(self):
        self._running = False
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass

    # ── 수신 루프 ─────────────────────────────────────────────────
    def _run(self):
        while self._running:
            try:
                data, addr = self._sock.recvfrom(10240)
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                self._handle_packet(data, addr)
            except Exception as e:
                log.debug(f"[ATEM UDP] 패킷 처리 오류 {addr}: {e}")

    # ── 패킷 처리 ─────────────────────────────────────────────────
    def _handle_packet(self, data: bytes, addr: Tuple[str, int]):
        if len(data) < HDR_LEN:
            return

        word0      = struct.unpack_from(">H", data, 0)[0]
        flags      = word0 >> 11
        pkt_len    = word0 & 0x7FF
        session_id = struct.unpack_from(">H", data, 2)[0]
        ack_id     = struct.unpack_from(">H", data, 4)[0]
        pkt_id     = struct.unpack_from(">H", data, 10)[0]

        # ── Hello: 신규 또는 재접속 ──────────────────────────────
        if flags & FLAG_HELLO:
            self._on_hello(addr)
            return

        # ── 세션 조회 ─────────────────────────────────────────────
        with self._lock:
            sid = self._addr_to_sid.get(addr)
            if sid is None:
                return
            sess = self._sessions.get(sid)
        if not sess:
            return

        sess.last_remote = pkt_id

        # ── ACK (flags=0x10): 우리 패킷에 대한 응답 → 무시 ─────────
        if flags & FLAG_ACK:
            return

        # ── ackRequest (flags=0x01): ACK 로 응답 ───────────────────
        if flags & FLAG_ACK_REQ:
            self._send_ack(sess, pkt_id)

        # ── requestNextAfter (flags=0x08): 재전송 요청 → 무시 ──────
        if flags & FLAG_REQ_NEXT:
            return

        # ── 명령 블록 파싱 ─────────────────────────────────────────
        payload_end = min(pkt_len, len(data))
        if payload_end > HDR_LEN:
            self._parse_commands(data[HDR_LEN:payload_end], sess)

    # ── Hello 핸드셰이크 ─────────────────────────────────────────
    def _on_hello(self, addr: Tuple[str, int]):
        with self._lock:
            # 기존 세션 정리 후 새 세션 발급
            old_sid = self._addr_to_sid.get(addr)
            if old_sid is not None:
                del self._sessions[old_sid]

            sid = self._next_session
            self._next_session = (self._next_session + 3) & 0xFFFF or 0x0001
            sess = _Session(sid, addr)
            self._sessions[sid] = sess
            self._addr_to_sid[addr] = sid

        # Server Hello 응답: flags=HELLO, length=20, bookStatus=2
        extra = bytearray(8)
        extra[0] = 0x02   # bookStatus = 2 (accepted)
        extra[3] = 0x01   # connection count
        resp = _hdr(FLAG_HELLO, 20, sid) + bytes(extra)
        self._sock.sendto(resp, addr)

        # 초기 상태 덤프 전송 (별도 스레드)
        threading.Thread(target=self._send_init, args=(sess,),
                         daemon=True).start()

    # ── ACK 전송 ──────────────────────────────────────────────────
    def _send_ack(self, sess: _Session, remote_pkt_id: int):
        pkt = _hdr(FLAG_ACK, HDR_LEN, sess.session_id, ack_id=remote_pkt_id)
        self._sock.sendto(pkt, sess.addr)

    # ── 초기 상태 덤프 ───────────────────────────────────────────
    def _send_init(self, sess: _Session):
        time.sleep(0.05)   # 핸드셰이크 ACK 도착 대기
        st = self._sim.state

        # ─ 패킷 1: 버전/모델/토폴로지/PGM/PVW ────────────────────
        pin_str = b"ATEM Mini Simulator"
        pin_data = pin_str + b"\x00" * (44 - len(pin_str))

        body1  = _cmd("_ver", struct.pack(">HH", 2, 30))
        body1 += _cmd("_pin", pin_data)
        body1 += _cmd("_top", struct.pack(">BBBBBBBBBB", 1, 4, 2, 1, 0, 0, 1, 0, 0, 0))
        body1 += _cmd("PrgI", struct.pack(">BBH", 0, 0, st.pgm))
        body1 += _cmd("PrvI", struct.pack(">BBH", 0, 0, st.pvw))

        pid1 = sess.next_pkt_id()
        self._sock.sendto(
            _hdr(FLAG_ACK_REQ, HDR_LEN + len(body1), sess.session_id, pkt_id=pid1) + body1,
            sess.addr)

        time.sleep(0.01)

        # ─ 패킷 2: 전환/키어 상태 ────────────────────────────────
        style_n = STYLE_MAP.get(st.transition_style.upper(), 0)
        ktype_n = KTYPE_MAP.get(st.keyer_type.lower(), 0)

        body2  = _cmd("TrSS", struct.pack(">BBBBBBBB",
                      0, style_n, 0x01, style_n, 0x01, 0, 0, 0))
        body2 += _cmd("TMxP", struct.pack(">BBH", 0, st.transition_rate, 0))
        body2 += _cmd("KeOn", struct.pack(">BBBB",
                      0, 0, 0x01 if st.keyer_on else 0x00, 0))

        # KeBP: me, keyer, type, pad, pad, fly, fill(U16), key(U16), masked, pad,
        #        top(S16), bottom(S16), left(S16), right(S16)
        body2 += _cmd("KeBP", struct.pack(">BBBBBBHHBBhhhh",
                      0, 0, ktype_n, 0, 0, 0,
                      st.pip_src, st.pip_src,
                      0, 0, 0, 0, 0, 0))

        # KeDV: me, keyer, pad(H), sizeX(U32), sizeY(U32), posX(S32), posY(S32), +zeros
        kedv_head = struct.pack(">BBHIIii",
                                0, 0, 0,
                                int(st.dve_size * 1000),
                                int(st.dve_size * 1000),
                                int(st.dve_pos_x * 1000),
                                int(st.dve_pos_y * 1000))
        body2 += _cmd("KeDV", kedv_head + bytes(64 - len(kedv_head)))

        pid2 = sess.next_pkt_id()
        self._sock.sendto(
            _hdr(FLAG_ACK_REQ, HDR_LEN + len(body2), sess.session_id, pkt_id=pid2) + body2,
            sess.addr)

        time.sleep(0.01)

        # ─ 패킷 3: InCm (초기화 완료 신호) ──────────────────────
        # PyATEMMax 파서: cmdLength > 8 이어야 핸들러 호출 → 4바이트 더미 필요
        incm_data = b"\x00\x00\x00\x00"
        pid3 = sess.next_pkt_id()
        self._sock.sendto(
            _hdr(FLAG_ACK_REQ, HDR_LEN + CMD_HDR_LEN + len(incm_data), sess.session_id, pkt_id=pid3)
            + _cmd("InCm", incm_data),
            sess.addr)

        sess.init_done = True
        log.debug(f"[ATEM UDP] 초기 상태 전송 완료 → {sess.addr}")

    # ── 클라이언트 명령 파싱 ─────────────────────────────────────
    def _parse_commands(self, body: bytes, sess: _Session):
        idx = 0
        while idx < len(body):
            if idx + CMD_HDR_LEN > len(body):
                break
            blk_len = struct.unpack_from(">H", body, idx)[0]
            if blk_len < CMD_HDR_LEN or idx + blk_len > len(body):
                break
            code = body[idx + 4: idx + 8].decode("ascii", errors="replace")
            data = body[idx + 8: idx + blk_len]
            self._dispatch(code, data, sess)
            idx += blk_len

    def _dispatch(self, code: str, data: bytes, sess: _Session):
        sim     = self._sim
        changed: List[str] = []

        try:
            if code == "CPgI" and len(data) >= 4:
                src = struct.unpack_from(">H", data, 2)[0]
                sim.setProgramInputVideoSource(0, src)
                changed.append("pgm")

            elif code == "CPvI" and len(data) >= 4:
                src = struct.unpack_from(">H", data, 2)[0]
                sim.setPreviewInputVideoSource(0, src)
                changed.append("pvw")

            elif code == "DCut":
                sim.performCutME(0)
                changed += ["pgm", "pvw"]

            elif code == "DAut":
                sim.performAutoME(0)
                # auto 완료는 콜백(_on_sim_change)에서 처리

            elif code == "CTTp" and len(data) >= 4:
                if data[0] & 0x01:   # style 비트
                    v = data[2]
                    sim.setTransitionStyle(0, STYLE_NAMES[v] if v < len(STYLE_NAMES) else "MIX")
                    changed.append("trss")

            elif code == "CTMx" and len(data) >= 2:
                sim.setMixTransitionRate(0, data[1])
                changed.append("tmxp")

            elif code == "CKOn" and len(data) >= 3:
                sim.setKeyerOnAir(0, 0, bool(data[2]))
                changed.append("keon")

            elif code == "CKTp" and len(data) >= 4:
                if data[0] & 0x01:   # type 비트
                    v = data[3]
                    sim.setKeyerType(0, 0, KTYPE_NAMES[v] if v < len(KTYPE_NAMES) else "luma")
                    changed.append("kebp")

            elif code == "CKeF" and len(data) >= 4:
                src = struct.unpack_from(">H", data, 2)[0]
                sim.setKeyerFillInputVideoSource(0, 0, src)
                changed.append("kebp")

            elif code == "CKDV" and len(data) >= 24:
                fb = data[3]   # flags byte
                if fb & 0x01:
                    sim.setKeyerDVESizeX(0, 0, struct.unpack_from(">I", data, 8)[0] / 1000.0)
                    changed.append("kedv")
                if fb & 0x02:
                    sim.setKeyerDVESizeY(0, 0, struct.unpack_from(">I", data, 12)[0] / 1000.0)
                    changed.append("kedv")
                if fb & 0x04:
                    sim.setKeyerDVEPositionX(0, 0, struct.unpack_from(">i", data, 16)[0] / 1000.0)
                    changed.append("kedv")
                if fb & 0x08:
                    sim.setKeyerDVEPositionY(0, 0, struct.unpack_from(">i", data, 20)[0] / 1000.0)
                    changed.append("kedv")

        except Exception as e:
            log.debug(f"[ATEM UDP] 명령 오류 [{code}]: {e}")
            return

        if changed and sess.init_done:
            self._push_state(changed)

    # ── 상태 변경 시 모든 클라이언트에 push ───────────────────────
    def _push_state(self, changed: List[str]):
        """변경된 항목을 모든 연결된 클라이언트에 전송"""
        st   = self._sim.state
        body = b""

        if "pgm" in changed:
            body += _cmd("PrgI", struct.pack(">BBH", 0, 0, st.pgm))
        if "pvw" in changed:
            body += _cmd("PrvI", struct.pack(">BBH", 0, 0, st.pvw))
        if "trss" in changed:
            s = STYLE_MAP.get(st.transition_style.upper(), 0)
            body += _cmd("TrSS", struct.pack(">BBBBBBBB", 0, s, 0x01, s, 0x01, 0, 0, 0))
        if "tmxp" in changed:
            body += _cmd("TMxP", struct.pack(">BBH", 0, st.transition_rate, 0))
        if "keon" in changed:
            body += _cmd("KeOn", struct.pack(">BBBB",
                         0, 0, 0x01 if st.keyer_on else 0x00, 0))
        if "kebp" in changed:
            t = KTYPE_MAP.get(st.keyer_type.lower(), 0)
            body += _cmd("KeBP", struct.pack(">BBBBBBHHBBhhhh",
                         0, 0, t, 0, 0, 0, st.pip_src, st.pip_src, 0, 0, 0, 0, 0, 0))
        if "kedv" in changed:
            head = struct.pack(">BBHIIii", 0, 0, 0,
                               int(st.dve_size * 1000), int(st.dve_size * 1000),
                               int(st.dve_pos_x * 1000), int(st.dve_pos_y * 1000))
            body += _cmd("KeDV", head + bytes(64 - len(head)))

        if not body:
            return

        with self._lock:
            sessions = [s for s in self._sessions.values() if s.init_done]

        for sess in sessions:
            pid = sess.next_pkt_id()
            pkt = _hdr(FLAG_ACK_REQ, HDR_LEN + len(body), sess.session_id, pkt_id=pid) + body
            try:
                self._sock.sendto(pkt, sess.addr)
            except Exception:
                pass

    # ── ATEMSimulator 콜백 (auto 전환 완료 시 호출됨) ────────────
    def _on_sim_change(self, changed: List[str]):
        if not self._running:
            return
        with self._lock:
            any_connected = any(s.init_done for s in self._sessions.values())
        if any_connected:
            self._push_state(changed)
