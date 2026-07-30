#!/usr/bin/env python3
"""Contrast checker for pages with a decorative layer behind the text.

Run this BEFORE choosing how bold the decoration can be. Eyeballing it fails:
on one build an assumed-fine 0.30 opacity measured 2.5:1 — a clear WCAG
failure — while a darker pocket behind the text let the same decoration go to
0.38 with body text at 7.4:1.

Two things this catches that a normal contrast checker will not:

  1. Semi-transparent text takes its colour from whatever is behind it. Over a
     moving layer that is different every frame. Pass text colours as SOLID
     hex; if yours are rgba, use --flatten to see what they resolve to.
  2. The worst case is not the page background — it is text sitting on the
     brightest decoration over the brightest part of the background.

Usage
-----
    python3 contrast.py
    python3 contrast.py --bg 0B0713 --wash 5A2E8C:0.42 --deco FBF6EA \
                        --text F4EEE2 C0B9AF ADA69D --veil 07040C:0.82
    python3 contrast.py --flatten F4EEE2:0.66 --bg 0B0713
"""
import argparse
import sys


def hex2rgb(h):
    h = h.lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    if len(h) != 6:
        raise ValueError(f'bad hex colour: {h!r}')
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def rgb2hex(c):
    return '#' + ''.join(f'{round(v):02X}' for v in c)


def _lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb):
    r, g, b = (_lin(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a, b):
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def over(fg, alpha, bg):
    """Composite fg at `alpha` over bg, in sRGB space as CSS does."""
    return [alpha * f + (1 - alpha) * b for f, b in zip(fg, bg)]


def parse_layer(s):
    """'RRGGBB:0.42' -> ([r,g,b], 0.42)"""
    if ':' in s:
        h, a = s.split(':', 1)
        return hex2rgb(h), float(a)
    return hex2rgb(s), 1.0


AA, AAA = 4.5, 7.0
LARGE_AA = 3.0          # >=24px, or >=18.66px bold


def verdict(r):
    if r >= AAA:
        return 'AAA '
    if r >= AA:
        return 'AA  '
    if r >= LARGE_AA:
        return 'lg  '     # passes only at >=24px, or >=18.66px bold
    return 'FAIL'


def main(argv=None):
    p = argparse.ArgumentParser(add_help=True)
    p.add_argument('--bg', default='0B0713', help='page background hex')
    p.add_argument('--wash', default='5A2E8C:0.42',
                   help='brightest overlay on the background, HEX:ALPHA')
    p.add_argument('--deco', default='FBF6EA',
                   help='decoration colour (card face, shape, image highlight)')
    p.add_argument('--text', nargs='+', default=['F4EEE2', 'C0B9AF', 'ADA69D'],
                   help='SOLID text colours, brightest first')
    p.add_argument('--veil', default=None,
                   help='darker pocket behind text, HEX:ALPHA (e.g. 07040C:0.82)')
    p.add_argument('--opacities', nargs='+', type=float,
                   default=[0.10, 0.15, 0.20, 0.25, 0.30, 0.38, 0.45])
    p.add_argument('--flatten', default=None,
                   help='resolve an rgba text colour to solid: HEX:ALPHA')
    a = p.parse_args(argv)

    bg = hex2rgb(a.bg)
    wash_c, wash_a = parse_layer(a.wash)
    worst_bg = over(wash_c, wash_a, bg)
    deco = hex2rgb(a.deco)
    texts = [(t.upper(), hex2rgb(t)) for t in a.text]

    if a.flatten:
        c, al = parse_layer(a.flatten)
        flat = over(c, al, bg)
        print(f'\nrgba({",".join(str(round(v)) for v in c)},{al}) over {rgb2hex(bg)}'
              f'  ->  {rgb2hex(flat)}')
        print('Use that solid value. Translucent text over a moving layer takes')
        print('its colour from whatever happens to be behind it.\n')
        return 0

    print(f'\npage bg      {rgb2hex(bg)}   L={luminance(bg):.4f}')
    print(f'+ wash       {rgb2hex(worst_bg)}   L={luminance(worst_bg):.4f}   <- worst case')
    print(f'decoration   {rgb2hex(deco)}')
    if a.veil:
        vc, va = parse_layer(a.veil)
        print(f'veil         {rgb2hex(vc)} @ {va}')
    print()

    hdr = 'deco  ' + ''.join(f'{n:>16}' for n, _ in texts) + '    deco vs page'
    print(hdr)
    print('-' * len(hdr))

    max_ok = None
    for op in a.opacities:
        card = over(deco, op, worst_bg)
        surface = over(*parse_layer(a.veil), card) if a.veil else card
        cells, ok = '', True
        for _, t in texts:
            r = ratio(t, surface)
            ok &= r >= AA
            flag = ' ' if r >= AA else '!'
            cells += f'   {flag}{r:5.2f} {verdict(r)}'
        vis = ratio(card, worst_bg)
        print(f'{op:4.2f}  {cells}         {vis:4.2f}:1')
        if ok:
            max_ok = op

    print()
    if max_ok is None:
        print('! No tested opacity clears AA for every text colour.')
        print('  Either add a veil behind the text (--veil 07040C:0.82) or')
        print('  brighten the dimmest text. A veil is usually the better move:')
        print('  it lets the decoration stay bold instead of fading it out.')
    else:
        print(f'Max decoration opacity clearing AA for all text: {max_ok:.2f}')
        if not a.veil:
            print('Adding a veil behind the text typically buys 2-3x more.')
    print('\n! = below AA (4.5:1) for normal-size text.')
    print('A decoration needs only ~1.2:1 against the page to be plainly visible,')
    print('so "visible" and "legible" are rarely actually in conflict.\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
