# Cosmic Cat vs the Earth Yarn Ball

Entry for make.fun **ai-excited-01** — "Make the AI judge excited".

A giant ginger cat leaps through deep space and bats planet Earth — wound up
like a ball of yarn — with its paws, while the yarn unravels in a sparkling
spiral. One clear focal point, a diagonal burst of motion, and a scale-twist
surprise: the whole planet as a toy. A "WOW!" speech bubble shouts at the
judge.

## How it works

`main.py` (Python 3, standard library only) draws the image procedurally
with a tiny built-in vector rasterizer (discs, ellipses, capsules, polygons,
bezier strokes) and a pure-stdlib PNG encoder. One fixed seed, no network,
no clock: two runs write byte-identical PNGs.

Run it:

```
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 -P -s main.py
```

Output: `out/entry.png` — 1024x1024 PNG, well under 1 MiB.

## License

MIT — see `LICENSE`.
