// node pruebas/probar_js.mjs  → compara js/ventana-calib.js con los vectores de Python
import fs from 'fs'; import path from 'path'; import { fileURLToPath } from 'url';
const raiz = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const { calibrar, recomendar, crearEstado } = await import(path.join(raiz, 'js/ventana-calib.js'));
const V = JSON.parse(fs.readFileSync(path.join(raiz, 'datos/vectores_prueba.json')));
const m = JSON.parse(fs.readFileSync(path.join(raiz, 'modelos/modelo.json')));
let mal = 0;
for (const c of V.calibrar) {
  const a = calibrar(c.lectura, m).pm25, b = calibrar(c.lectura).pm25;
  if (Math.abs(a - c.modelo) > 0.011 || Math.abs(b - c.epa) > 0.011) { mal++; if (mal < 5) console.log('calib', c, a, b); }
}
const est = crearEstado();
for (const r of V.recomendar_secuencia) {
  const o = recomendar(r.entrada, est);
  if (o.accion !== r.accion || o.nivel !== r.nivel) { mal++; if (mal < 5) console.log('rec', r, o); }
}
console.log(mal === 0 ? `JS OK: ${V.calibrar.length + V.recomendar_secuencia.length} casos iguales a Python` : `JS FALLA: ${mal}`);
process.exit(mal ? 1 : 0);
