---
name: expressive-web
description: Build or redesign a website that has real visual character instead of the generic AI-generated look — portfolios, marketing sites, product pages. Use when the site needs a distinct identity, a memorable centrepiece, or genuine motion (scroll-driven, pointer-driven, canvas/WebGL/CSS-3D). Also use when someone says a design looks generic, templated, "like every other site", or like AI slop, or asks to add animation with personality. Covers concept-first design, the specific tells of the default AI aesthetic, motion that reads as intentional, and the performance, legibility and first-paint traps that sink this kind of work.
---

# Expressive web

Sites like this fail in one of two directions: they're tasteful and forgettable, or they're busy and unusable. The way through is a **single concrete idea** that generates every decision, executed with **one genuinely real thing** at its centre, with legibility and performance treated as measurable constraints rather than matters of taste.

## 1. Start with a concept, not a moodboard

Before any code, find one **concrete metaphor drawn from the subject itself** and write it in a sentence. Not a mood ("elegant, minimal, refined") — a thing.

> "The page is the interior of a ruby. Every app we build is a facet of it."

That sentence then decides everything downstream, and you should be able to trace each choice back to it:

| Derived from the concept | Not chosen for its own sake |
|---|---|
| Near-black ground with crimson light | "dark mode looks premium" |
| High-contrast Didone type | "a serif feels editorial" |
| Products as facets of one stone | "a card grid for the portfolio" |
| Copy about cutting, clarity, polish | generic craft language |

**Test:** if you can swap the concept out and the design still works unchanged, the design isn't expressing anything. Ask the user for the metaphor if it isn't obvious — a name, a product mechanic, a material, a process. It is almost always hiding in the subject.

**Ask before building.** Direction, centrepiece and intensity are taste calls with materially different work behind them. Present 2–3 concrete options with ASCII previews rather than guessing, then commit hard to the answer.

## 2. Actively avoid the default AI aesthetic

There is a recognisable house style that generated sites fall into. Name it so you can avoid it. If a design has three or more of these, it will read as templated:

- Cream / off-white background (`#FAF9F6`, `#FAF7F0`) with charcoal text
- Cormorant Garamond, Playfair Display, or Instrument Serif as the display face
- Hairline `1px` dividers between full-width sections
- Three-column feature grids with small line-art icons
- Rounded-corner cards with soft, even drop shadows
- Copy like "thoughtfully crafted", "we build with intention", "beautifully simple"
- Fade-up-on-scroll as the only motion, applied uniformly to everything
- A perfectly centred hero with a headline, a sub-line, and two buttons

None of these is bad alone. Together they are a fingerprint. Break the pattern deliberately: asymmetry, an unexpected type pairing, motion that responds to input rather than to scroll position alone, and copy with a specific point of view.

## 3. Make one thing genuinely real

The single highest-leverage decision. Pick **one** element and implement it for real rather than approximating it decoratively. Real means the thing behaves according to its actual rules:

- A gem: ray-trace a convex polyhedron cut to real proportions, with refraction, total internal reflection and wavelength-dependent absorption — not a radial gradient with sparkle PNGs.
- A thrown deck: evaluate real ballistics with per-card launch parameters — not a CSS keyframe loop.
- Playing cards: real pip layouts, so a four shows four and a ten shows ten, inverted below the midline like an actual card.

This is what makes a site impossible to mistake for a template, and it costs less than it sounds — a few hundred lines. Everything *else* should be restrained; one real centrepiece plus quiet surroundings beats five competing effects.

Get the underlying facts right. Look up real proportions, real layouts, real physical constants. Verify them numerically (see §7). Correctness is what reads as craft.

## 4. Motion the user drives

Autoplay animation is wallpaper; people stop seeing it in seconds. Motion tied to input feels like the page is responding to *them*.

Ranked, best first:

1. **Pointer-driven** — cursor as light source, drag to rotate, hover to reveal.
2. **Scroll-scrubbed** — position is a function of scroll offset, so scrolling back rewinds it.
3. **State-driven** — a click reveals, retints, reorients.
4. **Autoplay** — only for ambient texture, and only if it pauses off-screen.

**The critical technical rule: make the pose a pure function of the input, not an integrated simulation.**

```js
// GOOD — pure function of scroll. Reversible, cannot drift, no state.
function pose(s) {
  const t = T0 + s * SPAN;
  for (const c of cards) {
    c.el.style.transform =
      `translate3d(${c.x0 + c.vx*t}px, ${c.y0 + c.vy*t + 0.5*G*t*t}px, ${c.z}px)` +
      ` rotateX(${c.rx0 + c.vrx*t}deg)`;
  }
}

// BAD — integrates each frame. Accumulates error, cannot run backwards.
function frame(dt) { c.vy += G*dt; c.y += c.vy*dt; }
```

