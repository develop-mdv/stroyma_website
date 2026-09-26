// Ландшафт участка: лес по периметру, луговая трава, кустарники,
// кострище с чурбаками, дорожка из плит, гамак и забор.
//
// Дом отсюда не меняется — модуль только расставляет окружение и знает
// зоны, куда сажать нельзя (пятно дома, отмостка, терраса, площадка костра).
//
// Всё, что встречается больше пары раз, собрано в InstancedMesh:
// ~130 деревьев и ~2600 кустиков травы идут за десяток вызовов отрисовки.

import * as THREE from '../vendor/three/build.three.module.js?v=45';
import { mergeGeometries } from '../vendor/three/examples/jsm/utils/BufferGeometryUtils.js?v=45';

const FIRE = { x: -7.6, z: 12.2 };
// Опушка: ближе этого радиуса деревьев нет. Камера орбитит внутри кольца
// (maxDistance меньше TREE_LINE), поэтому ствол никогда не встаёт перед домом.
const TREE_LINE = 32;
const HAMMOCK = { x: -15.2, z1: 5.4, z2: 9.6 };

/* ---------- утилиты ---------- */

function rng(seed) {
  let s = seed >>> 0;
  return () => {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

// Куда сажать нельзя.
function blocked(x, z) {
  if (Math.abs(x) < 9.4 && Math.abs(z) < 6.7) return true;            // дом с отмосткой
  if (Math.abs(x) < 4.8 && z > 3.6 && z < 9.8) return true;           // терраса и ступени
  if (Math.hypot(x - FIRE.x, z - FIRE.z) < 3.3) return true;          // площадка костра
  if (Math.hypot(x - HAMMOCK.x, z - (HAMMOCK.z1 + HAMMOCK.z2) / 2) < 2.6) return true;
  return distToPath(x, z) < 0.9;
}

// Дорожка от ступеней террасы к кострищу — дуга из нескольких точек.
const PATH = [
  [0.0, 10.1], [-1.4, 10.4], [-2.8, 10.6], [-4.1, 10.9], [-5.4, 11.4], [-6.5, 11.9],
];
function distToPath(x, z) {
  let d = Infinity;
  for (const [px, pz] of PATH) d = Math.min(d, Math.hypot(x - px, z - pz));
  return d;
}

// Разброс вершин, чтобы кроны не читались как гранёные кристаллы.
// Смещение выводится из самой координаты — общие вершины расходятся одинаково
// и геометрия не рвётся по швам.
function jitter(geo, amount, axes = 'xyz') {
  const p = geo.getAttribute('position');
  for (let i = 0; i < p.count; i++) {
    const x = p.getX(i), y = p.getY(i), z = p.getZ(i);
    let h = Math.imul(Math.round(x * 997) ^ 0x9e37, 374761393)
          + Math.imul(Math.round(y * 997) ^ 0x85eb, 668265263)
          + Math.imul(Math.round(z * 997) ^ 0xc2b2, 2654435761);
    h = Math.imul(h ^ (h >>> 13), 1274126177);
    const k = 1 + (((h ^ (h >>> 16)) >>> 0) / 4294967296 - 0.5) * amount;
    p.setXYZ(i, x * k, axes === 'xyz' ? y * k : y, z * k);
  }
  p.needsUpdate = true;
  geo.computeVertexNormals();
  return geo;
}

function instanced(geo, mat, count) {
  const m = new THREE.InstancedMesh(geo, mat, count);
  m.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  return m;
}

/* ---------- материалы ---------- */

function createMaterials() {
  const std = (c, o = {}) => new THREE.MeshStandardMaterial({ color: new THREE.Color(c), roughness: 0.92, metalness: 0, ...o });
  return {
    barkDark:   std('#4b4137'),
    barkBirch:  std('#cfccc2', { roughness: 0.85 }),
    conifer:    std('#2e3d2c', { roughness: 1 }),
    leafLight:  std('#6a7c46', { roughness: 1 }),
    leafMid:    std('#53673a', { roughness: 1 }),
    shrub:      std('#4d6440', { roughness: 1 }),
    shrubSage:  std('#6f8168', { roughness: 1 }),
    stone:      std('#7d7a72'),
    gravel:     std('#8a867d'),
    log:        std('#7c6349'),
    logTop:     std('#a98d68'),
    fence:      std('#6d5c49'),
    hammock:    std('#d9cdb4', { roughness: 0.95, side: THREE.DoubleSide }),
    rope:       std('#b0a58c'),
  };
}

/* ---------- деревья ---------- */

// Хвойное: ствол плюс несколько ярусов-конусов.
function coniferGeo(rand) {
  const h = 7 + rand() * 6;
  const trunk = new THREE.CylinderGeometry(0.09, 0.22, h * 0.6, 6).translate(0, h * 0.3, 0);
  const layers = [];
  const n = 5 + Math.floor(rand() * 3);
  for (let i = 0; i < n; i++) {
    const k = i / n;
    const r = (1.9 - k * 1.35) * (0.85 + rand() * 0.3);
    const ch = h * (0.30 - k * 0.10);
    layers.push(jitter(new THREE.ConeGeometry(r, ch, 9, 2), 0.3, 'xz')
      .translate(0, h * (0.34 + k * 0.52), 0));
  }
  return { trunk, foliage: mergeGeometries(layers), h };
}

// Лиственное: ствол и облако из низкополигональных сфер.
function broadleafGeo(rand, birch) {
  const h = 6.5 + rand() * 5.5;
  const trunk = new THREE.CylinderGeometry(birch ? 0.07 : 0.13, birch ? 0.15 : 0.28, h * 0.72, 6)
    .translate(0, h * 0.36, 0);
  const blobs = [];
  const n = 5 + Math.floor(rand() * 4);
  for (let i = 0; i < n; i++) {
    const r = (birch ? 0.85 : 1.15) * (0.7 + rand() * 0.7);
    const a = rand() * Math.PI * 2;
    const rad = rand() * (birch ? 1.1 : 1.5);
    blobs.push(
      jitter(new THREE.IcosahedronGeometry(r, 1), 0.42).translate(
        Math.cos(a) * rad,
        h * (0.62 + rand() * 0.34),
        Math.sin(a) * rad
      )
    );
  }
  return { trunk, foliage: mergeGeometries(blobs), h };
}

function buildTrees(mats, rand) {
  const g = new THREE.Group();
  g.name = 'Trees';

  // три варианта каждой породы — достаточно, чтобы лес не выглядел клонированным
  const kinds = [
    { make: () => coniferGeo(rand),        bark: mats.barkDark,  leaf: mats.conifer,   share: 0.46 },
    { make: () => broadleafGeo(rand, true), bark: mats.barkBirch, leaf: mats.leafLight, share: 0.28 },
    { make: () => broadleafGeo(rand, false), bark: mats.barkDark, leaf: mats.leafMid,  share: 0.26 },
  ];

  // расстановка: кольцо вокруг участка, гуще позади дома
  const spots = [];
  const TOTAL = 190;
  let guard = 0;
  while (spots.length < TOTAL && guard++ < 9000) {
    const a = rand() * Math.PI * 2;
    const r = TREE_LINE + Math.pow(rand(), 0.7) * 30;
    const x = Math.cos(a) * r;
    const z = Math.sin(a) * r;
    if (blocked(x, z)) continue;
    if (z > 0 && rand() < 0.3) continue;                 // спереди лес реже
    spots.push([x, z, r]);
  }

  let cursor = 0;
  for (const kind of kinds) {
    const count = Math.round(spots.length * kind.share);
    const slice = spots.slice(cursor, cursor + count);
    cursor += count;
    if (!slice.length) continue;

    const variants = [kind.make(), kind.make(), kind.make()];
    const buckets = variants.map(() => []);
    slice.forEach((s, i) => buckets[i % 3].push(s));

    variants.forEach((v, vi) => {
      const list = buckets[vi];
      if (!list.length) return;
      const trunk = instanced(v.trunk, kind.bark, list.length);
      const leaf = instanced(v.foliage, kind.leaf, list.length);
      const m = new THREE.Matrix4();
      const q = new THREE.Quaternion();
      const col = new THREE.Color();

      list.forEach(([x, z, r], i) => {
        const s = 0.75 + rand() * 0.6;
        q.setFromEuler(new THREE.Euler(0, rand() * Math.PI * 2, 0));
        m.compose(new THREE.Vector3(x, 0, z), q, new THREE.Vector3(s, s * (0.9 + rand() * 0.3), s));
        trunk.setMatrixAt(i, m);
        leaf.setMatrixAt(i, m);
        const k = 0.82 + rand() * 0.3;
        col.setRGB(k * (0.95 + rand() * 0.1), k, k * (0.9 + rand() * 0.12));
        leaf.setColorAt(i, col);
      });

      // весь лес за пределами карты теней солнца — тень с него всё равно не попадёт в кадр
      trunk.castShadow = leaf.castShadow = false;
      trunk.receiveShadow = leaf.receiveShadow = true;
      g.add(trunk, leaf);
    });
  }
  return g;
}

/* ---------- трава ---------- */

// Пучок травы: три скрещенных плоскости с альфа-текстурой.
function tuftGeometry() {
  const p = new THREE.PlaneGeometry(1, 1, 1, 1).translate(0, 0.5, 0);
  const geo = mergeGeometries([p, p.clone().rotateY(Math.PI / 3), p.clone().rotateY(-Math.PI / 3)]);
  // нормали вверх: иначе травинки чернеют с той стороны, куда смотрит плоскость
  const n = geo.getAttribute('normal');
  for (let i = 0; i < n.count; i++) n.setXYZ(i, 0, 1, 0);
  n.needsUpdate = true;
  return geo;
}

function bladeTexture(size = 256) {
  const c = document.createElement('canvas');
  c.width = c.height = size;
  const ctx = c.getContext('2d');
  const rand = rng(0x9e3a);
  ctx.clearRect(0, 0, size, size);
  ctx.lineCap = 'round';

  for (let i = 0; i < 46; i++) {
    const baseX = size * (0.14 + rand() * 0.72);
    const len = size * (0.42 + rand() * 0.55);
    const lean = (rand() - 0.5) * size * 0.5;
    const w = size * (0.008 + rand() * 0.014);
    const dark = 0.55 + rand() * 0.25;

    const grad = ctx.createLinearGradient(0, size, 0, size - len);
    grad.addColorStop(0, `rgb(${(78 * dark) | 0},${(104 * dark) | 0},${(50 * dark) | 0})`);
    grad.addColorStop(1, `rgb(${(164 * dark) | 0},${(190 * dark) | 0},${(104 * dark) | 0})`);
    ctx.strokeStyle = grad;
    ctx.lineWidth = w * 2;
    ctx.beginPath();
    ctx.moveTo(baseX, size);
    ctx.quadraticCurveTo(baseX + lean * 0.35, size - len * 0.6, baseX + lean, size - len);
    ctx.stroke();
  }

  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.needsUpdate = true;
  return t;
}

function buildGrass(rand) {
  const g = new THREE.Group();
  g.name = 'Grass';
  const tex = bladeTexture();
  const mat = new THREE.MeshStandardMaterial({
    map: tex, alphaTest: 0.42, side: THREE.DoubleSide, roughness: 1, metalness: 0,
  });
  const geo = tuftGeometry();

  const spots = [];
  let guard = 0;
  while (spots.length < 5400 && guard++ < 80000) {
    const a = rand() * Math.PI * 2;
    const r = 4 + Math.pow(rand(), 0.55) * 42;
    const x = Math.cos(a) * r, z = Math.sin(a) * r;
    if (blocked(x, z)) continue;
    // ближе к дому — подстриженный газон, редкие пучки; дальше — луг
    const wild = Math.min(1, Math.max(0, (r - 11) / 16));
    if (rand() > 0.2 + wild * 0.8) continue;
    spots.push([x, z, wild]);
  }

  const mesh = instanced(geo, mat, spots.length);
  const m = new THREE.Matrix4();
  const q = new THREE.Quaternion();
  const col = new THREE.Color();
  spots.forEach(([x, z, wild], i) => {
    const tall = rand() < 0.13 + wild * 0.2;                 // декоративные злаки повыше
    const s = (0.34 + rand() * 0.3) * (tall ? 2.0 : 1) * (0.65 + wild * 0.6);
    q.setFromEuler(new THREE.Euler(0, rand() * Math.PI, 0));
    m.compose(new THREE.Vector3(x, 0, z), q, new THREE.Vector3(s * 1.3, s, s * 1.3));
    mesh.setMatrixAt(i, m);
    const k = 0.8 + rand() * 0.45;
    col.setRGB(k * (tall ? 1.25 : 1), k, k * (tall ? 0.72 : 0.95)); // злаки суше и желтее
    mesh.setColorAt(i, col);
  });
  mesh.receiveShadow = true;
  g.add(mesh);
  return g;
}

/* ---------- кустарники ---------- */

function shrubGeo(rand, wide) {
  const blobs = [];
  const n = 4 + Math.floor(rand() * 4);
  for (let i = 0; i < n; i++) {
    const r = (wide ? 0.34 : 0.24) * (0.75 + rand() * 0.5);
    const a = rand() * Math.PI * 2;
    const rad = rand() * (wide ? 0.4 : 0.26);
    blobs.push(jitter(new THREE.IcosahedronGeometry(r, 1), 0.4)
      .translate(Math.cos(a) * rad, r * 0.75 + rand() * 0.25, Math.sin(a) * rad));
  }
  return mergeGeometries(blobs);
}

function buildShrubs(mats, rand) {
  const g = new THREE.Group();
  g.name = 'Shrubs';

  // группы у фасада — вдоль стены, но за отмосткой
  const spots = [];
  for (let x = -7.2; x <= 7.2; x += 0.78) {
    if (Math.abs(x) < 5.1) continue;                       // не перед террасой
    spots.push([x + (rand() - 0.5) * 0.28, 6.6 + rand() * 0.55, rand() < 0.3]);
  }
  // свободные куртины по участку
  let guard = 0;
  while (spots.length < 96 && guard++ < 4000) {
    const a = rand() * Math.PI * 2;
    const r = 8 + Math.pow(rand(), 0.7) * 20;
    const x = Math.cos(a) * r, z = Math.sin(a) * r;
    if (blocked(x, z)) continue;
    spots.push([x, z, rand() < 0.28]);
  }

  for (const sage of [false, true]) {
    const list = spots.filter((s) => s[2] === sage);
    if (!list.length) continue;
    const variants = [shrubGeo(rand, true), shrubGeo(rand, false), shrubGeo(rand, true)];
    variants.forEach((geo, vi) => {
      const part = list.filter((_, i) => i % 3 === vi);
      if (!part.length) return;
      const mesh = instanced(geo, sage ? mats.shrubSage : mats.shrub, part.length);
      const m = new THREE.Matrix4();
      const q = new THREE.Quaternion();
      const col = new THREE.Color();
      part.forEach(([x, z], i) => {
        const s = 0.55 + rand() * 0.5;
        q.setFromEuler(new THREE.Euler(0, rand() * Math.PI * 2, 0));
        m.compose(new THREE.Vector3(x, 0, z), q, new THREE.Vector3(s, s * (0.7 + rand() * 0.45), s));
        mesh.setMatrixAt(i, m);
        const k = 0.82 + rand() * 0.36;
        col.setRGB(k, k * (0.96 + rand() * 0.1), k * 0.94);
        mesh.setColorAt(i, col);
      });
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      g.add(mesh);
    });
  }
  return g;
}

/* ---------- кострище, дорожка, гамак, забор ---------- */

function buildFirePit(mats, rand) {
  const g = new THREE.Group();
  g.name = 'FirePit';

  const pad = new THREE.Mesh(new THREE.CircleGeometry(2.5, 32), mats.gravel);
  pad.rotation.x = -Math.PI / 2;
  pad.position.set(FIRE.x, 0.015, FIRE.z);
  pad.receiveShadow = true;
  g.add(pad);

  // кольцо камней
  for (let i = 0; i < 14; i++) {
    const a = (i / 14) * Math.PI * 2;
    const s = 0.16 + rand() * 0.1;
    const st = new THREE.Mesh(new THREE.DodecahedronGeometry(s, 0), mats.stone);
    st.position.set(FIRE.x + Math.cos(a) * 0.85, s * 0.6, FIRE.z + Math.sin(a) * 0.85);
    st.rotation.set(rand(), rand(), rand());
    st.castShadow = true;
    st.receiveShadow = true;
    g.add(st);
  }
  // поленья в центре
  for (let i = 0; i < 5; i++) {
    const a = (i / 5) * Math.PI * 2 + rand();
    const log = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.07, 0.9, 6), mats.log);
    log.position.set(FIRE.x + Math.cos(a) * 0.12, 0.16, FIRE.z + Math.sin(a) * 0.12);
    log.rotation.set(Math.PI / 2 - 0.5, a, 0);
    log.castShadow = true;
    g.add(log);
  }
  // чурбаки-сиденья
  for (let i = 0; i < 5; i++) {
    const a = (i / 5) * Math.PI * 2 + 0.5;
    const h = 0.42 + rand() * 0.1;
    const seat = new THREE.Mesh(new THREE.CylinderGeometry(0.27, 0.29, h, 12), mats.log);
    seat.position.set(FIRE.x + Math.cos(a) * 2.0, h / 2, FIRE.z + Math.sin(a) * 2.0);
    seat.castShadow = true;
    seat.receiveShadow = true;
    const top = new THREE.Mesh(new THREE.CylinderGeometry(0.265, 0.265, 0.02, 12), mats.logTop);
    top.position.set(seat.position.x, h + 0.005, seat.position.z);
    g.add(seat, top);
  }
  return g;
}

