# Patterns

Copy-ready implementations. Every one of these is load-bearing in a shipped site; the comments record *why*, because each replaced something that was subtly wrong.

---

## 1. Scroll-scrubbed motion

The core loop. Pose is a pure function of scroll offset, the loop reads scroll itself, and it stops completely when idle.

```js
const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;
// Touch scrolling is already continuous, so smoothing it only adds lag.
// A wheel arrives in coarse jumps and genuinely benefits.
const COARSE = matchMedia('(pointer: coarse)').matches;

let curr = 0, raf = null, last = 0, lastS = -1, idle = 0;

function tick(now) {
  // Read scroll HERE, every frame — not from the scroll event. iOS defers
  // those during momentum scrolling, exactly when motion is fastest, which
  // leaves an event-driven pose visibly dragging behind the page.
  const s  = window.pageYOffset || document.documentElement.scrollTop || 0;
  const dt = last ? Math.min((now - last) / 1000, 0.05) : 0.016;
  last = now;

  const moved = Math.abs(s - lastS) > 0.05;
  lastS = s;

  if (COARSE) curr = s;
  else curr += (s - curr) * (1 - Math.exp(-dt * 18));   // frame-rate independent
  if (Math.abs(s - curr) < 0.35) curr = s;              // snap when close

  pose(curr);

  // Idle out on unchanged frames, after a grace period so a throttled burst
  // of scrolling doesn't keep paying to spin the loop back up.
  if (!moved && s === curr) {
    if (++idle > 12) { raf = null; last = 0; idle = 0; return; }
  } else idle = 0;

  raf = requestAnimationFrame(tick);
}

function sync() {
  idle = 0;
  if (raf === null) { last = 0; raf = requestAnimationFrame(tick); }
}

pose(curr = lastS = window.pageYOffset);
if (!REDUCED) {
  addEventListener('scroll', sync, { passive: true });
  addEventListener('resize', () => { measure(); sync(); });
}
```

### Closed-form ballistics

```js
const G = 1500, T0 = 0.60, SPAN = 1.10;   // px/s², resting point, scrub length

// Randomness stored as UNIT values, velocities derived from them plus the
// measured frame size — so a resize re-fits the same throw instead of
// dealing a new one, and the motion fills any viewport.
function deal() {
  for (const c of items) {
    c.u = Math.random(); c.ua = Math.random() - 0.5;
    c.rx0 = Math.random() * 360; c.vrx = (Math.random() - 0.5) * 300;
  }
  derive();
}

function derive() {
  const { width: W, height: H } = stage.getBoundingClientRect();
  const half = items[0].el.offsetHeight / 2;
  // Solve for the speeds that put the softest throw just inside the bottom
  // edge and the hardest just inside the top, whatever the frame size.
  const base  = Y0 + 0.5 * G * T0 * T0;
  const spMin = (base + half + 18) / T0;
  const spMax = Math.max(spMin + 150, (base + H - half) / T0);
  for (const c of items) {
    const sp  = spMin + c.u * (spMax - spMin);
    const ang = (-90 + c.ua * 54) * Math.PI / 180;
    c.vx = Math.cos(ang) * sp * 0.62 * (W / 380);
    c.vy = Math.sin(ang) * sp;
  }
}

function pose(p) {
  const t = T0 + p * SPAN, fall = 0.5 * G * t * t;
  for (const c of items) {
    c.el.style.transform =
      `translate3d(${(c.x0 + c.vx*t).toFixed(1)}px,${(Y0 + c.vy*t + fall).toFixed(1)}px,${c.z}px)` +
      ` rotateX(${(c.rx0 + c.vrx*t).toFixed(1)}deg)`;
  }
}
```

### Parallax field (wrapping, page-wide)

