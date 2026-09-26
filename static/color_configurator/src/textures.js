// Процедурная генерация текстур штукатурки.
// Каждая фактура рисуется на canvas как карта высот, из неё считается normal map,
// а альбедо остаётся почти белым (серым) — чтобы тонировка цветом работала честно.
//
// В продакшене эти функции заменяются на загрузку реальных сканов:
//   makeFacadeMaps() -> { albedo, normal, roughness } из PNG/KTX2
//   makePlinthMaps() -> { albedo, normal } из скана конкретного артикула

import * as THREE from '../vendor/three/build.three.module.js?v=45';

const FACADE_TILE_M = 1.0;  // сколько метров стены покрывает один тайл фасада
const PLINTH_TILE_M = 0.5;  // тайл цоколя мельче — зерно мозаики должно читаться

/* ---------- утилиты ---------- */

function canvas(size) {
  const c = document.createElement('canvas');
  c.width = c.height = size;
  return c;
}

// willReadFrequently: дальше из этих холстов читаем getImageData (normal/albedo/speckle).
// Без флага Chromium каждый раз снимает GPU-снимок — на 1024² это сотни миллисекунд.

// детерминированный ГПСЧ, чтобы текстура не «прыгала» между перерисовками
function rng(seed) {
  let s = seed >>> 0;
  return () => {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

// Рисует фигуру с зацикливанием по краям — иначе тайл будет со швом.
//
// Раньше каждая фигура рисовалась ДЕВЯТЬ раз (3×3). У камешковой 1,5 мм на 1024 px
// это ~1,1 млн радиальных градиентов на старте — главная причина «Сборка модели…».
// Почти все зёрна внутри тайла и на шов не влияют. Дублируем только те, что
// пересекают край: `rad` — радиус (или полудиагональ) фигуры вокруг (x, y).
function wrapped(ctx, size, x, y, draw, rad = 8) {
  draw(x, y);
  const L = x < rad, R = x > size - rad, T = y < rad, B = y > size - rad;
  if (!(L || R || T || B)) return;
  if (L) draw(x + size, y);
  if (R) draw(x - size, y);
  if (T) draw(x, y + size);
  if (B) draw(x, y - size);
  if (L && T) draw(x + size, y + size);
  if (R && T) draw(x - size, y + size);
  if (L && B) draw(x + size, y - size);
  if (R && B) draw(x - size, y - size);
}

// Мелкий шум поверх основы — «песок» в растворе.
function speckle(ctx, size, rand, amount, alpha) {
  const img = ctx.getImageData(0, 0, size, size);
  const d = img.data;
  for (let i = 0; i < d.length; i += 4) {
    const n = (rand() - 0.5) * amount;
    d[i] = clamp255(d[i] + n);
    d[i + 1] = clamp255(d[i + 1] + n);
    d[i + 2] = clamp255(d[i + 2] + n);
  }
  ctx.putImageData(img, 0, 0);
}

const clamp255 = (v) => (v < 0 ? 0 : v > 255 ? 255 : v);

/* ---------- карты высот по фактурам ---------- */

// Короед: борозды от зерна, которое протаскивают тёркой.
//
// Направление ВЕРТИКАЛЬНОЕ — борозда идёт сверху вниз, длинная ось канавки по Y,
// блуждание (drift) по X. Так тёркой ведут «на снос воды»: вертикальный короед
// на фасаде практичнее, дождь стекает по борозде и не задерживается в ней.
//
// На стыках это работает само, без дополнительных правок:
//   • тайл бесшовный в обе стороны — wrapped() дублирует борозду у края тайла,
//     поэтому канавка, ушедшая за край, входит с противоположной стороны;
//   • на УГЛУ дома и на боковом откосе проёма UV положены как V = высота
//     (см. WallUV.generateSideWallUV в house.js), значит вертикальная борозда
//     остаётся вертикальной и на торце — рисунок не разворачивается на 90°;
//   • на верхнем и нижнем откосе проёма V = глубина стены, и борозда уходит
//     внутрь откоса — ровно так, как ложится настоящая штукатурка.
// Менять направление обратно на горизонтальное — только здесь, разворотом осей.
function heightKoroed(size, grainMm, seed) {
  const c = canvas(size);
  const ctx = c.getContext('2d', { willReadFrequently: true });
  const rand = rng(seed);
  const pxPerMm = size / (FACADE_TILE_M * 1000);

  ctx.fillStyle = '#8a8a8a';
  ctx.fillRect(0, 0, size, size);

  // борозды: короткие блуждающие вертикальные канавки
  const grooveW = Math.max(1.2, grainMm * pxPerMm);
  const count = Math.round((size * size) / (grooveW * 260));
  ctx.lineCap = 'round';
  for (let i = 0; i < count; i++) {
    const x = rand() * size;
    const y = rand() * size;
    const len = (30 + rand() * 140) * (size / 1024);
    const drift = (rand() - 0.5) * 26 * (size / 1024);
    const depth = 30 + rand() * 55;
    const rad = Math.abs(drift) + len + grooveW * 2;
    ctx.strokeStyle = `rgba(0,0,0,${(depth / 255).toFixed(3)})`;
    ctx.lineWidth = grooveW * (0.7 + rand() * 0.7);
    wrapped(ctx, size, x, y, (px, py) => {
      ctx.beginPath();
      ctx.moveTo(px, py);
      ctx.bezierCurveTo(px + drift * 0.4, py + len * 0.35, px + drift, py + len * 0.7, px + drift * 0.6, py + len);
      ctx.stroke();
    }, rad);
    // светлый валик вдоль борозды — приподнятый край
    ctx.strokeStyle = 'rgba(255,255,255,0.16)';
    ctx.lineWidth = grooveW * 0.5;
    // валик сдвинут перпендикулярно борозде — раз борозда вертикальная, сдвиг по X
    wrapped(ctx, size, x - grooveW * 0.8, y, (px, py) => {
      ctx.beginPath();
      ctx.moveTo(px, py);
      ctx.bezierCurveTo(px + drift * 0.4, py + len * 0.35, px + drift, py + len * 0.7, px + drift * 0.6, py + len);
      ctx.stroke();
    }, rad);
  }

  ctx.filter = 'blur(0.6px)';
  ctx.drawImage(c, 0, 0);
  ctx.filter = 'none';
  speckle(ctx, size, rand, 22);
  return c;
}

// Шуба: набрызг — плотные округлые нашлёпки раствора.
// Фракций у неё две (мешки 1,5 и 2,5 мм), и разницу между ними надо ВИДЕТЬ.
// Тайл — 1 м на 1024 px, то есть 1 мм ≈ 1 px: при честном масштабе нашлёпка мелкой
// фракции занимала бы полтора пикселя, обе фракции выглядели бы одинаково гладкими.
// Поэтому радиус намеренно увеличен (×1.15 вместо ×0.7) — зерно читается, и 1,5 мм
// заметно мельче 2,5 мм. Это осознанное преувеличение ради наглядности.
function heightShuba(size, grainMm, seed) {
  const c = canvas(size);
  const ctx = c.getContext('2d', { willReadFrequently: true });
  const rand = rng(seed);
  const pxPerMm = size / (FACADE_TILE_M * 1000);
  const r = Math.max(1.8, grainMm * pxPerMm * 1.15);

  ctx.fillStyle = '#6f6f6f';
  ctx.fillRect(0, 0, size, size);

  const count = Math.round((size * size) / (r * r * 3.4));
  for (let i = 0; i < count; i++) {
    const x = rand() * size;
    const y = rand() * size;
    const rr = r * (0.6 + rand() * 1.1);
    const h = 150 + rand() * 105;
    wrapped(ctx, size, x, y, (px, py) => {
      const g = ctx.createRadialGradient(px, py, 0, px, py, rr);
      g.addColorStop(0, `rgb(${h | 0},${h | 0},${h | 0})`);
      g.addColorStop(1, 'rgba(120,120,120,0)');
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(px, py, rr, 0, Math.PI * 2);
      ctx.fill();
    }, rr);
  }
  ctx.filter = 'blur(0.8px)';
  ctx.drawImage(c, 0, 0);
  ctx.filter = 'none';
  speckle(ctx, size, rand, 18);
  return c;
}

// Камешковая: плотно уложенное округлое зерно одной фракции.
function heightKamesh(size, grainMm, seed) {
  const c = canvas(size);
  const ctx = c.getContext('2d', { willReadFrequently: true });
  const rand = rng(seed);
  const pxPerMm = size / (FACADE_TILE_M * 1000);
  // Тот же приём, что и у «шубы»: 1 мм ≈ 1 px, поэтому при честном масштабе зерно
  // 1 и 2,5 мм упиралось бы в один и тот же минимум и все фракции выглядели одинаково.
  // Радиус увеличен (×1.15) — фракции видно и они отличаются друг от друга.
  const r = Math.max(1.4, grainMm * pxPerMm * 1.15);

  ctx.fillStyle = '#5a5a5a';
  ctx.fillRect(0, 0, size, size);

  const count = Math.round((size * size) / (r * r * 2.6));
  for (let i = 0; i < count; i++) {
    const x = rand() * size;
    const y = rand() * size;
    const rr = r * (0.8 + rand() * 0.5);
    const h = 165 + rand() * 80;
    wrapped(ctx, size, x, y, (px, py) => {
      const g = ctx.createRadialGradient(px - rr * 0.3, py - rr * 0.3, rr * 0.1, px, py, rr);
      g.addColorStop(0, `rgb(${(h + 35) | 0},${(h + 35) | 0},${(h + 35) | 0})`);
      g.addColorStop(0.75, `rgb(${h | 0},${h | 0},${h | 0})`);
      g.addColorStop(1, 'rgba(70,70,70,0.85)');
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(px, py, rr, 0, Math.PI * 2);
      ctx.fill();
    }, rr);
  }
  ctx.filter = 'blur(0.5px)';
  ctx.drawImage(c, 0, 0);
  ctx.filter = 'none';
  speckle(ctx, size, rand, 14);
  return c;
}

// Под дерево (Visage CT 720/721) — рисунок натурального дуба, как на референсе.
//
// Считается ПО ПИКСЕЛЯМ, а не штрихами: у настоящего распила рисунок — это годовые
// кольца, срезанные плоскостью. Модель ровно такая: под поверхностью доски лежит ось
// бревна на расстоянии h(x), кольца — окружности вокруг неё, а то, что мы видим, это
// линия пересечения колец с плоскостью: r = √((y − yc(x))² + h(x)²). Там, где h(x)
// уменьшается, кольца сходятся и получается характерная «ёлочка» (собор) — то самое,
// что на фото. Сучки — локальные возмущения этого поля.
//
// Полос-канавок и торцевых швов больше нет: на референсе это цельное полотно, доски
// различаются только тоном. Бесшовность: всё, что зависит от x, — целые гармоники
// sin(2πk·x/size); полосы делят тайл нацело; шум вдоль y замкнут по кольцу.
// ⚠️ Масштаб намеренно крупнее натурального. Кольца дуба идут через 1–2 см; на стене
// в 14 м это тоньше пикселя — рендер сваливается в муар («отпечаток пальца»), что и
// вылезло на первой попытке. Берём тайл 1,6 м и кольца пореже: рисунок читается как
// дерево и с трёх метров, и вблизи.
const WOOD_TILE_M = 1.6;    // столько метров стены покрывает один тайл
const WOOD_BOARDS = 5;      // ламелей в тайле → ~32 см на ламель

function heightWood(size, grainMm, seed) {
  const c = canvas(size);
  const ctx = c.getContext('2d', { willReadFrequently: true });
  const rand = rng(seed);
  // grain у дерева задаёт не фракцию, а «приближение»: 2 — стена, 8 — превью в панели
  // (facadeThumb умножает grain на 4). При зуме показываем меньший кусок стены.
  const zoom = Math.max(1, grainMm / 2);
  const boards = Math.max(2, Math.round(WOOD_BOARDS / zoom));
  const bh = size / boards;
  const px1024 = size / 1024;

  // 1D-шум вдоль y, замкнутый по кольцу: даёт тонкие продольные волокна
  const noiseN = size;
  const noise = new Float32Array(noiseN);
  for (let i = 0; i < noiseN; i++) noise[i] = rand();
  const smooth = (t) => {
    const i0 = Math.floor(t), f = t - i0;
    const a = noise[((i0 % noiseN) + noiseN) % noiseN];
    const b = noise[((i0 + 1) % noiseN + noiseN) % noiseN];
    const u = f * f * (3 - 2 * f);
    return a + (b - a) * u;
  };

  // параметры ламелей
  const B = [];
  for (let b = 0; b < boards; b++) {
    B.push({
      tone: -8 + rand() * 16,                       // ламели чуть отличаются по тону
      // ⚠️ Замкнутое кольцо («глаз») появляется там, где ось бревна подходит к самой
      // поверхности. Если позволить h(x) гулять сильно и часто, вся текстура зарастает
      // такими глазами — получается дешёвый «принт под дерево», что и вышло с первого раза.
      // Поэтому: ось лежит ГЛУБОКО (h0 велик), гуляет мягко (hAmp мал) и ОДИН раз на тайл
      // (k2 = 1). Тогда на ламель приходится один-два длинных «собора», как на распиле.
      yc: bh * (0.15 + rand() * 0.7),               // где проходит «сердцевина»
      amp: bh * (0.04 + rand() * 0.10),             // как гуляет сердцевина по длине
      k1: 1,
      ph1: rand() * Math.PI * 2,
      // h0 — компромисс: слишком мал → всё зарастает «глазами», слишком велик → кольца
      // почти не гнутся и текстура выходит пустой. Рабочая вилка ≈ 0.18…0.5 высоты ламели.
      h0: bh * (0.18 + rand() * 0.32),              // расстояние до оси бревна
      hAmp: bh * (0.08 + rand() * 0.16),            // его игра по длине → «соборы»
      k2: 1,
      ph2: rand() * Math.PI * 2,
      freq: (0.10 + rand() * 0.045) / (px1024 * zoom), // частота колец (реже, чем в натуре)
      knots: rand() < 0.5
        ? [{ x: rand() * size, y: bh * (0.2 + rand() * 0.6), r: bh * (0.05 + rand() * 0.05) }]
        : [],
    });
  }

  const img = ctx.createImageData(size, size);
  const px = img.data;
  const TAU = Math.PI * 2;

  for (let y = 0; y < size; y++) {
    const b = Math.min(boards - 1, Math.floor(y / bh));
    const p = B[b];
    const ly = y - b * bh;

    for (let x = 0; x < size; x++) {
      const yc = p.yc + p.amp * Math.sin((TAU * p.k1 * x) / size + p.ph1);
      let h = p.h0 + p.hAmp * Math.sin((TAU * p.k2 * x) / size + p.ph2);
      let dy = ly - yc;

      // сучок: рядом с ним кольца стягиваются в тугой овал
      for (const kt of p.knots) {
        let ddx = (x - kt.x) % size;
        if (ddx > size / 2) ddx -= size;
        if (ddx < -size / 2) ddx += size;
        const ddy = ly - kt.y;
        const dist = Math.hypot(ddx * 0.7, ddy);
        if (dist < kt.r * 4) {
          const f = 1 - dist / (kt.r * 4);
          h *= 1 - 0.85 * f * f;
          dy += ddy * 0.6 * f * f;
        }
      }

      const r = Math.sqrt(dy * dy + h * h);
      // кольца: тонкая тёмная линия на светлом поле
      const t = 0.5 + 0.5 * Math.sin(r * p.freq * TAU + 0.5 * Math.sin((TAU * 2 * x) / size + p.ph1));
      const ring = Math.pow(1 - t, 2.2);

      // продольные волокна: 1D-шум вдоль y, слегка гуляющий по x
      // два масштаба волокна: крупные прожилки + тонкий «ворс», как на распиле
      const fib = (smooth(y * 1.1 + 9 * Math.sin((TAU * 2 * x) / size + p.ph2)) - 0.5)
                + (smooth(y * 3.7 + 4 * Math.sin((TAU * 3 * x) / size + p.ph1)) - 0.5) * 0.55;

      let g = 176 + p.tone - ring * 40 + fib * 34;
      if (g < 0) g = 0; else if (g > 255) g = 255;

      const i = (y * size + x) * 4;
      px[i] = px[i + 1] = px[i + 2] = g;
      px[i + 3] = 255;
    }
  }
  ctx.putImageData(img, 0, 0);

  ctx.filter = 'blur(0.4px)';
  ctx.drawImage(c, 0, 0);
  ctx.filter = 'none';
  speckle(ctx, size, rand, 7);
  return c;
}

// Гладкая (окрашенный фасад): именно ГЛАДКАЯ — почти плоская карта высот.
// Раньше здесь рисовались широкие мазки шпателем, и на стене они читались как полосы —
// «гладкая» выглядела чем угодно, только не гладкой. Оставлен лишь микрошум,
// чтобы поверхность не была стерильно-пластиковой в бликах.
function heightSmooth(size, seed) {
  const c = canvas(size);
  const ctx = c.getContext('2d', { willReadFrequently: true });
  const rand = rng(seed);
  ctx.fillStyle = '#808080';
  ctx.fillRect(0, 0, size, size);
  speckle(ctx, size, rand, 5, 0.05);   // зерно валика, почти незаметное
  ctx.filter = 'blur(1.2px)';
  ctx.drawImage(c, 0, 0);
  ctx.filter = 'none';
  return c;
}

// Мозаичная штукатурка цоколя: цветная крошка в прозрачном связующем.
function mosaicCanvases(size, article, seed) {
  const albedo = canvas(size);
  const height = canvas(size);
  const ca = albedo.getContext('2d', { willReadFrequently: true });
  const ch = height.getContext('2d', { willReadFrequently: true });
  const rand = rng(seed);
  const pxPerMm = size / (PLINTH_TILE_M * 1000);
  const r = Math.max(1.8, 1.6 * pxPerMm); // зерно ~1.6 мм

  ca.fillStyle = article.base;
  ca.fillRect(0, 0, size, size);
  ch.fillStyle = '#5c5c5c';
  ch.fillRect(0, 0, size, size);

  const count = Math.round((size * size) / (r * r * 2.3));
  for (let i = 0; i < count; i++) {
    const x = rand() * size;
    const y = rand() * size;
    const rr = r * (0.75 + rand() * 0.6);
    const color = article.crumbs[(rand() * article.crumbs.length) | 0];
    const h = 150 + rand() * 95;
    const ry = rr * (0.75 + rand() * 0.4);   // считаем заранее: внутри wrapped()
    const rot = rand() * Math.PI;            // случайность дала бы разные копии и шов

    const grainR = Math.max(rr, ry);
    wrapped(ctx0(ca), size, x, y, (px, py) => {
      ca.fillStyle = color;
      ca.beginPath();
      ca.ellipse(px, py, rr, ry, rot, 0, Math.PI * 2);
      ca.fill();
    }, grainR);
    wrapped(ctx0(ch), size, x, y, (px, py) => {
      const g = ch.createRadialGradient(px - rr * 0.3, py - rr * 0.3, rr * 0.1, px, py, rr);
      g.addColorStop(0, `rgb(${(h + 40) | 0},${(h + 40) | 0},${(h + 40) | 0})`);
      g.addColorStop(0.8, `rgb(${h | 0},${h | 0},${h | 0})`);
      g.addColorStop(1, 'rgba(60,60,60,0.9)');
      ch.fillStyle = g;
      ch.beginPath();
      ch.arc(px, py, rr, 0, Math.PI * 2);
      ch.fill();
    }, grainR);
  }

  // лёгкий глянец связующего + затемнение впадин
  ca.filter = 'blur(0.4px)';
  ca.drawImage(albedo, 0, 0);
  ca.filter = 'none';
  ch.filter = 'blur(0.5px)';
  ch.drawImage(height, 0, 0);
  ch.filter = 'none';
  return { albedo, height };
}

const ctx0 = (c) => c; // wrapped() ждёт первым аргументом контекст, но использует только замыкание

/* ---------- преобразования карт ---------- */

// Normal map из карты высот (OpenGL-конвенция, зелёный вверх). Края зациклены.
function normalFromHeight(hCanvas, strength) {
  const size = hCanvas.width;
  const src = hCanvas.getContext('2d', { willReadFrequently: true }).getImageData(0, 0, size, size).data;
  const out = canvas(size);
  const octx = out.getContext('2d', { willReadFrequently: true });
  const img = octx.createImageData(size, size);
  const d = img.data;
  const at = (x, y) => src[(((y + size) % size) * size + ((x + size) % size)) * 4] / 255;

  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const dx = (at(x + 1, y) - at(x - 1, y)) * strength * 4;
      const dy = (at(x, y + 1) - at(x, y - 1)) * strength * 4;
      let nx = -dx, ny = dy, nz = 1;
      const len = Math.hypot(nx, ny, nz);
      nx /= len; ny /= len; nz /= len;
      const i = (y * size + x) * 4;
      d[i]     = (nx * 0.5 + 0.5) * 255;
      d[i + 1] = (ny * 0.5 + 0.5) * 255;
      d[i + 2] = (nz * 0.5 + 0.5) * 255;
      d[i + 3] = 255;
    }
  }
  octx.putImageData(img, 0, 0);
  return out;
}

