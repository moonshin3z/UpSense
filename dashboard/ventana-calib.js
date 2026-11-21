/*
 * ventana-calib.js · núcleo científico de Ventana para el dashboard
 *
 * Dos hallazgos convertidos en código:
 *  1. Sitarek et al. 2026 (Sensors 26:6718, doi:10.3390/s26216718):
 *     corregir por software el error de humedad de sensores ópticos baratos
 *     con T, HR y presión y un modelo liviano.  →  calibrar()
 *  2. Vouriot et al. 2024 (J R Soc Interface, doi:10.1098/rsif.2024.0270):
 *     con un sensor de CO2 se estima la fracción de aire reexhalado y el
 *     riesgo relativo de contagio (Wells-Riley / Rudnick-Milton). → recomendar()
 *
 * Misma lógica que python/ventana (los vectores de datos/vectores_prueba.json
 * deben dar lo mismo en ambos). Sin dependencias. Es un ES module
 * (<script type="module">); además deja todo en window.VentanaCalib.
 *
 * Uso:
 *   import { calibrar, recomendar, crearEstado } from './ventana-calib.js';
 *   const modelo = await (await fetch('modelo.json')).json();  // opcional
 *   const c = calibrar({ pm25_cf1: 42, rh: 88, temp: 18, pressure: 851 }, modelo);
 *   // c = { pm25: 14.1, crudo: 42, metodo: 'ventana-polinomio', alerta_humedad: 'dudosa' }
 *   const estado = crearEstado();             // uno por aula, se reutiliza
 *   const r = recomendar({ co2: 1350, pm25: c.pm25, fuentePm: 'interior', pm25Tendencia: 1 }, estado);
 *   // r = { accion: 'abrir', titulo, texto, nivel: 3, f: 0.0243, riesgoRelativo: 2.46, ... }
 */

// ------------------------------------------------------------ constantes
export const CO2_ALIENTO_PPM = 38000;   // [POR CONFIRMAR] valor exacto en Vouriot 2024
export const CO2_EXTERIOR_PPM = 425;    // [POR CONFIRMAR] medir en el patio
export const CO2_REFERENCIA_PPM = 800;  // aula "bien ventilada"
export const F_VERDE = 0.010;           // ≈ 805 ppm
export const F_ROJO = 0.020;            // ≈ 1185 ppm
export const PM_SENSIBLES = 35.4;       // AQI EPA 2024
export const PM_DANINO = 55.4;
export const HISTERESIS_F = 0.0015;
export const HISTERESIS_PM = 3.0;
export const TENDENCIA_ENTRADA = 5.0;
export const RH_DUDOSA = 85;
export const RH_NIEBLA = 95;
const RH_MAX = 98;

// ------------------------------------------------------------ variables derivadas
const clampRh = (rh) => Math.min(Math.max(rh, 1), RH_MAX);

export function dewpoint(temp, rh) {
  const a = 17.62, b = 243.12;
  const g = Math.log(clampRh(rh) / 100) + (a * temp) / (b + temp);
  return (b * g) / (a - g);
}

/** Crudas + derivadas (dewpoint, dpd, hgf). Acepta nombres alternativos. */
export function derivadas(l) {
  const v = {
    pm25_cf1: num(l.pm25_cf1 ?? l.pm25Cf1),
    rh: num(l.rh ?? l.humedad, 50),
    temp: num(l.temp ?? l.temperatura, 20),
    pressure: num(l.pressure ?? l.presion, 850),
  };
  const rh = clampRh(v.rh);
  v.dewpoint = dewpoint(v.temp, rh);
  v.dpd = v.temp - v.dewpoint;
  v.hgf = rh / (100 - rh);           // crecimiento higroscópico κ-Köhler
  // alias que usa el evaluador del dashboard
  v.rh2 = v.rh * v.rh;
  v.pm25cf1_rh = v.pm25_cf1 * v.rh;
  return v;
}

function num(x, porDefecto = NaN) {
  const n = Number(x);
  return x === null || x === undefined || Number.isNaN(n) ? porDefecto : n;
}

