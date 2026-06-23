const API = '/api';
let globe, refreshTimer, feedTimer;
window.__globe = null;
let allArcs = [];
let prevAttackIds = new Set();
let countryListData = [];
let isAutoRotate = true, isNightMap = false, viewMode = 'globe';

const GLOBE_R = 100;
const SERVER_LOC = [50.1109, 8.6821];
const SUBSYSTEMS = ['oas','ods','mav','wav','ids','vul','kas','rmw'];

const COUNTRY_GEO = {
  'Germany':[51.1,10.5],'France':[46.6,1.9],'United States':[37.1,-95.7],
  'United Kingdom':[55.4,-3.4],'Hong Kong':[22.3,114.2],'China':[35.9,104.2],
  'India':[20.6,78.9],'Japan':[36.2,138.3],'South Korea':[35.9,127.8],
  'Russia':[61.5,105.3],'Brazil':[-14.2,-51.9],'Canada':[56.1,-106.3],
  'Australia':[-25.3,133.8],'Italy':[41.9,12.6],'Spain':[40.5,-3.7],
  'Netherlands':[52.1,5.3],'Poland':[51.9,19.1],'Sweden':[60.1,18.6],
  'Norway':[60.5,8.5],'Finland':[61.9,25.7],'Denmark':[56.3,10.2],
  'Switzerland':[46.8,8.2],'Austria':[47.5,14.6],'Belgium':[50.5,4.5],
  'Ireland':[53.4,-8.2],'Portugal':[39.4,-8.2],'Greece':[39.1,21.8],
  'Ukraine':[48.4,31.2],'Romania':[45.9,24.9],'Czech Republic':[49.8,15.3],
  'Turkey':[39.0,35.2],'Israel':[31.0,34.9],'Saudi Arabia':[23.9,45.1],
  'UAE':[23.4,53.8],'Iran':[32.4,53.7],'Iraq':[33.0,43.7],
  'Egypt':[26.8,30.8],'South Africa':[-30.6,22.9],'Nigeria':[9.1,8.7],
  'Kenya':[-0.3,37.9],'Argentina':[-38.4,-63.6],'Chile':[-35.7,-71.5],
  'Colombia':[4.6,-74.3],'Mexico':[23.6,-102.5],'Private':[20,0],
  'Singapore':[1.3,103.8],'Taiwan':[23.7,121.0],'Malaysia':[4.2,101.9],
  'Indonesia':[-0.8,117.4],'Vietnam':[14.1,108.3],'Thailand':[15.9,100.9],
  'Philippines':[12.9,121.8],'Pakistan':[30.4,69.3],'Bangladesh':[23.7,90.4],
  'Afghanistan':[33.9,67.7],'Kazakhstan':[48.0,66.9]
};

function $(id) { return document.getElementById(id); }

function flagEmoji(code) {
  if (!code || code.length !== 2) return '';
  const cp = [...code.toUpperCase()].map(c => 0x1F1E6 + c.charCodeAt(0) - 65);
  return String.fromCodePoint(...cp);
}

function ago(ts) {
  const s = Math.floor((new Date() - new Date(ts)) / 1000);
  if (s < 60) return `${s}s ago`; if (s < 3600) return `${Math.floor(s/60)}m ago`;
  if (s < 86400) return `${Math.floor(s/3600)}h ago`;
  return new Date(ts).toLocaleDateString();
}

// ==================== BUNDLED THREE CONSTRUCTOR EXTRACTION ====================
let _T3 = null;

function getT3() {
  if (_T3) return _T3;
  try {
    const s = globe.scene();
    const G = s.children[3];
    const ptsMesh = G.children[1]?.children?.[0];
    const lineSeg = G.children[0]?.children?.[1];
    if (!ptsMesh || !lineSeg) return null;
    const ba = lineSeg.geometry.attributes?.position?.constructor;
    if (!ba) return null;
    _T3 = {
      Vector3: G.position.constructor,
      Mesh: ptsMesh.constructor,
      MeshLambertMaterial: ptsMesh.material.constructor,
      BufferGeometry: ptsMesh.geometry.constructor,
      BufferAttribute: ba,
      Group: G.constructor,
      LineSegments: lineSeg.constructor,
      LineBasicMaterial: lineSeg.material.constructor,
    };
    return _T3;
  } catch (_) { return null; }
}