// Альбедо фасада: почти белое, с лёгким затемнением во впадинах.
// Умножается на выбранный цвет — поэтому рельеф читается в любом оттенке.
function albedoFromHeight(hCanvas, contrast) {
  const size = hCanvas.width;
  const src = hCanvas.getContext('2d', { willReadFrequently: true }).getImageData(0, 0, size, size);
  const d = src.data;
  for (let i = 0; i < d.length; i += 4) {
    const h = d[i] / 255;
    const v = 255 * (1 - contrast * (1 - h));
    d[i] = d[i + 1] = d[i + 2] = clamp255(v);
    d[i + 3] = 255;
  }
  const out = canvas(size);
  out.getContext('2d', { willReadFrequently: true }).putImageData(src, 0, 0);
  return out;
}

// Шероховатость: во впадинах матовее, на выступах чуть глаже.
function roughnessFromHeight(hCanvas, base, variance) {
  const size = hCanvas.width;
  const src = hCanvas.getContext('2d', { willReadFrequently: true }).getImageData(0, 0, size, size);
  const d = src.data;
  for (let i = 0; i < d.length; i += 4) {
    const h = d[i] / 255;
    const v = (base + (1 - h) * variance) * 255;
    d[i] = d[i + 1] = d[i + 2] = clamp255(v);
    d[i + 3] = 255;
  }
  const out = canvas(size);
  out.getContext('2d', { willReadFrequently: true }).putImageData(src, 0, 0);
  return out;
}