/** Evalúa un término: 'pm25_cf1', 'pm25_cf1*hgf', 'pm25_cf1*hgf^2', '1'. */
export function valorTermino(nombre, v) {
  if (nombre === '1') return 1;
  let total = 1;
  for (const f of nombre.split('*')) {
    const [base, exp] = f.split('^');
    if (!(base in v)) throw new Error(`variable desconocida: ${base}`);
    total *= exp ? Math.pow(v[base], parseInt(exp, 10)) : v[base];
  }
  return total;
}

// ------------------------------------------------------------ calibración
export function pm25CorregidoEpa(cf1, rhIn) {
  const x = Math.max(0, cf1);
  const rh = Math.min(Math.max(rhIn, 0), 100);
  let y;
  if (x < 30) y = 0.524 * x - 0.0862 * rh + 5.75;
  else if (x < 50) {
    const w = x / 20 - 1.5;
    y = (0.786 * w + 0.524 * (1 - w)) * x - 0.0862 * rh + 5.75;
  } else if (x < 210) y = 0.786 * x - 0.0862 * rh + 5.75;
  else if (x < 260) {
    const w = x / 50 - 4.2;
    y = (0.69 * w + 0.786 * (1 - w)) * x - 0.0862 * rh * (1 - w)
      + 2.966 * w + 5.75 * (1 - w) + 8.84e-4 * x * x * w;
  } else y = 2.966 + 0.69 * x + 8.84e-4 * x * x;
  return Math.max(0, y);
}

function evalArbol(t, x) {
  let n = 0;
  while (t.children_left[n] !== -1) {
    n = x[t.feature[n]] <= t.threshold[n] ? t.children_left[n] : t.children_right[n];
  }
  return t.value[n];
}

export function evaluar(modelo, v) {
  if (modelo.kohler) {
    const { a, kappa } = modelo.kohler;
    return v.pm25_cf1 / (a * (1 + (kappa / 1.65) * v.hgf));
  }
  if (modelo.tipo === 'lineal') {
    let y = modelo.intercepto ?? 0;
    modelo.features.forEach((f, i) => { y += modelo.coef[i] * valorTermino(f, v); });
    return y;
  }
  if (modelo.tipo === 'arboles') {
    const x = modelo.features.map((f) => valorTermino(f, v));
    let s = 0;
    for (const t of modelo.arboles) s += evalArbol(t, x);
    if (modelo.agregacion === 'media') return s / modelo.arboles.length;
    return (modelo.base ?? 0) + (modelo.learning_rate ?? 1) * s;
  }
  throw new Error('tipo de modelo desconocido');
}

/**
 * @param lectura {pm25_cf1, rh, temp, pressure}  crudas del firmware
 * @param modelo  contenido de modelo.json, o null → corrección EPA
 * @returns {pm25, crudo, metodo, alerta_humedad: null|'dudosa'|'niebla'}
 */
export function calibrar(lectura, modelo = null) {
  const v = derivadas(lectura);
  if (Number.isNaN(v.pm25_cf1)) return { pm25: null, crudo: null, metodo: 'sin_datos', alerta_humedad: null };
  let pm, metodo;
  if (modelo) { pm = evaluar(modelo, v); metodo = modelo.id || 'modelo'; }
  else { pm = pm25CorregidoEpa(v.pm25_cf1, v.rh); metodo = 'epa'; }
  pm = Math.max(modelo?.min ?? 0, pm);
  const alerta = v.rh > RH_NIEBLA ? 'niebla' : v.rh > RH_DUDOSA ? 'dudosa' : null;
  return { pm25: Math.round(pm * 100) / 100, crudo: v.pm25_cf1, metodo, alerta_humedad: alerta };
}

// ------------------------------------------------------------ CO2 → riesgo (Vouriot 2024)
export function fraccionReexhalada(co2, co2Ext = CO2_EXTERIOR_PPM) {
  return Math.max(0, (co2 - co2Ext) / CO2_ALIENTO_PPM);
}

export function riesgoRelativo(f, co2Ext = CO2_EXTERIOR_PPM) {
  return f / fraccionReexhalada(CO2_REFERENCIA_PPM, co2Ext);
}

/** Wells-Riley con CO2: P = 1 - exp(-f·I·q·t/n). q es ILUSTRATIVO. */
export function probContagio(fMedia, horas, personas, infectados = 1, quantaH = 15) {
  if (personas <= 0) return 0;
  return 1 - Math.exp((-fMedia * infectados * quantaH * horas) / personas);
}