function buildPath(mats, rand) {
  const g = new THREE.Group();
  g.name = 'Path';
  for (let i = 0; i < PATH.length; i++) {
    const [x, z] = PATH[i];
    const slab = new THREE.Mesh(new THREE.BoxGeometry(0.62, 0.07, 0.46), mats.stone);
    slab.position.set(x + (rand() - 0.5) * 0.12, 0.035, z + (rand() - 0.5) * 0.12);
    slab.rotation.y = (rand() - 0.5) * 0.5;
    slab.receiveShadow = true;
    g.add(slab);
  }
  return g;
}

// Гамак между двумя деревьями: провисающая плоскость плюс верёвки.
function buildHammock(mats) {
  const g = new THREE.Group();
  g.name = 'Hammock';

  // стойки с укосинами
  for (const [z, dir] of [[HAMMOCK.z1, -1], [HAMMOCK.z2, 1]]) {
    const post = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.08, 1.9, 8), mats.log);
    post.position.set(HAMMOCK.x, 0.95, z);
    post.castShadow = true;
    g.add(post);
    const brace = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 1.6, 6), mats.log);
    brace.position.set(HAMMOCK.x, 0.75, z + dir * 0.55);
    brace.rotation.x = dir * 0.62;
    brace.castShadow = true;
    g.add(brace);
  }
  const len = HAMMOCK.z2 - HAMMOCK.z1 - 0.9;
  const geo = new THREE.PlaneGeometry(len, 1.05, 24, 3);
  const pos = geo.getAttribute('position');
  for (let i = 0; i < pos.count; i++) {
    const u = pos.getX(i) / (len / 2);          // -1..1 вдоль гамака
    const v = pos.getY(i);
    const sag = (1 - u * u) * 0.42;             // провис
    pos.setXYZ(i, pos.getX(i), v * (0.55 + (1 - u * u) * 0.45) - sag, 0);
  }
  geo.computeVertexNormals();
  geo.rotateX(-Math.PI / 2);
  geo.rotateY(Math.PI / 2);

  const cloth = new THREE.Mesh(geo, mats.hammock);
  cloth.position.set(HAMMOCK.x, 1.25, (HAMMOCK.z1 + HAMMOCK.z2) / 2);
  cloth.castShadow = true;
  g.add(cloth);

  for (const [z, dir] of [[HAMMOCK.z1 + 0.45, -1], [HAMMOCK.z2 - 0.45, 1]]) {
    const rope = new THREE.Mesh(new THREE.CylinderGeometry(0.018, 0.018, 0.72, 5), mats.rope);
    rope.position.set(HAMMOCK.x, 1.5, z - dir * 0.22);
    rope.rotation.x = -dir * 0.62;
    g.add(rope);
  }
  return g;
}

