// Процедурная геометрия дома.
//
// Главное для конфигуратора:
//   • Facade и Plinth — РАЗНЫЕ объекты с разными материалами;
//   • стены строятся через ExtrudeGeometry из плоских контуров с проёмами,
//     поэтому UV сразу в метрах (1 UV-юнит = 1 м) и тайлинг штукатурки честный;
//   • откосы проёмов получаются автоматически — это боковые грани экструзии.

import * as THREE from '../vendor/three/build.three.module.js?v=45';
import { FIXED } from './data.js?v=45';

/* ---------- размеры, м ---------- */
export const DIM = {
  L: 14.0,          // длина (вдоль X), конёк параллелен длинной стене
  W: 9.0,           // ширина (вдоль Z)
  wallT: 0.35,      // толщина стены
  plinthH: 0.55,    // высота цоколя
  plinthOut: 0.05,  // вынос цоколя из плоскости фасада
  wallH: 3.05,      // от верха цоколя до карниза
  pitch: 23,        // уклон кровли, градусов
  eaveOv: 0.55,     // свес по карнизу
  rakeOvW: 0.60,    // свес по фронтону, западный торец
  rakeOvE: 1.25,    // свес по фронтону, восточный торец (выразительный, как на референсе)
  roofT: 0.22,
};

const RAD = (d) => (d * Math.PI) / 180;
const TAN = Math.tan(RAD(DIM.pitch));

export const LEVELS = {
  plinthTop: DIM.plinthH,
  eave: DIM.plinthH + DIM.wallH,                      // 3.60
  ridge: DIM.plinthH + DIM.wallH + (DIM.W / 2) * TAN, // 5.51
};

/* ---------- проёмы ---------- */
// u — по ширине стены от её центра, v — от верха цоколя.
const OPENINGS = {
  south: [ // главный фасад, +Z
    { u: -5.65, v: 0.95, w: 1.35, h: 1.55 },
    { u: -3.85, v: 0.95, w: 1.35, h: 1.55 },
    // Выход на террасу — один портал по центру террасы (она тоже центрирована, ширина 6.6).
    // История правок: было две секции по 2.30 с зазором → стало одно окно 4.70 с узкой и
    // широкой створкой → теперь узкая убрана совсем, портал уже (3.00) и поделён на ТРИ
    // равные створки (panels: 3 — импосты ставятся на равных долях ширины).
    { u: -1.50, v: 0.12, w: 3.00, h: 2.62, kind: 'panorama', panels: 3 },
    { u:  4.35, v: 0.95, w: 1.35, h: 1.55 },
  ],
  north: [ // дворовый фасад, -Z
    { u: -5.20, v: 0.95, w: 1.10, h: 1.45 },
    { u: -2.10, v: 0.02, w: 1.00, h: 2.15, kind: 'door' },
    { u:  1.40, v: 0.95, w: 1.60, h: 1.45 },
    { u:  4.10, v: 1.20, w: 0.70, h: 1.10 },
  ],
  east: [  // торец с большим свесом, +X
    { u: -0.90, v: 0.20, w: 1.75, h: 2.45, kind: 'panorama' },
    { u: -0.55, v: 3.30, w: 1.10, h: 0.80, kind: 'gable' },
  ],
  west: [  // торец, -X
    { u: -1.60, v: 1.00, w: 1.30, h: 1.50 },
    { u:  0.40, v: 1.00, w: 1.30, h: 1.50 },
  ],
};