Closed-form gives exact reversibility, no drift however long the user scrubs, and a genuine idle state with zero work. **Reach for simulation only when the motion has no closed form** (collisions, springs settling, inertia after a fling).

### Interaction rules that matter

- **A hover should not change the whole scene.** Passing a cursor over something is not a decision. Hover = local affordance; click = commit. If a click both selects *and* opens a panel, the panel hides the transition you just built — stage it, ~300ms apart, with immediate feedback on the click so it still feels instant.
- **Give idle a job.** If an interaction isn't discoverable without a hover, cycle it slowly until the user touches it, then stand down permanently.
- **On touch, start gestures undecided.** A full-bleed draggable element that claims every touch and calls `preventDefault` makes the page unscrollable. Wait for the first move: mostly-vertical → release it to the page for good; mostly-horizontal → claim it. This is the single worst mobile bug in this genre and it is invisible on desktop.

## 5. Legibility is structural, not a judgement call

Bold decoration and readable text are not in tension if you separate them **structurally**. Two rules:

**Never put semi-transparent text over a moving background.** `rgba(255,255,255,0.66)` takes its colour from whatever happens to be behind it. Over a moving layer that is different every frame, and it is how a page like this quietly fails contrast. Flatten body colours to solid hex.

**Give text its own darker pocket, then let the decoration be bold.** A feathered dark wash — not a panel — lets the background stay expressive while text sits on a known backdrop:

```css
.veil { position: relative; }
.veil::before {
  content: ""; position: absolute; inset: -52px -56px; z-index: -1;
  pointer-events: none;
  --feather: 46px;
  background: rgba(7, 4, 12, 0.82);
  /* Fixed-distance feather, not a percentage: a percentage under-covers a
     tall block. Masking feathers the fill AND the blur together — without it
     the blur stops at a hard rectangle. */
  mask-image:
    linear-gradient(to right,  transparent, #000 var(--feather), #000 calc(100% - var(--feather)), transparent),
    linear-gradient(to bottom, transparent, #000 var(--feather), #000 calc(100% - var(--feather)), transparent);
  mask-composite: intersect;
  -webkit-mask-composite: source-in;
}
@media (min-width: 900px) and (hover: hover) {
  .veil::before { backdrop-filter: blur(8px); }   /* desktop only — see §6 */
}
```

Keep the contrast in the *fill*, so the blur is pure enhancement and its absence changes nothing legible.

**Compute the numbers; do not eyeball them.** Run `references/contrast.py` against your actual colours before choosing a decoration opacity. On one build this turned an assumed-fine 0.30 opacity into a measured **2.5:1** — a clear failure — and showed that with a veil the same decoration could go to 0.38 while text stayed at 7.4:1. Write the binding constraint into a comment so nobody raises it later.

## 6. Performance traps specific to this work

Every one of these was a real bug, not a hypothetical.

**Read scroll inside the frame loop, never from the event.** iOS defers `scroll` events during momentum scrolling — exactly when things move fastest — so an event-driven pose visibly drags behind the page.

```js
function tick(now) {
  const s = window.pageYOffset;    // read HERE, every frame
  ...
}
```

**Track the target exactly; ease only a separate offset.** Lerping the position itself every frame leaves the element permanently trailing the page, which reads as stutter. Pin it to the target and give it a decaying offset, so scrolling is pixel-locked and only a *change of target* produces a glide.

**Don't smooth touch input.** Touch scrolling is already continuous; a lerp only adds lag. Smooth wheel input, which arrives in coarse jumps. `matchMedia('(pointer: coarse)')`.

**`backdrop-filter` re-blurs whatever moves behind it, every frame.** Across several elements over a moving layer it will be the most expensive thing on the page. Desktop-only, and make sure a solid fill carries the contrast so mobile loses nothing that matters.

**`mix-blend-mode` forces everything beneath it to re-composite.** A grain overlay at `inset: -50%` costs four times the area for no benefit — it never moves. Use `inset: 0`, and drop blend modes entirely on mobile.

**You cannot measure GPU headroom from JS.** A draw call returns long before the GPU has finished, so "upgrade if fast" reads its own submit time as free and escalates on weak hardware. Pick a quality tier from device signals, then **only ever step down**, on real frame-to-frame time.