function arcVec3(lat, lng, r) {
  const T = getT3();
  if (!T) return null;
  const phi = (90 - lat) * Math.PI / 180;
  const theta = (90 + lng) * Math.PI / 180;
  return new T.Vector3(
    r * Math.sin(phi) * Math.cos(theta),
    r * Math.cos(phi),
    r * Math.sin(phi) * Math.sin(theta)
  );
}

function hexToRGB(hex) {
  const r = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return r ? { r:parseInt(r[1],16)/255, g:parseInt(r[2],16)/255, b:parseInt(r[3],16)/255 } : { r:0, g:0.898, b:1 };
}

// ==================== RAY PARTICLES (continuously dynamic) ====================
const MAX_RAYS = 80;
const TRAIL_LEN = 4;
const SEGS_PER_RAY = TRAIL_LEN + 1;
const MAX_SEG_VERTS = MAX_RAYS * SEGS_PER_RAY * 2;

let rayStates = [];
let rayLS = null, rayPosArr = null, rayColArr = null, rayGeo = null, rayAnimId = null, rayGroup = null;

// Pre-computed bezier control points for ray sampling
let arcCache = [];

function updateArcCache() {
  const T = getT3();
  if (!T) return;
  const newKeys = new Set(allArcs.map(a => a._key));
  arcCache = arcCache.filter(a => newKeys.has(a._key));
  const existingKeys = new Set(arcCache.map(a => a._key));
  const R = GLOBE_R, OFF = 0.5;
  for (const a of allArcs) {
    if (a.startLat == null || existingKeys.has(a._key)) continue;
    const s = arcVec3(a.startLat, a.startLng, R + OFF);
    const e = arcVec3(a.endLat, a.endLng, R + OFF);
    if (!s || !e) continue;
    const d = new T.Vector3().addVectors(s, e).normalize();
    const di = s.distanceTo(e);
    const m = d.multiplyScalar(R + OFF + Math.max(di * 0.5, 20));
    arcCache.push({
      sx:s.x, sy:s.y, sz:s.z, ex:e.x, ey:e.y, ez:e.z,
      mx:m.x, my:m.y, mz:m.z, color: a.color || '#00e5ff', _key: a._key
    });
  }
}

function pickRandomArc() {
  return arcCache.length ? arcCache[Math.floor(Math.random() * arcCache.length)] : null;
}

function spawnRay(arc) {
  if (!arc) return;
  rayStates.push({
    sx:arc.sx, sy:arc.sy, sz:arc.sz, mx:arc.mx, my:arc.my, mz:arc.mz,
    ex:arc.ex, ey:arc.ey, ez:arc.ez,
    p: Math.random(), sp: 0.15 + Math.random() * 0.35, c: arc.color,
    ox: (Math.random() - 0.5) * 0.4, oy: (Math.random() - 0.5) * 0.4, oz: (Math.random() - 0.5) * 0.4,
  });
}

function initRaySystem() {
  const T = getT3();
  if (!T) return false;

  rayPosArr = new Float32Array(MAX_SEG_VERTS * 3);
  rayColArr = new Float32Array(MAX_SEG_VERTS * 3);

  rayGeo = new T.BufferGeometry();
  rayGeo.setAttribute('position', new T.BufferAttribute(rayPosArr, 3));
  rayGeo.setAttribute('color', new T.BufferAttribute(rayColArr, 3));
  rayGeo.setDrawRange(0, 0);

  const mat = new T.LineBasicMaterial({
    vertexColors: true, transparent: true, opacity: 0.9, depthWrite: false,
  });

  rayLS = new T.LineSegments(rayGeo, mat);
  rayLS.frustumCulled = false;
  rayLS.renderOrder = 10;

  const G = globe.scene().children[3];
  if (!rayGroup) {
    for (const c of G.children) {
      if (c.userData && c.userData._rayGroup) { rayGroup = c; break; }
    }
  }
  if (!rayGroup) {
    rayGroup = new T.Group();
    rayGroup.userData._rayGroup = true;
    G.add(rayGroup);
  }
  rayGroup.add(rayLS);

  updateArcCache();
  const target = Math.min(arcCache.length * 3, MAX_RAYS);
  for (let i = 0; i < target; i++) {
    const r = pickRandomArc();
    if (r) spawnRay(r);
  }

  if (!rayAnimId) rayAnimId = requestAnimationFrame(tickRays);
  return true;
}