/* ---------- материалы ---------- */
export function createMaterials() {
  const std = (color, opts = {}) =>
    new THREE.MeshStandardMaterial({ color: new THREE.Color(color), roughness: 0.85, metalness: 0, ...opts });

  const materials = {
    // ↓ эти два меняет пользователь
    facade: std('#ffffff', { name: 'M_Facade', roughness: 0.8 }),
    plinth: std('#ffffff', { name: 'M_Plinth', roughness: 0.5 }),

    roof:     std(FIXED.roof, { roughness: 0.55, metalness: 0.38 }),
    seam:     std(FIXED.roof, { roughness: 0.48, metalness: 0.42 }),
    frame:    std(FIXED.frame, { roughness: 0.45, metalness: 0.25 }),
    // стекло: заметная отражённость, иначе окна читаются чёрными дырами
    glass:    new THREE.MeshStandardMaterial({
                color: new THREE.Color(FIXED.glass), roughness: 0.09, metalness: 1.0,
                envMapIntensity: 1.1,
                emissive: new THREE.Color('#ffb877'), emissiveIntensity: 0,
              }),
    wood:     std(FIXED.wood, { roughness: 0.72 }),
    woodDark: std(FIXED.woodDark, { roughness: 0.75 }),
    deck:     std(FIXED.deck, { roughness: 0.8 }),
    soffit:   std(FIXED.soffit, { roughness: 0.7 }),
    chimney:  std(FIXED.chimney, { roughness: 0.9 }),
    metal:    std(FIXED.metal, { roughness: 0.5, metalness: 0.5 }),
    lamp:     new THREE.MeshStandardMaterial({
                color: new THREE.Color('#23262a'), roughness: 0.4, metalness: 0.4,
                emissive: new THREE.Color('#ffcf94'), emissiveIntensity: 0,
              }),
    apron:    std('#7d7a72', { roughness: 1 }),
    ground:   std('#7a8460', { roughness: 1 }),
  };
  return materials;
}

/* ---------- вспомогательное ---------- */

function box(w, h, d, mat, pos, rot) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
  if (pos) m.position.set(pos[0], pos[1], pos[2]);
  if (rot) m.rotation.set(rot[0] || 0, rot[1] || 0, rot[2] || 0);
  m.castShadow = true;
  m.receiveShadow = true;
  return m;
}

// UV-генератор для стен и цоколя.
//
// Лицевая грань берёт UV прямо из контура (он в метрах) — борозда короеда ложится
// горизонтально, как и должна. А боковые грани экструзии — это торцы стен НА УГЛАХ дома
// и откосы проёмов. Штатный three'вский WorldUVGenerator на вертикальном ребре кладёт
// U вдоль ВЫСОТЫ (`Vector2(y, 1 - z)`), поэтому фактура там разворачивалась на 90°:
// на углу одна стена шла бороздой горизонтально, соседний торец — вертикально.
// Здесь на вертикальных рёбрах U — глубина стены, V — высота: рисунок продолжается
// с фасада без поворота. Горизонтальные рёбра (верх/низ проёма) оставлены как в three —
// там U и так идёт вдоль стены.
const WallUV = {
  generateTopUV(geometry, vertices, indexA, indexB, indexC) {
    return [
      new THREE.Vector2(vertices[indexA * 3], vertices[indexA * 3 + 1]),
      new THREE.Vector2(vertices[indexB * 3], vertices[indexB * 3 + 1]),
      new THREE.Vector2(vertices[indexC * 3], vertices[indexC * 3 + 1]),
    ];
  },
  generateSideWallUV(geometry, vertices, indexA, indexB, indexC, indexD) {
    const p = (i) => ({ x: vertices[i * 3], y: vertices[i * 3 + 1], z: vertices[i * 3 + 2] });
    const a = p(indexA), b = p(indexB), c = p(indexC), d = p(indexD);

    if (Math.abs(a.y - b.y) < Math.abs(a.x - b.x)) {
      // ребро горизонтальное (верх/низ проёма): U вдоль стены, V — глубина
      return [
        new THREE.Vector2(a.x, 1 - a.z), new THREE.Vector2(b.x, 1 - b.z),
        new THREE.Vector2(c.x, 1 - c.z), new THREE.Vector2(d.x, 1 - d.z),
      ];
    }
    // ребро вертикальное (угол дома, боковой откос): U — глубина, V — высота
    return [
      new THREE.Vector2(a.z, a.y), new THREE.Vector2(b.z, b.y),
      new THREE.Vector2(c.z, c.y), new THREE.Vector2(d.z, d.y),
    ];
  },
};

