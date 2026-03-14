// BASE, updateConnInfo, setWsOnline, setAtemOnline, updateWsCount,
// reconnect, loadAtemAddr 는 header.js 에서 제공

let presets = [];
let status  = null;

// ── 프리셋 로드 (10초마다) ─────────────────────
async function loadPresets() {
  try {
    const res = await fetch(BASE + '/presets');
    if (!res.ok) return;
    const data = await res.json();
    presets = data.presets || [];
    render(presets);
    if (status) updateActive();
  } catch (_) {}
}

// ── 소스 이름 로드 ────────────────────────────
let sourceNames = ['소스 1', '소스 2', '소스 3', '소스 4'];

async function loadSources() {
  try {
    const res = await fetch(BASE + '/sources');
    if (!res.ok) return;
    const data = await res.json();
    sourceNames = data.sources || sourceNames;
    renderPgmBar();
    if (status) updatePgmActive();
  } catch (_) {}
}

// ── 상태 로드 ─────────────────────────────────
async function fetchStatus() {
  if (_wsLive) return;   // WS로 실시간 수신 중이면 HTTP 폴링 불필요
  try {
    const res = await fetch(BASE + '/status');
    if (!res.ok) return;
    status = await res.json();
    updateActive();
    updatePgmActive();
    updatePipActive();
    setAtemOnline(status.atem_connected ?? false);
  } catch (_) {}
}

// ── 렌더링 ────────────────────────────────────
function render(list) {
  const bar = document.getElementById('preset-bar');
  bar.innerHTML = '';

  if (!list.length) {
    bar.innerHTML = '<span id="empty">프리셋 없음</span>';
    return;
  }

  list.forEach(p => {
    const btn = document.createElement('button');
    btn.className = 'p-btn';
    btn.dataset.id = p.id;
    btn.dataset.confirm = p.confirm ? '1' : '0';
    btn.title = p.label || '';

    const dot = document.createElement('div');
    dot.className = 'p-dot';
    btn.appendChild(dot);

    const nameEl = document.createElement('div');
    nameEl.className = 'p-name';
    nameEl.textContent = p.name;
    btn.appendChild(nameEl);

    if (p.description) {
      const descEl = document.createElement('div');
      descEl.className = 'p-desc';
      descEl.textContent = p.description;
      btn.appendChild(descEl);
    }

    btn.addEventListener('click', () => handlePresetClick(p.id, btn));
    bar.appendChild(btn);
  });
}

// ── 활성 프리셋 판단 ──────────────────────────
function isMatch(p, s) {
  if (p.pgm !== s.pgm) return false;
  const km = p.keyer?.mode ?? 'off';
  if (km !== s.keyer_mode) return false;
  if (km !== 'off' && p.keyer?.source !== s.pip_src) return false;
  return true;
}

function updateActive() {
  document.querySelectorAll('.p-btn').forEach(btn => {
    const p = presets.find(x => x.id === Number(btn.dataset.id));
    btn.classList.toggle('active', p ? isMatch(p, status) : false);
  });
}

function updatePgmActive() {
  document.querySelectorAll('.pgm-btn').forEach(btn => {
    btn.classList.toggle('pgm-active', Number(btn.dataset.src) === status?.pgm);
  });
}

// ── 실행 ─────────────────────────────────────
async function runPreset(id, btn) {
  if (btn.disabled) return;
  btn.disabled = true;
  try {
    const res = await fetch(BASE + `/preset/${id}`, { method: 'POST' });
    if (res.ok) {
      status = await res.json();
      updateActive();
      updatePgmActive();
    }
    flash(btn, res.ok ? 'flash-ok' : 'flash-err');
  } catch (_) {
    flash(btn, 'flash-err');
  } finally {
    btn.disabled = false;
  }
}

// ── confirm 클릭 처리 ─────────────────────────
function handlePresetClick(id, btn) {
  if (btn.dataset.confirm !== '1') {
    runPreset(id, btn);
    return;
  }
  if (btn.classList.contains('confirm-pending')) {
    clearTimeout(btn._confirmTimer);
    btn.classList.remove('confirm-pending');
    runPreset(id, btn);
  } else {
    btn.classList.add('confirm-pending');
    btn._confirmTimer = setTimeout(() => {
      btn.classList.remove('confirm-pending');
    }, 2000);
  }
}

function flash(btn, cls) {
  btn.classList.add(cls);
  setTimeout(() => btn.classList.remove(cls), 600);
}

// ── PGM 직접 출력 ──────────────────────────
async function directPgm(src, btn) {
  if (btn.disabled) return;
  btn.disabled = true;
  try {
    const res = await fetch(BASE + '/switching/pgm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source: src })
    });
    if (res.ok) {
      status = await res.json();
      updateActive();
      updatePgmActive();
    }
  } catch (_) {
  } finally {
    btn.disabled = false;
  }
}

function renderPgmBar() {
  const bar = document.getElementById('pgm-bar');
  bar.innerHTML = '';
  for (let i = 1; i <= 4; i++) {
    const btn = document.createElement('button');
    btn.className = 'pgm-btn';
    btn.textContent = sourceNames[i - 1] ?? `소스 ${i}`;
    btn.dataset.src = i;
    btn.addEventListener('click', () => directPgm(i, btn));
    bar.appendChild(btn);
  }
}