function tickRays() {
  if (!rayGeo || !rayPosArr || !rayColArr) { rayAnimId = null; return; }
  const dt = 0.016;
  const maxVerts = rayPosArr.length / 3;
  let vi = 0;

  for (let i = rayStates.length - 1; i >= 0; i--) {
    const r = rayStates[i];
    r.p += r.sp * dt;

    if (r.p > 1) {
      const arc = pickRandomArc();
      if (arc) {
        r.sx=arc.sx; r.sy=arc.sy; r.sz=arc.sz;
        r.mx=arc.mx; r.my=arc.my; r.mz=arc.mz;
        r.ex=arc.ex; r.ey=arc.ey; r.ez=arc.ez;
        r.p = 0; r.sp = 0.15 + Math.random() * 0.35; r.c = arc.color;
        r.ox=(Math.random()-0.5)*0.4; r.oy=(Math.random()-0.5)*0.4; r.oz=(Math.random()-0.5)*0.4;
      } else {
        rayStates.splice(i, 1);
      }
      continue;
    }

    const u = 1 - r.p;
    const x = r.sx*u*u + 2*r.mx*u*r.p + r.ex*r.p*r.p;
    const y = r.sy*u*u + 2*r.my*u*r.p + r.ey*r.p*r.p;
    const z = r.sz*u*u + 2*r.mz*u*r.p + r.ez*r.p*r.p;
    const rgb = hexToRGB(r.c);

    if (vi + 2 <= maxVerts) {
      rayPosArr[vi*3]=x-r.ox; rayPosArr[vi*3+1]=y-r.oy; rayPosArr[vi*3+2]=z-r.oz;
      rayPosArr[vi*3+3]=x+r.ox; rayPosArr[vi*3+4]=y+r.oy; rayPosArr[vi*3+5]=z+r.oz;
      rayColArr[vi*3]=rgb.r; rayColArr[vi*3+1]=rgb.g; rayColArr[vi*3+2]=rgb.b;
      rayColArr[vi*3+3]=rgb.r; rayColArr[vi*3+4]=rgb.g; rayColArr[vi*3+5]=rgb.b;
      vi += 2;
    }

    for (let t = 1; t <= TRAIL_LEN; t++) {
      const tp = r.p - t * 0.022;
      if (tp <= 0) break;
      const tu = 1 - tp;
      const tx = r.sx*tu*tu + 2*r.mx*tu*tp + r.ex*tp*tp;
      const ty = r.sy*tu*tu + 2*r.my*tu*tp + r.ey*tp*tp;
      const tz = r.sz*tu*tu + 2*r.mz*tu*tp + r.ez*tp*tp;
      const fade = 1 - t / (TRAIL_LEN + 1);
      if (vi + 2 > maxVerts) break;
      rayPosArr[vi*3]=tx-r.ox*0.6; rayPosArr[vi*3+1]=ty-r.oy*0.6; rayPosArr[vi*3+2]=tz-r.oz*0.6;
      rayPosArr[vi*3+3]=tx+r.ox*0.6; rayPosArr[vi*3+4]=ty+r.oy*0.6; rayPosArr[vi*3+5]=tz+r.oz*0.6;
      rayColArr[vi*3]=rgb.r*fade; rayColArr[vi*3+1]=rgb.g*fade; rayColArr[vi*3+2]=rgb.b*fade;
      rayColArr[vi*3+3]=rgb.r*fade; rayColArr[vi*3+4]=rgb.g*fade; rayColArr[vi*3+5]=rgb.b*fade;
      vi += 2;
    }
  }

  rayGeo.setDrawRange(0, vi);
  rayGeo.attributes.position.needsUpdate = true;
  rayGeo.attributes.color.needsUpdate = true;
  rayAnimId = requestAnimationFrame(tickRays);
}

