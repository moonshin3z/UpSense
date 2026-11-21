import { COLOR_LED, PM_SENSIBLES, PM_DANINO, CO2_EXTERIOR_PPM, CO2_ALIENTO_PPM, F_VERDE, F_ROJO } from './ventana-calib.js';
import { cargarDemo, parsearCsv, procesarSerie, leerJson, historialAMuestras } from './fuentes.js';
import { lineas, hhmm } from './graficas.js';

const $ = (id) => document.getElementById(id);
const fmt = (v, d = 0) => (v == null || Number.isNaN(v) ? '—' : Number(v).toFixed(d));
const colorAccion = (a) => `rgb(${(COLOR_LED[a] || COLOR_LED.sin_datos).join(',')})`;

// Qué hacer, dicho como se lo diría una persona al aula
const TEXTOS = {
  nada: ['Todo bien.', 'No hace falta abrir ni cerrar la ventana.'],
  abrir_parcial: ['Abran un poco la ventana.', 'El aire del aula se está cargando.'],
  abrir: ['Abran la ventana.', 'Hay mucho aire que ya respiraron otros.'],
  cerrar: ['Cierren la ventana.', 'Subió el humo o el polvo dentro del aula.'],
  ventilar_corto: ['Abran cinco minutos y cierren.', 'El aula necesita aire, pero hay humo o polvo.'],
  sin_datos: ['Esperando al sensor.', 'Todavía no hay lectura del aire del aula.'],
};
const fCo2 = (co2) => Math.max(0, (co2 - CO2_EXTERIOR_PPM) / CO2_ALIENTO_PPM);
const palabraPm = (v) => v == null ? '—' : v <= 15 ? 'Limpio' : v <= PM_SENSIBLES ? 'Regular' : v <= PM_DANINO ? 'Sucio' : 'Muy sucio';
const palabraAire = (co2) => { if (co2 == null) return '—'; const f = fCo2(co2); return f < F_VERDE ? 'Fresco' : f < F_ROJO ? 'Algo cargado' : 'Muy cargado'; };
const palabraHum = (rh) => rh == null ? '—' : rh > 95 ? 'Niebla o vapor' : rh > 85 ? 'Alta' : 'Normal';
const num = (v) => Math.round(v).toLocaleString('es-GT');

// ---------------------------------------------------------------- estado
let modelo = null;
const st = {
  fuente: null, datos: null,       // datos: {nombre, muestras, crudo, paso, resumen?}
  tc: 0, play: false, vel: 3,      // cursor (ms) y reproducción (min por segundo)
  vivo: { filas: [], timer: null, base: '', ultimoLed: 0 },
};
let csvCargado = null;

function muestraEn(t) {
  const m = st.datos?.muestras || [];
  if (!m.length) return {};
  let lo = 0, hi = m.length - 1;
  while (lo < hi) { const mid = (lo + hi + 1) >> 1; if (m[mid].t <= t) lo = mid; else hi = mid - 1; }
  return { m: m[lo], c: st.datos.crudo?.[lo] };
}
const t0 = () => st.datos.muestras[0].t;
const t1 = () => st.datos.muestras[st.datos.muestras.length - 1].t;

// Cambio de frase: la nueva entra con un fundido suave (sin animar si el sistema pide menos movimiento)
const menosMov = matchMedia('(prefers-reduced-motion: reduce)');
function ponerTexto(el, txt, retraso = 0) {
  if (el.textContent === txt) return;
  const primera = !el.dataset.listo;
  el.textContent = txt; el.dataset.listo = '1';
  if (primera || menosMov.matches || !el.animate) return;
  el.animate([
    { opacity: 0, transform: 'translateY(14px)', filter: 'blur(10px)' },
    { opacity: 1, transform: 'none', filter: 'blur(0)' },
  ], { duration: 620, delay: retraso, easing: 'cubic-bezier(.2,.8,.2,1)', fill: 'backwards' });
}

