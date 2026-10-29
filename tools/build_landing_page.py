"""Build web/index.html (the GitHub Pages landing page) from the live game data and art.

The page stays fully self-contained (art embedded as base64 data URIs, no external requests
besides the two fonts) so it renders identically when opened from disk.  It is regenerated --
never hand-edited -- because everything on it comes from the game itself:

- all 327 forms of the current roster (assets/scimon_database.json), each with its canonical
  display name, types, stats, ability, techniques, rarity and description,
- both views of every form (the 654 individually separated front/rear artworks from the named
  sprite pack, downscaled to 96px 64-colour palette thumbnails to keep the page light),
- the evolution chains (FAM) so starter cards and the database detail show the full
  Florabot -> Floravine -> Floratitan lines with their level thresholds,
- the eighteen-type chart and colours straight from the database,
- the previous canonical names (previous_name), surfaced in the database as "formerly logged
  as", documenting the display-name patch,
- an updated FEATURES section describing what shipped with this rebuild.

Run after any sprite / database change:

    python tools/build_landing_page.py
"""
import base64
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "web", "index.html")
THUMB = 96          # px, longest side of the embedded thumbnails
COLORS = 64         # palette size per thumbnail

# hero party strip: starters first, then striking final forms (display names, verified below)
HERO_NAMES = ["Florabot", "Pyrodrive", "Aquabit", "Floratitan", "Pyrodrake", "Aquarex",
              "Teslarch", "Quantarch", "Cryotitan", "Luminarch", "Hexacorvus", "Anemocerv",
              "Bathyray", "Tardiscope"]