// Контур стены с прямоугольными проёмами → объёмная стена с откосами.
function wallGeometry(outline, holes, depth) {
  const shape = new THREE.Shape();
  outline.forEach(([x, y], i) => (i === 0 ? shape.moveTo(x, y) : shape.lineTo(x, y)));
  shape.closePath();

  for (const o of holes) {
    const p = new THREE.Path();
    p.moveTo(o.u, o.v);
    p.lineTo(o.u + o.w, o.v);
    p.lineTo(o.u + o.w, o.v + o.h);
    p.lineTo(o.u, o.v + o.h);
    p.closePath();
    shape.holes.push(p);
  }
  // WorldUVGenerator в ExtrudeGeometry берёт UV прямо из координат контура —
  // а он у нас в метрах, значит тайлинг штукатурки задаётся одним repeat.
  return new THREE.ExtrudeGeometry(shape, {
    depth, bevelEnabled: false, curveSegments: 1,
    UVGenerator: WallUV,   // без него фактура на углах и откосах поворачивалась на 90°
  });
}

// Рама проёма: наружная рамка толщиной frameW, внутри — стекло.
function openingParts(o, mats, depth) {
  const g = new THREE.Group();
  const fw = o.kind === 'panorama' ? 0.075 : 0.06;

  const outer = new THREE.Shape();
  outer.moveTo(o.u, o.v);
  outer.lineTo(o.u + o.w, o.v);
  outer.lineTo(o.u + o.w, o.v + o.h);
  outer.lineTo(o.u, o.v + o.h);
  const inner = new THREE.Path();
  inner.moveTo(o.u + fw, o.v + fw);
  inner.lineTo(o.u + o.w - fw, o.v + fw);
  inner.lineTo(o.u + o.w - fw, o.v + o.h - fw);
  inner.lineTo(o.u + fw, o.v + o.h - fw);
  outer.holes.push(inner);

  const frame = new THREE.Mesh(
    new THREE.ExtrudeGeometry(outer, { depth: 0.11, bevelEnabled: false, curveSegments: 1 }),
    mats.frame
  );
  frame.position.z = depth - 0.11;
  frame.castShadow = true;
  g.add(frame);

  const glass = new THREE.Mesh(new THREE.PlaneGeometry(o.w - fw * 2, o.h - fw * 2), mats.glass);
  glass.position.set(o.u + o.w / 2, o.v + o.h / 2, depth - 0.09);
  g.add(glass);

  // Импосты: проём делится на o.panels равных створок (по умолчанию две — как было).
  if (o.kind === 'panorama' || o.w > 1.5) {
    const panels = o.panels || 2;
    for (let i = 1; i < panels; i++) {
      g.add(box(0.05, o.h - fw * 2, 0.09, mats.frame,
        [o.u + (o.w * i) / panels, o.v + o.h / 2, depth - 0.055]));
    }
  }
  // подоконный отлив
  if (o.kind !== 'door' && o.kind !== 'panorama') {
    const sill = box(o.w + 0.12, 0.03, 0.16, mats.metal, [o.u + o.w / 2, o.v - 0.015, depth - 0.02]);
    g.add(sill);
  }
  return g;
}

// Одна стена целиком: коробка + рамы + стёкла, в локальных координатах.
function buildWall(outline, holes, mats, group) {
  const geo = wallGeometry(outline, holes, DIM.wallT);
  const mesh = new THREE.Mesh(geo, mats.facade);
  mesh.name = 'Facade';
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  group.add(mesh);
  for (const o of holes) group.add(openingParts(o, mats, DIM.wallT));
}

function placeWall(group, side) {
  const { L, W, wallT } = DIM;
  switch (side) {
    case 'south': group.position.set(0, LEVELS.plinthTop, W / 2 - wallT); break;
    case 'north': group.rotation.y = Math.PI;      group.position.set(0, LEVELS.plinthTop, -W / 2 + wallT); break;
    case 'east':  group.rotation.y = Math.PI / 2;  group.position.set(L / 2 - wallT, LEVELS.plinthTop, 0); break;
    case 'west':  group.rotation.y = -Math.PI / 2; group.position.set(-L / 2 + wallT, LEVELS.plinthTop, 0); break;
  }
}

