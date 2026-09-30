import * as THREE from '../vendor/three/build.three.module.js?v=45';
import { OrbitControls } from '../vendor/three/examples/jsm/controls/OrbitControls.js?v=45';

import { FACADE_TEXTURES, FACADE_KINDS, FACADE_COLORS, PLINTH_TEXTURES, TIME_PRESETS, LANDSCAPE_LEVELS, DEFAULTS } from './data.js?v=45';
import { facadeMaps, plinthMaps, facadeThumb, plinthThumb, skyTexture, groundTexture } from './textures.js?v=52';
import { buildHouse, createMaterials, DIM, LEVELS } from './house.js?v=45';

const $ = (sel) => document.querySelector(sel);

/* ---------- состояние ---------- */

const state = { ...DEFAULTS, ...readURL() };

/* ---------- режим «только выбор цвета» ----------
 * Витрина карточки товара открывает виджет так: дом остаётся, но справа —
 * только палитра с ценами и кнопка «Подтвердить». Фактура/цоколь/освещение скрыты.
 * Цены приходят с сайта (?pr=base64 JSON {id цвета: надбавка}), потому что живут
 * в БД (modx_colors_products), а виджет — статика и в базу не ходит.
 */
const COLOR_ONLY = new URLSearchParams(location.search).get('mode') === 'color';
/* ?pm= — множитель надбавки (мелкая фасовка колеруется дешевле, правило
 * discount_coloring живёт в базе сайта). Применяем ОДИН раз при разборе: дальше
 * и палитра, и подпись «+N ₽», и цена, которую виджет возвращает на сайт,
 * уже эффективные. Иначе виджет обещал 800 ₽, а корзина считала 400 ₽. */
const PRICE_MUL = (() => {
  const v = parseFloat(new URLSearchParams(location.search).get('pm'));
  return isFinite(v) && v > 0 ? v : 1;
})();
const COLOR_PRICES = (() => {
  try {
    const b = new URLSearchParams(location.search).get('pr');
    const map = b ? JSON.parse(decodeURIComponent(escape(atob(b)))) : {};
    if (PRICE_MUL !== 1) {
      Object.keys(map).forEach((k) => { map[k] = Math.round(Number(map[k]) * PRICE_MUL); });
    }
    return map;
  } catch (e) { return {}; }
})();

function readURL() {
  const p = new URLSearchParams(location.search);
  const s = {};
  if (['none', 'lawn', 'full'].includes(p.get('l'))) s.landscape = p.get('l');
  if (FACADE_TEXTURES.some((t) => t.id === p.get('f'))) s.facadeTexture = p.get('f');
  if (FACADE_COLORS.some((c) => c.id === p.get('c'))) s.facadeColor = p.get('c');
  if (PLINTH_TEXTURES.some((t) => t.id === p.get('p'))) s.plinthTexture = p.get('p');
  if (TIME_PRESETS.some((t) => t.id === p.get('t'))) s.time = p.get('t');
  return s;
}

function writeURL() {
  const p = new URLSearchParams({
    f: state.facadeTexture, c: state.facadeColor, p: state.plinthTexture,
    t: state.time, l: state.landscape,
  });
  history.replaceState(null, '', `${location.pathname}?${p}`);
}

/* ---------- сцена ---------- */

// Телефон/планшет тянет всё то же самое, но втрое медленнее, а экран мельче.
// Поэтому на тач-устройствах уменьшаем три самые дорогие величины: плотность пикселей,
// карту теней и размер процедурных текстур. На глаз в кадре 375px разницы нет,
// а старт заметно короче.
const COARSE = matchMedia('(pointer: coarse)').matches;
// Тач не единственный признак слабого устройства: малопамятные настольные
// компьютеры тоже получают облегчённые карты, тени и плотность пикселей.
const LOW_END = COARSE || (navigator.deviceMemory > 0 && navigator.deviceMemory <= 4)
  || (navigator.hardwareConcurrency > 0 && navigator.hardwareConcurrency <= 2);
// Первый кадр — 512 px: фактура читается, а генерация вчетверо короче 1024.
// Полный размер доезжает после показа дома (см. upgradeMaps).
const TEX_START = LOW_END ? 256 : 512;
const TEX_FULL = LOW_END ? 256 : 1024;
let texSize = TEX_START;
const SKY_SIZE = LOW_END ? 256 : 1024;

const canvas = $('#view');
// PNG export explicitly renders before copying the canvas. Retaining the GPU
// buffer between frames would waste memory and reduce mobile performance.
const renderer = new THREE.WebGLRenderer({ canvas, antialias: !LOW_END, preserveDrawingBuffer: false, powerPreference: LOW_END ? 'low-power' : 'high-performance' });
renderer.setPixelRatio(Math.min(devicePixelRatio, LOW_END ? 1 : 1.75));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

const MAX_ANISO = Math.min(renderer.capabilities.getMaxAnisotropy(), LOW_END ? 4 : 8);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(38, 1, 0.5, 400);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.06;
controls.minDistance = 6.5;  // ближе — чтобы рассмотреть фактуру фасада и крошку цоколя
controls.maxDistance = 29;   // остаёмся внутри лесного кольца — дом не перекрывается
controls.maxPolarAngle = Math.PI / 2 - 0.045;   // не даём уйти под землю
controls.minPolarAngle = 0.35;
// Свободное перемещение кадра: тянуть можно и по горизонтали, и по вертикали,
// чтобы подвести к нужному месту и приблизить фактуру.
controls.enablePan = true;
controls.screenSpacePanning = true;   // пан идёт в плоскости экрана — интуитивно вверх/вниз/вбок
controls.zoomToCursor = true;         // зум идёт К КУРСОРУ, а не к центру — целимся в фасад/цоколь

// ⚠️ На телефоне палец НЕ должен застревать в 3D-кадре.
// OrbitControls в конструкторе ставит канвасу инлайновый `touch-action: none` —
// после этого браузер не отдаёт виджету ни одного вертикального свайпа странице, и
// страница-хост перестаёт скроллиться, как только виджет занял экран (выглядит как
// «сайт сломался после блока с домом»). На тач-устройствах меняем на `pan-y`:
// вертикальный свайп = прокрутка страницы, горизонтальный = поворот дома,
// два пальца = зум. Делать это надо ПОСЛЕ создания OrbitControls — иначе перезатрёт.
if (matchMedia('(pointer: coarse)').matches) {
  renderer.domElement.style.touchAction = 'none';
  // Один палец вертикально = страница (жест ловим сами). Горизонталь на кадре —
  // поворот. Два пальца = зум и наклон. DOLLY_PAN на телефоне не нужен.
  controls.touches = { ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_ROTATE };
  controls.enablePan = false;
}