```js
const wrap = (v, m) => ((v % m) + m) % m;

function pose(s) {
  for (const c of items) {
    // Drift up as the page goes down, recycling through a band taller than
    // the viewport so items are fully off-screen at both ends.
    const y = wrap(c.uy * SPAN - s * c.par, SPAN) - CH * 1.2;
    const x = c.ux * (W + CH) - CH * 0.5 + Math.sin(s * 0.0013 + c.ph) * 14;
    c.el.style.transform = `translate3d(${x}px,${y}px,${c.z}px) rotateY(${c.ry0 + s*c.sry}deg)`;
  }
}
// par and opacity both follow depth — that is what sells it as one space
// rather than a collage.  c.par = 0.14 + c.ud * 0.42
```

---

## 2. Pinning an element across sections

One persistent canvas whose on-screen position is a *uniform*, eased toward whichever anchor element is in view. Lets a centrepiece travel between sections without being rebuilt.

```html
<div class="slot" data-anchor data-fit="0.94" data-op="1" data-op-narrow="0.68"></div>
```

```js
// Track the anchor EXACTLY and carry a separate decaying offset. Easing the
// position itself leaves it a dozen frames behind during a scroll, which
// reads as stutter; this way scrolling is pixel-locked and only a change of
// anchor produces a glide.
const anchorEl = updateTargets();          // returns the winning anchor
if (anchorEl && anchorEl !== lastAnchor) {
  off.x = S.cx - S.tcx;                    // hand over current position
  off.y = S.cy - S.tcy;
  lastAnchor = anchorEl;
}
const decay = Math.exp(-dt * 3.6);
off.x *= decay; off.y *= decay;
S.cx = S.tcx + off.x;
S.cy = S.tcy + off.y;
```

Pick the anchor nearest the viewport centre, and fade out when the nearest one is far off-screen so you never pay for something nobody can see. Support a `data-op-narrow` so anchors behind text can ask to be dimmer when the layout collapses to one column.

---

## 3. Quality tiers (downgrade only)

```js
const TIERS = [
  { name:'low',  aa:1, bounces:2, disp:1, dpr:1.0 },
  { name:'mid',  aa:1, bounces:3, disp:3, dpr:1.5 },
  { name:'high', aa:2, bounces:4, disp:3, dpr:2.0 },
];

// Spare GPU headroom is not measurable from JS — a draw call returns long
// before the GPU has done the work, so "upgrade if fast" reads its own submit
// time as free and escalates on weak hardware. And a tier change resizes the
// backbuffer, so churning mid-scroll is visible. Pick from device signals,
// then only ever step DOWN, on real frame-to-frame time.
function initialTier() {
  const coarse = matchMedia('(pointer: coarse)').matches;
  const cores  = navigator.hardwareConcurrency || 4;
  const mem    = navigator.deviceMemory || 4;
  if (coarse && (cores <= 4 || mem <= 4)) return 0;
  if (coarse || cores <= 4 || innerWidth < 1024) return 1;
  return 2;
}

let acc = 0, frames = 0, cooldown = 0;
function watch(dt) {                        // dt from rAF, i.e. real frame cost
  cooldown -= dt; acc += dt; frames++;
  if (frames < 60) return;                  // skip the noisy first second
  const avg = acc / frames; acc = 0; frames = 0;
  if (cooldown > 0) return;
  if (avg > 22 && tier > 0) { cooldown = 3000; use(tier - 1); resize(); }
}
```

---

## 4. Touch gesture disambiguation

Required for any full-bleed draggable element. Without it the page cannot be scrolled where the element sits, and the bug is invisible on desktop.

