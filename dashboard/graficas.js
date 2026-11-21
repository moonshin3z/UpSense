// Gráficas SVG mínimas, sin librerías (la app debe funcionar en el ESP32 sin internet).

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
export const hhmm = (t) => { const d = new Date(t); return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`; };

/**
 * lineas(el, {
 *   t0, t1,                       // rango de tiempo (ms)
 *   series: [{ data: [[t, v]], color, ancho, guion, eje: 'izq'|'der', nombre }],
 *   maxIzq, maxDer, unidadDer,    // escalas
 *   lineasH: [{ v, color, texto }],
 *   bandas: [{ t0, t1, color }],  // zonas sombreadas (p. ej. humedad alta)
 *   cursor,                       // t del cursor (línea vertical)
 *   corteGap,                     // ms: no unir puntos más separados que esto
 * })
 */
export function lineas(el, o) {
  const W = el.clientWidth || 640, H = el.clientHeight || 200;
  const pl = 40, pr = o.maxDer ? 40 : 10, pt = 10, pb = 22;
  const t0 = o.t0, t1 = Math.max(o.t1, o.t0 + 1);
  const ys = o.series.filter((s) => s.eje !== 'der').flatMap((s) => s.data.map((d) => d[1])).filter((v) => v != null);
  const maxI = o.maxIzq ?? Math.max(10, ...ys, ...(o.lineasH || []).map((l) => l.v * 1.1)) * 1.08;
  const maxD = o.maxDer || 100;
  const x = (t) => pl + ((t - t0) / (t1 - t0)) * (W - pl - pr);
  const yI = (v) => pt + (1 - Math.min(v, maxI) / maxI) * (H - pt - pb);
  const yD = (v) => pt + (1 - Math.min(v, maxD) / maxD) * (H - pt - pb);
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(o.titulo || 'gráfica')}">`;
  for (const b of o.bandas || []) {
    const a = Math.max(x(b.t0), pl), z = Math.min(x(b.t1), W - pr);
    if (z > a) s += `<rect x="${a}" y="${pt}" width="${z - a}" height="${H - pt - pb}" fill="${b.color}"/>`;
    if (b.texto && z - a >= 7 * b.texto.length) s += `<text x="${a + 8}" y="${pt + 32}" font-size="11" fill="var(--muted)">${esc(b.texto)}</text>`;
  }
  if (o.unidadEje) s += `<text x="${pl}" y="${pt + 14}" font-size="10.5" fill="var(--muted)" dx="6">${esc(o.unidadEje)}</text>`;
  for (const f of [0, 0.5, 1]) {
    s += `<line x1="${pl}" x2="${W - pr}" y1="${yI(maxI * f)}" y2="${yI(maxI * f)}" stroke="var(--grid)"/>`;
    s += `<text x="${pl - 6}" y="${yI(maxI * f) + 4}" font-size="11" text-anchor="end" fill="var(--muted)">${Math.round(maxI * f)}</text>`;
    if (o.maxDer) s += `<text x="${W - pr + 6}" y="${yD(maxD * f) + 4}" font-size="11" fill="var(--muted)">${Math.round(maxD * f)}${o.unidadDer || ''}</text>`;
  }
  for (const l of o.lineasH || []) {
    s += `<line x1="${pl}" x2="${W - pr}" y1="${yI(l.v)}" y2="${yI(l.v)}" stroke="${l.color}" stroke-dasharray="5 5" stroke-width="1.5"/>`;
    if (l.texto) s += `<text x="${W - pr - 4}" y="${yI(l.v) - 5}" font-size="11" text-anchor="end" fill="${l.color}">${esc(l.texto)}</text>`;
  }
  const n = 4;
  for (let i = 0; i <= n; i++) {
    const t = t0 + (i / n) * (t1 - t0);
    s += `<text x="${x(t)}" y="${H - 5}" font-size="11" text-anchor="${i === 0 ? 'start' : i === n ? 'end' : 'middle'}" fill="var(--muted)">${o.etiquetaX ? o.etiquetaX(t) : hhmm(t)}</text>`;
  }
  const gap = o.corteGap ?? Infinity;
  for (const se of o.series) {
    const y = se.eje === 'der' ? yD : yI;
    let d = '', prev = null;
    for (const [t, v] of se.data) {
      if (v == null || t < t0 - 1 || t > t1 + 1) { prev = null; continue; }
      d += `${prev == null || t - prev > gap ? 'M' : 'L'}${x(t).toFixed(1)},${y(v).toFixed(1)}`;
      prev = t;
    }
    s += `<path d="${d}" fill="none" stroke="${se.color}" stroke-width="${se.ancho || 2}" stroke-linejoin="round" stroke-linecap="round"${se.guion ? ` stroke-dasharray="${se.guion}"` : ''}/>`;
  }
  // Etiquetas directas al final de cada serie con nombre (≤ 4 series)
  const etiquetas = [];
  for (const se of o.series) {
    if (o.sinEtiquetas || !se.nombre || se.eje === 'der') continue;
    const ult = [...se.data].reverse().find(([t, v]) => v != null && t <= t1 && t >= t0);
    if (ult) etiquetas.push({ y: yI(ult[1]), x: x(ult[0]), txt: se.nombre, color: se.color });
  }
  etiquetas.sort((p, q) => p.y - q.y);
  for (let i = 1; i < etiquetas.length; i++) if (etiquetas[i].y - etiquetas[i - 1].y < 14) etiquetas[i].y = etiquetas[i - 1].y + 14;
  for (const et of etiquetas) {
    s += `<text x="${Math.min(et.x + 6, W - pr - 2)}" y="${et.y + 4}" font-size="11" font-weight="600" fill="var(--fg)" text-anchor="${et.x + 60 > W - pr ? 'end' : 'start'}" paint-order="stroke" stroke="var(--card)" stroke-width="4">${esc(et.txt)}</text>`;
  }
  for (const m of o.marcas || []) {
    if (m.t < t0 || m.t > t1) continue;
    const mx = x(m.t), my = Math.max(pt + 12, yI(m.v) - 12);
    const anc = mx > W - pr - 90 ? 'end' : mx < pl + 90 ? 'start' : 'middle';
    s += `<text x="${mx}" y="${my}" font-size="11.5" font-weight="600" fill="var(--fg)" text-anchor="${anc}" paint-order="stroke" stroke="var(--card)" stroke-width="4">${esc(m.texto)}</text>`;
  }
  if (o.cursor != null && o.cursor >= t0 && o.cursor <= t1) {
    s += `<line x1="${x(o.cursor)}" x2="${x(o.cursor)}" y1="${pt}" y2="${H - pb}" stroke="var(--fg)" stroke-width="1.5" opacity=".35"/>`;
    // Un punto sobre cada serie en el momento actual
    for (const se of o.series) {
      if (se.eje === 'der') continue;
      let v = null; for (const [t, vv] of se.data) { if (t > o.cursor) break; if (vv != null) v = vv; }
      if (v != null) s += `<circle cx="${x(o.cursor)}" cy="${yI(v)}" r="${se.guion ? 3.5 : 5}" fill="${se.color}" stroke="var(--bg)" stroke-width="2.5"/>`;
    }
  }
  if (!o.series.some((se) => se.data.length)) s += `<text x="${W / 2}" y="${H / 2}" text-anchor="middle" font-size="13" fill="var(--muted)">Sin datos todavía</text>`;
  s += `<line class="pelo" x1="0" x2="0" y1="${pt}" y2="${H - pb}" stroke="var(--muted)" stroke-width="1" visibility="hidden"/>`;
  el.innerHTML = s + '</svg><div class="tip" hidden></div>';
  capaHover(el, { x, t0, t1, pl, pr, W, series: o.series, unidad: o.unidad || '', alClic: o.alClic, etiquetaX: o.etiquetaX });
}