// ---------------------------------------------------------------- render
function render() {
  const d = st.datos;
  if (!d || !d.muestras.length) { renderVacio(); return; }
  const vivo = st.fuente === 'vivo';
  const { m, c } = muestraEn(vivo ? Infinity : st.tc);

  let [tit, razon] = TEXTOS[m.accion] || TEXTOS.sin_datos;
  if (m.accion === 'sin_datos' && !d.muestras.some((x) => x.co2 != null)) {
    tit = 'Este archivo no trae CO₂.'; razon = 'Sin CO₂ no hay recomendación, pero abajo se ve cómo UpSense corrige las partículas.';
  }
  ponerTexto($('titulo'), tit);
  ponerTexto($('razon'), razon, 60);
  $('punto').style.background = colorAccion(m.accion);
  document.body.style.setProperty('--tono', colorAccion(m.accion));
  $('hora').textContent = (vivo ? 'En vivo' : d.nombre) + ' · ' + hhmm(m.t);
  document.title = `${tit} · UpSense`;

  // Lo que diría un sensor sin corregir, solo si se equivoca
  const otro = c && c.accion && c.accion !== m.accion;
  $('contraste').hidden = !otro;
  if (otro) {
    $('contraste').replaceChildren('Un sensor sin corregir diría ', Object.assign(document.createElement('s'), { textContent: `«${TEXTOS[c.accion][0].replace(/\.$/, '')}»` }),
      m.alerta ? '. Es humedad, no humo.' : '. Sigue con la falsa alarma.');
  }

  // Tres indicadores siempre visibles, en palabras
  const nivel = (id, f) => { $(id).style.width = `${Math.round(Math.min(1, Math.max(0, f)) * 100)}%`; };
  ponerTexto($('iAire'), palabraAire(m.co2)); $('nAire').textContent = m.co2 != null ? `CO₂ ${num(m.co2)} ppm` : 'CO₂';
  nivel('bAire', m.co2 != null ? fCo2(m.co2) / (F_ROJO * 1.5) : 0);
  ponerTexto($('iPolvo'), palabraPm(m.corr)); $('nPolvo').textContent = m.corr != null ? `${fmt(m.corr)} µg/m³ corregido` : 'Partículas';
  nivel('bPolvo', m.corr != null ? m.corr / (PM_DANINO * 1.2) : 0);
  ponerTexto($('iHum'), palabraHum(m.rh)); $('nHum').textContent = m.rh != null ? `${fmt(m.rh)} %` + (m.temp != null ? ` · ${fmt(m.temp)} °C` : '') : 'Humedad relativa';
  nivel('bHum', m.rh != null ? m.rh / 100 : 0);

  // Detalles (detrás de un toque)
  $('dAire').textContent = m.co2 != null ? `${palabraAire(m.co2)} · CO₂ ${num(m.co2)} ppm` : '—';
  $('dPolvo').textContent = m.corr != null ? `${palabraPm(m.corr)} · PM2.5 ${fmt(m.corr)} µg/m³` + (m.cf1 != null ? ` (sin corregir ${fmt(m.cf1)})` : '') : '—';
  $('dHum').textContent = m.rh != null ? `${palabraHum(m.rh)} · ${fmt(m.rh)} %` + (m.temp != null ? ` · ${fmt(m.temp)} °C` : '') : '—';
  $('dRiesgo').textContent = m.co2 != null ? `${fmt(Math.max(fCo2(m.co2) / fCo2(800), 0), 1)} × un aula bien ventilada` : '—';

  renderGrafica();
  if (!vivo) $('barra').value = Math.round(((st.tc - t0()) / Math.max(1, t1() - t0())) * 1000);
}