// ------------------------------------------------------------ semáforo
const TEXTOS = {
  nada: ['Aire en buen estado', 'No hace falta hacer nada.'],
  abrir_parcial: ['Abra un poco la ventana', 'El aire del aula se está cargando.'],
  abrir: ['Abra la ventana ya', 'Mucho aire ya respirado por otros: ventile ahora.'],
  cerrar: ['Cierre la ventana', 'Está entrando humo o polvo de afuera.'],
  ventilar_corto: ['Ventile 5 minutos y cierre',
    'El aula necesita aire, pero afuera está sucio: abra del todo 5 min y vuelva a cerrar.'],
  sin_datos: ['Sin datos', 'Revise el sensor de CO2.'],
};
const NIVEL = { nada: 0, abrir_parcial: 1, cerrar: 2, ventilar_corto: 2, abrir: 3, sin_datos: 0 };

export function crearEstado() { return { nivelCo2: 0, nivelPm: 0 }; }

function nivelHist(valor, cortes, anterior, h) {
  let nivel = 0;
  cortes.forEach((c, i) => { if (valor >= (anterior >= i + 1 ? c - h : c)) nivel = i + 1; });
  return nivel;
}

/**
 * @param {co2, pm25, fuentePm: 'interior'|'exterior', pm25Tendencia, co2Exterior?}
 *        co2 y pm25 promediados ~5 min, pm25 YA calibrado
 * @param estado objeto de crearEstado() (histéresis); opcional
 * @returns {accion, titulo, texto, nivel 0-3, f, riesgoRelativo, nivelCo2, nivelPm}
 */
export function recomendar(e, estado = crearEstado()) {
  if (e.co2 === null || e.co2 === undefined || Number.isNaN(Number(e.co2))) {
    const [titulo, texto] = TEXTOS.sin_datos;
    return { accion: 'sin_datos', titulo, texto, nivel: 0, f: null, riesgoRelativo: null };
  }
  const co2Ext = e.co2Exterior ?? CO2_EXTERIOR_PPM;
  const f = fraccionReexhalada(e.co2, co2Ext);
  const rr = riesgoRelativo(f, co2Ext);
  const nc = nivelHist(f, [F_VERDE, F_ROJO], estado.nivelCo2, HISTERESIS_F);
  const tienePm = e.pm25 !== null && e.pm25 !== undefined && !Number.isNaN(Number(e.pm25));
  const npm = tienePm ? nivelHist(e.pm25, [PM_SENSIBLES, PM_DANINO], estado.nivelPm, HISTERESIS_PM) : 0;
  estado.nivelCo2 = nc; estado.nivelPm = npm;

  const entrando = e.fuentePm === 'exterior'
    || (e.pm25Tendencia !== null && e.pm25Tendencia !== undefined && e.pm25Tendencia >= TENDENCIA_ENTRADA);
  let accion;
  if (nc === 0) accion = npm === 0 ? 'nada' : (entrando ? 'cerrar' : 'abrir_parcial');
  else if (npm >= 1) accion = 'ventilar_corto';
  else accion = nc === 1 ? 'abrir_parcial' : 'abrir';

  const [titulo, texto] = TEXTOS[accion];
  return {
    accion, titulo, texto, nivel: NIVEL[accion],
    f: Math.round(f * 1e5) / 1e5, riesgoRelativo: Math.round(rr * 100) / 100,
    nivelCo2: nc, nivelPm: npm,
  };
}

// Colores sugeridos para la tira LED / UI (RGB)
export const COLOR_LED = {
  nada: [0, 160, 60], abrir_parcial: [255, 170, 0], abrir: [220, 20, 20],
  cerrar: [130, 40, 200], ventilar_corto: [255, 90, 0], sin_datos: [40, 40, 40],
};

if (typeof window !== 'undefined') {
  window.VentanaCalib = {
    calibrar, recomendar, crearEstado, derivadas, evaluar, pm25CorregidoEpa,
    fraccionReexhalada, riesgoRelativo, probContagio, COLOR_LED,
  };
}