// На телефоне «Отправить заявку» переезжает из последней строки панели в ПОДВАЛ —
// красной кнопкой на виду. В строке её приходилось искать: панель больше не
// скроллится внутри, а высота у неё общая с 3D-кадром, поэтому лишняя строка с
// заголовком и пояснением стоила бы дому 50+ px.
// Переносим сам элемент, а не рисуем второй: два одинаковых id — это когда JS
// цепляется к первому и «кнопка есть, но мёртвая» (LESSONS, дубликаты id).
// Слушатель клика переезжает вместе с элементом, порядок вызовов не важен.
// (Раньше здесь кнопка заявки переезжала в подвал панели на мобильной. Отменено:
// строка «Получить консультацию» показывается целиком на всех экранах — см. index.html.)

// Прицел кадра — не в геометрический центр дома, а ЧУТЬ НИЖЕ: так в фокусе
// оказываются фасад и цоколь, где как раз показываем фактуру.
const HOME = { pos: new THREE.Vector3(12.6, 5.2, 19.6), target: new THREE.Vector3(0, 2.1, 0) };
camera.position.copy(HOME.pos);
controls.target.copy(HOME.target);

const sun = new THREE.DirectionalLight(0xffffff, 3);
sun.castShadow = true;
sun.shadow.mapSize.set(LOW_END ? 512 : 1024, LOW_END ? 512 : 1024);
sun.shadow.camera.left = -24;
sun.shadow.camera.right = 24;
sun.shadow.camera.top = 20;
sun.shadow.camera.bottom = -16;
sun.shadow.camera.near = 1;
sun.shadow.camera.far = 160;
sun.shadow.bias = -0.0006;
sun.shadow.normalBias = 0.035;
scene.add(sun, sun.target);

const hemi = new THREE.HemisphereLight(0xffffff, 0x444433, 0.6);
scene.add(hemi);

const materials = createMaterials();
const { root: house, ground } = buildHouse(materials);
scene.add(house, ground);

// У CircleGeometry UV нормированные, не метровые — задаём тайлинг вручную.
const grassTex = groundTexture(LOW_END ? 256 : 512, MAX_ANISO);
grassTex.repeat.set(26, 26);
materials.ground.map = grassTex;
materials.ground.needsUpdate = true;

// Деревья/камни строятся ПОСЛЕ первого кадра: дом появляется сразу, окружение
// доезжает следующим тиком. Раньше вся сцена собиралась до первого рендера, и на
// телефоне это была лишняя секунда на чёрном экране.
let planting = null, scenery = null, sceneryPending = false;
function buildScenery() {
  if (planting || sceneryPending) return;
  sceneryPending = true;
  import('./landscape.js?v=46').then(({ buildLandscape }) => {
    const l = buildLandscape({ lowEnd: LOW_END });
    planting = l.planting; scenery = l.scenery;
    scene.add(planting, scenery);
    applyLandscape();
    requestRender();
    if (window.__cfg) { window.__cfg.planting = planting; window.__cfg.scenery = scenery; }
  }).catch(() => { sceneryPending = false; });
}

// Фасадные светильники: включаются вместе со светом в окнах.
const wallLights = [-6.5, -2.6, 2.6, 6.2].map((x) => {
  const l = new THREE.PointLight(0xffc98f, 0, 7.5, 2);
  l.position.set(x, LEVELS.plinthTop + 2.3, DIM.W / 2 + 0.3);
  scene.add(l);
  return l;
});

const pmrem = new THREE.PMREMGenerator(renderer);
pmrem.compileEquirectangularShader();
const timeCache = new Map();   // пресет освещения → { небо, PMREM-окружение }

/* ---------- применение выбора ---------- */

// Последняя выбранная фракция каждого вида: вернулся к «Камешковой» — получил ту,
// на которой остановился, а не дефолтную. Без этого выбор в пикере терялся при
// переключении видов в ленте.
const lastByKind = {};

function applyFacade() {
  const def = FACADE_TEXTURES.find((t) => t.id === state.facadeTexture);
  lastByKind[def.kind] = def.id;
  const col = FACADE_COLORS.find((c) => c.id === state.facadeColor);
  const maps = facadeMaps(def, texSize, MAX_ANISO);

  const m = materials.facade;
  m.map = maps.map;
  m.normalMap = maps.normalMap;
  m.roughnessMap = maps.roughnessMap;
  m.normalScale.set(1.25, 1.25);
  m.color.set(col.hex);           // тонировка: альбедо почти белое, цвет умножается сверху
  m.needsUpdate = true;

  $('#facadeLabel').textContent = `${def.name} · ${col.name}`;
  requestRender();
}

function applyPlinth() {
  const art = PLINTH_TEXTURES.find((t) => t.id === state.plinthTexture);
  const maps = plinthMaps(art, texSize, MAX_ANISO);

  const m = materials.plinth;
  m.map = maps.map;
  m.normalMap = maps.normalMap;
  m.roughnessMap = maps.roughnessMap;
  m.color.set(0xffffff);          // мозаику не тонируем — цвет задаёт сама крошка
  m.needsUpdate = true;

  $('#plinthLabel').textContent = `Мозаичная · ${art.name}`;
  requestRender();
}

function applyTime() {
  const p = TIME_PRESETS.find((t) => t.id === state.time);

  const el = (p.sun.el * Math.PI) / 180;
  const az = (p.sun.az * Math.PI) / 180;
  const R = 70;
  sun.position.set(R * Math.cos(el) * Math.sin(az), R * Math.sin(el), R * Math.cos(el) * Math.cos(az));
  sun.target.position.set(0, 2, 0);
  sun.color.set(p.sun.color);
  sun.intensity = p.sun.intensity;
  sun.castShadow = p.sun.intensity > 0.8;

  hemi.color.set(p.hemi.sky);
  hemi.groundColor.set(p.hemi.ground);
  hemi.intensity = p.hemi.intensity;

  materials.glass.emissiveIntensity = p.interior * 0.9;
  materials.lamp.emissiveIntensity = p.interior * 2.2;
  wallLights.forEach((l) => (l.intensity = p.interior * 7));
  renderer.toneMappingExposure = p.exposure;

  // Небо и окружение (PMREM) тяжёлые, а пресетов всего четыре — считаем каждый ОДИН раз
  // и кэшируем. Иначе переключение погоды каждый раз пересобирает env и подвешивает кадр.
  let env = timeCache.get(p.id);
  if (!env) {
    const sky = skyTexture(p, SKY_SIZE);
    env = { sky, rt: pmrem.fromEquirectangular(sky) };
    timeCache.set(p.id, env);
  }
  scene.background = env.sky;
  scene.fog = new THREE.Fog(new THREE.Color(p.sky.horizon), 42, 155);
  scene.environment = env.rt.texture;
  requestRender();
}