```js
let pending = false, dragging = false, startX = 0, startY = 0;

addEventListener('pointerdown', e => {
  if (!overTarget(e.clientX, e.clientY)) return;
  startX = lastX = e.clientX; startY = lastY = e.clientY;
  if (e.pointerType === 'touch') { pending = true; return; }  // undecided
  beginDrag(e);
});

addEventListener('pointermove', e => {
  if (pending) {
    const dx = e.clientX - startX, dy = e.clientY - startY;
    // Mostly vertical: it's the page scrolling — release it for good.
    if (Math.abs(dy) > 10 && Math.abs(dy) >= Math.abs(dx)) { pending = false; return; }
    if (Math.abs(dx) > 8) { beginDrag(e); lastX = e.clientX; lastY = e.clientY; }
    else return;
  }
  if (!dragging) return;
  /* ...apply rotation... */
}, { passive: true });

// Only ever preventDefault once the gesture is genuinely ours.
document.addEventListener('touchmove', e => { if (dragging) e.preventDefault(); },
                          { passive: false });
```

### Trackball rotation

```js
// Screen y runs down and the camera looks along +z, so BOTH deltas invert to
// make the grabbed face follow the cursor. Getting this wrong feels subtly
// backwards without being obviously broken.
const rx = -dx * 0.0068, ry = -dy * 0.0068;
q = qNorm(qMul(qMul(qAxis(0,1,0, rx), qAxis(1,0,0, ry)), q));
```

---

## 5. Staged selection

```js
// Click selects (rotate, retint, feedback); the panel follows a beat later so
// the transition you built is actually seen rather than hidden behind it.
btn.addEventListener('click', () => {
  if (openPanel) return;
  selectFacet(btn, app, k);                       // immediate feedback
  clearTimeout(openTimer);
  openTimer = setTimeout(() => { openTimer = null; open(btn, app, k); },
                         REDUCED ? 0 : 340);
});

// Escape during the lead-in must cancel the queued panel AND release the
// selection, or you're left with a changed scene and no panel to explain it.
if (openPanel || openTimer) { closePanel(); return; }
```

Idle demo, so the interaction is discoverable without a hover — and stands down for good once touched:

```js
if (!openPanel && !dragging && !userTouched && !REDUCED && inView) {
  idleCycle += dt;
  if (idleCycle > 3400) { idleCycle = 0; present(names[i % 3], ks[i % 3]); i++; }
}
```

---

## 6. Word-by-word type reveal

Walk text nodes so inline markup survives, then stagger.

```js
function shatter(el) {
  if (el.dataset.done) return;
  el.dataset.done = '1';
  (function walk(node) {
    [...node.childNodes].forEach(kid => {
      if (kid.nodeType === 3) {
        const frag = document.createDocumentFragment();
        kid.textContent.split(/(\s+)/).forEach(tok => {
          if (!tok) return;
          if (/^\s+$/.test(tok)) { frag.append(document.createTextNode(tok)); return; }
          const w = document.createElement('span'); w.className = 'w';
          const i = document.createElement('span'); i.className = 'w-i';
          i.textContent = tok; w.append(i); frag.append(w);
        });
        node.replaceChild(frag, kid);
      } else if (kid.nodeType === 1 && kid.className !== 'w') walk(kid);
    });
  })(el);
  el.querySelectorAll('.w-i').forEach((n, i) => n.style.transitionDelay = `${i * 55}ms`);
}
```

```css
/* overflow:hidden clips descenders, hence the padding-bottom. */
.w   { display:inline-block; overflow:hidden; vertical-align:bottom; padding-bottom:0.08em; }
.w-i { display:inline-block; transform:translateY(112%); opacity:0;
       transition:transform 1000ms cubic-bezier(.16,1,.3,1), opacity 700ms ease; }
.is-in .w-i { transform:none; opacity:1; }
```

---

## 7. Chamfered edges

A cheap, distinctive alternative to rounded corners. Note `box-shadow` is *not* clipped by `clip-path`, so outer glows still work.

```css
.cut {
  clip-path: polygon(0 0, calc(100% - 26px) 0, 100% 26px,
                     100% 100%, 26px 100%, 0 calc(100% - 26px));
}
/* Leave a corner square if a close button has to sit in it. */
.cut-tr-square {
  clip-path: polygon(26px 0, 100% 0, 100% calc(100% - 26px),
                     calc(100% - 26px) 100%, 0 100%, 0 26px);
}
```