def thumb_data_uri(path):
    from PIL import Image
    im = Image.open(path).convert("RGBA")
    im.thumbnail((THUMB, THUMB), Image.LANCZOS)
    q = im.quantize(colors=COLORS, method=Image.FASTOCTREE)
    buf = io.BytesIO()
    q.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def build_payloads():
    sys.path.insert(0, ROOT)
    from data import SPECIES, DB

    tech_name = {t["id"]: t["name"] for t in DB["techniques"]}
    fams = {f["id"]: {"name": f["name"], "chain": f["chain_ids"],
                      "levels": f["evolution_levels"], "starter": bool(f.get("starter_gift_eligible"))}
            for f in DB["families"]}
    starters = [fid for fid, f in fams.items() if f["starter"]]
    assert starters == ["florabot", "pyrodrive", "aquabit"], starters

    dex, img = [], {}
    recs = {r["id"]: r for r in DB["species"]}
    for sp in SPECIES.values():
        for view, rel in (("front", sp.front), ("back", sp.back)):
            path = os.path.join(ROOT, "assets", "scimon", rel)
            assert os.path.isfile(path), f"missing art: {rel}"
            img[f"{sp.id}-{view}"] = thumb_data_uri(path)
        seen, mv = set(), []
        for _lv, tid in sp.learnset:
            if tid not in seen and tid in tech_name:
                seen.add(tid)
                mv.append(tech_name[tid])
        dex.append({
            "id": sp.id, "no": sp.dex, "name": sp.name, "cls": sp.classification,
            "t": list(sp.types), "b": list(sp.base[:6]), "ab": sp.ability, "r": sp.rarity,
            "d": sp.desc, "fam": sp.family_id, "stage": sp.stage_ordinal,
            "evoTo": sp.evolves_to, "evoLv": sp.evolution_level,
            "prev": recs[sp.id].get("previous_name"),
            "mv": " · ".join(mv),
        })

    names = {m["name"]: m["id"] for m in dex}
    hero = [names[n] for n in HERO_NAMES]
    assert len(hero) == len(HERO_NAMES) and len(set(hero)) == len(hero)

    types = {t["id"]: t["color"] for t in DB["types"]}
    strong = {t["id"]: t["strong_against"] for t in DB["types"]}
    weak = {t["id"]: t["weak_against"] for t in DB["types"]}
    assert len(types) == 18, len(types)
    return {"IMG": img, "DEX": dex, "FAM": fams, "HERO": hero, "STARTERS": starters,
            "TC": types, "STRONG": strong, "WEAK": weak}


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>SCI-MON – The Scientific Monster RPG</title>
<meta name="description" content="SCI-MON is a monster-collecting RPG about autonomous machines: 327 forms across 109 evolution families, every one with its own front and rear artwork. Play it free in your browser.">
<meta property="og:title" content="SCI-MON – The Scientific Monster RPG">
<meta property="og:description" content="327 machines. 109 evolution families. Pick a starter, battle your rival Kael and explore Riven Town. Play free in your browser.">
<link rel="icon" href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAKsAAAEACAMAAAD7mnayAAAB/lBMVEVgX1zg9O9kZGPU4OEpKCWa2ePr3aBbW1vc6enf9/dq1OeqqqqWlpZcXFuplmFHOB6SdDLKrGGcnJxfTym1kDDqzWonJyednJgwrNjhtzUjJCNRtNLHupO8vcEiJSQ8PUCHeF49QUJ/+/u9wLz21jx+gH4+QD0okLQA//9/f/+zs/SZzNS35uk7O2VAPkBBQDtxuLg0xOFlZR9+gHzjsbHAvsQ/PkEAf38+QkIRdKEAf/9APUB/foB9gX1Mpb2Af4CBgX2+vsC/xMT/AADEvr7//78AAAADAwPzyUaGiYtJSks0NDRWV1a1trgpKSkWFRVnZ2i6ii/63Id0d3h2fIH+/v6np6j31m6XmJj51FH84446OjrGxsfzyDwwJRd8gYRsZVTEljJQRzCsikXO+vr4/PxGRkd+fn61lUzLqFAlGA1pWDHAjjGMeUqSiW3lvEv85FCpqamv+PnXtlO1///U1NR2ZDWppZf0/f4aGhqS5/B1dHSv6PA4ODjOpjf85HIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACDOjMiAAAAgHRSTlPv56Id4fr+DmWc/RWfXf7+//5f///+n/T7/2z9/v8c/v3+Av7//v/4AQIJBaMJ/1cD/guvEv+4AlH3AmO0R/v/T2p1AY8EAP7+/v7+/v/+/f7//v7/Bv///v/+BP///f/+//7++C7KA/7+/f7//v7//gT9/gP+/v9Oaf7X+m7//2rYGgYAACdNSURBVHja7Z2JX+LKtu/DDDIjSNva857O3uecO7z75nm4CRlIgjHMIqIISKPd2qLttvFfv2tVJRBGEUPfd+5nr97tVlvDl19WrVpVtarCsH87xvzB+gfrv33W9+//4+c/dLWbVf/75p89AV1f6RX14K/692Rl/Xc7Jzqr/3+q6xeXSfariw2ceDwOvaWv9DYDAT045zd11xfdTl3hYgHPzn3AtYqsuq7fe+4Dc35VX11XffQm9T/5A039C/lmM3Cys+NY8T7+pv/Z4znxs673M24d2wwskmA5XX8FKTccxgUdno0XO+ABK7G2dBc40L1/pqp6wOPxs8Ens/7yiw5SulxfvoC6X9jAxouTWxAa/O3kxYsXK+uKRCeorE7uksU5vrB+x+UOKPL5yaxf2Nt7aD/mF8C64UHAwOXGP7y4u/frwRVhg0TZu4Dhnn8a/kPzfmPj0nFr+c7yrH7PzkngFk136cD64n942OatYwM84KT5jHiFjRPuUkBHKnoZF1z41nH5YgPewS9Pb1s623Tce+7QoCmwgbuNuxOH4/7y/vLyDhryb8+Iky7dgXfJo/+mvwdFIPy5WPgIIgCra5U48AuLl0TbcASagcu7k8D95cbGBhA7bsed7YkGzRMvfH/LQjDw7Ox4LgN+D32lAPtlpZgFId/zAuBAUGL+25PLO9A0cAlCP48V7tLGxj24gR/vHbgphAZ8IWgGq7F+0ZH18vLk5BI++LEB4yf6n+/uyNvX9ZVZ/SeXnksP3ilosCd35G5dbkCKsbAZLGLFlunxXFJVXcDuwE8wmDvgH3XieSvrCu/68h6Q7/0OkAAa8eXGnb7IWxeyQn8YwHd7Ah5624SvWB36laZ+AgIA+HN0dWB0CjjgSicQFvGqLLBe+hc3g8V9LEZTYEWqYDD4z/jN2wBeFATwn5zga+gr6XoPN73JnlyeOAL63+P3oB+Ay35ZVddfaOTfuIO3bmQGuqsJ7Qt8FiK3Zwf+KbBSI9NdEEzvT5pN/23TSDwcl56Ny9s...">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=VT323&display=swap" rel="stylesheet">
<style>
/* Palette lifted from the game itself (settings.py / data.py): cream panels, ink text, teal frame, orange accent */
:root{--cream:#f3efd6;--cream2:#e6e0bf;--shade:#b8b48f;--ink:#2a2a33;--teal:#3d6763;--teal-d:#243f3c;--teal-dd:#162826;--orange:#d1552f;
--hp:#78c850;--stab:#4a8fd8;--gold:#e8c33a;
--px:"Press Start 2P",ui-monospace,Menlo,Consolas,monospace;--body:"VT323",ui-monospace,Menlo,Consolas,monospace}
*{box-sizing:border-box;margin:0}
html{scroll-behavior:smooth}
body{color:var(--cream);font:22px/1.35 var(--body);min-height:100vh;
background:
 linear-gradient(rgba(255,255,255,.025) 1px,transparent 1px) 0 0/32px 32px,
 linear-gradient(90deg,rgba(255,255,255,.025) 1px,transparent 1px) 0 0/32px 32px,
 radial-gradient(900px 480px at 50% -8%,#4f8a7f 0,transparent 70%),var(--teal-dd)}
a{color:var(--gold)}
.wrap{max-width:1040px;margin:0 auto;padding:0 20px}
/* pixel panel = the in-game dialogue box */
.panel{background:var(--cream);color:var(--ink);border:4px solid var(--ink);border-radius:4px;box-shadow:inset 0 0 0 3px var(--cream2),inset 0 0 0 5px var(--shade),6px 6px 0 rgba(0,0,0,.4)}
header.hero{text-align:center;padding:52px 0 24px}
.logo{font:clamp(28px,7vw,60px)/1.1 var(--px);letter-spacing:2px;color:var(--cream);text-shadow:0 4px 0 var(--orange),5px 8px 0 var(--ink),0 0 30px rgba(243,239,214,.25)}
.logo span{color:var(--orange);text-shadow:0 4px 0 var(--ink),5px 8px 0 var(--ink)}
.tag{margin:26px auto 0;max-width:680px;color:var(--cream2);font-size:clamp(20px,3vw,26px)}
.btn{display:inline-block;margin-top:26px;padding:16px 26px;font:14px var(--px);color:var(--cream);background:var(--orange);border:3px solid var(--ink);border-radius:4px;cursor:pointer;box-shadow:0 5px 0 var(--ink);text-decoration:none;transition:transform .1s,box-shadow .1s}
.btn:hover{transform:translateY(2px);box-shadow:0 3px 0 var(--ink)}
.btn:active{transform:translateY(5px);box-shadow:0 0 0 var(--ink)}
.btn.alt{background:var(--cream);color:var(--ink);margin:0}
.party{display:flex;flex-wrap:wrap;justify-content:center;align-items:flex-end;gap:10px 18px;margin-top:34px}
.party img{height:84px;width:auto;max-width:96px;object-fit:contain;image-rendering:pixelated;animation:bob 2.4s ease-in-out infinite;filter:drop-shadow(0 6px 0 rgba(0,0,0,.35))}
.party img:nth-child(2n){animation-delay:-.8s}.party img:nth-child(3n){animation-delay:-1.5s}
@keyframes bob{50%{transform:translateY(-9px)}}
@media (prefers-reduced-motion:reduce){.party img{animation:none}html{scroll-behavior:auto}}
h2{font:16px var(--px);color:var(--cream);margin:56px 0 18px;text-shadow:3px 3px 0 var(--ink);display:flex;align-items:center;gap:12px}
h2::before{content:"";width:14px;height:14px;background:var(--orange);border:3px solid var(--ink);flex:none}
.sub{color:var(--cream2);margin:-6px 0 20px}
/* type chips: same colours as the in-game label chips */
.chip{display:inline-block;font:9px/1 var(--px);color:#fff;padding:6px 7px 5px;border:2px solid var(--ink);border-radius:3px;margin-right:4px;text-shadow:1px 1px 0 rgba(0,0,0,.45);letter-spacing:.5px}
/* evolution chains (starter cards + database detail) */
.chain{display:flex;align-items:flex-start;justify-content:center;gap:6px;flex-wrap:wrap}
.chain .st{display:flex;flex-direction:column;align-items:center;gap:3px}
.chain img{height:58px;width:auto;max-width:76px;object-fit:contain;image-rendering:pixelated;animation:bob 2.6s ease-in-out infinite}
.chain .st:nth-child(2n) img{animation-delay:-.9s}
.chain .nm{font:7px/1.3 var(--px);color:var(--ink)}
.chain .arrow{align-self:center;font:12px var(--px);color:var(--teal);display:flex;flex-direction:column;align-items:center;gap:2px;padding:0 2px}
.chain .arrow small{font:7px var(--px);color:var(--orange)}
.chain.mini img{height:40px;max-width:56px}
.chain.mini .nm{font-size:6px}
/* starters */
.starters{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px}
.starter{padding:18px;text-align:center;display:flex;flex-direction:column;gap:10px}
.starter .stage{min-height:150px;display:flex;align-items:center;justify-content:center;border:3px solid var(--ink);border-radius:3px;background:linear-gradient(#cfe7c4 0 62%,#a9cf8f 62%);padding:14px 8px}
.starter .stage .chain .nm{color:var(--teal-d)}
.starter h3{font:14px var(--px);color:var(--ink)}
.starter .cls{color:var(--teal);font-size:21px}
.starter p.d{font-size:20px;line-height:1.2;min-height:48px}
.stats{display:grid;grid-template-columns:44px 1fr 28px;gap:4px 8px;align-items:center;text-align:left;font:8px var(--px)}
.bar{height:10px;background:var(--cream2);border:2px solid var(--ink);border-radius:2px;overflow:hidden}
.bar i{display:block;height:100%;background:var(--hp);width:0;transition:width .7s ease}
.bar i.s{background:var(--stab)}
.stats b{font-weight:400;color:var(--teal);text-align:right}
/* database */
.dexbar{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:0 0 14px}
.dexbar input,.dexbar select{font:20px var(--body);padding:8px 12px;border:3px solid var(--ink);border-radius:3px;background:var(--cream);color:var(--ink)}
.dexbar input{flex:1;min-width:200px}
.dexbar select{flex:0 0 auto}
.dexcount{font:9px var(--px);color:var(--cream2)}
.dex{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1fr);gap:20px;align-items:start}
.dexlist{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;align-content:start}
.cell{all:unset;box-sizing:border-box;cursor:pointer;background:var(--cream);color:var(--ink);border:3px solid var(--ink);border-radius:3px;padding:8px 6px 6px;text-align:center;box-shadow:0 4px 0 var(--ink);transition:transform .08s,box-shadow .08s;display:flex;flex-direction:column;align-items:center;gap:6px}
.cell:hover{transform:translateY(2px);box-shadow:0 2px 0 var(--ink)}
.cell:focus-visible{outline:3px solid var(--gold);outline-offset:2px}
.cell[aria-pressed=true]{background:var(--gold);transform:translateY(3px);box-shadow:0 1px 0 var(--ink)}
.cell img{height:64px;width:auto;max-width:88%;object-fit:contain;image-rendering:pixelated}
.cell small{font:8px/1.3 var(--px)}
.cell .no{font:8px var(--px);color:var(--teal)}
.detail{padding:20px;display:flex;flex-direction:column;gap:12px;position:sticky;top:16px}
.detail .top{display:flex;justify-content:space-between;align-items:center;font:10px var(--px);color:var(--teal)}
.detail .stage{height:190px;display:flex;align-items:flex-end;justify-content:center;border:3px solid var(--ink);border-radius:3px;background:linear-gradient(#cfe7c4 0 62%,#a9cf8f 62%);padding:10px;position:relative;overflow:hidden}
.detail .stage img{max-height:100%;max-width:80%;object-fit:contain;image-rendering:pixelated;position:relative;z-index:1}
.detail .stage::after{content:"";position:absolute;left:50%;bottom:8px;width:120px;height:14px;margin-left:-60px;background:rgba(0,0,0,.18);border-radius:50%}
.detail h3{font:16px var(--px)}
.detail .cls{color:var(--teal);font-size:22px;margin-top:-4px}
.detail .row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.detail .ab{font-size:20px}.detail .ab b{font-weight:400;color:var(--orange)}
.detail .prev{font-size:19px;color:var(--shade)}
.rar{font:8px var(--px);padding:5px 6px 4px;border:2px solid var(--ink);border-radius:3px;background:var(--cream2)}
.rar.rare{background:var(--gold)}.rar.uncommon{background:#9fd3a6}
.flip{font:9px var(--px);padding:8px 10px;background:var(--teal);color:var(--cream);border:3px solid var(--ink);border-radius:3px;cursor:pointer;box-shadow:0 3px 0 var(--ink);align-self:flex-start}
.flip:active{transform:translateY(3px);box-shadow:none}
.flip[hidden]{display:none}
.moves{font-size:19px;color:var(--teal)}
.evolbl{font:8px var(--px);color:var(--teal);margin-top:2px}
/* type & disc guide */
.typelist{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.tcell{all:unset;box-sizing:border-box;cursor:pointer;font:8px/1.4 var(--px);color:#fff;text-shadow:1px 1px 0 rgba(0,0,0,.45);border:2px solid var(--ink);border-radius:3px;padding:11px 8px 9px;box-shadow:0 3px 0 var(--ink);transition:transform .08s,box-shadow .08s}
.tcell:hover{transform:translateY(2px);box-shadow:0 1px 0 var(--ink)}
.tcell:focus-visible{outline:3px solid var(--gold);outline-offset:2px}
.tcell[aria-pressed=true]{outline:3px solid var(--orange);outline-offset:-3px;transform:translateY(3px);box-shadow:0 0 0 var(--ink)}
.trow{margin:0 0 12px}.trow b{font:8px var(--px);font-weight:400;color:var(--teal);display:block;margin-bottom:5px}
.trow .none{color:var(--shade);font-size:19px}
.gearlbl{font:8px var(--px);color:var(--teal);margin:14px 0 4px}
.gearline{display:flex;align-items:center;flex-wrap:wrap;gap:6px 12px;padding:9px 0;border-bottom:3px solid var(--cream2)}
.gearline:last-child{border:0}
.gearline .nm{color:var(--ink)}
.gearline .mut{color:var(--teal);font-size:19px}
/* console */
#play{padding:36px 0 0}
.console{background:var(--teal);border:4px solid var(--ink);border-radius:10px;padding:14px;box-shadow:inset 0 0 0 3px var(--teal-d),8px 8px 0 rgba(0,0,0,.45)}
.screen{position:relative;aspect-ratio:3/2;background:#05070d;border:4px solid var(--ink);border-radius:4px;overflow:hidden;touch-action:none;-webkit-user-select:none;user-select:none;-webkit-touch-callout:none}
.screen iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
.poster{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;text-align:center;padding:16px;background:linear-gradient(#cfe7c4 0 70%,#a9cf8f 70%);color:var(--ink)}
.poster h2{margin:0;color:var(--ink);text-shadow:none}.poster h2::before{display:none}
.poster p{color:var(--teal-d);max-width:480px}
.poster .mons{display:flex;gap:18px;align-items:flex-end;height:96px}
.poster .mons img{height:100%;width:auto;image-rendering:pixelated;animation:bob 2.4s ease-in-out infinite}
.poster .mons img:nth-child(2){animation-delay:-.9s}.poster .mons img:nth-child(3){animation-delay:-1.6s}
.poster .btn{margin-top:4px}
.cbar{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-top:14px;color:var(--cream2)}
.cbar .btn{padding:10px 14px;font-size:10px}
/* how to play */
table{width:100%;border-collapse:collapse}
td{padding:12px 16px;border-bottom:3px solid var(--cream2)}
tr:last-child td{border:0}
td:first-child{white-space:nowrap;width:1%}
kbd{font:10px var(--px);background:var(--cream2);color:var(--ink);border:2px solid var(--ink);border-bottom-width:4px;border-radius:4px;padding:6px 7px;margin-right:4px;display:inline-block}
.scroll{overflow-x:auto}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}
.card{padding:18px}
.card h3{font:11px/1.5 var(--px);color:var(--orange);margin-bottom:8px}
.card p{color:var(--ink)}
footer{margin-top:60px;padding:28px 0 40px;border-top:4px solid var(--ink);text-align:center;color:var(--cream2);font-size:19px}
.touch-only{display:none}
@media (pointer:coarse){.touch-only{display:table-row}.kbd-only{display:none}}
@media (max-width:760px){.dex{grid-template-columns:1fr}.detail{position:static;order:-1}}
@media (max-width:600px){body{font-size:20px}.btn{font-size:12px}}
body.playing{overflow:hidden;overscroll-behavior:none}
body.playing .wrap>*:not(#play){display:none}
body.playing .wrap,body.playing #play{padding:0;max-width:none}
body.playing .console{position:fixed;inset:0;z-index:50;width:100%;height:100vh;height:100dvh;border-radius:0;border:0;padding:env(safe-area-inset-top) env(safe-area-inset-right) 0 env(safe-area-inset-left);background:#000;display:flex;flex-direction:column;box-shadow:none}
body.playing .screen{aspect-ratio:auto;flex:1;border-radius:0;border:0}
body.playing .cbar{margin:0;padding:4px 8px calc(4px + env(safe-area-inset-bottom));justify-content:flex-end}
body.playing .cbar>span{display:none}
</style>
</head>
<body>
<div class="wrap">
  <header class="hero">
    <h1 class="logo">SCI<span>-</span>MON</h1>
    <p class="tag">The Scientific Monster RPG. 327 machines across 109 evolution families — every one with its own front and rear artwork. Pick a starter, face your rival Kael and explore Riven Town.</p>
    <a class="btn" href="#play">▶ PLAY NOW</a>
    <div class="party" id="party" aria-hidden="true"></div>
  </header>

  <h2>CHOOSE YOUR STARTER</h2>
  <p class="sub">Every family now grows through three named stages — the starter you pick is only the beginning.</p>
  <div class="starters" id="starters"></div>

  <section id="play">
    <h2>PLAY</h2>
    <div class="console">
      <div class="screen" id="screen">
        <div class="poster" id="poster">
          <div class="mons" id="posterMons"></div>
          <h2>READY?</h2>
          <p>Runs in your browser. First load downloads about a minute of game data, so hang tight.</p>
          <button class="btn" id="start" type="button">▶ START GAME</button>
        </div>
      </div>
      <div class="cbar">
        <span class="kbd-only">Progress saves automatically in this browser. Click the game once, then use the keyboard.</span><span class="touch-only" style="display:none">Progress saves automatically. Rotate your phone sideways for the biggest screen.</span>
        <button class="btn alt" id="fs" type="button">⛶ FULLSCREEN</button>
        <button class="btn alt" id="exit" type="button" hidden>✕ EXIT</button>
      </div>
    </div>
  </section>

  <h2>SCI-DATABASE</h2>
  <p class="sub">All 327 machines logged. Search by name or number, filter by type, tap an entry to read it — and flip every card to inspect its rear chassis.</p>
  <div class="dexbar">
    <input id="q" type="search" placeholder="search name or number…" aria-label="Search the database">
    <select id="tf" aria-label="Filter by type"><option value="">all types</option></select>
    <span class="dexcount" id="count"></span>
  </div>
  <div class="dex">
    <div class="dexlist" id="dexlist"></div>
    <div class="panel detail" id="detail" aria-live="polite"></div>
  </div>

  <h2>TYPE &amp; DISC GUIDE</h2>
  <p class="sub">All eighteen types: what each one hits hard, what it struggles against, and the discs and gear tuned for it. Tap a type.</p>
  <div class="dex">
    <div class="typelist" id="typelist"></div>
    <div class="panel detail" id="typedetail" aria-live="polite"></div>
  </div>

  <h2>DISCS &amp; TYPE GEAR</h2>
  <div class="panel scroll" id="gear" style="padding:4px 20px 14px"></div>

  <h2>HOW TO PLAY</h2>
  <div class="panel scroll"><table>
    <tr><td><kbd>←↑↓→</kbd><kbd>WASD</kbd></td><td>Move and navigate menus</td></tr>
    <tr><td><kbd>Enter</kbd><kbd>Space</kbd><kbd>Z</kbd></td><td>Confirm, talk, advance dialogue</td></tr>
    <tr><td><kbd>Esc</kbd><kbd>X</kbd></td><td>Go back or close</td></tr>
    <tr><td><kbd>H</kbd></td><td>Open the Type &amp; Disc guide in-game (matchups, discs, modules)</td></tr>
    <tr><td><kbd>I</kbd><kbd>Tab</kbd></td><td>Open the Pack</td></tr>
    <tr><td><kbd>M</kbd></td><td>Mute sound effects</td></tr>
    <tr class="touch-only"><td><kbd>TOUCH</kbd></td><td>On phones and tablets, an on-screen D-pad plus A (confirm), B (back) and PACK buttons appear. Tap any menu item directly.</td></tr>
  </table></div>
  <p style="margin-top:10px;color:var(--cream2)">Every menu also works with the mouse or by tapping. Touch controls appear automatically on mobile.</p>

  <h2>FEATURES</h2>
  <div class="grid">
    <div class="panel card"><h3>109 FAMILIES · 327 FORMS</h3><p>Every family evolves through three named stages — Voltling → Voltrix → Teslarch, Qubit → Qubiton → Quantarch. The Sci-Database logs them all, searchable and filterable.</p></div>
    <div class="panel card"><h3>ALL-NEW INDIVIDUAL SPRITES</h3><p>654 hand-separated artworks: a unique front <em>and</em> a true rear view for every form — rear sprites are drawn from behind, never mirrored. Clean cutouts, crisp at any size.</p></div>
    <div class="panel card"><h3>STAGE-AWARE BATTLE SIZING</h3><p>Combat scales each creature from its actual body, not a flat resize: first stages read small, finals tower — and floating lines hover above the battlefield with their shadows left behind.</p></div>
    <div class="panel card"><h3>CANONICAL NAMES, SAFE SAVES</h3><p>Forms carry their real names everywhere — battles, Sci-Database, evolution announcements ("Florabot evolved into Floravine!"). Old saves migrate automatically and player nicknames are always preserved.</p></div>
    <div class="panel card"><h3>COLLECT &amp; BATTLE</h3><p>Turn-based fights with eighteen types, techniques, capture modules, held cells and XP growth across all 327 forms.</p></div>
    <div class="panel card"><h3>EXPLORE RIVEN TOWN</h3><p>Shops, eight interiors, beaches and a cast of characters to meet — plus the Corrupt Bandits storyline beyond it.</p></div>
    <div class="panel card"><h3>SCI-DATABASE</h3><p>Log every machine you meet, manage your party, bag and held items across eight storage boxes.</p></div>
    <div class="panel card"><h3>PLAYS ANYWHERE</h3><p>Python &amp; Pygame compiled to WebAssembly (pygbag): keyboard, mouse or touch, fullscreen on phones, progress saved in the browser.</p></div>
  </div>

  <footer>SCI-MON · Python &amp; Pygame, running in your browser via WebAssembly (pygbag) · art: 654 individually separated front/rear views · generated by tools/build_landing_page.py</footer>
</div>
<script>
(function(){
  /* real game art (assets/scimon/*) and data (assets/scimon_database.json), embedded so this one
     file is self-contained.  Generated by tools/build_landing_page.py -- do not hand-edit. */
  var IMG=@@IMG@@;
  var TC=@@TC@@;
  var STRONG=@@STRONG@@;
  var WEAK=@@WEAK@@;
  var TYP=Object.keys(TC);
  /* 327 forms; b = [hp, power, defense, sp.power, sp.defense, speed] */
  var DEX=@@DEX@@;
  /* evolution chains: fam -> {name, chain ids, level thresholds, starter flag} */
  var FAM=@@FAM@@;
  var HERO=@@HERO@@, STARTERS=@@STARTERS@@;
  var LBL=["HP","PWR","DEF","SP.A","SP.D","SPD"];
  function $(s){return document.querySelector(s)}
  function pad(n){return String(n).padStart(3,"0")}
  function esc(s){return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;")}
  var BYID={};DEX.forEach(function(m){BYID[m.id]=m});
  function byId(id){return BYID[id]}
  function chips(m){return m.t.map(function(t){return '<span class="chip" style="background:'+(TC[t]||"#777")+'">'+t.toUpperCase()+'</span>'}).join("")}
  function stats(m){return '<div class="stats">'+m.b.map(function(v,i){return '<span>'+LBL[i]+'</span><div class="bar"><i class="'+(i==0?'':'s')+'" data-w="'+Math.min(100,v/70*100)+'"></i></div><b>'+v+'</b>'}).join("")+'</div>'}
  function grow(root){requestAnimationFrame(function(){requestAnimationFrame(function(){root.querySelectorAll(".bar i").forEach(function(i){i.style.width=i.dataset.w+"%"})})})}
  /* evolution chain strip: img + name per stage, ▶ + level threshold between stages */
  function chainHTML(fid,mini){
    var f=FAM[fid];if(!f)return"";
    var out=['<div class="chain'+(mini?' mini':'')+'">'];
    f.chain.forEach(function(sid,i){
      if(i)out.push('<span class="arrow">▶<small>Lv '+f.levels[i-1]+'</small></span>');
      var m=byId(sid);
      out.push('<span class="st"><img src="'+IMG[sid+"-front"]+'" alt="'+esc(m?m.name:sid)+'"><span class="nm">'+esc(m?m.name:sid)+'</span></span>');
    });
    out.push('</div>');
    return out.join("");
  }

  /* hero party + poster */
  $("#party").innerHTML=HERO.map(function(id){return '<img src="'+IMG[id+"-front"]+'" alt="">'}).join("");
  $("#posterMons").innerHTML=STARTERS.map(function(fid){return '<img src="'+IMG[fid+"-front"]+'" alt="">'}).join("");

  /* starters: one card per starter family, showing its full evolution line */
  $("#starters").innerHTML=STARTERS.map(function(fid){
    var f=FAM[fid],m=byId(f.chain[0]);
    return '<article class="panel starter"><div class="stage">'+chainHTML(fid)+'</div>'+
      '<h3>'+esc(f.name).toUpperCase()+'</h3><div class="cls">'+esc(m.cls)+'</div><div>'+chips(m)+'</div><p class="d">'+esc(m.d)+'</p>'+stats(m)+'</article>'}).join("");
  grow($("#starters"));

  /* database: searchable, type-filterable, every form with a flip to its rear view */
  var cur=null,side="front";
  $("#tf").innerHTML='<option value="">all types</option>'+TYP.map(function(t){return '<option value="'+t+'">'+t+'</option>'}).join("");
  function matches(m){
    var q=$("#q").value.trim().toLowerCase();
    if(q&&String(m.no)!==q&&m.name.toLowerCase().indexOf(q)<0&&m.id.indexOf(q)<0)return false;
    var t=$("#tf").value;
    if(t&&m.t.indexOf(t)<0)return false;
    return true;
  }
  function renderList(){
    var rows=DEX.filter(matches);
    $("#dexlist").innerHTML=rows.map(function(m){
      return '<button class="cell" type="button" data-id="'+m.id+'" aria-pressed="'+(m.id===cur)+'"><span class="no">No.'+pad(m.no)+'</span><img src="'+IMG[m.id+"-front"]+'" alt="" loading="lazy"><small>'+esc(m.name).toUpperCase()+'</small></button>'}).join("");
    $("#count").textContent=rows.length+" / "+DEX.length;
  }
  function show(id){
    cur=id;side="front";var m=byId(id);
    document.querySelectorAll(".cell").forEach(function(c){c.setAttribute("aria-pressed",c.dataset.id===id)});
    $("#detail").innerHTML='<div class="top"><span>No.'+pad(m.no)+'</span><span class="rar '+m.r+'">'+m.r.toUpperCase()+'</span></div>'+
      '<div class="stage"><img id="dimg" src="'+IMG[id+"-front"]+'" alt="'+esc(m.name)+'"></div>'+
      '<button class="flip" id="flip" type="button">↻ VIEW REAR</button>'+
      '<h3>'+esc(m.name).toUpperCase()+'</h3><div class="cls">'+esc(m.cls)+'</div><div class="row">'+chips(m)+'</div>'+
      '<div class="ab">Ability: <b>'+esc(m.ab)+'</b></div>'+
      (m.prev?'<div class="prev">Formerly logged as: '+esc(m.prev)+'</div>':'')+
      '<p>'+esc(m.d)+'</p>'+stats(m)+
      (m.mv?'<div class="moves">Techniques: '+esc(m.mv)+'</div>':'')+
      (m.stage<3?'<div class="evolbl">EVOLVES'+(m.evoLv?' AT LEVEL '+m.evoLv:'')+'</div>'+chainHTML(m.fam,true):'<div class="evolbl">FINAL STAGE</div>'+chainHTML(m.fam,true));
    grow($("#detail"));
    $("#flip").addEventListener("click",function(){
      side=side==="front"?"back":"front";
      $("#dimg").src=IMG[cur+"-"+side];
      $("#flip").textContent=side==="front"?"↻ VIEW REAR":"↻ VIEW FRONT"});
  }
  $("#q").addEventListener("input",renderList);
  $("#tf").addEventListener("change",renderList);
  $("#dexlist").addEventListener("click",function(e){var c=e.target.closest(".cell");if(c)show(c.dataset.id)});
  renderList();
  show("florabot");

  /* type & disc guide */
  $("#typelist").innerHTML=TYP.map(function(t){return '<button class="tcell" type="button" data-t="'+t+'" aria-pressed="false" style="background:'+TC[t]+'">'+t.toUpperCase()+'</button>'}).join("");
  function takesFrom(map,t){return TYP.filter(function(a){return (map[a]||[]).indexOf(t)>=0})}
  function tchips(list){return list.length?list.map(function(t){return '<span class="chip" style="background:'+TC[t]+'">'+t.toUpperCase()+'</span>'}).join(""):'<span class="none">- nothing -</span>'}
  function showType(t){
    document.querySelectorAll(".tcell").forEach(function(c){c.setAttribute("aria-pressed",c.dataset.t===t)});
    $("#typedetail").innerHTML='<div class="top"><span style="color:'+TC[t]+'">TYPE</span><span>SCANNER NOTES</span></div>'+
      '<h3 style="color:'+TC[t]+'">'+t.toUpperCase()+'</h3>'+
      '<div class="trow"><b>STRONG VS · DEALS 1.5x DAMAGE</b>'+tchips(STRONG[t]||[])+'</div>'+
      '<div class="trow"><b>WEAK VS · DEALS 0.6x DAMAGE</b>'+tchips(WEAK[t]||[])+'</div>'+
      '<div class="trow"><b>WEAK TO · TAKES 1.5x FROM</b>'+tchips(takesFrom(STRONG,t))+'</div>'+
      '<div class="trow"><b>RESISTS · TAKES 0.6x FROM</b>'+tchips(takesFrom(WEAK,t))+'</div>';
  }
  $("#typelist").addEventListener("click",function(e){var c=e.target.closest(".tcell");if(c)showType(c.dataset.t)});
  showType("Thermal");

  /* discs & gear: same catalogue as the game's CATALOG / MODULES */
  var GEAR=[
   {h:"MOVE DISCS · A GYM LEADER'S SIGNATURE TECHNIQUE - NO OTHER WAY TO LEARN IT",rows:[
     ["Verdant Disc","Teaches Verdant Storm (Botanic, POW 75) to a",["Botanic","Bio"]]]},
   {h:"CAPTURE MODULES · THROW ONE IN BATTLE TO CATCH - A MATCHED TYPE IS 1.7x MORE LIKELY TO STICK",rows:[
     ["Standard Module","General-purpose, works on",null],
     ["Cryo Module","Tuned for",["Thermal"]],
     ["Magnetic Module","Tuned for",["Metallic"]],
     ["Bio Capsule","Tuned for",["Bio"]]]},
   {h:"HELD CELLS · THE HOLDER'S TECHNIQUES OF THAT TYPE GET +20% POWER",rows:[
     ["Thermal Core","Boosts",["Thermal"]],
     ["Hydro Cell","Boosts",["Hydro"]],
     ["Bio Trellis","Boosts",["Botanic"]]]}
  ];
  $("#gear").innerHTML=GEAR.map(function(g){return '<div class="gearlbl">'+g.h+'</div>'+g.rows.map(function(r){
    return '<div class="gearline"><span class="nm">'+r[0]+'</span><span class="mut">'+r[1]+'</span>'+
      (r[2]||[]).map(function(t){return '<span class="chip" style="background:'+TC[t]+'">'+t.toUpperCase()+'</span>'}).join("")+
      (r[2]?"":'<span class="mut">type</span>')+'</div>'}).join("")}).join("");

  /* game launcher (unchanged behaviour) */
  var screen=$('#screen'),poster=$('#poster'),frame=null,fsBtn=$('#fs'),exitBtn=$('#exit');
  var touch=window.matchMedia&&matchMedia('(pointer:coarse)').matches;
  function start(){
    if(frame)return;
    frame=document.createElement('iframe');
    frame.src='play/';frame.title='SCI-MON game';
    frame.allow='autoplay; fullscreen; gamepad';frame.setAttribute('allowfullscreen','');
    screen.appendChild(frame);poster.style.display='none';
    frame.addEventListener('load',function(){frame.focus()});
  }
  function setPlaying(on){
    document.body.classList.toggle('playing',on);
    exitBtn.hidden=!on;fsBtn.hidden=on;
    if(!on&&document.fullscreenElement)document.exitFullscreen().catch(function(){});
  }
  function nativeFs(){
    var el=document.documentElement,rq=el.requestFullscreen||el.webkitRequestFullscreen;
    if(!rq)return;
    var p=rq.call(el);
    var lock=function(){try{screen.orientation.lock('landscape').catch(function(){})}catch(e){}};
    if(p&&p.then)p.then(lock).catch(function(){});
  }
  $('#start').addEventListener('click',function(){start();if(touch){setPlaying(true);nativeFs();}});
  fsBtn.addEventListener('click',function(){start();setPlaying(true);nativeFs();});
  exitBtn.addEventListener('click',function(){setPlaying(false)});
  document.addEventListener('fullscreenchange',function(){
    if(!document.fullscreenElement&&document.body.classList.contains('playing')&&!touch)setPlaying(false);
  });
  if(location.hash==='#autostart'){start();if(touch)setPlaying(true);}
})();
</script>
</body>
</html>
"""


def main():
    payloads = build_payloads()
    html = TEMPLATE
    for token, key in (("@@IMG@@", "IMG"), ("@@DEX@@", "DEX"), ("@@FAM@@", "FAM"), ("@@HERO@@", "HERO"),
                       ("@@STARTERS@@", "STARTERS"), ("@@TC@@", "TC"), ("@@STRONG@@", "STRONG"), ("@@WEAK@@", "WEAK")):
        html = html.replace(token, json.dumps(payloads[key], ensure_ascii=False, separators=(",", ":")))
    assert "@@" not in html, "unreplaced template token"
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    n = len(payloads["DEX"])
    print(f"wrote {os.path.relpath(OUT, ROOT)}: {n} forms, {len(payloads['IMG'])} embedded views, "
          f"{os.path.getsize(OUT) / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