function renderGrafica() {
  const d = st.datos, vivo = st.fuente === 'vivo';
  if ($('prueba').hidden || !d?.muestras.length) return;
  const ms = d.muestras;
  const a = vivo ? Math.max(t0(), t1() - 3600e3) : t0(), b = vivo ? Math.max(t1(), a + 60e3) : t1();
  const bandas = [];
  for (const x of ms) {
    if (!(x.alerta === 'niebla' || x.alerta === 'subida')) continue;
    const last = bandas[bandas.length - 1];
    if (last && x.t - last.t1 <= d.paso * 1.5) last.t1 = x.t + d.paso; else bandas.push({ t0: x.t, t1: x.t + d.paso, color: 'var(--humo)' });
  }
  const tieneRef = ms.some((x) => x.ref != null);
  $('leyRef').hidden = !tieneRef;
  lineas($('gPm'), {
    titulo: 'Partículas: sensor sin corregir y UpSense', t0: a, t1: b, corteGap: d.paso * 5, bandas, unidad: ' µg/m³',
    alClic: vivo ? null : (t) => { ponerPlay(false); st.tc = t; render(); },
    series: [
      { nombre: 'Sin corregir', data: ms.map((x) => [x.t, x.cf1]), color: 'var(--s-crudo)', ancho: 2 },
      ...(tieneRef ? [{ nombre: 'Referencia', data: ms.map((x) => [x.t, x.ref]), color: 'var(--s-ref)', ancho: 1.5, guion: '2 4' }] : []),
      { nombre: 'UpSense', data: ms.map((x) => [x.t, x.corr]), color: 'var(--s-ventana)', ancho: 2.25 },
    ],
    lineasH: [{ v: PM_SENSIBLES, color: 'var(--faint)', texto: 'alarma' }],
    cursor: vivo ? null : st.tc, sinEtiquetas: true,
  });
}

function renderVacio() {
  $('titulo').textContent = st.fuente === 'csv' ? 'Elija un archivo.' : st.fuente === 'vivo' ? 'Conecte su equipo.' : 'Cargando';
  $('razon').textContent = st.fuente === 'csv' ? 'UpSense le muestra qué habría recomendado en cada momento.' : st.fuente === 'vivo' ? 'Escriba la dirección que muestra el equipo al encenderse.' : '';
  $('hora').textContent = '—';
  $('punto').style.background = 'var(--estado)';
  document.body.style.removeProperty('--tono');
  $('contraste').hidden = true;
  $('prueba').hidden = true;
  for (const k of ['Aire', 'Polvo', 'Hum']) { $('i' + k).textContent = '—'; $('b' + k).style.width = '0'; }
}

// ---------------------------------------------------------------- la prueba (resumen + gráfica)
function renderPrueba() {
  const d = st.datos;
  const hay = d && d.muestras.length;
  $('prueba').hidden = !hay;
  if (!hay) return;
  if (d.resumen) {
    const c = d.resumen.sensor_crudo, v = d.resumen.ventana;
    $('pruebaTitulo').textContent = `En una mañana con niebla, el sensor común dio ${c.min_falsa_alarma_pm} minutos de falsa alarma. UpSense, ${v.min_falsa_alarma_pm}.`;
    $('pruebaSub').textContent = `La maestra que le hizo caso al sensor común cerró el aula, y el riesgo de contagio llegó a ${fmt(c.riesgo_relativo_medio, 1)} veces el de un aula ventilada. Con UpSense fue ${fmt(v.riesgo_relativo_medio, 1)}. Mañana simulada, aula de 32 alumnos en la Ciudad de Guatemala.`;
    return;
  }
  if (st.fuente === 'vivo') {
    $('pruebaTitulo').textContent = 'La última hora en su aula.';
    $('pruebaSub').textContent = 'La línea clara es lo que mide el sensor solo; la oscura, lo que corrige UpSense.';
    return;
  }
  const ms = d.muestras, min = d.paso / 60e3;
  const ref = ms.some((x) => x.ref != null);
  const falsa = (k) => ms.filter((x) => x[k] != null && x[k] > PM_SENSIBLES && (ref ? x.ref != null && x.ref <= PM_SENSIBLES : true)).length * min / 60;
  const mae = (k) => { const xs = ms.filter((x) => x[k] != null && x.ref != null); return xs.length ? xs.reduce((s, x) => s + Math.abs(x[k] - x.ref), 0) / xs.length : null; };
  $('pruebaTitulo').textContent = ref
    ? `Sin corregir: ${fmt(falsa('cf1'), 1)} h de falsa alarma. Con UpSense: ${fmt(falsa('corr'), 1)} h.`
    : `Sin corregir: ${fmt(falsa('cf1'), 1)} h sobre el umbral de alarma. Con UpSense: ${fmt(falsa('corr'), 1)} h.`;
  $('pruebaSub').textContent = `${ms.length.toLocaleString('es-GT')} lecturas en ${fmt((t1() - t0()) / 3600e3, 1)} h.` + (ref ? ` Error medio contra la referencia: ${fmt(mae('cf1'), 1)} µg/m³ sin corregir y ${fmt(mae('corr'), 1)} con UpSense.` : '');
}