**Layer count is element count × faces.** A 3D card with a front and back is two composited layers. Twenty-six cards is fifty-two. Cut the count on mobile.

**Stop when idle.** Idle out after a few unchanged frames and cancel the rAF entirely. Pause on `visibilitychange` and when the element leaves the viewport.

## 7. Verify numerically; be honest about what you haven't seen

You usually cannot see the page. Compensate by checking what *is* checkable, and by being explicit about what isn't.

- **Compute geometry and physics before shipping.** Does the throw fit the frame at every breakpoint? Does the trajectory stay in view? Print a table.
- **Validate the maths of your own construction.** Confirm every plane normal is unit length and the origin is inside every half-space, so the solid really is closed and convex.
- **Look at images you generate.** Read a cropped or resized file back and actually look at it before shipping.
- **Syntax-check inline scripts** by extracting the last `<script>` block and running `node --check`.
- **Verify against the live response, not the config.** A cache header rule that looks right can be overridden by rule ordering.

State plainly what has not been verified. A headless browser on Linux is **not** a proxy for iOS Safari, and mobile is where this genre breaks. Ask the user to check the specific thing on the specific device — that is faster and more accurate than approximating it.

## 8. Accessibility as a constraint on the design

- **`prefers-reduced-motion` must produce a *designed* still state**, not a broken one. If the concept is a thrown deck, the reduced state is one frozen throw — often the best frame of the whole thing.
- **Interactive elements are real `<button>`s** with visible labels, so keyboard and screen-reader users get the same affordances. Decorative canvases get `aria-hidden`.
- **Content lives in the markup.** Panels and reveals are progressive enhancement, so the page is complete with JS disabled.
- **Escape closes; focus returns** to what opened it. Keep focus inside an open dialog.
- **Alt text describes what is actually on screen** — write it after looking at the image, not from the filename.

## 9. First paint and assets

**Kill the white flash** — three layers, in the order they take effect:

1. `<meta name="color-scheme" content="dark">` — the only signal the browser has before author CSS, and what decides the pre-paint canvas colour.
2. A tiny inline `<style>` setting the `html` background, before anything external. The canvas colour comes from `<html>`, not `<body>`.
3. **No render-blocking stylesheets in `<head>`.** An external stylesheet blocks first paint entirely; until it lands the browser shows its own white canvas.

Be honest about the floor: before the HTML response arrives there is no document, so nothing you write can colour that moment. Reducing it is a network problem.

**Self-host fonts.** Google Fonts costs two extra DNS+TLS handshakes to third-party origins before a glyph can arrive. Fetch the CSS with a browser user-agent, keep only the subsets you need, preload the faces used above the fold. Watch two traps: a variable font listed under several discrete weights needs a **weight range** or the other weights won't match, and confirm the file actually carries the axes your CSS drives (`fvar` via `fontTools`).

**Match format to content.** Photographic → lossy WebP (a 3.4 MB photo PNG became 54 KB). Flat UI → *lossless* WebP, which beat PNG at half the size. Size to the real display box × DPR, not the source. Crop baked-in status bars **out of the asset** rather than masking them with a matching colour — cropping needs no colour match and survives a palette change.

## 10. CSS gotchas that cost real debugging time

- **`overflow-y: auto` alone makes `overflow-x` compute to `auto`.** Per spec, when one axis is not `visible` and the other is, the visible one becomes `auto`. State both, or you get surprise horizontal panning.
- **Transformed elements count toward scrollable overflow.** An animation ending at `translateX(100%)` with `fill-mode: both` parks the element off to the side *permanently*, creating scrollable width forever.
- **`aspect-ratio` applies to the border box.** With `box-sizing: border-box` and padding, the ratio is not the shape of the content box — so an image inside will never match its frame. Put the ratio on the box that holds the thing.
- **Percentage heights against an aspect-ratio parent are unreliable on iOS Safari.** Give the child its own `aspect-ratio` instead of `height: 100%`, removing the dependency entirely.
- **`z-index: -1` on a `::before` escapes only as far as the nearest stacking context.** Useful for veils; check the ancestor actually creates one.
- **In a `preserve-3d` context, `z-index` is ignored** — paint order comes from 3D position.

## References

- `references/patterns.md` — copy-ready implementations: scroll-scrubbed pose loop, quality tiers, touch disambiguation, reveal choreography, the veil.
- `references/contrast.py` — run before choosing a decoration opacity. Prints text/background ratios and the maximum opacity that still clears AA.
