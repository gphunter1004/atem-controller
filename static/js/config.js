const BASE = `${location.protocol}//${location.host}`;

// ── 설정 로드 ──────────────────────────────────────────────────
async function loadConfig() {
  try {
    const res = await fetch(BASE + '/api/config');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const d = await res.json();

    document.getElementById('atem_ip').value                = d.atem_ip;
    document.getElementById('atem_port').value              = d.atem_port ?? 9910;
    document.getElementById('simulator_mode').checked       = d.simulator_mode;
    document.getElementById('api_port').value               = d.api_port;
    document.getElementById('transition_rate_frames').value = d.transition_rate_frames;
    document.getElementById('device_sync_interval').value   = d.device_sync_interval;
    document.getElementById('show_console').checked         = d.show_console ?? true;
    d.source_names.forEach((n, i) => {
      document.getElementById(`name${i + 1}`).value = n;
    });

    document.getElementById('tcl_enabled').checked = d.tcl_enabled ?? false;
    document.getElementById('tcl_port').value       = d.tcl_port ?? 4001;
    (d.tcl_tvs || []).forEach((tv, i) => {
      document.getElementById(`tcl_tv${i + 1}_ip`).value   = tv.ip   ?? '';
      document.getElementById(`tcl_tv${i + 1}_name`).value = tv.name ?? '';
    });
    (d.tcl_input_names || []).forEach((n, i) => {
      document.getElementById(`tcl_in${i + 1}_name`).value = n;
    });
    (d.tcl_input_cmds || []).forEach((c, i) => {
      document.getElementById(`tcl_in${i + 1}_cmd`).value = c;
    });

    updateSimDesc();
    updateConsoleDesc();
    updateRateHint();
    updateTclDesc();
    updateConfBadge(d.conf_exists, d.conf_file);
  } catch (e) {
    showNotice('설정을 불러오지 못했습니다: ' + e.message, true);
  }
}

// ── conf 파일 상태 표시 ────────────────────────────────────────
function updateConfBadge(exists, path) {
  const badge  = document.getElementById('conf-badge');
  const pathEl = document.getElementById('conf-path-bar');

  if (exists) {
    badge.textContent = '● CUSTOM CONF';
    badge.className   = 'custom';
  } else {
    badge.textContent = '● DEFAULT (no conf)';
    badge.className   = 'default';
  }
  pathEl.textContent = path;
}

// ── 시뮬레이터 토글 설명 ──────────────────────────────────────
function updateSimDesc() {
  const on   = document.getElementById('simulator_mode').checked;
  const desc = document.getElementById('sim-desc');
  desc.textContent = on ? 'ON — 실제 장비 없이 테스트' : 'OFF — 실제 ATEM 연결';
  desc.style.color  = on ? 'var(--yellow)' : 'var(--green)';
}

// ── 콘솔 창 토글 설명 ─────────────────────────────────────────
function updateConsoleDesc() {
  const on   = document.getElementById('show_console').checked;
  const desc = document.getElementById('console-desc');
  desc.textContent = on ? 'ON — 콘솔 창 표시' : 'OFF — 콘솔 창 숨김';
  desc.style.color  = on ? 'var(--text)' : 'var(--muted)';
}

// ── AUTO 속도 힌트 ─────────────────────────────────────────────
function updateRateHint() {
  const frames = parseInt(document.getElementById('transition_rate_frames').value) || 0;
  const ms = Math.round(frames / 30 * 1000);
  document.getElementById('rate-hint').textContent = `≈ ${ms}ms`;
}

// ── TCL 활성화 설명 ────────────────────────────────────────────
function updateTclDesc() {
  const on   = document.getElementById('tcl_enabled').checked;
  const desc = document.getElementById('tcl-enabled-desc');
  if (!desc) return;
  desc.textContent = on ? 'ON — TCL TV 제어 활성화' : 'OFF — TCL TV 제어 비활성화';
  desc.style.color  = on ? 'var(--green)' : 'var(--muted)';
}

// ── 이벤트 ────────────────────────────────────────────────────
document.getElementById('simulator_mode').addEventListener('change', updateSimDesc);
document.getElementById('tcl_enabled').addEventListener('change', updateTclDesc);
document.getElementById('show_console').addEventListener('change', updateConsoleDesc);
document.getElementById('transition_rate_frames').addEventListener('input', updateRateHint);