// ---------------------------------------------------------------- reproductor
let ultimoFrame = 0;
function bucle(ts) {
  if (st.play && st.datos?.muestras.length && st.fuente !== 'vivo') {
    const dt = ultimoFrame ? (ts - ultimoFrame) / 1000 : 0;
    st.tc += dt * st.vel * 60e3;
    if (st.tc >= t1()) { st.tc = t1(); ponerPlay(false); }
    render();
  }
  ultimoFrame = ts;
  requestAnimationFrame(bucle);
}
function ponerPlay(on) {
  st.play = on;
  $('btnPlay').textContent = on ? 'Pausar' : 'Reproducir';
  if (on && st.datos?.muestras.length && st.tc >= t1()) st.tc = t0();
}
function momentos() {
  const el = $('momentos'); el.replaceChildren();
  if (st.fuente !== 'demo') return;
  const ms = st.datos.muestras;
  const lista = [];
  const niebla = ms.find((x) => x.alerta === 'niebla'); if (niebla) lista.push([niebla.t, 'Niebla']);
  const crudoMax = st.datos.crudo.reduce((a, b) => (b.co2 > (a?.co2 ?? 0) ? b : a), null);
  if (crudoMax) lista.push([crudoMax.t - 20 * 60e3, 'Falsa alarma']);
  const quema = ms.find((x) => x.t >= ms[0].t + 4 * 3600e3 && (x.ref ?? 0) > PM_SENSIBLES);
  if (quema) lista.push([quema.t, 'Humo de una quema']);
  for (const [t, txt] of lista.sort((a, b) => a[0] - b[0])) {
    const b = document.createElement('button');
    b.append(Object.assign(document.createElement('b'), { textContent: hhmm(t) }), txt);
    b.onclick = () => { ponerPlay(false); st.tc = t; render(); };
    el.appendChild(b);
  }
}

// ---------------------------------------------------------------- fuentes
async function usarFuente(f) {
  st.fuente = f;
  document.querySelectorAll('.fuentes button').forEach((b) => b.setAttribute('aria-selected', String(b.dataset.fuente === f)));
  $('panelCsv').hidden = f !== 'csv'; $('panelVivo').hidden = f !== 'vivo';
  $('jugador').hidden = f !== 'demo';
  $('notaDatos').hidden = f !== 'demo';
  pararVivo(); ponerPlay(false);
  try { history.replaceState(null, '', `#${f}`); } catch {}
  st.datos = null;
  if (f === 'demo') {
    st.datos = await cargarDemo();
    st.tc = t0();
    ponerPlay(true);
  } else if (f === 'csv') {
    if (csvCargado) { st.datos = csvCargado; st.tc = t1(); }
  } else if (f === 'vivo') {
    iniciarVivo();
  }
  momentos(); renderPrueba(); render();
}