function buildFence(mats, rand) {
  const g = new THREE.Group();
  g.name = 'Fence';
  const x = -25.5;
  const z0 = -10, z1 = 17;
  const step = 0.17;
  const n = Math.floor((z1 - z0) / step);

  const board = instanced(new THREE.BoxGeometry(0.05, 1.5, 0.12), mats.fence, n);
  const m = new THREE.Matrix4();
  const q = new THREE.Quaternion();
  for (let i = 0; i < n; i++) {
    m.compose(
      new THREE.Vector3(x + (rand() - 0.5) * 0.04, 0.75 + (rand() - 0.5) * 0.06, z0 + i * step),
      q, new THREE.Vector3(1, 1, 1)
    );
    board.setMatrixAt(i, m);
  }
  board.castShadow = true;
  g.add(board);

  for (const y of [0.45, 1.25]) {
    const rail = new THREE.Mesh(new THREE.BoxGeometry(0.07, 0.09, z1 - z0), mats.fence);
    rail.position.set(x - 0.06, y, (z0 + z1) / 2);
    g.add(rail);
  }
  return g;
}

/* ---------- сборка ---------- */

export function buildLandscape() {
  const mats = createMaterials();
  const rand = rng(0x2f7a41);

  // «Газон» — то, что читается как благоустройство участка
  const planting = new THREE.Group();
  planting.name = 'Planting';
  planting.add(buildGrass(rand), buildShrubs(mats, rand));

  // «Полный» — сценарий участка: лес, зона костра, гамак, забор
  const scenery = new THREE.Group();
  scenery.name = 'Scenery';
  scenery.add(
    buildTrees(mats, rand),
    buildPath(mats, rand),
    buildFirePit(mats, rand),
    buildHammock(mats),
    buildFence(mats, rand)
  );

  return { planting, scenery };
}
