// BASE, updateConnInfo, setWsOnline, setAtemOnline, updateWsCount,
// reconnect, loadAtemAddr 는 header.js 에서 제공

let keyerSrc   = 1;
let pipSrc     = 1;
let presets    = [];
let lastStatus = null;
const pipPos = {
  tl: [-12.0,  7.0],
  tr: [ 12.0,  7.0],
  bl: [-12.0, -7.0],
  br: [ 12.0, -7.0]
};
let selectedPos = 'tr'; // 기본 우상단

function getBase() { return BASE; }

// ── API 호출 ──────────────────────────────────
async function call(method, path, body = null) {
  const ts = new Date().toTimeString().slice(0, 8);
  try {
    const res = await fetch(getBase() + path, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : null
    });
    const data = await res.json();
    if (!res.ok) {
      addLog(ts, false, `${method} ${path} → HTTP ${res.status}: ${data.detail || JSON.stringify(data)}`);
      return null;
    }
    addLog(ts, true, `${method} ${path} → ${JSON.stringify(data)}`);
    if (data.pgm !== undefined) updateStatus(data);
    return data;
  } catch (e) {
    addLog(ts, false, `${method} ${path} → ${e.message}`);
  }
}

// ── 기능 ──────────────────────────────────────
function directPgm(src)     { call('POST', '/switching/pgm', { source: src }); }
function setPvw(src)         { call('POST', '/switching/pvw', { source: src }); }
function doTransition(type)  { call('POST', `/switching/${type}`); }
function setTransStyle(style){ call('POST', '/switching/style', { style }); }
function keyOff()            { call('POST', '/key/off'); }
function runPreset(id)       { call('POST', `/preset/${id}`); }

function keyUp() {
  call('POST', '/key/up', { source: keyerSrc });
}

function pipOn() {
  const size = document.getElementById('pip-size').value / 100;
  const [px, py] = pipPos[selectedPos];
  call('POST', '/key/pip', { source: pipSrc, size, pos_x: px, pos_y: py });
}

function setKeyerSrc(src) {
  keyerSrc = src;
  document.getElementById('keyup-src').textContent = src;
  document.querySelectorAll('#keyer-src-grid .src-btn').forEach((b, i) => {
    b.classList.toggle('pgm-active', i + 1 === src);
  });
}

function setPipSrc(src) {
  pipSrc = src;
  document.getElementById('pip-src-label').textContent = src;
  document.querySelectorAll('#pip-src-grid .src-btn').forEach((b, i) => {
    b.classList.toggle('pgm-active', i + 1 === src);
  });
}

function setPipPos(pos, e) {
  selectedPos = pos;
  document.querySelectorAll('.pos-btn').forEach(b => b.classList.remove('sel'));
  e.target.classList.add('sel');
}

// ── 상태 동기화 ───────────────────────────────
async function fetchStatus() {
  if (_wsLive) return;   // WS로 실시간 수신 중이면 HTTP 폴링 불필요
  await call('GET', '/status'); // call() 내부에서 updateStatus 자동 호출
}

// ── 프리셋 핫리로드 ────────────────────────────
async function reloadPresets() {
  await call('POST', '/admin/reload');
  await loadPresets();
}

// ── 재연결 성공 콜백 (header.js reconnect() 에서 호출) ────────────
function _onReconnectSuccess(data) { updateStatus(data); }

