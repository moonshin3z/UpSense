// Fuentes de datos de la app. Todas entregan muestras con la misma forma:
//   { t (ms), cf1 (PM2.5 crudo CF=1), corr (PM2.5 calibrado), ref (referencia, si hay),
//     rh, temp, pressure, co2, alerta (null|'dudosa'|'niebla'|'subida'), pausa (bool),
//     accion, f, rr }
import { calibrar, recomendar, crearEstado, RH_NIEBLA, RH_DUDOSA } from './ventana-calib.js';

const hoy = new Date(); hoy.setHours(0, 0, 0, 0);
const deMinuto = (min) => hoy.getTime() + min * 60e3;

// ---------------------------------------------------------------- demo
// datos/demo_aula.json: mañana simulada (32 alumnos, lluvia, quema a las 11:00)
// generada por el núcleo UpSense: dos maestras, una con el sensor crudo y otra con UpSense.
export async function cargarDemo(url = 'datos/demo_aula.json') {
  // Formato compacto (una fila por minuto desde d.inicio), generado desde calibracion/datos/demo_aula.json
  const d = await (await fetch(url)).json();
  const i = Object.fromEntries(d.cols.map((c, k) => [c, k]));
  const muestras = d.filas.map((r, k) => ({
    t: deMinuto(d.inicio + k), cf1: r[i.cf1], corr: r[i.corr], ref: r[i.ref], rh: r[i.rh], temp: r[i.temp],
    pressure: 850, co2: r[i.co2], alerta: d.alertas[r[i.alerta]], pausa: d.alertas[r[i.alerta]] === 'niebla',
    accion: d.acciones[r[i.accion]],
  }));
  const crudo = d.crudo.map(([co2, a], k) => ({ t: muestras[k].t, co2, accion: d.acciones[a] }));
  return { nombre: 'Mañana en el aula (simulada)', paso: 60e3, nota: d.nota, resumen: d.resumen, muestras, crudo };
}

// ---------------------------------------------------------------- CSV
// Acepta el CSV que exporta esta app, demo_aula.csv o una co-ubicación
// (pm25_cf1, rh, temp, pressure, pm25_referencia). Columnas por nombre.
const ALIAS = {
  t: ['t', 'timestamp', 'fecha', 'datetime', 'time'], hora: ['hora'], t_horas: ['t_horas'], minuto: ['minuto'],
  cf1: ['pm25_cf1', 'pm25_crudo', 'pm2.5_cf1', 'pm25cf1'], atm: ['pm25', 'pm25_atm'],
  rh: ['rh', 'humedad', 'hr'], temp: ['temp', 'temperatura', 't_c'], pressure: ['pressure', 'presion', 'p_hpa'],
  co2: ['co2', 'co2_ppm'], ref: ['pm25_referencia', 'pm25_real', 'referencia', 'pm25_ref'],
};

export function parsearCsv(texto) {
  const lineas = texto.trim().split(/\r?\n/);
  const sep = (lineas[0].match(/;/g) || []).length > (lineas[0].match(/,/g) || []).length ? ';' : ',';
  const cab = lineas[0].split(sep).map((c) => c.trim().toLowerCase().replace(/^"|"$/g, ''));
  const idx = {};
  for (const [k, al] of Object.entries(ALIAS)) { const i = cab.findIndex((c) => al.includes(c)); if (i >= 0) idx[k] = i; }
  if (idx.cf1 == null && idx.atm != null) idx.cf1 = idx.atm;
  if (idx.cf1 == null) throw new Error('No encuentro una columna de PM2.5 (pm25_cf1, pm25_crudo o pm25).');
  const num = (v) => { if (v == null || v === '') return null; const n = Number(String(v).replace(',', '.')); return Number.isFinite(n) ? n : null; };
  const filas = [];
  for (let i = 1; i < lineas.length; i++) {
    const c = lineas[i].split(sep);
    let t;
    if (idx.t != null) { t = Date.parse(c[idx.t]); if (Number.isNaN(t)) t = null; }
    if (t == null && idx.minuto != null) t = deMinuto(num(c[idx.minuto]));
    if (t == null && idx.t_horas != null) t = hoy.getTime() + num(c[idx.t_horas]) * 3600e3;
    if (t == null && idx.hora != null && /\d+:\d+/.test(c[idx.hora])) { const [h, m] = c[idx.hora].split(':').map(Number); t = deMinuto(h * 60 + m); }
    if (t == null) t = hoy.getTime() + (i - 1) * 60e3;  // sin tiempo: 1 fila = 1 minuto
    filas.push({ t, cf1: num(c[idx.cf1]), rh: num(c[idx.rh]), temp: num(c[idx.temp]), pressure: num(c[idx.pressure]),
      co2: num(c[idx.co2]), ref: idx.ref != null ? num(c[idx.ref]) : null });
  }
  filas.sort((a, b) => a.t - b.t);
  return filas;
}