// 저장
document.getElementById('cfg-form').addEventListener('submit', async (e) => {
  e.preventDefault();

  const names = [1, 2, 3, 4].map(i => {
    const v = document.getElementById(`name${i}`).value.trim();
    return v || `소스 ${i}`;
  });

  const body = {
    atem_ip:                document.getElementById('atem_ip').value.trim(),
    atem_port:              parseInt(document.getElementById('atem_port').value),
    simulator_mode:         document.getElementById('simulator_mode').checked,
    api_port:               parseInt(document.getElementById('api_port').value),
    transition_rate_frames: parseInt(document.getElementById('transition_rate_frames').value),
    device_sync_interval:   parseInt(document.getElementById('device_sync_interval').value),
    show_console:           document.getElementById('show_console').checked,
    source_names:           names,
    tcl_enabled:            document.getElementById('tcl_enabled').checked,
    tcl_port:               parseInt(document.getElementById('tcl_port').value) || 4001,
    tcl_tvs:                [1, 2, 3].map(i => ({
      ip:   document.getElementById(`tcl_tv${i}_ip`).value.trim(),
      name: document.getElementById(`tcl_tv${i}_name`).value.trim() || `TV ${i}`,
    })),
    tcl_input_names:        [1, 2, 3, 4].map(i => document.getElementById(`tcl_in${i}_name`).value.trim() || `입력 ${i}`),
    tcl_input_cmds:         [1, 2, 3, 4].map(i => document.getElementById(`tcl_in${i}_cmd`).value.trim()),
  };

  try {
    const res = await fetch(BASE + '/api/config', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    await loadConfig();
    showNotice('저장되었습니다. (즉시 적용 항목은 바로 반영됨)');
  } catch (e) {
    showNotice('저장 실패: ' + e.message, true);
  }
});

// 초기화
document.getElementById('btn-reset').addEventListener('click', async () => {
  if (!confirm('설정 파일을 삭제하고 기본값으로 되돌리겠습니까?\n서버 재시작 후 기본값이 적용됩니다.')) return;
  try {
    const res = await fetch(BASE + '/api/config', { method: 'DELETE' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    await loadConfig();
    showNotice('설정 파일이 삭제되었습니다. 서버 재시작 후 기본값이 적용됩니다.');
  } catch (e) {
    showNotice('초기화 실패: ' + e.message, true);
  }
});

// ── 서버 재시작 ───────────────────────────────────────────────
document.getElementById('btn-restart').addEventListener('click', async () => {
  if (!confirm('서버를 재시작하겠습니까?\n잠시 연결이 끊어집니다.')) return;

  const btn = document.getElementById('btn-restart');
  btn.disabled = true;
  showNotice('재시작 중...', false, true);

  try {
    await fetch(BASE + '/admin/restart', { method: 'POST' });
  } catch (_) {
    // 서버가 응답 전에 종료될 수 있음 — 무시
  }

  // 서버가 다시 올라올 때까지 폴링 (최대 30초)
  const deadline = Date.now() + 30000;
  while (Date.now() < deadline) {
    await new Promise(r => setTimeout(r, 1000));
    try {
      const r = await fetch(BASE + '/api/config', { signal: AbortSignal.timeout(2000) });
      if (r.ok) {
        await loadConfig();
        showNotice('서버가 재시작되었습니다.');
        btn.disabled = false;
        return;
      }
    } catch (_) {
      // 아직 준비 안 됨
    }
  }

  showNotice('재시작 시간 초과. 페이지를 새로 고침하세요.', true);
  btn.disabled = false;
});

// ── 알림 ──────────────────────────────────────────────────────
function showNotice(msg, isError = false, persistent = false) {
  const el = document.getElementById('notice');
  el.textContent = msg;
  el.className   = 'notice ' + (isError ? 'error' : 'ok');
  clearTimeout(el._t);
  if (!persistent) {
    el._t = setTimeout(() => { el.className = 'notice hidden'; }, 5000);
  }
}

// ── TCL 페어링 ────────────────────────────────────────────────
let _tclPairingTv = null;

async function tclPairStart(tvIndex) {
  const ip = document.getElementById(`tcl_tv${tvIndex}_ip`).value.trim();
  if (!ip) { showNotice('먼저 IP 주소를 입력하세요.', true); return; }

  _tclPairingTv = tvIndex;
  const box = document.getElementById('tcl-pair-box');
  const msg = document.getElementById('tcl-pair-msg');
  box.style.display = '';
  msg.textContent   = `TV ${tvIndex} (${ip}) — 연결 중...`;
  document.getElementById('tcl-pair-pin').value = '';

  try {
    const res = await fetch(BASE + '/tcl/pair/start', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ tv: tvIndex }),
    });
    const d = await res.json();
    msg.textContent = d.ok
      ? `${d.tv} — TV 화면에 표시된 PIN을 입력하세요.`
      : `실패: ${d.message}`;
    msg.style.color = d.ok ? 'var(--blue)' : 'var(--red, #f55)';
    if (!d.ok) { box.style.display = 'none'; _tclPairingTv = null; }
  } catch (e) {
    msg.textContent = '오류: ' + e.message;
    msg.style.color = 'var(--red, #f55)';
  }
}

async function tclPairFinish() {
  const pin = document.getElementById('tcl-pair-pin').value.trim();
  if (!pin || !_tclPairingTv) return;

  const msg = document.getElementById('tcl-pair-msg');
  msg.textContent = '페어링 중...';

  try {
    const res = await fetch(BASE + '/tcl/pair/finish', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ tv: _tclPairingTv, pin }),
    });
    const d = await res.json();
    if (d.ok) {
      showNotice(`${d.tv} 페어링 완료!`);
      document.getElementById('tcl-pair-box').style.display = 'none';
    } else {
      msg.textContent = `실패: ${d.message}`;
      msg.style.color = 'var(--red, #f55)';
    }
  } catch (e) {
    msg.textContent = '오류: ' + e.message;
  }
  _tclPairingTv = null;
}

function tclPairCancel() {
  document.getElementById('tcl-pair-box').style.display = 'none';
  _tclPairingTv = null;
}

// ── 초기화 ────────────────────────────────────────────────────
loadConfig();