// Hover: pelo vertical que se pega al dato más cercano + tooltip con todas las series.
function capaHover(el, c) {
  const svg = el.querySelector('svg'), pelo = el.querySelector('.pelo'), tip = el.querySelector('.tip');
  el.style.position = 'relative';
  const tDe = (ev) => {
    const r = svg.getBoundingClientRect();
    const px = ((ev.clientX - r.left) / r.width) * c.W;
    return c.t0 + ((px - c.pl) / (c.W - c.pl - c.pr)) * (c.t1 - c.t0);
  };
  const cercano = (data, t) => {
    let lo = 0, hi = data.length - 1;
    if (hi < 0) return null;
    while (lo < hi) { const m = (lo + hi) >> 1; if (data[m][0] < t) lo = m + 1; else hi = m; }
    const a = data[Math.max(0, lo - 1)], b = data[lo];
    return Math.abs(a[0] - t) < Math.abs(b[0] - t) ? a : b;
  };
  const mover = (ev) => {
    const t = tDe(ev);
    if (t < c.t0 || t > c.t1) { salir(); return; }
    const filas = c.series.map((se) => ({ se, d: cercano(se.data, t) })).filter((f) => f.d);
    if (!filas.length) return;
    const tt = filas[0].d[0];
    const px = c.x(tt);
    pelo.setAttribute('x1', px); pelo.setAttribute('x2', px); pelo.setAttribute('visibility', 'visible');
    tip.replaceChildren();
    const h = document.createElement('div'); h.className = 'tip-h'; h.textContent = c.etiquetaX ? c.etiquetaX(tt) : hhmm(tt); tip.append(h);
    for (const { se, d } of filas) {
      if (!se.nombre) continue;
      const row = document.createElement('div'); row.className = 'tip-r';
      const k = document.createElement('i'); k.style.borderColor = se.color; if (se.guion) k.style.borderTopStyle = 'dashed';
      const v = document.createElement('b'); v.textContent = d[1] == null ? '—' : `${Math.round(d[1] * 10) / 10}${se.unidad ?? c.unidad}`;
      const n = document.createElement('span'); n.textContent = se.nombre;
      row.append(k, v, n); tip.append(row);
    }
    tip.hidden = false;
    const r = svg.getBoundingClientRect();
    const left = (px / c.W) * r.width;
    tip.style.left = `${Math.min(Math.max(left + 12, 0), r.width - tip.offsetWidth - 4)}px`;
    if (left + 12 + tip.offsetWidth > r.width) tip.style.left = `${Math.max(0, left - tip.offsetWidth - 12)}px`;
  };
  const salir = () => { tip.hidden = true; pelo.setAttribute('visibility', 'hidden'); };
  el.onpointerleave = () => { el._ultimo = null; salir(); };
  // Al redibujar (reproducción) se conserva el tooltip si el puntero sigue encima
  if (el._ultimo) mover(el._ultimo);
  // Arrastrar sobre la gráfica (mouse o dedo) recorre la mañana
  el.onclick = null;
  el.style.cursor = c.alClic ? 'ew-resize' : '';
  el.onpointerdown = c.alClic ? (ev) => {
    const t = tDe(ev); if (t < c.t0 || t > c.t1) return;
    el._arrastre = true; try { el.setPointerCapture(ev.pointerId); } catch {}
    c.alClic(t);
  } : null;
  el.onpointermove = (ev) => {
    el._ultimo = ev;
    if (el._arrastre && c.alClic) { const t = Math.min(c.t1, Math.max(c.t0, tDe(ev))); c.alClic(t); return; }
    mover(ev);
  };
  el.onpointerup = el.onpointercancel = () => { el._arrastre = false; };
}