function applyLandscape() {
  if (!scenery) return;            // окружение ещё не построено — доедет своим тиком
  planting.visible = state.landscape !== 'none';
  scenery.visible = state.landscape === 'full';
  requestRender();
}

/* ---------- цвета по семействам ---------- */

const FAMILIES = [];
{
  const idx = {};
  for (const c of FACADE_COLORS) {
    if (!idx[c.fam]) { idx[c.fam] = { name: c.fam, items: [] }; FAMILIES.push(idx[c.fam]); }
    idx[c.fam].items.push(c);
  }
}

/* ---------- компактные ленты ---------- */

function texChip(def, thumb, active, onClick, label) {
  const b = document.createElement('button');
  b.className = 'chip' + (active ? ' is-active' : '');
  b.type = 'button';
  const img = document.createElement('span');
  img.className = 'chip__thumb';
  img.style.backgroundImage = `url(${thumb})`;
  const t = document.createElement('span');
  t.className = 'chip__label';
  t.textContent = label || def.name;
  b.append(img, t);
  b.addEventListener('click', onClick);
  return b;
}

// Ленты цвета (210 образцов) и цоколя (48) шире панели всегда. На тачскрине их листает
// сам браузер, а мышью на десктопе горизонтальной прокрутки нет — только shift+колесо,
// о котором никто не догадывается. Поэтому ленту можно ТЯНУТЬ левой кнопкой.
// Тач не трогаем: там нативная прокрутка инерционнее любой самодельной.
function dragScroll(el) {
  let id = null, x0 = 0, left0 = 0, far = 0, held = false;
  el.addEventListener('pointerdown', (e) => {
    if (e.pointerType !== 'mouse' || e.button !== 0) return;
    if (el.scrollWidth <= el.clientWidth) return;      // тянуть нечего
    id = e.pointerId; x0 = e.clientX; left0 = el.scrollLeft; far = 0; held = false;
  });
  el.addEventListener('pointermove', (e) => {
    if (e.pointerId !== id) return;
    const dx = e.clientX - x0;
    far = Math.max(far, Math.abs(dx));
    if (far <= 3) return;                              // дрожь руки — это ещё клик
    // Захват нужен, чтобы курсор мог уехать за пределы ленты и лента продолжала тянуться.
    // ⚠️ Он НЕ обязателен и обязан быть в try: setPointerCapture бросает NotFoundError,
    // если указателя с таким id уже нет в системе. Без try исключение убивало обработчик
    // ровно перед строкой прокрутки — лента не двигалась вообще (поймано на замере).
    if (!held) {
      held = true;
      try { el.setPointerCapture(id); } catch (err) { /* тянем без захвата */ }
      el.classList.add('is-grabbing');
    }
    el.scrollLeft = left0 - dx;
    e.preventDefault();
  });
  const end = (e) => {
    if (e.pointerId !== id) return;
    try { if (el.hasPointerCapture(id)) el.releasePointerCapture(id); } catch (err) { /* уже отпущен */ }
    el.classList.remove('is-grabbing');
    id = null; held = false;
    // После протяжки браузер всё равно шлёт click по образцу, на котором отпустили
    // кнопку, — без этого «пролистал ленту» превращалось бы в «выбрал случайный цвет».
    if (far > 3) {
      el.addEventListener('click', (ev) => { ev.stopPropagation(); ev.preventDefault(); },
                          { capture: true, once: true });
    }
  };
  el.addEventListener('pointerup', end);
  el.addEventListener('pointercancel', end);
}

function colorSwatch(c, active, onClick, cls = 'sw') {
  const b = document.createElement('button');
  b.className = cls + (active ? ' is-active' : '');
  b.type = 'button';
  b.style.setProperty('--c', c.hex);
  b.title = `${c.name} · ${c.hex}`;
  b.setAttribute('aria-label', c.name);
  b.addEventListener('click', onClick);
  return b;
}

// Образец в пикере с ПОДПИСЬЮ: у Ceresit цвета различаются номером внутри коллекции
// («Atlantic 3» vs «Atlantic 4»), по одному квадратику их не различить.
function colorSwatchLabeled(c, onClick) {
  const b = document.createElement('button');
  b.className = 'pk-cell';
  b.type = 'button';
  b.title = `${c.name} · ${c.hex}`;
  // «Sahara 3» → «3»: название коллекции стоит заголовком над рядом, дублировать незачем
  const short = c.fam && c.name.indexOf(c.fam) === 0 ? c.name.slice(c.fam.length).trim() : c.name;
  const swatch = document.createElement('span');
  swatch.className = 'pk-cell__c';
  swatch.style.setProperty('--c', c.hex);
  const label = document.createElement('span');
  label.className = 'pk-cell__n';
  label.textContent = short || c.name;
  b.append(swatch, label);
  b.addEventListener('click', onClick);
  return b;
}

// Карточка цвета для режима «только цвет»: образец, название и надбавка за колеровку.
function colorCard(c, onClick) {
  const b = document.createElement('button');
  b.className = 'cc';
  b.type = 'button';
  b.title = `${c.name} · ${c.hex}`;
  const price = COLOR_PRICES[c.id];
  const swatch = document.createElement('span');
  swatch.className = 'cc__sw';
  swatch.style.setProperty('--c', c.hex);
  const info = document.createElement('span');
  info.className = 'cc__t';
  const name = document.createElement('b');
  name.textContent = c.name;
  const amount = document.createElement('i');
  amount.textContent = price ? `+${Number(price).toLocaleString('ru-RU')} \u20BD` : 'цена по запросу';
  if (!price) amount.className = 'cc__no';
  info.append(name, amount);
  b.append(swatch, info);
  b.addEventListener('click', onClick);
  return b;
}

/* Прокрутить активный образец к центру ленты — ТОЛЬКО по горизонтали и ТОЛЬКО
 * внутри самой ленты.
 *
 * ⚠️ scrollIntoView здесь применять нельзя, даже с block:'nearest'. Он поднимается
 * по ВСЕМ прокручиваемым предкам, а виджет живёт в <iframe> — цепочка предков
 * уходит за границу кадра, в родительскую страницу. Из-за этого главная при
 * загрузке сама уезжала вниз к блоку подбора цвета (~1270 px): человек обновлял
 * страницу и вместо баннера видел конфигуратор. Поймано 27.08.2026.
 *
 * Считаем через getBoundingClientRect, а не offsetLeft: лента не обязана быть
 * offsetParent для образца, и на вложенной разметке offsetLeft соврал бы. */
