// static/js/header.js — 공통 헤더 (panel, ui 페이지 공유)
// BASE, updateConnInfo, setWsOnline, setAtemOnline, updateWsCount,
// reconnect, loadAtemAddr 를 전역으로 제공

const BASE = `${location.protocol}//${location.host}`;

// ── 접속 정보 표시 ────────────────────────────
function updateConnInfo(ip, id) {
  const el = document.getElementById('conn-info');
  if (!el) return;
  el.innerHTML =
    `<span class="dot-label">WS</span><span class="ws-dot"></span>` +
    `<span class="dot-label">ATEM</span><span class="atem-dot"></span>` +
    `${ip}<span class="conn-id">#${id}</span><span class="ws-count"></span>`;
}

function setWsOnline(online) {
  const el = document.getElementById('conn-info');
  if (el) el.classList.toggle('ws-online', online);
}

function setAtemOnline(online) {
  const el = document.getElementById('conn-info');
  if (el) el.classList.toggle('atem-online', online);
  document.body.classList.toggle('atem-offline', !online);
}

function updateWsCount(n) {
  const el = document.querySelector('#conn-info .ws-count');
  if (el) el.textContent = `· ${n}명`;
}

// ── ATEM 재연결 ───────────────────────────────
async function reconnect() {
  const btn = document.getElementById('reconnect-btn');
  if (!btn || btn.disabled) return;
  btn.disabled = true;
  const orig = btn.textContent;
  btn.textContent = '연결 중…';
  try {
    const res  = await fetch(BASE + '/admin/connect', { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      if (typeof _onReconnectSuccess === 'function') _onReconnectSuccess(data);
      setAtemOnline(true);
      btn.textContent = '연결됨';
      setTimeout(() => { btn.textContent = orig; }, 1500);
    } else {
      btn.textContent = data.error ?? '실패';
      setTimeout(() => { btn.textContent = orig; }, 2500);
    }
  } catch (_) {
    btn.textContent = '오류';
    setTimeout(() => { btn.textContent = orig; }, 2500);
  } finally {
    btn.disabled = false;
  }
}

// ── ATEM 주소 로드 ────────────────────────────
async function loadAtemAddr() {
  try {
    const res = await fetch(BASE + '/api/config');
    if (!res.ok) return;
    const d = await res.json();
    const el = document.getElementById('atem-addr');
    if (el) el.textContent = d.atem_ip ?? '';
  } catch (_) {}
}

// ── conn-info 기본 HTML 초기화 ────────────────
(function () {
  const el = document.getElementById('conn-info');
  if (el && !el.innerHTML.trim()) {
    el.innerHTML =
      '<span class="dot-label">WS</span><span class="ws-dot"></span>' +
      '<span class="dot-label">ATEM</span><span class="atem-dot"></span>';
  }
})();