/** Franja de colores con la acción del semáforo a lo largo del tiempo. */
export function franja(el, { t0, t1, tramos, cursor, alClic }) {
  const W = el.clientWidth || 640, H = el.clientHeight || 28, pl = 40, pr = 10;
  const x = (t) => pl + ((t - t0) / Math.max(1, t1 - t0)) * (W - pl - pr);
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="acciones del semáforo">`;
  s += `<rect x="${pl}" y="2" width="${W - pl - pr}" height="${H - 4}" rx="5" fill="var(--grid)"/>`;
  for (const tr of tramos) {
    const a = x(tr.t0), z = x(tr.t1);
    s += `<rect x="${a}" y="2" width="${Math.max(1, z - a)}" height="${H - 4}" fill="${tr.color}"><title>${esc(tr.texto || '')}</title></rect>`;
  }
  if (cursor != null) s += `<rect x="${x(cursor) - 1.5}" y="0" width="3" height="${H}" fill="var(--fg)"/>`;
  el.innerHTML = s + '</svg>';
  el.onclick = alClic ? (ev) => { const r = el.getBoundingClientRect(); const px = ((ev.clientX - r.left) / r.width) * W; const t = t0 + ((px - pl) / (W - pl - pr)) * (t1 - t0); if (t >= t0 && t <= t1) alClic(t); } : null;
  el.style.cursor = alClic ? 'pointer' : '';
}

/** Convierte una serie de muestras con .accion en tramos contiguos. */
export function tramosDe(muestras, colorDe, paso) {
  const out = [];
  for (const m of muestras) {
    const c = colorDe(m.accion);
    const last = out[out.length - 1];
    if (last && last.accion === m.accion && m.t - last.t1 <= paso * 1.5) last.t1 = m.t + paso;
    else out.push({ t0: m.t, t1: m.t + paso, color: c, accion: m.accion, texto: m.accion });
  }
  return out;
}