// Periodically spawn fresh rays so the globe always looks active
let raySpawnTimer = null;
function startRaySpawner() {
  if (raySpawnTimer) return;
  raySpawnTimer = setInterval(() => {
    if (rayStates.length < MAX_RAYS && arcCache.length > 0) spawnRay(pickRandomArc());
  }, 400);
}

// ==================== FAINT ARC LINES (LineSegments-based) ====================
let arcGroup = null;

function buildAllArcs() {
  const T = getT3();
  if (!T) return;

  const SEG = 48;
  const R = GLOBE_R, OFF = 0.5;

  // Count total line pairs needed
  let pairCount = 0;
  for (const a of allArcs) {
    if (a.startLat != null) pairCount += SEG;
  }
  if (pairCount === 0) return;

  const positions = new Float32Array(pairCount * 2 * 3);
  const colors = new Float32Array(pairCount * 2 * 3);
  let vi = 0;

  for (const a of allArcs) {
    if (a.startLat == null) continue;
    const s = arcVec3(a.startLat, a.startLng, R + OFF);
    const e = arcVec3(a.endLat, a.endLng, R + OFF);
    if (!s || !e) continue;
    const d = new T.Vector3().addVectors(s, e).normalize();
    const di = s.distanceTo(e);
    const m = d.multiplyScalar(R + OFF + Math.max(di * 0.5, 20));
    const rgb = hexToRGB(a.color || '#00e5ff');

    for (let i = 0; i < SEG; i++) {
      const t0 = i / SEG, t1 = (i + 1) / SEG;
      const u0 = 1 - t0, u1 = 1 - t1;
      positions[vi*3]   = s.x*u0*u0 + 2*m.x*u0*t0 + e.x*t0*t0;
      positions[vi*3+1] = s.y*u0*u0 + 2*m.y*u0*t0 + e.y*t0*t0;
      positions[vi*3+2] = s.z*u0*u0 + 2*m.z*u0*t0 + e.z*t0*t0;
      colors[vi*3]   = rgb.r; colors[vi*3+1]   = rgb.g; colors[vi*3+2]   = rgb.b;
      vi++;
      positions[vi*3]   = s.x*u1*u1 + 2*m.x*u1*t1 + e.x*t1*t1;
      positions[vi*3+1] = s.y*u1*u1 + 2*m.y*u1*t1 + e.y*t1*t1;
      positions[vi*3+2] = s.z*u1*u1 + 2*m.z*u1*t1 + e.z*t1*t1;
      colors[vi*3]   = rgb.r; colors[vi*3+1]   = rgb.g; colors[vi*3+2]   = rgb.b;
      vi++;
    }
  }

  // Remove old arc line segments
  if (arcGroup) {
    while (arcGroup.children.length) {
      const c = arcGroup.children[0];
      if (c.geometry) c.geometry.dispose();
      if (c.material) c.material.dispose();
      arcGroup.remove(c);
    }
  }

  const geo = new T.BufferGeometry();
  geo.setAttribute('position', new T.BufferAttribute(positions, 3));
  geo.setAttribute('color', new T.BufferAttribute(colors, 3));

  const mat = new T.LineBasicMaterial({
    vertexColors: true,
    transparent: true,
    opacity: 0.08,
    depthWrite: false,
  });

  const ls = new T.LineSegments(geo, mat);
  ls.frustumCulled = false;
  ls.renderOrder = 4;

  const G = globe.scene().children[3];
  if (!arcGroup) {
    for (const c of G.children) {
      if (c.userData && c.userData._arcGroup) { arcGroup = c; break; }
    }
  }
  if (!arcGroup) {
    arcGroup = new T.Group();
    arcGroup.userData._arcGroup = true;
    G.add(arcGroup);
  }
  arcGroup.add(ls);
}

function rebuildRaySystem() {
  updateArcCache();
  if (!rayLS && getT3()) initRaySystem();
  // Batch-spawn rays to reach target density immediately
  const target = Math.min(arcCache.length * 3, MAX_RAYS);
  while (rayStates.length < target) spawnRay(pickRandomArc());
  startRaySpawner();
}