// Calibra, aplica la guardia de humedad y calcula el semáforo fila por fila,
// igual que en vivo: promedios de 5 min y tendencia de 10 min.
export function procesarSerie(filas, modelo) {
  const est = crearEstado(), estCrudo = crearEstado();
  const out = [], crudo = [];
  let fiable = null;
  // media de k en (desde, hasta] recorriendo hacia atrás (filas ordenadas por t)
  const media = (arr, k, desde, hasta) => {
    let s = 0, n = 0;
    for (let j = arr.length - 1; j >= 0 && arr[j].t > desde; j--) if (arr[j].t <= hasta && arr[j][k] != null) { s += arr[j][k]; n++; }
    return n ? s / n : null;
  };
  for (let i = 0; i < filas.length; i++) {
    const r = filas[i];
    const c = r.cf1 == null ? { pm25: null } : calibrar({ pm25_cf1: r.cf1, rh: r.rh ?? 50, temp: r.temp ?? 22, pressure: r.pressure ?? 850 }, modelo);
    let rhMin = r.rh;
    for (let j = i - 1; j >= 0 && filas[j].t >= r.t - 120e3; j--) if (filas[j].rh != null) rhMin = Math.min(rhMin, filas[j].rh);
    const subida = r.rh != null && r.rh - rhMin >= 6;
    const alerta = r.rh == null ? null : r.rh > RH_NIEBLA ? 'niebla' : subida ? 'subida' : r.rh > RH_DUDOSA ? 'dudosa' : null;
    const pausa = alerta === 'niebla' || alerta === 'subida';
    if (!pausa && c.pm25 != null) fiable = c.pm25;
    const m = { ...r, corr: pausa ? fiable : c.pm25, corrModelo: c.pm25, alerta, pausa };
    out.push(m);
    // ventana de 5 min (al menos la muestra actual si los datos son más espaciados)
    const v5 = Math.min(r.t - 5 * 60e3, r.t - 1);
    // Tendencia: contra hace 9-15 min; si la medición es más corta, contra lo anterior a 5 min
    const antes = (k) => media(out, k, r.t - 15 * 60e3, r.t - 9 * 60e3) ?? media(out, k, -Infinity, v5);
    const pmA = media(out, 'corr', v5, r.t), pmB = antes('corr');
    const co2 = media(out, 'co2', v5, r.t);
    const rec = recomendar({ co2, pm25: pausa ? null : pmA, fuentePm: 'interior', pm25Tendencia: pmA != null && pmB != null ? pmA - pmB : null }, est);
    Object.assign(m, { accion: rec.accion, f: rec.f, rr: rec.riesgoRelativo });
    // Lo que haría la maestra con el sensor sin corregir (mismos datos, PM crudo)
    const cA = media(out, 'cf1', v5, r.t), cB = antes('cf1');
    const recC = recomendar({ co2, pm25: cA, fuentePm: 'interior', pm25Tendencia: cA != null && cB != null ? cA - cB : null }, estCrudo);
    crudo.push({ t: r.t, accion: recC.accion });
  }
  const paso = filas.length > 1 ? Math.max(1e3, (filas[filas.length - 1].t - filas[0].t) / (filas.length - 1)) : 60e3;
  return { muestras: out, crudo, paso };
}

// ---------------------------------------------------------------- en vivo
export async function leerJson(url, ms = 4000) {
  const ctl = new AbortController();
  const to = setTimeout(() => ctl.abort(), ms);
  try {
    const r = await fetch(url, { cache: 'no-store', signal: ctl.signal });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return await r.json();
  } finally { clearTimeout(to); }
}

// Historial del equipo (/api/history) a muestras
export function historialAMuestras(h) {
  const i = Object.fromEntries(h.fields.map((f, k) => [f, k]));
  const ahora = Date.now();
  return h.rows.map((r) => ({ t: ahora - (h.uptime - r[i.t]) * 1000, cf1: r[i.pm25_cf1], rh: r[i.rh], temp: r[i.temp], pressure: 850, co2: r[i.co2], ref: null }));
}