function scrollActiveIntoView(wrap) {
  const a = wrap.querySelector('.is-active');
  if (!a) return;
  const wr = wrap.getBoundingClientRect();
  const ar = a.getBoundingClientRect();
  wrap.scrollLeft += (ar.left - wr.left) - (wr.width - ar.width) / 2;
}

// Превью-плитки дорогие (canvas + toDataURL). Раньше вся панель пересобиралась на КАЖДЫЙ
// клик — 48 мозаик + 5 фактур рисовались заново и подвешивали вкладку. Теперь каждое
// превью считается ОДИН раз и кэшируется; один размер для ленты и для пикера — CSS масштабирует.
const THUMB = LOW_END ? 80 : 160;
const thumbCache = new Map();
function facadeThumbC(def) {
  const k = 'f:' + def.id;
  if (!thumbCache.has(k)) thumbCache.set(k, facadeThumb(def, THUMB));
  return thumbCache.get(k);
}
function plinthThumbC(art) {
  const k = 'p:' + art.id;
  if (!thumbCache.has(k)) thumbCache.set(k, plinthThumb(art, THUMB));
  return thumbCache.get(k);
}

// Превью рисуем ТОЛЬКО когда образец реально попал в кадр. Мозаик 48 штук, каждая —
// canvas + toDataURL; на старте это была заметная пауза до первого кадра, хотя в ленте
// одновременно видно 6–8 образцов. Остальные дорисовываются при прокрутке ленты.
const lazyIO = 'IntersectionObserver' in window
  ? new IntersectionObserver((entries) => {
      for (const e of entries) {
        if (!e.isIntersecting) continue;
        lazyIO.unobserve(e.target);
        // Each preview gets its own task so swiping and clicking can run
        // between procedural canvas jobs.
        if (e.target.__drawThumb) setTimeout(() => e.target.__drawThumb(), 0);
      }
    }, { rootMargin: '150px' })
  : null;

function lazyBg(el, make) {
  const draw = () => {
    el.style.backgroundImage = `url(${make()})`;
    el.removeAttribute('data-pending');   // снимаем «скелет»: превью готово
  };
  if (!lazyIO) { draw(); return; }        // нет IntersectionObserver — рисуем сразу
  el.dataset.pending = '';                // пока не нарисовано — мягкая пульсация вместо пустоты
  el.__drawThumb = draw;
  lazyIO.observe(el);
}

// Цоколь показываем как цвет фасада — маленькими образцами, только фон образца это
// текстура мозаики (крошку не сплющиваем в плоский цвет). Имя выбранного — в подписи строки.
function plinthSwatch(art, active, onClick, cls = 'sw') {
  const b = document.createElement('button');
  b.className = cls + (active ? ' is-active' : '');
  b.type = 'button';
  lazyBg(b, () => plinthThumbC(art));
  b.style.backgroundSize = 'cover';
  b.style.backgroundPosition = 'center';
  b.title = art.name;
  b.setAttribute('aria-label', art.name);
  b.addEventListener('click', onClick);
  return b;
}

// Мозаика тоже сгруппирована по семействам (Chile, Granada, Laos …) — как веер фасада.
const PLINTH_FAMILIES = [];
{
  const idx = {};
  for (const a of PLINTH_TEXTURES) {
    const fam = a.name.split(' ')[0];
    if (!idx[fam]) { idx[fam] = { name: fam, items: [] }; PLINTH_FAMILIES.push(idx[fam]); }
    idx[fam].items.push(a);
  }
}

function seg(label, onClick) {
  const b = document.createElement('button');
  b.className = 'seg';
  b.type = 'button';
  b.textContent = label;
  b.addEventListener('click', onClick);
  return b;
}

/* ---------- компактная панель: строим ОДИН раз, дальше только подсветка ---------- */

const refs = { facadeTex: [], facadeColor: [], plinth: [], time: [] };
let compactBuilt = false;

function buildCompact() {
  const mk = (b, id) => { b.dataset.id = id; return b; };

  // Витрина фактур: три вида + «Все фактуры». Фракции живут в пикере.
  // dataset.id тут — ВИД (koroed/kamesh/smooth), подсветка идёт по нему.
  refs.facadeTex = FACADE_KINDS.map((k) => {
    const def = FACADE_TEXTURES.find((t) => t.id === k.def) || FACADE_TEXTURES.find((t) => t.kind === k.kind);
    return mk(texChip(def, facadeThumbC(def), false, () => busy(() => {
      // если у этого вида уже выбрана фракция — не сбрасываем её на дефолтную
      const cur = FACADE_TEXTURES.find((t) => t.id === state.facadeTexture);
      state.facadeTexture = cur && cur.kind === k.kind ? cur.id : (lastByKind[k.kind] || k.def);
      applyFacade();
      syncActive();
    }, 'Готовим фактуру…'), k.name), k.kind);
  });
  // Пятой плитки «Все фактуры» тут больше нет — вход в полный список стоит ссылкой
  // в заголовке строки (data-open="facadeTex"), как у цвета и цоколя. Плитка занимала
  // место образца, и лента из-за неё не помещалась по ширине.
  $('#facadeTextures').replaceChildren(...refs.facadeTex);

  refs.facadeColor = FACADE_COLORS.map((c) => mk(
    COLOR_ONLY
      ? colorCard(c, () => { state.facadeColor = c.id; applyFacade(); syncActive(); })
      : colorSwatch(c, false, () => { state.facadeColor = c.id; applyFacade(); syncActive(); }),
    c.id));
  $('#facadeColors').replaceChildren(...refs.facadeColor);

  // Цоколь — образцами, как цвет фасада (фон образца = текстура мозаики).
  refs.plinth = PLINTH_TEXTURES.map((art) => mk(
    plinthSwatch(art, false,
      () => busy(() => { state.plinthTexture = art.id; applyPlinth(); syncActive(); }, 'Готовим мозаику…')), art.id));
  $('#plinthTextures').replaceChildren(...refs.plinth);

  refs.time = TIME_PRESETS.map((p) => mk(
    seg(p.name, () => busy(() => { state.time = p.id; applyTime(); syncActive(); }, 'Меняем освещение…')), p.id));
  $('#timePresets').replaceChildren(...refs.time);

  // Тяга мышью — на обеих лентах-каруселях. Фактуры теперь сетка, там нечего тянуть,
  // но обработчик сам проверяет scrollWidth и молчит.
  document.querySelectorAll('.strip').forEach(dragScroll);

  compactBuilt = true;
}