function updateStatus(data) {
  lastStatus = data;
  document.getElementById('s-pgm').textContent  = `소스 ${data.pgm}`;
  document.getElementById('s-pvw').textContent  = `소스 ${data.pvw}`;
  document.getElementById('s-mode').textContent = data.mode;

  // KEYER 상태
  const keyerEl = document.getElementById('s-keyer');
  if (data.keyer_mode === 'keyup') {
    keyerEl.textContent = `KEY UP  S${data.pip_src}`;
    keyerEl.className = 'v keyer-on';
  } else if (data.keyer_mode === 'pip') {
    const pct = data.dve_size !== undefined ? Math.round(data.dve_size * 100) : '?';
    keyerEl.textContent = `PiP  S${data.pip_src}  ${pct}%`;
    keyerEl.className = 'v keyer-pip';
  } else {
    keyerEl.textContent = 'OFF';
    keyerEl.className = 'v keyer-off';
  }

  // TRAN 마지막 전환 타입
  const tranEl = document.getElementById('s-tran');
  if (data.last_transition === 'CUT') {
    tranEl.textContent = 'CUT';
    tranEl.className = 'v tran-cut';
  } else if (data.last_transition === 'AUTO') {
    tranEl.textContent = 'AUTO';
    tranEl.className = 'v tran-auto';
  } else {
    tranEl.textContent = '—';
    tranEl.className = 'v';
  }

  // CUT / AUTO 버튼 활성 표시
  document.getElementById('btn-cut').classList.toggle('active',  data.last_transition === 'CUT');
  document.getElementById('btn-auto').classList.toggle('active', data.last_transition === 'AUTO');

  // 키어 버튼 활성 표시
  document.getElementById('btn-keyup').classList.toggle('active',  data.keyer_mode === 'keyup');
  document.getElementById('btn-pip').classList.toggle('active',    data.keyer_mode === 'pip');
  document.getElementById('btn-keyoff').classList.toggle('active', data.keyer_mode === 'off');

  // 트랜지션 스타일 버튼 하이라이트
  ['MIX','DIP','WIPE','STING'].forEach(s => {
    const btn = document.getElementById('style-' + s);
    if (btn) btn.classList.toggle('active', data.transition_style === s);
  });

  // PGM 버튼 하이라이트
  document.querySelectorAll('#pgm-grid .src-btn').forEach((b, i) => {
    b.classList.toggle('pgm-active', i + 1 === data.pgm);
  });

  // PVW 버튼 하이라이트
  document.querySelectorAll('#pvw-grid .src-btn').forEach((b, i) => {
    b.classList.toggle('pvw-active', i + 1 === data.pvw);
  });

  // 키어 소스 동기화
  if (data.keyer_mode === 'keyup') {
    setKeyerSrc(data.pip_src);
  } else if (data.keyer_mode === 'pip') {
    setPipSrc(data.pip_src);
  }

  // PiP 슬라이더/위치 동기화
  if (data.keyer_mode === 'pip') {
    if (data.dve_size !== undefined) {
      const pct = Math.round(data.dve_size * 100);
      document.getElementById('pip-size').value = pct;
      document.getElementById('pip-size-v').textContent = pct + '%';
    }

    if (data.dve_pos_x !== undefined && data.dve_pos_y !== undefined) {
      for (const [pos, [x, y]] of Object.entries(pipPos)) {
        if (Math.abs(x - data.dve_pos_x) < 0.01 && Math.abs(y - data.dve_pos_y) < 0.01) {
          selectedPos = pos;
          document.querySelectorAll('.pos-btn').forEach(b => b.classList.remove('sel'));
          const order = ['tl', 'tr', 'bl', 'br'];
          const btn = document.querySelectorAll('.pos-btn')[order.indexOf(pos)];
          if (btn) btn.classList.add('sel');
          break;
        }
      }
    }
  }
  updateActivePreset(data);
  if (data.atem_connected !== undefined) setAtemOnline(data.atem_connected);
}

function updateActivePreset(s) {
  document.querySelectorAll('#preset-list .btn.preset').forEach(btn => {
    const id = Number(btn.getAttribute('data-id'));
    const p  = presets.find(x => x.id === id);
    const km = p?.keyer?.mode ?? 'off';
    const match = p &&
      p.pgm === s.pgm &&
      km === s.keyer_mode &&
      (km === 'off' || p.keyer.source === s.pip_src);
    btn.classList.toggle('active', match);
  });
}

// ── 프리셋 렌더링 ──────────────────────────────
async function loadPresets() {
  const data = await call('GET', '/presets');
  if (!data) return;

  presets = data.presets;

  const list = document.getElementById('preset-list');
  list.innerHTML = '';
  data.presets.forEach(p => {
    const row = document.createElement('div');
    row.className = 'preset-row';

    const btn = document.createElement('button');
    btn.className = 'btn preset';
    btn.dataset.id = p.id;
    btn.title = p.label || '';
    btn.textContent = p.description ? `${p.name} (${p.description})` : p.name;
    btn.addEventListener('click', () => runPreset(p.id));

    const del = document.createElement('button');
    del.className = 'preset-del';
    del.title = '삭제';
    del.textContent = '×';
    del.addEventListener('click', () => deletePreset(p.id));

    row.appendChild(btn);
    row.appendChild(del);
    list.appendChild(row);
  });
  if (lastStatus) updateActivePreset(lastStatus);
}