async function cargarArchivo(file) {
  const msg = $('csvMsg');
  try {
    const filas = parsearCsv(await file.text());
    const r = procesarSerie(filas, modelo);
    csvCargado = { nombre: file.name.replace(/\.csv$/i, ''), ...r };
    msg.className = 'aviso'; msg.textContent = `${filas.length.toLocaleString('es-GT')} lecturas de ${file.name}.`;
    st.datos = csvCargado; st.tc = t1();
    momentos(); renderPrueba(); render();
  } catch (e) { msg.className = 'aviso error'; msg.textContent = `No se pudo leer el archivo: ${e.message}`; }
}

// --- en vivo
const baseVivo = () => (st.vivo.base || '').replace(/\/$/, '');
function pararVivo() { clearInterval(st.vivo.timer); st.vivo.timer = null; }
async function iniciarVivo() {
  const msg = $('vivoMsg');
  st.vivo.filas = [];
  st.datos = { nombre: 'En vivo', muestras: [], crudo: [], paso: 2000 };
  if (location.protocol === 'https:' && baseVivo().startsWith('http:')) {
    msg.className = 'aviso error';
    msg.textContent = 'Por seguridad, el navegador no deja leer el equipo desde esta página. Abra la app desde el propio equipo, en http://aire.local.';
    return;
  }
  try { st.vivo.filas = historialAMuestras(await leerJson(`${baseVivo()}/api/history`, 5000)); } catch { /* sigue sin historial */ }
  msg.className = 'aviso'; msg.textContent = 'Conectando…';
  await tickVivo();
  st.vivo.timer = setInterval(tickVivo, 2000);
}
async function tickVivo() {
  const msg = $('vivoMsg');
  try {
    const r = await leerJson(`${baseVivo()}/api/now`);
    $('btnVapor').hidden = r.fw !== 'sim';
    st.vivo.filas.push({ t: Date.now(), cf1: r.pm25_cf1, rh: r.rh, temp: r.temp, pressure: r.pressure ?? 850, co2: r.co2_warmup ? null : r.co2, ref: null });
    const corte = Date.now() - 4 * 3600e3;
    while (st.vivo.filas.length && st.vivo.filas[0].t < corte) st.vivo.filas.shift();
    st.datos = { nombre: 'En vivo', ...procesarSerie(st.vivo.filas, modelo), paso: 2000 };
    const avisos = [];
    if (!r.pms_ok) avisos.push('el sensor de partículas no responde');
    if (r.co2_warmup) avisos.push('el sensor de CO₂ se está calentando (unos 3 minutos)');
    else if (!r.co2_ok) avisos.push('el sensor de CO₂ no responde');
    if (r.rh == null) avisos.push('falta el sensor de humedad, así que no se puede corregir');
    msg.className = avisos.length ? 'aviso error' : 'aviso';
    msg.textContent = avisos.length ? `Conectado, pero ${avisos.join(' y ')}.` : `Conectado a ${r.device}.`;
    if ($('prueba').hidden) renderPrueba();
    enviarALed();
    render();
  } catch {
    msg.className = 'aviso error';
    msg.textContent = `No se encuentra el equipo${baseVivo() ? ' en ' + baseVivo() : ''}. Revise que estén en la misma red WiFi.`;
    if (!st.datos.muestras.length) renderVacio();
  }
}
async function enviarALed() {
  const m = st.datos.muestras[st.datos.muestras.length - 1];
  if (!m || Date.now() - st.vivo.ultimoLed < 10000) return;
  st.vivo.ultimoLed = Date.now();
  try { await fetch(`${baseVivo()}/api/semaforo`, { method: 'POST', body: new URLSearchParams({ accion: m.accion, ttl: 60 }) }); } catch {}
}
function descargarCsv() {
  const ms = st.datos?.muestras || [];
  const cols = ['t', 'pm25_cf1', 'pm25_ventana', 'rh', 'temp', 'pressure', 'co2', 'accion'];
  const filas = ms.map((x) => [new Date(x.t).toISOString(), x.cf1, x.corr, x.rh, x.temp, x.pressure, x.co2, x.accion].map((v) => v ?? '').join(','));
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([[cols.join(','), ...filas].join('\n')], { type: 'text/csv' }));
  a.download = `upsense-${new Date().toISOString().slice(0, 16).replace(':', '')}.csv`;
  a.click();
}