function markActive(list, cur) {
  list.forEach((b) => b.classList.toggle('is-active', b.dataset.id === cur));
}

// лёгкое обновление: только классы активности, без пересборки DOM и превью
function syncActive() {
  if (!compactBuilt) buildCompact();
  // в ленте фактур подсвечиваем ВИД, а не конкретную фракцию — фракция видна в подписи строки
  const curTex = FACADE_TEXTURES.find((t) => t.id === state.facadeTexture);
  markActive(refs.facadeTex, curTex ? curTex.kind : '');
  markActive(refs.facadeColor, state.facadeColor);
  markActive(refs.plinth, state.plinthTexture);
  markActive(refs.time, state.time);
  scrollActiveIntoView($('#facadeColors'));
  scrollActiveIntoView($('#plinthTextures'));
  writeURL();
  reportChange();   // сайт-хозяин узнаёт о выборе сразу, без опроса
}

/* ---------- пикер (drill-down: назад / подтвердить) ---------- */

const picker = $('#picker');
const pickerBody = $('#pickerBody');

// какой пикер открыт, что было выбрано на момент открытия (для «Назад» = отмена),
// и кнопки текущего пикера — чтобы подсвечивать выбор без пересборки списка
let pickerKind = null;
let pickerPrev = null;
let pickerRefs = [];

// grid образцов по семействам (веер) — общий строитель для фасада и цоколя
function buildFamilyGrid(families, activeIdFn, swatchFn) {
  pickerRefs = [];
  pickerBody.replaceChildren(...families.map((fam) => {
    const box = document.createElement('div');
    box.className = 'fam';
    const h = document.createElement('p');
    h.className = 'fam__name';
    h.textContent = fam.name;
    const row = document.createElement('div');
    row.className = 'fam__row';
    row.append(...fam.items.map((item) => {
      const b = swatchFn(item);
      b.dataset.id = item.id;
      pickerRefs.push(b);
      return b;
    }));
    box.append(h, row);
    return box;
  }));
}

const PICKERS = {
  facadeColor: {
    title: 'Цвет фасада',
    get: () => state.facadeColor,
    name: () => (FACADE_COLORS.find((c) => c.id === state.facadeColor) || {}).name || '',
    set: (id) => { state.facadeColor = id; applyFacade(); },
    build: () => buildFamilyGrid(FAMILIES, () => state.facadeColor, (c) =>
      colorSwatchLabeled(c, () => { state.facadeColor = c.id; applyFacade(); pickPreview(); })),
  },
  facadeTex: {
    title: 'Фактура фасада',
    get: () => state.facadeTexture,
    name: () => (FACADE_TEXTURES.find((t) => t.id === state.facadeTexture) || {}).name || '',
    set: (id) => { state.facadeTexture = id; applyFacade(); },
    // В пикере фактуры разложены по видам: заголовок — вид, плитки — фракции в мм.
    build: () => buildKindTiles(),
  },
  plinth: {
    title: 'Цоколь — мозаика',
    get: () => state.plinthTexture,
    name: () => (PLINTH_TEXTURES.find((t) => t.id === state.plinthTexture) || {}).name || '',
    set: (id) => { state.plinthTexture = id; applyPlinth(); },
    // как цвет фасада: образцы по семействам (Chile, Granada, Laos …)
    build: () => buildFamilyGrid(PLINTH_FAMILIES, () => state.plinthTexture, (art) =>
      plinthSwatch(art, false, () => busy(() => { state.plinthTexture = art.id; applyPlinth(); pickPreview(); }, 'Готовим мозаику…'), 'pk-sw')),
  },
};

// Фактуры в пикере — по видам: «Короед» → 1,5 / 2 / 2,5 / 3 / 3,5 мм и так далее.
// Плитка подписана фракцией (`short`), потому что вид уже назван в заголовке группы.
function buildKindTiles() {
  pickerRefs = [];
  pickerBody.replaceChildren(...FACADE_KINDS.map((k) => {
    const box = document.createElement('div');
    box.className = 'fam';
    const h = document.createElement('p');
    h.className = 'fam__name';
    h.textContent = k.name;
    const grid = document.createElement('div');
    grid.className = 'tiles';
    grid.append(...FACADE_TEXTURES.filter((t) => t.kind === k.kind).map((def) => {
      const b = document.createElement('button');
      b.className = 'tile';
      b.type = 'button';
      b.dataset.id = def.id;
      const th = document.createElement('span');
      th.className = 'tile__thumb';
      th.style.backgroundImage = `url(${facadeThumbC(def)})`;
      const nm = document.createElement('span');
      nm.className = 'tile__name';
      nm.textContent = def.short || def.name;
      b.append(th, nm);
      b.addEventListener('click', () => busy(() => {
        state.facadeTexture = def.id;
        applyFacade();
        pickPreview();
      }, 'Готовим фактуру…'));
      pickerRefs.push(b);
      return b;
    }));
    box.append(h, grid);
    return box;
  }));
}

function buildTiles(list, thumbC, subFn, onPick) {
  pickerRefs = [];
  const grid = document.createElement('div');
  grid.className = 'tiles';
  grid.append(...list.map((item) => {
    const b = document.createElement('button');
    b.className = 'tile';
    b.type = 'button';
    b.dataset.id = item.id;
    const th = document.createElement('span');
    th.className = 'tile__thumb';
    th.style.backgroundImage = `url(${thumbC(item)})`;   // кэшированное превью — «приблизить фактуру»
    const nm = document.createElement('span');
    nm.className = 'tile__name';
    nm.textContent = item.name;
    const sub = document.createElement('span');
    sub.className = 'tile__sub';
    sub.textContent = subFn(item);
    b.append(th, nm, sub);
    b.addEventListener('click', () => onPick(item.id));
    pickerRefs.push(b);
    return b;
  }));
  pickerBody.replaceChildren(grid);
}

// после выбора в пикере — подсветка активной кнопки + пишем, что конкретно выбрано
function pickPreview() {
  const cfg = PICKERS[pickerKind];
  const cur = cfg.get();
  pickerRefs.forEach((b) => b.classList.toggle('is-active', b.dataset.id === cur));
  $('#pickerSub').textContent = 'Выбрано: ' + cfg.name();
  writeURL();
  reportChange();   // хост видит выбор сразу, ещё до «Подтвердить»
}

function openPicker(kind) {
  const cfg = PICKERS[kind];
  if (!cfg) return;
  pickerKind = kind;
  pickerPrev = cfg.get();
  $('#pickerTitle').textContent = cfg.title;
  cfg.build();
  pickPreview();                 // проставить активную кнопку + подпись «Выбрано: …»
  picker.classList.add('is-open');
  picker.setAttribute('aria-hidden', 'false');
  pickerBody.scrollTop = 0;
}