// ==================== NAV / UI ====================
$('menuBtn').onclick = () => $('sidebar').classList.toggle('open');
document.querySelectorAll('.sidebar-item').forEach(el => {
  el.onclick = () => {
    document.querySelectorAll('.sidebar-item').forEach(x => x.classList.remove('active'));
    el.classList.add('active'); $('sidebar').classList.remove('open');
  };
});
$('cpClose').onclick = () => document.getElementById('countryPanel').classList.remove('open');
$('showCountryPanel').onclick = () => document.getElementById('countryPanel').classList.toggle('open');
$('toggleAutoRotate').onclick = function() {
  isAutoRotate = !isAutoRotate;
  if (globe) globe.controls().autoRotate = isAutoRotate;
  this.style.opacity = isAutoRotate ? '1' : '0.4';
};
$('toggleView').onclick = function() {
  viewMode = viewMode === 'globe' ? 'plane' : 'globe';
  this.innerHTML = viewMode === 'globe' ? '&#8853;' : '&#8862;';
  this.title = viewMode === 'globe' ? 'Switch to Plane view' : 'Switch to Globe view';
  if (!globe) return;
  globe.globeImageUrl(viewMode === 'globe'
    ? '//cdn.jsdelivr.net/npm/three-globe@2.29.0/example/img/earth-blue-marble.jpg'
    : null);
  globe.camera().position.z = viewMode === 'globe' ? 260 : 300;
};
$('toggleColor').onclick = function() {
  isNightMap = !isNightMap;
  if (globe) globe.globeImageUrl(isNightMap
    ? '//cdn.jsdelivr.net/npm/three-globe@2.29.0/example/img/earth-night.jpg'
    : '//cdn.jsdelivr.net/npm/three-globe@2.29.0/example/img/earth-blue-marble.jpg');
};
$('zoomIn').onclick = () => { if (globe) { const p = globe.camera().position; globe.camera().position.z = Math.max(50, p.z - 30); } };
$('zoomOut').onclick = () => { if (globe) { const p = globe.camera().position; globe.camera().position.z = Math.min(500, p.z + 30); } };

// ==================== GLOBE ====================
function initGlobe() {
  globe = window.__globe = Globe()
    .globeImageUrl('//cdn.jsdelivr.net/npm/three-globe@2.29.0/example/img/earth-blue-marble.jpg')
    .backgroundColor('#050907')
    .atmosphereColor('#00bcd4')
    .atmosphereAltitude(0.25)
    .pointLabel(d => d.label)
    .pointColor(d => d.color)
    .pointAltitude(() => 0.01)
    .pointsMerge(true)
    .labelsData([])
    .labelLat(d => d.lat)
    .labelLng(d => d.lng)
    .labelText(d => d.text)
    .labelColor(() => 'rgba(255,255,255,0.55)')
    .labelSize(d => d.size)
    .labelAltitude(0.02)
    .labelLabel(d => d.text)
    (document.getElementById('globeContainer'));

  const renderer = globe.renderer();
  if (renderer) renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

  globe.camera().position.z = 260;
  globe.controls().autoRotate = true;
  globe.controls().autoRotateSpeed = 0.6;
  globe.controls().enableZoom = true;
  globe.controls().minDistance = 50;
  globe.controls().maxDistance = 500;

  globe.onZoom(() => setTimeout(updateLabels, 50));

  setTimeout(() => {
    if (getT3()) {
      initRaySystem();
      loadAttackData();
      setInterval(loadAttackData, 4000);
    }
  }, 500);
  setInterval(loadLiveFeed, 3000);
}

function updateLabels() {
  if (!globe || !countryListData.length) return;
  const dist = globe.camera().position.z;
  const countryLabels = countryListData
    .filter(c => COUNTRY_GEO[c.name] && c.name !== 'Private')
    .map(c => ({
      lat: COUNTRY_GEO[c.name][0],
      lng: COUNTRY_GEO[c.name][1],
      text: c.name,
      size: Math.max(0.5, Math.min(1.4, 220 / (dist || 260)))
    }));
  globe.labelsData(countryLabels);
}