/* ---------- сборка three.js текстур ---------- */

function toTexture(c, { srgb = false, tileM = FACADE_TILE_M, aniso = 8 } = {}) {
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(1 / tileM, 1 / tileM); // 1 UV-юнит = 1 метр → тайлинг в реальном масштабе
  t.anisotropy = aniso;
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  t.needsUpdate = true;
  return t;
}

function heightFor(def, size, seed) {
  switch (def.kind) {
    case 'koroed': return heightKoroed(size, def.grain, seed);
    case 'shuba':  return heightShuba(size, def.grain, seed);
    case 'kamesh': return heightKamesh(size, def.grain, seed);
    case 'wood':   return heightWood(size, def.grain, seed);
    default:       return heightSmooth(size, seed);
  }
}

const facadeCache = new Map();
const plinthCache = new Map();
// Ограничиваем число одновременно удерживаемых карт: 48 артикулов цоколя по
// три 1024px-карты иначе постепенно занимают сотни мегабайт памяти и GPU.
const MAX_CACHED_VARIANTS = 4;

function cachedMaps(cache, key) {
  const maps = cache.get(key);
  if (maps) {
    cache.delete(key);
    cache.set(key, maps);
  }
  return maps;
}

function rememberMaps(cache, key, maps) {
  cache.set(key, maps);
  if (cache.size > MAX_CACHED_VARIANTS) {
    const oldestKey = cache.keys().next().value;
    const oldest = cache.get(oldestKey);
    cache.delete(oldestKey);
    Object.values(oldest).forEach((texture) => texture.dispose());
  }
  return maps;
}