function closePicker(revert) {
  if (pickerKind && revert) {
    PICKERS[pickerKind].set(pickerPrev);   // «Назад» — вернуть, что было
  }
  picker.classList.remove('is-open');
  picker.setAttribute('aria-hidden', 'true');
  pickerKind = null;
  syncActive();
}

$('#pickerBack').addEventListener('click', () => closePicker(true));
$('#pickerConfirm').addEventListener('click', () => closePicker(false));
document.querySelectorAll('[data-open]').forEach((b) =>
  b.addEventListener('click', () => openPicker(b.dataset.open)));
addEventListener('keydown', (e) => { if (e.key === 'Escape' && pickerKind) closePicker(true); });

function refresh() {
  if (!compactBuilt) buildCompact();
  syncActive();
}



// Генерация текстуры 1024×1024 занимает заметное время — показываем состояние ожидания.
// Ждём кадр, чтобы курсор и блокировка панели успели отрисоваться, но обязательно
// со страховкой по таймеру: в скрытой вкладке или в свёрнутом iframe кадр не придёт
// никогда, и панель осталась бы с pointer-events: none навсегда.
// Показываем, что система думает: плашка со спиннером в углу кадра + курсор ожидания.
// Тяжёлая генерация текстур синхронная, поэтому запускаем её только через два кадра —
// иначе браузер не успевает нарисовать плашку и человек видит просто «залип».
function busy(fn, label) {
  const tag = document.getElementById('busyLabel');
  if (tag) tag.textContent = label || 'Считаем…';
  document.body.classList.add('is-busy');
  let done = false;
  const run = () => {
    if (done) return;
    done = true;
    fn();
    document.body.classList.remove('is-busy');
  };
  requestAnimationFrame(() => requestAnimationFrame(run));
  setTimeout(run, 80);
}

/* ---------- действия ---------- */

$('#btnReset').addEventListener('click', () => {
  camera.position.copy(HOME.pos);
  controls.target.copy(HOME.target);
  controls.update();
});