---

## 8. Convex polyhedron ray tracing

For a real faceted solid. The generalised slab method: walk every plane once, keep the furthest entry and nearest exit. Exact, and gives perfectly crisp edges an SDF would round off.

```glsl
// GLSL ES 1.00 forbids indexing a uniform array with a runtime value, so carry
// the per-facet payload OUT of the loop — reading uGlow[i] inside is legal,
// a later uGlow[hitIndex] is not.
bool hit(vec3 ro, vec3 rd, out float tIn, out vec3 nIn, out float gIn,
                           out float tOut, out vec3 nOut, out float gOut) {
  tIn = -1e20; tOut = 1e20;
  for (int i = 0; i < NP; i++) {
    if (i >= uN) break;                       // uN lets one shader serve tiers
    vec4 pl = uPlanes[i];
    float dn = dot(rd, pl.xyz);
    float sd = dot(ro, pl.xyz) - pl.w;
    if (abs(dn) < 1e-7) { if (sd > 0.0) return false; }
    else {
      float t = -sd / dn;
      if (dn < 0.0) { if (t > tIn)  { tIn  = t; nIn  = pl.xyz; gIn  = uGlow[i]; } }
      else          { if (t < tOut) { tOut = t; nOut = pl.xyz; gOut = uGlow[i]; } }
    }
  }
  return tOut > tIn && tOut > 0.0;
}
```

Free wireframe — the distance to the *second*-nearest plane goes to zero exactly along facet edges:

```glsl
float edgeDist(vec3 p) {
  float m1 = 1e9, m2 = 1e9;
  for (int i = 0; i < NP; i++) {
    if (i >= uN) break;
    float d = abs(dot(p, uPlanes[i].xyz) - uPlanes[i].w);
    if (d < m1) { m2 = m1; m1 = d; } else if (d < m2) { m2 = d; }
  }
  return m2;
}
```

Colour comes from **Beer–Lambert absorption over the internal path**, not from a tint — that is why it looks like a stone. Absorb the complement of the colour you want:

```js
const LOOKS = {
  ruby:  { absorb: [0.30, 3.40, 2.60] },   // eats green + blue
  green: { absorb: [3.60, 0.80, 3.00] },
  gold:  { absorb: [0.45, 1.45, 4.20] },
};
```

Verify the solid before trusting it:

```js
// Every normal unit length, and the origin strictly inside every half-space —
// otherwise the body is not closed and convex and the trace is meaningless.
planes.forEach(([x,y,z,d], i) => {
  if (Math.abs(Math.hypot(x,y,z) - 1) > 1e-6) throw new Error(`plane ${i} not unit`);
  if (d <= 0) throw new Error(`origin outside plane ${i}`);
});
```

Premultiplied output composites over the page background correctly:

```js
gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
// gl_FragColor = vec4(rgb * coverage, coverage) — do NOT multiply by coverage
// twice; averaging hit samples already premultiplies it.
```

---

## 9. Playing card pips

Real Anglo-American layouts. Assert the counts in a test — the whole point is that they are right.