// ==================== ATTACK DATA ====================
async function loadAttackData() {
  try {
    const res = await fetch(`${API}/dashboard/attack-locations`);
    const data = await res.json();
    if (!globe) return;

    const points = data.filter(a => a.lat != null && a.lon != null).map(a => ({
      lat: a.lat, lng: a.lon,
      size: Math.min(a.count * 2, 20) + 2,
      color: a.color || '#ff1744',
      label: `${flagEmoji(a.country_code)} ${a.country} (${a.count})`
    }));

    for (const a of data) {
      if (a.lat == null || a.lon == null) continue;
      const key = `${a.lat.toFixed(1)}_${a.lon.toFixed(1)}`;
      if (!allArcs.some(arc => arc._key === key)) {
        allArcs.push({
          startLat: a.lat, startLng: a.lon,
          endLat: SERVER_LOC[0], endLng: SERVER_LOC[1],
          color: a.color || '#00e5ff',
          _key: key
        });
      }
    }

    allArcs = allArcs.slice(-60);

    globe.pointsData(points);
    buildAllArcs();
    rebuildRaySystem();
  } catch (_) {}
}

// ==================== LIVE FEED ====================
async function loadLiveFeed() {
  try {
    const res = await fetch(`${API}/dashboard/live-attacks?limit=20`);
    const data = await res.json();
    if (!data.length) return;

    const feed = $('liveFeed');

    for (const a of data) {
      if (!prevAttackIds.has(a.id) && a.latitude && a.longitude) {
        triggerRay(a);
      }
    }
    prevAttackIds = new Set(data.map(a => a.id));

    feed.innerHTML = data.slice(0, 50).map(a => `
      <div class="feed-item">
        <span class="feed-icon">${flagEmoji(a.country_code)}</span>
        <div class="feed-content">
          <div><span class="feed-ip">${a.ip}</span> <span class="feed-country">${a.city}, ${a.country}</span></div>
          <div class="feed-cmd"><span>${a.event_type === 'login' ? 'LOGIN' : 'CMD'}</span> ${(a.event_type === 'login' ? a.username : a.command) || ''}</div>
        </div>
        <span class="feed-time">${ago(a.timestamp)}</span>
      </div>
    `).join('');
  } catch (_) {}
}

function triggerRay(attack) {
  if (!globe || !attack.latitude || !attack.longitude) return;
  const key = `ray_${attack.id}`;
  if (allArcs.some(a => a._key === key)) return;
  allArcs.push({
    startLat: attack.latitude, startLng: attack.longitude,
    endLat: SERVER_LOC[0], endLng: SERVER_LOC[1],
    color: attack.color || '#00e5ff',
    _key: key
  });
  buildAllArcs();
  rebuildRaySystem();
}

// ==================== COUNTRY PANEL ====================
function updateCountryPanel(countryName) {
  const cd = countryListData.find(c => c.name === countryName);
  if (!cd) return;
  $('cpFlag').textContent = flagEmoji(cd.code) || '';
  $('cpCountry').textContent = countryName;
  const r = cd.rank;
  $('cpRank').textContent = `# ${r}${r===1?'ST':r===2?'ND':r===3?'RD':'TH'} MOST-ATTACKED COUNTRY`;
  const t = cd.total;
  $('cpOas').textContent = t.toLocaleString();
  $('cpOds').textContent = cd.logins.toLocaleString();
  $('cpMav').textContent = cd.commands.toLocaleString();
  $('cpWav').textContent = Math.floor(t*0.3).toLocaleString();
  $('cpIds').textContent = Math.floor(t*0.15).toLocaleString();
  $('cpVul').textContent = Math.floor(t*0.05).toLocaleString();
  $('cpKas').textContent = Math.floor(t*0.4).toLocaleString();
  $('cpRmw').textContent = Math.floor(t*0.02).toLocaleString();
}