export function facadeMaps(def, size = 1024, aniso = 8) {
  const key = `${def.id}:${size}`;
  const cached = cachedMaps(facadeCache, key);
  if (cached) return cached;

  const h = heightFor(def, size, hashId(def.id));
  const tileM = def.kind === 'wood' ? WOOD_TILE_M : FACADE_TILE_M;
  const maps = {
    // у дерева перепад светлее/темнее заметнее — иначе рисунок читается только в блике
    // у дерева свой тайл (WOOD_TILE_M) — иначе рисунок повторяется каждый метр
    map: toTexture(albedoFromHeight(h, def.kind === 'smooth' ? 0.06 : def.kind === 'wood' ? 0.26 : 0.16), { srgb: true, aniso, tileM }),
    normalMap: toTexture(normalFromHeight(h, def.normal), { aniso, tileM }),
    roughnessMap: toTexture(roughnessFromHeight(h, def.rough[0], def.rough[1]), { aniso, tileM }),
  };
  return rememberMaps(facadeCache, key, maps);
}

export function plinthMaps(article, size = 1024, aniso = 8) {
  const key = `${article.id}:${size}`;
  const cached = cachedMaps(plinthCache, key);
  if (cached) return cached;

  const { albedo, height } = mosaicCanvases(size, article, hashId(article.id));
  const maps = {
    map: toTexture(albedo, { srgb: true, tileM: PLINTH_TILE_M, aniso }),
    normalMap: toTexture(normalFromHeight(height, 1.4), { tileM: PLINTH_TILE_M, aniso }),
    roughnessMap: toTexture(roughnessFromHeight(height, 0.42, 0.30), { tileM: PLINTH_TILE_M, aniso }),
  };
  return rememberMaps(plinthCache, key, maps);
}