/* ---------- крыша ---------- */

// Возвращает трансформацию для плоскости ската: sign = +1 (в сторону +Z) или -1.
function slopeTransform(sign, liftAlongNormal, zRangeCenterOverride) {
  const { W, eaveOv } = DIM;
  const zEave = W / 2 + eaveOv;
  const yEave = LEVELS.eave - eaveOv * TAN;
  const zc = (zRangeCenterOverride ?? zEave / 2) * sign;
  const yc = (LEVELS.ridge + yEave) / 2;
  const rot = sign > 0 ? RAD(DIM.pitch) : -RAD(DIM.pitch);
  const n = new THREE.Vector3(0, Math.cos(RAD(DIM.pitch)), sign * Math.sin(RAD(DIM.pitch)));
  return {
    rotX: rot,
    pos: new THREE.Vector3(0, yc, zc).addScaledVector(n, liftAlongNormal),
    slopeLen: zEave / Math.cos(RAD(DIM.pitch)),
    normal: n,
  };
}

function buildRoof(mats) {
  const g = new THREE.Group();
  const { L, rakeOvE, rakeOvW, roofT } = DIM;
  const roofLen = L + rakeOvE + rakeOvW;
  const xOff = (rakeOvE - rakeOvW) / 2;

  for (const sign of [1, -1]) {
    const t = slopeTransform(sign, roofT / 2);

    const slab = box(roofLen, roofT, t.slopeLen, mats.roof,
      [xOff + t.pos.x, t.pos.y, t.pos.z], [t.rotX, 0, 0]);
    g.add(slab);

    // стоячий фальц — рёбра вдоль ската с шагом 40 см
    const step = 0.4;
    const n = Math.floor(roofLen / step);
    const seam = new THREE.InstancedMesh(
      new THREE.BoxGeometry(0.035, 0.055, t.slopeLen), mats.seam, n
    );
    seam.castShadow = true;
    const m = new THREE.Matrix4();
    const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(t.rotX, 0, 0));
    const up = t.normal.clone().multiplyScalar(roofT / 2 + 0.027);
    for (let i = 0; i < n; i++) {
      const x = xOff - roofLen / 2 + step * (i + 0.5);
      m.compose(new THREE.Vector3(x + up.x, t.pos.y + up.y, t.pos.z + up.z), q, new THREE.Vector3(1, 1, 1));
      seam.setMatrixAt(i, m);
    }
    g.add(seam);

    // тёмный подшив под всей плоскостью
    const soffit = box(roofLen, 0.03, t.slopeLen, mats.soffit,
      [xOff, t.pos.y - roofT / 2 - 0.015, t.pos.z], [t.rotX, 0, 0]);
    soffit.castShadow = false;
    g.add(soffit);

    // деревянный подшив выразительного восточного свеса
    const woodLen = rakeOvE;
    const woodX = L / 2 + rakeOvE / 2;
    const wood = box(woodLen, 0.035, t.slopeLen, mats.wood,
      [woodX, t.pos.y - roofT / 2 - 0.03, t.pos.z], [t.rotX, 0, 0]);
    wood.castShadow = false;
    g.add(wood);

    // лобовая доска по карнизу
    const zEave = (DIM.W / 2 + DIM.eaveOv) * sign;
    const yEave = LEVELS.eave - DIM.eaveOv * TAN;
    g.add(box(roofLen, 0.20, 0.045, mats.soffit, [xOff, yEave - 0.06, zEave + 0.02 * sign]));

    // ветровая доска по фронтону: тёмная на западе, деревянная балка на востоке
    const rake = box(0.07, 0.24, t.slopeLen, mats.woodDark,
      [L / 2 + rakeOvE - 0.04, t.pos.y - 0.03, t.pos.z], [t.rotX, 0, 0]);
    g.add(rake);
    g.add(box(0.06, 0.20, t.slopeLen, mats.soffit,
      [-L / 2 - rakeOvW + 0.03, t.pos.y - 0.02, t.pos.z], [t.rotX, 0, 0]));
  }

  // конёк
  g.add(box(roofLen, 0.10, 0.30, mats.roof, [xOff, LEVELS.ridge + DIM.roofT / Math.cos(RAD(DIM.pitch)) - 0.02, 0]));
  return g;
}