// ── 재연결 성공 콜백 (header.js reconnect() 에서 호출) ────────────
function _onReconnectSuccess(data) {
  status = data;
  updateActive();
  updatePgmActive();
}

// ── 로그 ──────────────────────────────────────
const _logs = [];
const MAX_LOG = 5;

function addLog(msg, ts) {
  _logs.unshift({ msg, ts });
  if (_logs.length > MAX_LOG) _logs.length = MAX_LOG;
  renderLog();
}

function renderLog() {
  const bar = document.getElementById('log-bar');
  if (!bar) return;
  bar.innerHTML = '';
  _logs.forEach(l => {
    const div  = document.createElement('div');  div.className  = 'log-entry';
    const tsEl = document.createElement('span'); tsEl.className = 'log-ts';  tsEl.textContent = l.ts;
    const msgEl= document.createElement('span'); msgEl.className= 'log-msg'; msgEl.textContent = l.msg;
    div.appendChild(tsEl);
    div.appendChild(msgEl);
    bar.appendChild(div);
  });
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
        status = msg.data;
        updateActive();
        updatePgmActive();
        updatePipActive();
        setAtemOnline(status.atem_connected ?? false);
        if (msg.ws_count !== undefined) updateWsCount(msg.ws_count);
      }
      if (msg.type === 'log')    { addLog(msg.msg, msg.ts); }
      if (msg.type === 'count')  { updateWsCount(msg.n); }
      if (msg.type === 'reload') { loadPresets(); }
    } catch (_) {}
  };

  _ws.onclose = () => {
    _ws = null;
    _wsLive = false;
    setWsOnline(false);
    setAtemOnline(false);  // 연결 상태 불명 → 빨강 표시
    if (!_wsFallback) _wsFallback = setInterval(fetchStatus, 3000);
    _wsRetry = setTimeout(() => {
      _wsDelay = Math.min(_wsDelay * 2, 30000);
      connectWS();
    }, _wsDelay);
  };

  _ws.onerror = () => { _ws?.close(); };
}

// ── PiP 위치 바 ───────────────────────────────
const _pipPos = {
  tl: { label: '↖ 좌상', x: -12.0, y:  7.0 },
  tr: { label: '↗ 우상', x:  12.0, y:  7.0 },
  bl: { label: '↙ 좌하', x: -12.0, y: -7.0 },
  br: { label: '↘ 우하', x:  12.0, y: -7.0 },
};
const PIP_SIZE = 0.25;

function renderPipBar() {
  const bar = document.getElementById('pip-bar');
  bar.innerHTML = '';

  for (const [key, p] of Object.entries(_pipPos)) {
    const btn = document.createElement('button');
    btn.className = 'pip-btn';
    btn.dataset.pos = key;
    btn.textContent = p.label;
    btn.addEventListener('click', () => activatePip(key, btn));
    bar.appendChild(btn);
  }

  const off = document.createElement('button');
  off.className = 'pip-btn pip-off';
  off.id = 'pip-off-btn';
  off.textContent = 'KEY OFF';
  off.addEventListener('click', () => keyOff(off));
  bar.appendChild(off);
}

async function activatePip(posKey, btn) {
  if (btn.disabled) return;
  btn.disabled = true;
  const p = _pipPos[posKey];
  const src = status?.pip_src || 1;
  try {
    const res = await fetch(BASE + '/key/pip', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source: src, size: PIP_SIZE, pos_x: p.x, pos_y: p.y })
    });
    if (res.ok) {
      status = await res.json();
      updateActive();
      updatePgmActive();
      updatePipActive();
    }
    flash(btn, res.ok ? 'flash-ok' : 'flash-err');
  } catch (_) {
    flash(btn, 'flash-err');
  } finally {
    btn.disabled = false;
  }
}

async function keyOff(btn) {
  if (btn.disabled) return;
  btn.disabled = true;
  try {
    const res = await fetch(BASE + '/key/off', { method: 'POST' });
    if (res.ok) {
      status = await res.json();
      updateActive();
      updatePgmActive();
      updatePipActive();
    }
    flash(btn, res.ok ? 'flash-ok' : 'flash-err');
  } catch (_) {
    flash(btn, 'flash-err');
  } finally {
    btn.disabled = false;
  }
}

function updatePipActive() {
  const isPip = status?.keyer_mode === 'pip';
  document.querySelectorAll('.pip-btn[data-pos]').forEach(btn => {
    const p = _pipPos[btn.dataset.pos];
    const posMatch = isPip &&
      Math.abs((status.dve_pos_x ?? 0) - p.x) < 0.5 &&
      Math.abs((status.dve_pos_y ?? 0) - p.y) < 0.5;
    btn.classList.toggle('pip-active', posMatch);
  });
  const offBtn = document.getElementById('pip-off-btn');
  if (offBtn) offBtn.classList.toggle('pip-off-active', status?.keyer_mode !== 'pip');
}

// ── 초기화 ────────────────────────────────────
loadSources();                   // 소스 이름 로드 후 renderPgmBar 재호출
renderPipBar();
renderPgmBar();                  // 기본 이름으로 먼저 렌더
fetchStatus();                   // 페이지 오픈 시 HTTP로 즉시 상태 조회
loadPresets();
loadAtemAddr();                  // ATEM IP 표시 (header.js 제공)
connectWS();                     // 이후 상태 변경은 WS로 수신
setInterval(loadPresets, 10000); // 프리셋 목록 10초마다 갱신