// Превью-плитки для панели управления.
// ⚠️ Превью — это НЕ метр стены, а её кусок примерно 25×25 см (ZOOM = 4). Иначе фракции
// в панели неразличимы: тайл 1 м рисуется на 320 px, то есть 1 мм ≈ 0.32 px, и зерно
// любой фракции упирается в минимальную ширину штриха — все образцы выходили одинаковыми,
// хотя на стене (1024 px на метр) разница есть. Увеличиваем зерно ровно во столько же раз,
// во сколько «приближаем» кусок стены.
export function facadeThumb(def, size = 96) {
  const ZOOM = 4;
  const h = heightFor({ ...def, grain: def.grain * ZOOM }, size * 2, hashId(def.id));
  const a = albedoFromHeight(h, 0.42);
  return downscale(a, size);
}

export function plinthThumb(article, size = 96) {
  const { albedo } = mosaicCanvases(size * 2, article, hashId(article.id));
  return downscale(albedo, size);
}

function downscale(src, size) {
  const c = canvas(size);
  const ctx = c.getContext('2d', { willReadFrequently: true });
  ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(src, 0, 0, size, size);
  return c.toDataURL('image/png');
}

function hashId(id) {
  let h = 2166136261;
  for (let i = 0; i < id.length; i++) h = Math.imul(h ^ id.charCodeAt(i), 16777619);
  return h >>> 0;
}