async function deletePreset(id) {
  await call('DELETE', `/presets/${id}`);
  await loadPresets();
}

// ── 프리셋 저장 (현재 상태 기반) ──────────────
async function savePreset() {
  const nameInput = document.getElementById('preset-name');
  const descInput = document.getElementById('preset-desc');
  const name = nameInput.value.trim();
  if (!name) { nameInput.focus(); return; }

  // lastStatus를 우선 사용 (추가 요청 없이 경쟁 조건 최소화)
  const status = lastStatus ?? await call('GET', '/status');
  if (!status) return;

  const keyer = buildKeyerConfig(status);
  const label = buildPresetLabel(status);
  const description = descInput.value.trim() || null;
  await call('POST', '/presets', { name, label, description, pgm: status.pgm, pvw: status.pvw, keyer });
  nameInput.value = '';
  descInput.value = '';
  await loadPresets();
}

function buildKeyerConfig(status) {
  if (status.keyer_mode === 'keyup') {
    return { mode: 'keyup', source: status.pip_src };
  }
  if (status.keyer_mode === 'pip') {
    const size = document.getElementById('pip-size').value / 100;
    const [pos_x, pos_y] = pipPos[selectedPos];
    return { mode: 'pip', source: status.pip_src, size, pos_x, pos_y };
  }
  return { mode: 'off' };
}

function buildPresetLabel(status) {
  const parts = [`PGM:소스${status.pgm}`];
  if (status.keyer_mode === 'keyup') parts.push(`KEY:소스${status.pip_src}`);
  if (status.keyer_mode === 'pip')   parts.push(`PiP:소스${status.pip_src}`);
  return parts.join(' / ');
}

// ── 로그 ──────────────────────────────────────
function addLog(ts, ok, msg) {
  const log = document.getElementById('log');
  const line = document.createElement('div');
  line.className = 'log-line';
  const tsEl  = document.createElement('span'); tsEl.className  = 'ts';  tsEl.textContent = ts;
  const stEl  = document.createElement('span'); stEl.className  = ok ? 'ok' : 'err'; stEl.textContent = ok ? 'OK' : 'ERR';
  const msgEl = document.createElement('span'); msgEl.className = 'msg'; msgEl.textContent = msg;
  line.appendChild(tsEl);
  line.appendChild(stEl);
  line.appendChild(msgEl);
  log.prepend(line);
  // 최대 100줄
  while (log.children.length > 100) log.removeChild(log.lastChild);
}

// ── WebSocket ─────────────────────────────────
let _ws = null;
let _wsRetry = null;
let _wsFallback = null;
let _wsDelay = 3000; // 재연결 대기 (지수 백오프: 3s → 6s → 12s → 최대 30s)
let _wsLive = false; // WS가 status를 수신 중인 동안 true → HTTP 폴링 불필요

function connectWS() {
  clearTimeout(_wsRetry);
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  _ws = new WebSocket(`${proto}//${location.host}/ws`);

  _ws.onopen = () => {
    _wsDelay = 3000; // 연결 성공 시 대기 초기화
    if (_wsFallback) { clearInterval(_wsFallback); _wsFallback = null; }
    setWsOnline(true);
  };

  _ws.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data);
      if (msg.type === 'welcome') {
        updateConnInfo(msg.ip, msg.id);
        updateWsCount(msg.ws_count);
        setWsOnline(true);
      }
      if (msg.type === 'status') {
        _wsLive = true;
        updateStatus(msg.data);
        if (msg.ws_count !== undefined) updateWsCount(msg.ws_count);
      }
      if (msg.type === 'log')    { addLog(msg.ts, true, `[액션] ${msg.msg}`); }
      if (msg.type === 'count')  { updateWsCount(msg.n); }
      if (msg.type === 'reload') { loadPresets(); }
    } catch (_) {}
  };

  _ws.onclose = () => {
    _ws = null;
    _wsLive = false;
    setWsOnline(false);
    setAtemOnline(false); // 연결 상태 불명 → 빨강 표시
    // WS 끊김 → 폴링 폴백 + 지수 백오프 재연결
    if (!_wsFallback) _wsFallback = setInterval(fetchStatus, 3000);
    _wsRetry = setTimeout(() => {
      _wsDelay = Math.min(_wsDelay * 2, 30000);
      connectWS();
    }, _wsDelay);
  };

  _ws.onerror = () => { _ws?.close(); };
}