// Мансардные окна на южном скате.
function buildSkylights(mats) {
  const g = new THREE.Group();
  const t = slopeTransform(1, DIM.roofT / 2 + 0.04);
  const along = 1.35; // насколько вниз по скату от конька
  const dir = new THREE.Vector3(0, -Math.sin(RAD(DIM.pitch)), Math.cos(RAD(DIM.pitch)));
  for (const x of [-1.75, 1.15]) {
    const p = new THREE.Vector3(x, LEVELS.ridge, 0)
      .addScaledVector(dir, along)
      .addScaledVector(t.normal, DIM.roofT - 0.01); // сажаем в плоскость кровли, выступ ~4 см
    const frame = box(0.86, 0.10, 1.24, mats.frame, [p.x, p.y, p.z], [t.rotX, 0, 0]);
    g.add(frame);
    const glass = box(0.74, 0.06, 1.12, mats.glass,
      [p.x + t.normal.x * 0.03, p.y + t.normal.y * 0.03, p.z + t.normal.z * 0.03], [t.rotX, 0, 0]);
    g.add(glass);
  }
  return g;
}

/* ---------- цоколь ---------- */
// Отдельный объект с собственным материалом. Панели строятся тем же способом,
// что и стены, поэтому UV тоже в метрах и зерно мозаики не «плывёт».
function buildPlinth(mats) {
  const g = new THREE.Group();
  g.name = 'Plinth';
  const { L, W, plinthH, plinthOut } = DIM;
  const t = 0.06;
  const oL = L / 2 + plinthOut;
  const oW = W / 2 + plinthOut;

  const panel = (width, place) => {
    const geo = wallGeometry([[-width / 2, 0], [width / 2, 0], [width / 2, plinthH], [-width / 2, plinthH]], [], t);
    const m = new THREE.Mesh(geo, mats.plinth);
    m.name = 'Plinth';
    m.castShadow = true;
    m.receiveShadow = true;
    place(m);
    g.add(m);
  };

  // Длинные панели короче на две толщины — по той же причине, что и стены:
  // иначе их торцы лежат в одной плоскости с наружной гранью боковых панелей
  // и цоколь на углах мерцает.
  panel(oL * 2 - t * 2, (m) => m.position.set(0, 0, oW - t));
  panel(oL * 2 - t * 2, (m) => { m.rotation.y = Math.PI; m.position.set(0, 0, -oW + t); });
  panel(oW * 2, (m) => { m.rotation.y = Math.PI / 2; m.position.set(oL - t, 0, 0); });
  panel(oW * 2, (m) => { m.rotation.y = -Math.PI / 2; m.position.set(-oL + t, 0, 0); });

  // капельник поверх цоколя — отбивает границу и прячет стык
  const cap = new THREE.Group();
  cap.add(box(oL * 2 + 0.06, 0.035, oW * 2 + 0.06, mats.metal, [0, plinthH + 0.017, 0]));
  g.add(cap);
  return g;
}

/* ---------- окружение дома ---------- */

function buildTerrace(mats) {
  const g = new THREE.Group();
  const zStart = DIM.W / 2 + 0.05;
  const depth = 3.4, width = 6.6, top = 0.44;

  g.add(box(width, 0.28, depth, mats.deck, [0, top - 0.14, zStart + depth / 2]));

  // доски настила
  const pw = 0.14, gap = 0.02, n = Math.floor(width / (pw + gap));
  const planks = new THREE.InstancedMesh(new THREE.BoxGeometry(pw, 0.04, depth - 0.04), mats.deck, n);
  planks.castShadow = true;
  planks.receiveShadow = true;
  const m = new THREE.Matrix4();
  for (let i = 0; i < n; i++) {
    m.makeTranslation(-width / 2 + (pw + gap) * (i + 0.5), top + 0.005, zStart + depth / 2);
    planks.setMatrixAt(i, m);
  }
  g.add(planks);

  // две ступени
  g.add(box(2.6, 0.16, 0.34, mats.deck, [0, 0.30, zStart + depth + 0.17]));
  g.add(box(2.6, 0.16, 0.34, mats.deck, [0, 0.14, zStart + depth + 0.51]));
  return g;
}