// ---------------------------------------------------------------- portada: cómo funciona, en cuatro pasos
const ESCENAS = [
  { hora: '07:10', accion: 'nada', aire: ['Fresco', .25], polvo: ['Revisando…', .95], hum: ['Niebla o vapor', .97], nota: 'Lectura cruda: 140 µg/m³ con 97 % de humedad' },
  { hora: '07:12', accion: 'nada', aire: ['Fresco', .3], polvo: ['Limpio', .15], hum: ['Niebla o vapor', .97], nota: 'Corregida por humedad: 12 µg/m³' },
  { hora: '08:40', accion: 'abrir', aire: ['Muy cargado', .9], polvo: ['Limpio', .15], hum: ['Normal', .8], nota: '' },
  { hora: '08:52', accion: 'nada', aire: ['Fresco', .3], polvo: ['Limpio', .15], hum: ['Normal', .78], nota: '' },
];
function portada() {
  const esc = $('escena'); if (!esc) return;
  let i = 0;
  const pasos = [...$('pasos').children], cartas = [...esc.querySelectorAll('.flota')];
  const mostrar = (k) => {
    const e = ESCENAS[k], [tit, razon] = TEXTOS[e.accion];
    esc.style.setProperty('--tel-tono', colorAccion(e.accion));
    $('tHora').textContent = e.hora;
    ponerTexto($('tTitulo'), tit); $('tRazon').textContent = razon;
    for (const [id, [txt, f]] of [['Aire', e.aire], ['Polvo', e.polvo], ['Hum', e.hum]]) { ponerTexto($('t' + id), txt); $('tb' + id).style.width = `${f * 100}%`; }
    $('tNota').textContent = e.nota;
    pasos.forEach((p, j) => p.classList.toggle('on', j === k));
    cartas.forEach((c, j) => c.classList.toggle('on', j === k));
  };
  mostrar(menosMov.matches ? 2 : 0);
  if (menosMov.matches) return;
  setInterval(() => { if (document.hidden) return; i = (i + 1) % ESCENAS.length; mostrar(i); }, 3800);
  pasos.forEach((p, j) => { p.onclick = () => { i = j; mostrar(j); }; });
}

// ---------------------------------------------------------------- inicio
// Video de la demo: data-src en index.html, o ?video=<enlace> para probar sin publicar
function ponerVideo() {
  const caja = $('video');
  const src = (new URLSearchParams(location.search).get('video') || caja.dataset.src || '').trim();
  if (!src) return;
  let m, el;
  if ((m = src.match(/(?:youtu\.be\/|v=|shorts\/|embed\/)([\w-]{11})/))) {
    el = document.createElement('iframe');
    el.src = `https://www.youtube-nocookie.com/embed/${m[1]}?rel=0`;
  } else if ((m = src.match(/drive\.google\.com\/file\/d\/([\w-]+)/))) {
    el = document.createElement('iframe');
    el.src = `https://drive.google.com/file/d/${m[1]}/preview`;
  } else {
    el = document.createElement('video');
    el.src = src; el.controls = true; el.playsInline = true; el.preload = 'metadata';
  }
  if (el.tagName === 'IFRAME') { el.allow = 'autoplay; fullscreen; picture-in-picture'; el.allowFullscreen = true; el.title = 'Video de la demo de UpSense'; }
  caja.replaceChildren(el); caja.classList.add('lleno');
}