// Газон: пятнистая зелень, чтобы плоскость земли не читалась как заливка.
export function groundTexture(size = 512, aniso = 8) {
  const c = canvas(size);
  const ctx = c.getContext('2d', { willReadFrequently: true });
  const rand = rng(0x51a2);
  ctx.fillStyle = '#7b8560';
  ctx.fillRect(0, 0, size, size);

  const tints = ['#6f7a56', '#87916a', '#75805a', '#909a71'];
  for (let i = 0; i < 900; i++) {
    const x = rand() * size, y = rand() * size;
    const r = (6 + rand() * 34) * (size / 512);
    ctx.fillStyle = tints[(rand() * tints.length) | 0];
    ctx.globalAlpha = 0.16 + rand() * 0.22;
    wrapped(ctx, size, x, y, (px, py) => {
      ctx.beginPath();
      ctx.arc(px, py, r, 0, Math.PI * 2);
      ctx.fill();
    }, r);
  }
  ctx.globalAlpha = 1;
  ctx.filter = 'blur(1.5px)';
  ctx.drawImage(c, 0, 0);
  ctx.filter = 'none';
  speckle(ctx, size, rand, 26);
  return toTexture(c, { srgb: true, tileM: 6, aniso });
}

/* ---------- небо ---------- */

// Панорама неба для фона и для отражений (environment).
// Плоская заливка выглядит мёртво, поэтому здесь: многоступенчатый градиент,
// дымка у горизонта, кучевые облака и солнечное пятно в направлении источника.
export function skyTexture(preset, size = 1024) {
  const c = canvas(size);
  c.height = size / 2;
  const ctx = c.getContext('2d', { willReadFrequently: true });
  const W = c.width, H = c.height;
  const horizonY = H * 0.5;

  // зенит → горизонт → земля
  const g = ctx.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0.00, preset.sky.top);
  g.addColorStop(0.22, mix(preset.sky.top, preset.sky.horizon, 0.28));
  g.addColorStop(0.40, mix(preset.sky.top, preset.sky.horizon, 0.72));
  g.addColorStop(0.492, preset.sky.horizon);
  g.addColorStop(0.505, mix(preset.sky.horizon, preset.sky.ground, 0.55));
  g.addColorStop(0.60, preset.sky.ground);
  g.addColorStop(1.00, mix(preset.sky.ground, '#000000', 0.35));
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, W, H);

  const el = (preset.sun.el * Math.PI) / 180;
  const az = (preset.sun.az * Math.PI) / 180;
  const dir = { x: Math.cos(el) * Math.sin(az), y: Math.sin(el), z: Math.cos(el) * Math.cos(az) };
  const sunU = (Math.atan2(dir.z, dir.x) / (Math.PI * 2) + 0.5) * W;
  const sunV = (1 - (Math.asin(dir.y) / Math.PI + 0.5)) * H;

  // подсвет неба со стороны солнца — небо не бывает равномерным
  ctx.globalCompositeOperation = 'lighter';
  const wash = ctx.createRadialGradient(sunU, sunV, 0, sunU, sunV, W * 0.42);
  wash.addColorStop(0, hexA(preset.sun.color, 0.2));
  wash.addColorStop(1, hexA(preset.sun.color, 0));
  ctx.fillStyle = wash;
  ctx.fillRect(0, 0, W, horizonY);
  ctx.globalCompositeOperation = 'source-over';

  // Облака рисуются на отдельном холсте и накладываются размытыми:
  // иначе отдельные «пузыри» видны как круги, а не как масса.
  const cl = preset.clouds;
  if (cl && cl.cover > 0) {
    const layer = canvas(W);
    layer.height = H;
    const lc = layer.getContext('2d', { willReadFrequently: true });
    const rand = rng(0x51c0d);
    const count = Math.round(26 * cl.cover);
    const lit = mix('#ffffff', cl.tintTop, 0.3);
    const shade = cl.tintBase;

    for (let i = 0; i < count; i++) {
      const band = Math.pow(rand(), 0.55);             // 0 = зенит, 1 = горизонт
      const cy = H * (0.05 + band * 0.42);
      const cx = rand() * W;
      const scale = (1 - band * 0.4) * (0.9 + rand() * 0.9);
      const puffs = 6 + Math.floor(rand() * 5);
      const dense = (0.55 + rand() * 0.45) * (1 - band * 0.3);

      for (let k = 0; k < puffs; k++) {
        const dx = (rand() - 0.5) * W * 0.075 * scale;
        const dy = (rand() - 0.55) * H * 0.026 * scale;
        const rx = W * (0.016 + rand() * 0.028) * scale;
        const ry = rx * (0.4 + rand() * 0.28);
        const tone = dy < 0 ? lit : shade;             // верх подсвечен, низ в тени
        for (const ox of [-W, 0, W]) {                 // склейка по краю панорамы
          const gr = lc.createRadialGradient(cx + dx + ox, cy + dy, 0, cx + dx + ox, cy + dy, rx);
          gr.addColorStop(0, hexA(tone, dense));
          gr.addColorStop(0.5, hexA(tone, dense * 0.6));
          gr.addColorStop(1, hexA(tone, 0));
          lc.fillStyle = gr;
          lc.beginPath();
          lc.ellipse(cx + dx + ox, cy + dy, rx, ry, 0, 0, Math.PI * 2);
          lc.fill();
        }
      }
    }

    ctx.save();
    ctx.globalAlpha = cl.alpha;
    ctx.filter = 'blur(9px)';
    ctx.drawImage(layer, 0, 0);
    ctx.restore();
  }

  // дымка: у горизонта воздух светлее, дальний лес должен в неё уходить
  const haze = ctx.createLinearGradient(0, horizonY - H * 0.11, 0, horizonY);
  haze.addColorStop(0, hexA(preset.sky.horizon, 0));
  haze.addColorStop(1, hexA(preset.sky.horizon, 0.5));
  ctx.fillStyle = haze;
  ctx.fillRect(0, horizonY - H * 0.11, W, H * 0.11);

  // диск солнца
  ctx.globalCompositeOperation = 'lighter';
  const glow = ctx.createRadialGradient(sunU, sunV, 0, sunU, sunV, H * 0.20);
  glow.addColorStop(0, preset.sun.color);
  glow.addColorStop(0.045, hexA(preset.sun.color, 0.5));
  glow.addColorStop(0.22, hexA(preset.sun.color, 0.13));
  glow.addColorStop(1, hexA(preset.sun.color, 0));
  ctx.fillStyle = glow;
  ctx.fillRect(0, 0, W, H);
  ctx.globalCompositeOperation = 'source-over';

  const t = new THREE.Texture(c);
  t.mapping = THREE.EquirectangularReflectionMapping;
  t.colorSpace = THREE.SRGBColorSpace;
  t.needsUpdate = true;
  return t;
}

function mix(a, b, k) {
  const ca = hexRgb(a), cb = hexRgb(b);
  return `rgb(${Math.round(ca[0] + (cb[0] - ca[0]) * k)},${Math.round(ca[1] + (cb[1] - ca[1]) * k)},${Math.round(ca[2] + (cb[2] - ca[2]) * k)})`;
}
// Принимает и '#rrggbb', и 'rgb(r,g,b)' — mix() возвращает второе.
function hexRgb(h) {
  if (h[0] !== '#') return h.match(/\d+/g).slice(0, 3).map(Number);
  const s = h.replace('#', '');
  return [parseInt(s.slice(0, 2), 16), parseInt(s.slice(2, 4), 16), parseInt(s.slice(4, 6), 16)];
}
function hexA(h, a) {
  const [r, g, b] = hexRgb(h);
  return `rgba(${r},${g},${b},${a})`;
}