```js
const L = 0.32, C = 0.5, R = 0.68;
const LAYOUTS = {
  'A':  [[C,0.50]],
  '2':  [[C,0.14],[C,0.86]],
  '3':  [[C,0.14],[C,0.50],[C,0.86]],
  '4':  [[L,0.14],[R,0.14],[L,0.86],[R,0.86]],
  '5':  [[L,0.14],[R,0.14],[C,0.50],[L,0.86],[R,0.86]],
  '6':  [[L,0.14],[R,0.14],[L,0.50],[R,0.50],[L,0.86],[R,0.86]],
  '7':  [[L,0.14],[R,0.14],[C,0.32],[L,0.50],[R,0.50],[L,0.86],[R,0.86]],
  '8':  [[L,0.14],[R,0.14],[C,0.32],[L,0.50],[R,0.50],[C,0.68],[L,0.86],[R,0.86]],
  '9':  [[L,0.14],[R,0.14],[L,0.38],[R,0.38],[C,0.50],[L,0.62],[R,0.62],[L,0.86],[R,0.86]],
  '10': [[L,0.14],[R,0.14],[C,0.26],[L,0.38],[R,0.38],[L,0.62],[R,0.62],[C,0.74],[L,0.86],[R,0.86]],
};
// J/Q/K deliberately absent — a monogram beats a court figure you can't draw.
// Pips below the midline get rotate(180deg), and the corner index repeats
// upside-down in the opposite corner, so the card reads from either end.
```

---

## 10. Double-sided 3D cards

```css
.scene { perspective: 1100px; overflow: hidden; }   /* clip HERE, not on an ancestor */
.card  { transform-style: preserve-3d; will-change: transform; }
.side  {
  position: absolute; inset: 0;
  backface-visibility: hidden;
  -webkit-backface-visibility: hidden;
  /* No overflow clipping — on some engines it interferes with backface culling. */
}
.back  { transform: rotateY(180deg); }
```

`overflow` other than `visible` forces `transform-style: flat` on **that** element, so keep `perspective` and `preserve-3d` on separate elements: clip on the perspective parent, preserve 3D on the child that holds the cards.

A die that snaps to quarter turns lands face-on and reads as a flat square. Put a **static viewing tilt** on an intermediate wrapper so two side faces stay visible.

---

## 11. Image assets

```python
from PIL import Image

# Find a baked-in status bar by measuring, not guessing: rows of pixels far
# from the background colour, grouped into bands. First band is the status
# bar, second is real content — crop between them.
bg = im.load()[4, 4]
ink = [sum(1 for x in range(0, w, 3)
           if sum(abs(a-b) for a,b in zip(im.load()[x,y], bg)) > 60) > 2
       for y in range(int(h * 0.25))]

im = im.crop((0, cut, w, h))
im = im.resize((672, round(h2 * 672 / w)), Image.LANCZOS)   # display box x DPR

im.save('shot.webp', 'WEBP', quality=85, method=6)          # photographic
im.save('flat.webp', 'WEBP', lossless=True, method=6)       # flat UI — beats PNG
```

Then **read the output back and look at it** before shipping.

```css
/* aspect-ratio on the box that HOLDS the image, never on a padded ancestor:
   with box-sizing:border-box the ratio describes the outer box, which is not
   the shape of the content box. And its own ratio removes the height:100%
   dependency that iOS Safari resolves unreliably. */
.frame       { padding: 7px; overflow: hidden; }
.frame-inner { position: relative; width: 100%; aspect-ratio: 660 / 1368; overflow: hidden; }
.frame-inner img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
```

---

## 12. Self-hosted fonts

```python
# Fetch with a browser UA to get woff2, keep only the latin subset.
css = urlopen(Request(GOOGLE_CSS_URL, headers={'User-Agent': 'Mozilla/5.0 ... Chrome/125'})).read()

# A variable font is often listed under SEVERAL discrete weights against ONE
# file. Taking those at face value leaves the other weights unmatched — merge
# them into a range.
weight = f'{min(weights)} {max(weights)}'
```

```js
// Confirm the file really carries the axes your CSS drives.
// fontTools: TTFont(path)['fvar'].axes  ->  wght 400..900, opsz 6..96
```

```html
<link rel="preload" href="/assets/fonts/display.woff2" as="font" type="font/woff2" crossorigin>
```

Vercel applies **every** matching `headers` rule and the **last** match wins for a given key — so `/assets/fonts/(.*)` must come *after* `/assets/(.*)`, or the general rule silently overrides it. Verify against the live response.