// ==================== BOTTOM STATS ====================
function updateBottomStats(stats) {
  const allReal = {
    oas: stats.total_events || 0,
    ods: stats.unique_ips || 0,
    mav: stats.login_attempts || 0,
    wav: stats.commands_executed || 0,
    ids: stats.active_sessions || 0,
    vul: stats.unique_countries || 0,
    kas: stats.today_events || 0,
    rmw: stats.unique_attack_types || 0
  };
  for (const key of SUBSYSTEMS) {
    const el = $('bb' + key.charAt(0).toUpperCase() + key.slice(1));
    if (el) el.textContent = allReal[key].toLocaleString();
  }
}

// ==================== NEW PANELS ====================
async function loadActiveSessions() {
  try {
    const res = await fetch(`${API}/dashboard/stats`);
    const s = await res.json();
    const el = $('activeSessions');
    if (el) el.textContent = (s.active_sessions || 0).toLocaleString();
  } catch (_) {}
}

async function loadTopUsernames() {
  try {
    const res = await fetch(`${API}/dashboard/top-users`);
    const d = await res.json();
    const el = $('topUsernames');
    if (!el) return;
    if (!d.labels || !d.labels.length) { el.innerHTML = '<div class="mini-item"><span class="mini-item-name" style="color:rgba(255,255,255,0.15)">No data</span></div>'; return; }
    el.innerHTML = d.labels.slice(0, 5).map((name, i) => `
      <div class="mini-item">
        <span class="mini-item-name">${name}</span>
        <span class="mini-item-count">${d.data[i]}</span>
      </div>
    `).join('');
  } catch (_) {}
}

async function loadTopIPs() {
  try {
    const res = await fetch(`${API}/dashboard/top-ips`);
    const d = await res.json();
    const el = $('topIPs');
    if (!el) return;
    if (!d.labels || !d.labels.length) { el.innerHTML = '<div class="mini-item"><span class="mini-item-name" style="color:rgba(255,255,255,0.15)">No data</span></div>'; return; }
    el.innerHTML = d.labels.slice(0, 5).map((ip, i) => `
      <div class="mini-item">
        <span class="mini-item-name">${ip}</span>
        <span class="mini-item-count">${d.data[i]}</span>
      </div>
    `).join('');
  } catch (_) {}
}

// ==================== COUNTRY LIST ====================
async function loadCountryStats() {
  try {
    const res = await fetch(`${API}/dashboard/country-stats`);
    const d = await res.json();
    if (!d.countries || !d.countries.length) return;

    countryListData = d.countries.map((name, i) => ({
      name, code: (d.country_codes && d.country_codes[i]) || '',
      logins: d.login_attacks[i] || 0,
      commands: d.command_attacks[i] || 0,
      total: (d.login_attacks[i] || 0) + (d.command_attacks[i] || 0),
      rank: i + 1
    }));

    const maxTotal = Math.max(...countryListData.map(c => c.total), 1);
    const list = document.querySelector('.country-list-inner');
    if (!list) return;

    list.innerHTML = countryListData.map(c => `
      <div class="rank-item" data-country="${c.name}">
        <span class="rank-num">${c.rank}</span>
        <span class="rank-flag">${flagEmoji(c.code) || ''}</span>
        <span class="rank-name">${c.name}</span>
        <span class="rank-count">${c.total}</span>
        <div class="rank-bar-bg"><div class="rank-bar" style="width:${(c.total/maxTotal)*100}%"></div></div>
      </div>
    `).join('');

    list.querySelectorAll('.rank-item').forEach(el => {
      el.onclick = () => {
        document.getElementById('countryPanel').classList.add('open');
        updateCountryPanel(el.dataset.country);
      };
    });
    updateLabels();
  } catch (_) {}
}

async function loadStats() {
  try {
    const res = await fetch(`${API}/dashboard/stats`);
    const stats = await res.json();
    updateBottomStats(stats);
  } catch (_) {}
}

async function refreshAll() {
  await loadStats();
  loadCountryStats();
  loadActiveSessions();
  loadTopUsernames();
  loadTopIPs();
}

// ==================== INIT ====================
function init() {
  initGlobe();
  refreshAll();
  refreshTimer = setInterval(refreshAll, 6000);
}

document.addEventListener('DOMContentLoaded', init);
window.addEventListener('beforeunload', () => {
  if (refreshTimer) clearInterval(refreshTimer);
  if (feedTimer) clearInterval(feedTimer);
});