function buildChimney(mats) {
  const g = new THREE.Group();
  const h = LEVELS.ridge + 1.05;
  g.add(box(0.66, h, 0.66, mats.chimney, [1.9, h / 2, 0]));
  g.add(box(0.80, 0.10, 0.80, mats.metal, [1.9, h + 0.05, 0]));
  return g;
}

function buildLamps(mats) {
  const g = new THREE.Group();
  const z = DIM.W / 2 + 0.03;
  for (const x of [-6.5, -2.6, 2.6, 6.2]) {
    g.add(box(0.10, 0.24, 0.07, mats.lamp, [x, LEVELS.plinthTop + 2.55, z]));
  }
  return g;
}

function buildGround(mats) {
  const geo = new THREE.CircleGeometry(70, 64);
  const m = new THREE.Mesh(geo, mats.ground);
  m.rotation.x = -Math.PI / 2;
  m.receiveShadow = true;
  m.name = 'Ground';
  return m;
}

// Отмостка вокруг дома — отбивает цоколь от газона.
function buildApron(mats) {
  const g = new THREE.Group();
  const { L, W, plinthOut } = DIM;
  const oL = L / 2 + plinthOut, oW = W / 2 + plinthOut;
  const b = 0.85; // ширина отмостки
  const y = 0.045;
  g.add(box(oL * 2 + b * 2, 0.09, b, mats.apron, [0, y, oW + b / 2]));
  g.add(box(oL * 2 + b * 2, 0.09, b, mats.apron, [0, y, -oW - b / 2]));
  g.add(box(b, 0.09, oW * 2, mats.apron, [oL + b / 2, y, 0]));
  g.add(box(b, 0.09, oW * 2, mats.apron, [-oL - b / 2, y, 0]));
  g.children.forEach((c) => (c.castShadow = false));
  return g;
}

/* ---------- сборка ---------- */

export function buildHouse(mats) {
  const root = new THREE.Group();
  root.name = 'House';

  const { L, W, wallH, wallT } = DIM;
  const gableTop = wallH + (W / 2) * TAN;

  const rect = (w, h) => [[-w / 2, 0], [w / 2, 0], [w / 2, h], [-w / 2, h]];
  const gable = (w, h, top) => [[-w / 2, 0], [w / 2, 0], [w / 2, h], [0, top], [-w / 2, h]];

  const walls = new THREE.Group();
  walls.name = 'Facade';

  for (const [side, holes] of Object.entries(OPENINGS)) {
    const grp = new THREE.Group();
    const isGable = side === 'east' || side === 'west';
    // ⚠️ Длинные стены КОРОЧЕ на две толщины: они упираются в торцевые, а не
    // перекрывают их. Раньше обе стены доходили до угла, их наружные плоскости
    // совпадали — и на углу текстура «фонила» (z-fighting: два одинаковых
    // полигона в одной плоскости, видеокарта на каждом кадре выбирает разный).
    const outline = isGable ? gable(W, wallH, gableTop) : rect(L - wallT * 2, wallH);
    buildWall(outline, holes, mats, grp);
    placeWall(grp, side);
    walls.add(grp);
  }

  root.add(walls);
  root.add(buildPlinth(mats));
  root.add(buildRoof(mats));
  root.add(buildSkylights(mats));
  root.add(buildChimney(mats));
  root.add(buildTerrace(mats));
  root.add(buildLamps(mats));
  root.add(buildApron(mats));

  return { root, ground: buildGround(mats) };
}