// Прямоугольник со скруглением (ctx.roundRect есть не везде — рисуем сами).
function roundRectPath(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

$('#btnShot').addEventListener('click', () => {
  renderer.render(scene, camera);
  const src = renderer.domElement;                 // кадр в реальных пикселях (с pixelRatio)
  const W = src.width, H = src.height;

  const tex = FACADE_TEXTURES.find((t) => t.id === state.facadeTexture);
  const col = FACADE_COLORS.find((c) => c.id === state.facadeColor);
  const art = PLINTH_TEXTURES.find((t) => t.id === state.plinthTexture);

  // Подпись прямо на картинке: тип штукатурки + цвет фасада и цоколь.
  const s = W / 1600;                               // масштаб подписи от ширины кадра
  const barH = Math.round(104 * s);
  const pad = Math.round(28 * s);
  const out = document.createElement('canvas');
  out.width = W;
  out.height = H + barH;
  const g = out.getContext('2d');

  g.drawImage(src, 0, 0);
  g.fillStyle = '#12151b';                          // плашка подписи
  g.fillRect(0, H, W, barH);
  g.fillStyle = 'rgba(216,185,138,0.9)';            // акцентная линия сверху плашки
  g.fillRect(0, H, W, Math.max(2, Math.round(2 * s)));

  // образец цвета фасада
  const sw = Math.round(barH * 0.46);
  const swY = H + (barH - sw) / 2;
  roundRectPath(g, pad, swY, sw, sw, Math.round(7 * s));
  g.fillStyle = col.hex;
  g.fill();
  g.lineWidth = Math.max(1, Math.round(s));
  g.strokeStyle = 'rgba(255,255,255,0.25)';
  g.stroke();

  // две строки подписи
  const tx = pad + sw + Math.round(20 * s);
  g.textBaseline = 'middle';
  g.textAlign = 'left';
  g.fillStyle = '#f1f4f8';
  g.font = `700 ${Math.round(30 * s)}px ui-sans-serif, -apple-system, "Segoe UI", Arial, sans-serif`;
  g.fillText(`Фасад: ${tex.name} · ${col.name}`, tx, H + barH * 0.37);
  g.fillStyle = '#aeb6c1';
  g.font = `500 ${Math.round(24 * s)}px ui-sans-serif, -apple-system, "Segoe UI", Arial, sans-serif`;
  g.fillText(`Цоколь: Мозаичная штукатурка · ${art.name}`, tx, H + barH * 0.69);

  // бренд справа
  g.textAlign = 'right';
  g.fillStyle = 'rgba(255,255,255,0.42)';
  g.font = `600 ${Math.round(22 * s)}px ui-sans-serif, Arial, sans-serif`;
  g.fillText('СТРОЙМА', W - pad, H + barH / 2);

  // имя файла — реальными названиями, без запрещённых в файловой системе символов
  const safe = (v) => String(v).replace(/[\/\\:*?"<>|]+/g, '').replace(/\s+/g, ' ').trim();
  const filename = `Ceresit — ${safe(tex.name)}, ${safe(col.name)} · цоколь ${safe(art.name)}.png`;

  const a = document.createElement('a');
  a.download = filename;
  a.href = out.toDataURL('image/png');
  a.click();
});

$('#btnLink').addEventListener('click', async (e) => {
  writeURL();
  try {
    await navigator.clipboard.writeText(location.href);
    toast(e.target, 'Ссылка скопирована');
  } catch {
    toast(e.target, 'Скопируйте адрес из строки браузера');
  }
});

function toast(el, text) {
  const prev = el.textContent;
  el.textContent = text;
  setTimeout(() => (el.textContent = prev), 1600);
}

/* ---------- встраивание в сайт ---------- */

// Виджет умеет жить в iframe на чужой странице. Наружу уходят два сообщения:
//   facade-configurator:size   — какой высоты виджет (нужно в мобильной раскладке)
//   facade-configurator:change — что выбрал посетитель (можно подставить в заявку)
const embedded = window.parent !== window;

function postToHost(type, payload) {
  if (!embedded) return;
  window.parent.postMessage({ type: `facade-configurator:${type}`, ...payload }, location.origin);
}

let lastSize = '';
function reportSize() {
  const stacked = matchMedia('(max-width: 900px)').matches;
  const height = stacked ? Math.ceil(document.documentElement.scrollHeight) : null;
  const key = `${stacked}:${height}`;
  if (key === lastSize) return;
  lastSize = key;
  postToHost('size', { mode: stacked ? 'stacked' : 'side', height });
}

// Во встроенном режиме хост показывает форму. Если виджет открыт отдельной
// ссылкой, ведём на ту же форму сайта и переносим текущий выбор через URL.
$('#btnLead')?.addEventListener('click', () => {
  if (!embedded) {
    const url = new URL('/color-selection/', location.origin);
    const selected = {
      f: state.facadeTexture,
      c: state.facadeColor,
      p: state.plinthTexture,
      t: state.time,
      l: state.landscape,
    };
    for (const [key, value] of Object.entries(selected)) url.searchParams.set(key, value);
    url.searchParams.set('request', '1');
    url.hash = 'colorRequest';
    location.assign(url.href);
    return;
  }
  firstReport = false;            // жмёт «заявку» — значит отправляет то, что на экране
  reportChange();                 // сначала отдаём актуальный выбор
  postToHost('request', {});
});

// Самый первый отчёт уходит на старте, когда человек ещё ничего не выбирал, — он помечен
// initial. Хост по нему заполняет скрытые поля заявки, но НЕ показывает плашку «Ваш выбор»:
// иначе она висит на странице сразу, будто выбор уже сделан.
let firstReport = true;

// Колесо мыши из iframe наружу само не выходит. На главной (s=page):
// над домом — зум OrbitControls (не перехватываем), над палитрой и кнопками —
// страница. В пикере «Все цвета» крутится свой список; горизонталь ленты
// (shift / deltaX) остаётся ленте.
if (embedded && new URLSearchParams(location.search).get('s') === 'page') {
  document.documentElement.classList.add('is-page');
  document.body.classList.add('is-page');
  addEventListener('wheel', (e) => {
    if (e.target.closest('.stage, .frame, #view')) return;
    if (document.querySelector('.picker.is-open') && e.target.closest('.picker')) return;
    const onHStrip = e.target.closest('.strip, .ckPlinthRow');
    if (onHStrip && (e.shiftKey || Math.abs(e.deltaX) > Math.abs(e.deltaY))) return;
    postToHost('scroll', { dy: e.deltaY });
    e.preventDefault();
  }, { passive: false });
}

// Палец в iframe до страницы-хозяина сам не доходит. Только на главной (s=page):
// вертикаль — хосту, иначе OrbitControls крутит камеру вместе со scrollBy.
// На товаре (?mode=color) этот обработчик НЕ вешаем: там палитра должна скроллиться
// внутри виджета, а не листать карточку товара.
if (embedded && new URLSearchParams(location.search).get('s') === 'page') {
  let sx = 0, sy = 0, lastY = 0, mode = null;
  const SLOP = 10;
  const inPicker = () => !!document.querySelector('.picker.is-open');

  addEventListener('touchstart', (e) => {
    if (e.touches.length !== 1 || inPicker()) { mode = 'skip'; return; }
    sx = e.touches[0].clientX;
    sy = lastY = e.touches[0].clientY;
    mode = null;
  }, { passive: true, capture: true });

  addEventListener('touchmove', (e) => {
    if (mode === 'skip' || e.touches.length !== 1 || inPicker()) return;
    const x = e.touches[0].clientX;
    const y = e.touches[0].clientY;
    if (mode === null) {
      const adx = Math.abs(x - sx), ady = Math.abs(y - sy);
      if (adx < SLOP && ady < SLOP) return;
      const onHStrip = !!e.target.closest('.strip, .ckPlinthRow');
      const onView = !!e.target.closest('#view');
      mode = ((onHStrip || onView) && adx > ady) ? 'self' : 'page';
    }
    if (mode !== 'page') return;
    postToHost('scroll', { dy: lastY - y });
    lastY = y;
    e.preventDefault();
    e.stopPropagation();
  }, { passive: false, capture: true });

  addEventListener('touchend', () => { mode = null; }, { passive: true, capture: true });
  addEventListener('touchcancel', () => { mode = null; }, { passive: true, capture: true });
}

function reportChange() {
  const col = FACADE_COLORS.find((c) => c.id === state.facadeColor);
  const tex = FACADE_TEXTURES.find((t) => t.id === state.facadeTexture);
  const art = PLINTH_TEXTURES.find((t) => t.id === state.plinthTexture);
  const initial = firstReport;
  firstReport = false;
  postToHost('change', {
    initial,
    state: { ...state },
    // цвет и надбавка отдельными полями: сайт показывает их в кнопке подтверждения
    color: col.name,
    colorId: col.id,
    hex: col.hex,
    price: COLOR_PRICES[col.id] != null ? Number(COLOR_PRICES[col.id]) : null,
    label: {
      facade: `${tex.name}, ${col.name} (${col.hex})`,
      plinth: `Мозаичная штукатурка, ${art.name}`,
    },
    url: location.href,
  });
}

// Хост может запросить состояние после загрузки iframe: это страхует передачу
// выбора, если самый первый postMessage ушёл до установки обработчика у хоста.
if (embedded) {
  addEventListener('message', (event) => {
    if (event.source !== window.parent || event.origin !== location.origin) return;
    if (event.data?.type === 'facade-configurator:get-state') reportChange();
  });
}

if (embedded) {
  new ResizeObserver(reportSize).observe(document.body);
  addEventListener('resize', reportSize);
}

/* ---------- цикл ---------- */

let onScreen = true;
new IntersectionObserver(([e]) => {
  onScreen = e.isIntersecting;
  if (onScreen) requestRender();
}, { threshold: 0.01 })
  .observe(document.querySelector('.frame'));

// Кадр больше не 16:9 — на десктопе он растянут на всю высоту сцены, а на мобильном
// это широкая полоса сверху. Поэтому держим постоянным ГОРИЗОНТАЛЬНЫЙ угол обзора:
// у более узкого кадра вертикальный угол расширяется, дом остаётся в тех же границах
// по ширине, а лишняя высота уходит в небо и передний план. Если считать наоборот
// (фиксировать вертикальный угол, как было при жёстком 16:9), высокий кадр обрезал бы
// дом по бокам — именно это и вылезло, когда кадр стал занимать всю высоту.
const REF_ASPECT = 16 / 9, BASE_FOV = 38;
let lastWidth = 0, lastHeight = 0;

function resize() {
  const w = canvas.clientWidth, h = canvas.clientHeight;
  if (w > 0 && h > 0 && (w !== lastWidth || h !== lastHeight)) {
    lastWidth = w;
    lastHeight = h;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.fov = camera.aspect < REF_ASPECT
      ? THREE.MathUtils.radToDeg(
          2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(BASE_FOV) / 2) * (REF_ASPECT / camera.aspect)))
      : BASE_FOV;
    camera.updateProjectionMatrix();
  }
}

let framePending = false;
function requestRender() {
  if (framePending) return;
  framePending = true;
  requestAnimationFrame(tick);
}

function tick() {
  framePending = false;
  if (!onScreen || document.hidden) return;
  resize();
  controls.update();
  renderer.render(scene, camera);
}
controls.addEventListener('change', requestRender);
addEventListener('resize', requestRender);
document.addEventListener('visibilitychange', () => {
  if (!document.hidden) requestRender();
});

/* ---------- старт ---------- */

applyTime();
applyFacade();
applyPlinth();
requestRender();
reportSize();

$('#loader').classList.add('is-hidden');
window.__cfgReady = true;   // сигнал сторожу в index.html: старт прошёл
window.__cfgBootMs = Math.round(performance.now());

// Панель и деревья — ПОСЛЕ первого кадра. Превью четырёх фактур раньше держали
// чёрный экран ещё сотни миллисекунд после того, как дом уже был готов.
function afterFirstFrame() {
  refresh();
  buildScenery();
  const up = () => {
    if (texSize >= TEX_FULL) return;
    texSize = TEX_FULL;
    applyFacade();
    applyPlinth();
  };
  if ('requestIdleCallback' in window) requestIdleCallback(up, { timeout: 900 });
  else setTimeout(up, 180);
}
requestAnimationFrame(() => requestAnimationFrame(afterFirstFrame));
setTimeout(buildScenery, 500);

window.__cfg = {
  THREE, scene, camera, controls, renderer, materials, house, state,
  planting, scenery, applyFacade, applyPlinth, applyTime, applyLandscape,
};

console.info(
  '%cКонфигуратор фасада', 'font-weight:700',
  `\nФасад: ${FACADE_COLORS.length} цветов, ${FAMILIES.length} семейств · ${FACADE_TEXTURES.length} фактур`,
  `\nЦоколь: ${PLINTH_TEXTURES.length} артикулов мозаики`,
  `\nГабариты: ${DIM.L}×${DIM.W} м`
);

/* ---------- включение режима «только цвет» ---------- */
if (COLOR_ONLY) {
  document.body.classList.add('is-colorOnly');

  // Сразу открываем экран выбора цвета фасада: дом слева, палитра по коллекциям
  // справа. Это готовый экран виджета — второй список городить не нужно.
  openPicker('facadeColor');
  const back = $('#pickerBack');
  if (back) back.style.display = 'none';   // возвращаться некуда: это единственный экран

  /* Лента цоколя под палитрой: человек прикидывает, как выбранный цвет фасада
     смотрится с цоколем. Прокручивается по горизонтали, как ленты на главной.
     ВАЖНО: цоколь здесь только для примера — в заказ и в цену он не попадает,
     поэтому рядом стоит пояснение. */
  const pickerEl = $('#picker');
  const footEl = document.querySelector('.picker__foot');
  if (pickerEl && footEl) {
    const box = document.createElement('div');
    box.className = 'ckPlinth';
    box.innerHTML = '<div class="ckPlinthHead">'
      + '<span>Цоколь — для примера</span>'
      + '<button type="button" class="ckInfo" aria-label="Пояснение" '
      + 'title="Цвет цоколя подбирается только для наглядности: в заказ и в стоимость он не входит">i</button>'
      + '</div><div class="ckPlinthRow" id="ckPlinthRow"></div>';
    pickerEl.insertBefore(box, footEl);

    const row = box.querySelector('#ckPlinthRow');
    row.append(...PLINTH_TEXTURES.map((art) => {
      const b = plinthSwatch(art, art.id === state.plinthTexture,
        () => busy(() => {
          state.plinthTexture = art.id;
          applyPlinth();
          row.querySelectorAll('.ckPl').forEach((x) => x.classList.remove('is-active'));
          b.classList.add('is-active');
        }, 'Готовим мозаику…'), 'ckPl');
      return b;
    }));
  }

  // Подвал пикера: что выбрано, сколько стоит и подтверждение. Клик по образцу —
  // это уже выбор (дом перекрашивается сразу), кнопка лишь закрывает окно с результатом.
  const foot2 = document.querySelector('.picker__foot');
  if (foot2) {
    foot2.innerHTML = '<div class="ckFoot">'
      + '<div class="ckPick"><b id="ckName">—</b><span id="ckPrice"></span></div>'
      + '<div class="ckBtns">'
      + '<button type="button" class="ckGhost" id="ckNone">Без колеровки</button>'
      + '<button type="button" class="ckOk" id="ckOk">Подтвердить</button>'
      + '</div></div>';

    const paint = () => {
      const c = FACADE_COLORS.find((x) => x.id === state.facadeColor);
      if (!c) return;
      const pr = COLOR_PRICES[c.id];
      $('#ckName').textContent = c.name;
      $('#ckPrice').textContent = pr ? '+' + Number(pr).toLocaleString('ru-RU') + ' \u20BD' : 'цена по запросу';
    };
    paint();
    pickerBody.addEventListener('click', () => setTimeout(paint, 0));

    $('#ckOk').addEventListener('click', () => {
      const c = FACADE_COLORS.find((x) => x.id === state.facadeColor);
      if (!c) return;
      postToHost('pick', {
        colorId: c.id, color: c.name, hex: c.hex,
        price: COLOR_PRICES[c.id] != null ? Number(COLOR_PRICES[c.id]) : null,
      });
    });
    $('#ckNone').addEventListener('click', () => postToHost('pick', { clear: true }));
  }
  // Кнопка подтверждения: отдаёт хосту выбранный цвет и его цену.
  const foot = document.querySelector('.panel__foot');
  if (foot) {
    const ok = document.createElement('button');
    ok.className = 'btn btn--ok';
    ok.type = 'button';
    ok.id = 'btnPick';
    ok.textContent = 'Подтвердить выбор цвета';
    ok.addEventListener('click', () => {
      const c = FACADE_COLORS.find((x) => x.id === state.facadeColor);
      if (!c) return;
      postToHost('pick', {
        colorId: c.id,
        color: c.name,
        hex: c.hex,
        price: COLOR_PRICES[c.id] != null ? Number(COLOR_PRICES[c.id]) : null,
      });
    });
    // ВАЖНО: не replaceChildren — ниже по файлу к #btnReset/#btnShot/#btnLink
    // привязываются обработчики, и без них падало «Cannot read properties of null».
    // Прячем их стилями (body.is-colorOnly), а кнопку подтверждения ставим первой.
    foot.prepend(ok);
  }
}