async function main() {
  ponerVideo();
  try { modelo = await (await fetch('modelo.json', { cache: 'no-store' })).json(); } catch { modelo = null; }
  document.querySelectorAll('.fuentes button').forEach((b) => (b.onclick = () => usarFuente(b.dataset.fuente)));
  $('btnPlay').onclick = () => ponerPlay(!st.play);
  $('barra').oninput = (e) => { if (!st.datos?.muestras.length) return; ponerPlay(false); st.tc = t0() + (e.target.value / 1000) * (t1() - t0()); render(); };
  $('btnMas').onclick = () => {
    const abrir = $('detalle').hidden;
    $('detalle').hidden = !abrir;
    $('btnMas').textContent = abrir ? 'Ocultar números' : 'Ver números exactos';
    $('btnMas').setAttribute('aria-expanded', String(abrir));
  };
  $('archivo').onchange = (e) => e.target.files[0] && cargarArchivo(e.target.files[0]);
  const sol = $('soltar');
  sol.ondragover = (e) => { e.preventDefault(); sol.classList.add('encima'); };
  sol.ondragleave = () => sol.classList.remove('encima');
  sol.ondrop = (e) => { e.preventDefault(); sol.classList.remove('encima'); if (e.dataTransfer.files[0]) cargarArchivo(e.dataTransfer.files[0]); };
  let guardado = '';
  try { guardado = localStorage.getItem('ventana.device') || ''; } catch {}
  $('cfgDevice').value = guardado;
  $('btnConectar').onclick = () => { st.vivo.base = $('cfgDevice').value.trim(); try { localStorage.setItem('ventana.device', st.vivo.base); } catch {} usarFuente('vivo'); };
  $('btnVapor').onclick = () => fetch(`${baseVivo()}/api/sim/vapor`, { method: 'POST' });
  $('btnCsv').onclick = descargarCsv;
  // Doble clic en el estado: pantalla completa para proyectar
  const proyectar = (on) => {
    document.body.classList.toggle('presentar', on);
    try { if (on) document.documentElement.requestFullscreen?.(); else if (document.fullscreenElement) document.exitFullscreen(); } catch {}
  };
  $('btnProyectar').onclick = (e) => { e.stopPropagation(); proyectar(true); };
  document.querySelector('.estado').ondblclick = () => proyectar(!document.body.classList.contains('presentar'));
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') proyectar(false); });
  document.addEventListener('fullscreenchange', () => { if (!document.fullscreenElement) document.body.classList.remove('presentar'); });
  window.addEventListener('resize', () => renderGrafica());
  // Fondo que sigue al cursor o al dedo, con retardo suave
  let pend = false, mx = 0, my = 0;
  window.addEventListener('pointermove', (e) => {
    mx = (e.clientX / innerWidth) * 2 - 1; my = (e.clientY / innerHeight) * 2 - 1;
    if (pend) return; pend = true;
    requestAnimationFrame(() => { pend = false; const r = document.documentElement.style; r.setProperty('--mx', mx.toFixed(3)); r.setProperty('--my', my.toFixed(3)); });
  }, { passive: true });
  // Las secciones aparecen al llegar a ellas
  if ('IntersectionObserver' in window && !menosMov.matches) {
    const io = new IntersectionObserver((es) => es.forEach((en) => { if (en.isIntersecting) { en.target.classList.add('visto'); io.unobserve(en.target); } }), { rootMargin: '0px 0px -8% 0px' });
    document.querySelectorAll('.jugador, .prueba, .equipo h2, .equipo .sub, .aparato, .flujo li, .video, .como h2, .tres article, .nota').forEach((el, i) => { el.classList.add('revelar'); el.style.setProperty('--i', i % 3); io.observe(el); });
  }
  requestAnimationFrame(bucle);
  portada();

  const q = new URLSearchParams(location.search);
  if (q.get('presentar') === '1') document.body.classList.add('presentar');
  st.vivo.base = q.get('device') || guardado;
  // Si la página la sirve el propio equipo (o el simulador), arranca en vivo
  let pedida = location.hash.slice(1);
  if (!['demo', 'csv', 'vivo'].includes(pedida)) {
    pedida = 'demo';
    if (q.get('device')) pedida = 'vivo';
    else { try { await leerJson('api/now', 1500); st.vivo.base = ''; pedida = 'vivo'; } catch {} }
  }
  usarFuente(pedida);
}
main();