// ── TCL TV 제어 ───────────────────────────────
let tclSelectedTv = 0; // 0 = ALL

async function loadTclPanel() {
  const tvContainer  = document.getElementById('tcl-tv-btns');
  const inContainer  = document.getElementById('tcl-input-btns');
  const msg          = document.getElementById('tcl-msg');

  const res = await call('GET', '/tcl/status');
  if (!res) {
    msg.textContent = 'TCL 상태를 불러오지 못했습니다.';
    msg.style.color = 'var(--red)';
    return;
  }

  if (!res.enabled) {
    msg.textContent = 'TCL 제어 비활성화 — 설정에서 활성화하세요.';
    msg.style.color = 'var(--muted)';
    return;
  }

  msg.textContent = '';

  // TV 버튼 생성
  tvContainer.innerHTML = '';
  const allBtn = _tclBtn('ALL', () => _tclSelectTv(0), tclSelectedTv === 0);
  tvContainer.appendChild(allBtn);
  res.tvs.forEach((tv, i) => {
    if (!tv.ip) return;
    const btn = _tclBtn(tv.name, () => _tclSelectTv(i + 1), tclSelectedTv === i + 1);
    btn.title = tv.ip;
    tvContainer.appendChild(btn);
  });

  // 입력 버튼 생성
  inContainer.innerHTML = '';
  res.input_names.forEach((name, i) => {
    if (!res.input_cmds[i]) return;
    const btn = _tclBtn(name, () => tclSwitchInput(i + 1));
    inContainer.appendChild(btn);
  });
}

function _tclBtn(label, onClick, active = false) {
  const b = document.createElement('button');
  b.className = 'btn' + (active ? ' style-btn active' : ' style-btn');
  b.style.cssText = 'margin-right:6px;margin-bottom:6px';
  b.textContent = label;
  b.addEventListener('click', onClick);
  return b;
}

function _tclSelectTv(index) {
  tclSelectedTv = index;
  // 버튼 active 상태 갱신
  const btns = document.getElementById('tcl-tv-btns').querySelectorAll('button');
  btns.forEach((b, i) => {
    const isActive = i === index;
    b.classList.toggle('active', isActive);
  });
}

async function tclSwitchInput(inputIndex) {
  let res;
  if (tclSelectedTv === 0) {
    res = await call('POST', '/tcl/input/all', { input: inputIndex });
  } else {
    res = await call('POST', '/tcl/input', { tv: tclSelectedTv, input: inputIndex });
  }
  if (!res) return;

  const msg = document.getElementById('tcl-msg');
  if (res.results) {
    msg.innerHTML = res.results.map(r =>
      `<span style="color:${r.ok ? 'var(--green)' : 'var(--red)'}">${r.message}</span>`
    ).join('<br>');
  } else {
    msg.textContent = res.message || '';
    msg.style.color = res.ok ? 'var(--green)' : 'var(--red)';
  }
}

// ── 초기화 ────────────────────────────────────
setKeyerSrc(1);
setPipSrc(1);
fetchStatus();                   // 페이지 오픈 시 HTTP로 즉시 상태 조회
loadPresets();
loadAtemAddr();                  // ATEM IP 표시 (header.js 제공)
connectWS();                     // 이후 상태 변경은 WS로 수신
setInterval(loadPresets, 10000); // 프리셋 목록 10초마다 갱신
loadTclPanel();                  // TCL TV 패널 초기화
