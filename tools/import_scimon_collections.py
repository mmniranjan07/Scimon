"""Import the Scimon Collection 01/02 "Front and Back" design atlases into the game's sprite set.

The collections ship as 9 front + 9 back atlas PNGs per collection (each atlas is a grid of
`rows x 3` cells -- one family per row, stages BABY / MIDDLE / FINAL left to right) plus a
FAMILY_STAGE_AND_VIEW_KEY.csv that maps every family/stage to its atlas, row and column.
The atlases are painted on an opaque gradient backdrop and some designs overflow their cell,
so a straight grid slice is not enough.  The importer therefore:

1. grows the background from the atlas borders (a region grow that follows the smooth
   gradient but stops at the creatures' outlines) and keys enclosed backdrop pockets,
2. labels the remaining content into connected components and hands every component to the
   cell it overlaps most (overflowing fins stay whole; designs that touch and merge are
   separated by a marker watershed; detached decorations that drifted into the wrong cell
   are re-homed by palette affinity to the design they belong to),
3. trims each design to its opaque bounding box, normalises the atlas' 253-capped alpha and
   downscales it (premultiplied, to keep the edges clean) onto the game's ~256 px canvas,
4. saves it under assets/scimon/<species>-front.png / -back.png, using the game's species
   ids: family -> <family>[-baby|-final][-front|-back].png.  Designs whose game species does
   not exist (e.g. babies of two-stage lines) are skipped and reported.

The three starter families (florabot / pyrodrive / aquabit) and the three earlier wild
families glacibit / qubit / voltling are not part of the collections and keep their art.
Battles pick the new back views up automatically through assets.back_path(); re-run any time:

    python tools/import_scimon_collections.py            # both collections -> assets/scimon/
    python tools/import_scimon_collections.py --qa DIR   # also write per-collection QA sheets

Needs pillow + scipy + numpy (requirements-dev.txt) and reads the game's species table.
"""
import argparse
import csv
import os
import re
import sys
from collections import defaultdict

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

COLLECTIONS = ("01", "02")
K3 = np.ones((3, 3), dtype=np.float32)          # 3x3 neighbourhood kernel
STAGE_SUFFIX = {"baby": "-baby", "middle": "", "final": "-final"}
CONNECT8 = np.ones((3, 3), dtype=np.uint8)      # 8-connectivity for component labelling


# --------------------------------------------------------------------------- collection key
def sheet_number(value):
    """'collection_2_sheet_07.png', 'C02_Sheet_07_FRONT.png' or '7' -> 7 (the two CSVs disagree)."""
    m = re.search(r"(\d+)\.png$", str(value).strip())
    if m:
        return int(m.group(1))
    return int(value)


def load_key(csv_path):
    """family -> {stage: (sheet, row, column)} from a FAMILY_STAGE_AND_VIEW_KEY.csv."""
    fams = defaultdict(dict)
    with open(csv_path, newline="") as f:
        for r in csv.DictReader(f):
            fams[r["family"].strip().lower()][r["stage"].strip().lower()] = (
                sheet_number(r["sheet"]), int(r["row"]) - 1, int(r["column"]) - 1)
    return fams


def rows_per_sheet(fams):
    rows = defaultdict(set)
    for stages in fams.values():
        for sheet, row, _col in stages.values():
            rows[sheet].add(row)
    return {s: max(rs) + 1 for s, rs in rows.items()}


# --------------------------------------------------------------------------- background removal
def _grow(rgb, seed, tol, max_iter=900):
    """Region-grow `seed` across pixels close to the average of their accepted neighbours:
    follows the smooth backdrop gradient, stops at the hard creature outlines."""
    known = seed.copy()
    for _ in range(max_iter):
        newly = ndimage.binary_dilation(known) & ~known
        if not newly.any():
            break
        cnt = ndimage.convolve(known.astype(np.float32), K3, mode="constant")
        model = np.stack([ndimage.convolve(np.where(known, rgb[:, :, c], np.float32(0.0)), K3, mode="constant")
                          for c in range(3)], axis=2) / np.maximum(cnt, 1)[..., None]
        accept = newly & (np.sqrt(((rgb - model) ** 2).sum(axis=2)) < tol)
        if not accept.any():
            break
        known |= accept
    return known


def background_mask(rgb, alpha, tol, pocket_tol):
    """True where the pixel belongs to the painted backdrop (gradient wash + enclosed pockets)."""
    h, w = alpha.shape
    seed = alpha < 128
    seed[0, :], seed[-1, :], seed[:, 0], seed[:, -1] = True, True, True, True
    # the bulk of the background comes from a quarter-scale grow (the gradient is smooth by nature)
    rgb_s = np.asarray(Image.fromarray(rgb.astype(np.uint8)).resize(
        (w // 4, h // 4), Image.BOX)).astype(np.float32)
    seed_s = np.asarray(Image.fromarray(seed.astype(np.uint8) * 255).resize(
        (w // 4, h // 4), Image.BOX)) > 127
    bg_s = _grow(rgb_s, seed_s, tol)
    bg = np.asarray(Image.fromarray(bg_s.astype(np.uint8) * 255).resize((w, h), Image.BILINEAR)) > 127
    bg |= seed
    # refine the boundary at full resolution with a TIGHTER tolerance: the bulk grow already
    # covered the smooth gradient, and a tight refine cannot tunnel through the soft edge of a
    # creature (which would sever tails / hollow out dark bodies)
    bg = _grow(rgb, bg, tol * 0.6, max_iter=64)
    # enclosed pockets (backdrop showing between fins / through gaps): key against a large-scale
    # model built only from the flooded background, then keep only pockets reachable from it
    filled = np.where(bg[..., None], rgb, np.float32(0.0))
    wsum = ndimage.gaussian_filter(bg.astype(np.float32), 25)[..., None]
    model = np.stack([ndimage.gaussian_filter(filled[:, :, c], 25) for c in range(3)],
                     axis=2) / np.maximum(wsum, 1e-3)
    d_model = np.sqrt(((rgb - model) ** 2).sum(axis=2))
    keyed = (~bg) & (d_model < pocket_tol) & (wsum[..., 0] > 0.05)
    bg = bg | ndimage.binary_propagation(bg, mask=bg | keyed)
    # dark designs on dark backdrops: the region grow tunnels through soft edges and pocket
    # keying eats the interior, leaving hollow shells with FRAGMENTED (dotted) outlines.  Heal
    # in groups: components within 6px of each other (i.e. one design's outline dashes) close
    # and fill TOGETHER, every filled pixel is given back, but pixels within 8px of a DIFFERENT
    # group are left alone so two designs can never bridge into one blob.  A solid silhouette
    # beats a hollow shell -- enclosed regions are filled regardless of colour, because in the
    # pale-on-pale cases colour cannot tell body from backdrop anyway.
    for _ in range(2):
        content = ~bg
        if not content.any():
            break
        dil = ndimage.binary_dilation(content, structure=np.ones((3, 3)), iterations=3)
        glab, gn = ndimage.label(dil, structure=CONNECT8)
        restore = np.zeros_like(bg)
        for g in range(1, gn + 1):
            gm = glab == g
            if gm.sum() < 3000:
                continue
            m = content & gm
            if m.sum() < 3000:
                continue
            filled = ndimage.binary_fill_holes(ndimage.binary_closing(m, structure=np.ones((11, 11))))
            cand = filled & ~content & bg
            if not cand.any():
                continue
            others = content & (glab != g)
            if others.any():
                cand &= ndimage.distance_transform_edt(~others) > 8
            restore |= cand
        if not restore.any():
            break
        bg &= ~restore
    # weld severed parts back on: the grow tunnels through the thin neck connecting a head,
    # tail or pair of legs to their body, and the severed piece then glues to whatever design
    # it touches.  A neck candidate = body-coloured keyed pixels bridging TWO components --
    # it is only welded when its own palette matches BOTH sides (a severed piece of the same
    # design); overlaps between two different designs stay un-welded.
    for _ in range(2):
        content = ~bg
        if not content.any():
            break
        lab_c, n_c = ndimage.label(content, structure=CONNECT8)
        if n_c == 0:
            break
        # vectorised per-component colour histograms (quantised 4x4x4)
        idx = (rgb[:, :, 0].astype(np.int32) >> 6) * 16 + (rgb[:, :, 1].astype(np.int32) >> 6) * 4 + (rgb[:, :, 2].astype(np.int32) >> 6)
        comb = np.where(content, lab_c - 1, -1) * 64 + np.where(content, idx, 0)
        hist = np.bincount(comb[comb >= 0].ravel(), minlength=n_c * 64).reshape(n_c, 64).astype(np.float32)
        hist /= np.maximum(hist.sum(axis=1, keepdims=True), 1.0)
        near = ndimage.binary_dilation(content, structure=np.ones((3, 3)), iterations=6)
        border = near & bg & (d_model > 18)
        if not border.any():
            break
        clab, cn = ndimage.label(ndimage.binary_dilation(border, structure=np.ones((3, 3))), structure=CONNECT8)
        restore = np.zeros_like(bg)
        for g in range(1, cn + 1):
            cluster = border & (clab == g)
            if cluster.sum() < 24:
                continue
            zone = ndimage.binary_dilation(cluster, structure=np.ones((3, 3)), iterations=8)
            touching = np.unique(lab_c[zone & content])
            touching = touching[touching > 0]
            if len(touching) < 2:
                continue
            hp = _histogram(rgb, cluster)
            if hp is None:
                continue
            sims = [1.0 - 0.5 * float(np.abs(hp - hist[t - 1]).sum()) for t in touching]
            if min(sims) > 0.5:
                restore |= cluster
        if not restore.any():
            break
        bg &= ~restore
    return bg


# --------------------------------------------------------------------------- cell assignment
def _cell_grid(shape, rows, cols):
    h, w = shape
    rr, cc = np.indices(shape)
    x_edges = [round(w * c / cols) for c in range(cols + 1)]
    y_edges = [round(h * r / rows) for r in range(rows + 1)]
    cell_of = np.full(shape, -1, dtype=np.int32)
    for row in range(rows):
        for col in range(cols):
            cell_of[(rr >= y_edges[row]) & (rr < y_edges[row + 1]) &
                    (cc >= x_edges[col]) & (cc < x_edges[col + 1])] = row * cols + col
    return cell_of


def _overlap_table(labels, cell_of, n_comp, n_cells):
    per_cell = np.zeros((n_comp + 1, n_cells), dtype=np.int64)
    flat_lab, flat_cell = labels.ravel(), cell_of.ravel()
    ok = flat_lab > 0
    np.add.at(per_cell, (flat_lab[ok], flat_cell[ok]), 1)
    return per_cell


def _split_component(labels, lab, cell_of, n_cells, want_cell, shape, rows, cols):
    """Two designs drawn overlapping (a deer's antlers meeting the gorilla below it) merge into
    one component and steal the neighbour's cell.  Two attempts: (1) erosion cores -- a real
    merge has two THICK creature bodies (distance-transform cores, so a thin overflowing wing
    never qualifies); (2) if that fails or short-changes a cell the blob reaches deeply (the
    interior healing can make joints thick), a watershed anchored on each involved cell's own
    share of the blob.  Adopted only when the starved cell `want_cell` comes out with a real
    part."""
    m = labels == lab
    dist = ndimage.distance_transform_edt(m)
    involved = [c for c in range(n_cells) if (m & (cell_of == c)).sum() >= 1500]

    def adopt(out):
        cells = {c for c, _p in out}
        return want_cell in cells and len(cells) >= 2

    for r in range(6, 41, 2):
        cores, n_cores = ndimage.label(dist >= r, structure=CONNECT8)
        if n_cores < 2:
            continue
        big = [k for k in range(1, n_cores + 1) if (cores == k).sum() >= 400]
        cents = {k: ndimage.center_of_mass(cores == k) for k in big}
        if len({cell_of[int(y), int(x)] for y, x in cents.values()}) < 2:
            continue                                  # thick cores, but all in one cell: one creature
        markers = np.zeros(m.shape, dtype=np.int16)
        for k in big:
            markers[cores == k] = k
        relief = (255 - dist).astype(np.uint8)
        ws = ndimage.watershed_ift(relief, markers)
        parts = [m & (ws == k) for k in big]
        parts = [p for p in parts if p.sum() >= 1500]
        if len(parts) < 2:
            continue
        sub = np.zeros(shape, dtype=np.int32)
        for k, p in enumerate(parts, 1):
            sub[p] = k
        per_cell = _overlap_table(sub, cell_of, len(parts), n_cells)
        out = [(int(per_cell[k].argmax()), parts[k - 1])
               for k in range(1, len(parts) + 1) if per_cell[k].max() > 0]
        # a partition that leaves a deeply-involved cell empty short-changes that design
        coverage = defaultdict(int)
        for c, p in out:
            coverage[c] += int((p & (cell_of == c)).sum())
        if any(coverage.get(c, 0) < 1500 for c in involved):
            continue
        if adopt(out):
            return out
    if len(involved) >= 2:
        markers = np.zeros(m.shape, dtype=np.int16)
        for c in involved:
            markers[m & (cell_of == c)] = c + 1
        relief = (255 - dist).astype(np.uint8)
        ws = ndimage.watershed_ift(relief, markers)
        out = [(c, m & (ws == c + 1)) for c in involved]
        out = [(c, p) for c, p in out if p.sum() >= 1500]
        if adopt(out):
            return out
    return None


def _histogram(rgb, mask):
    """Normalised 4x4x4 RGB histogram of a component's opaque pixels (palette fingerprint)."""
    px = rgb[mask].astype(np.int32)
    if not len(px):
        return None
    idx = (px[:, 0] >> 6) * 16 + (px[:, 1] >> 6) * 4 + (px[:, 2] >> 6)
    h = np.bincount(idx, minlength=64).astype(np.float32)
    return h / max(float(h.sum()), 1.0)


def _reassign_floaters(assign, sizes, labels, rgb, cell_of, rows, cols, expected=()):
    """Detached decorations (orbs, sparks, puffs) drift across cell boundaries and the
    max-overlap rule can hand them to the wrong design.  Re-judge STRICT small floaters --
    pieces under 25% of their cell's dominant component, never the dominant piece itself.
    A fragment that nearly TOUCHES a body (edge distance < 14px -- e.g. a tail tip severed
    from its own design by the backdrop keying) belongs to that body outright.  Otherwise
    the fragment goes to the design whose palette it matches, as long as it is reasonably
    close.  Moves that would starve an expected cell are refused."""
    n_cells = rows * cols
    mass = defaultdict(int)
    dom = defaultdict(int)
    for lab, val in assign.items():
        cell = val[0] if isinstance(lab, tuple) else val
        s = int(val[1].sum()) if isinstance(lab, tuple) else int(sizes[lab])
        mass[cell] += s
        dom[cell] = max(dom[cell], s)
    # candidate bodies: the dominant int component per cell, plus watershed-split parts (a cell
    # whose content came out of a split has no int body -- its part is the design)
    cand_h, cand_c, cand_mask = {}, {}, {}
    for cell in range(n_cells):
        ints = [l for l, c in assign.items() if c == cell and isinstance(l, (int, np.integer))]
        if ints and dom[cell] >= 2000:
            big = max(ints, key=lambda l: sizes[l])
            if sizes[big] == dom[cell]:
                m = labels == big
                cand_h[cell] = _histogram(rgb, m)
                ys, xs = np.nonzero(m)
                cand_c[cell] = (float(ys.mean()), float(xs.mean()))
                cand_mask[cell] = m
    for lab, val in list(assign.items()):
        if not isinstance(lab, tuple):
            continue
        cell, p = val
        if p.sum() >= 2000 and cell not in cand_h:
            cand_h[cell] = _histogram(rgb, p)
            ys, xs = np.nonzero(p)
            cand_c[cell] = (float(ys.mean()), float(xs.mean()))
            cand_mask[cell] = p
    if not cand_h:
        return
    ch, cw = labels.shape[0] / rows, labels.shape[1] / cols
    diag = float(np.hypot(ch, cw))
    body_edt = {}

    def edge_to(cell, ys, xs):
        if cell not in body_edt:
            body_edt[cell] = ndimage.distance_transform_edt(~cand_mask[cell])
        return float(body_edt[cell][ys, xs].min())

    for lab, val in list(assign.items()):
        if isinstance(lab, tuple):
            continue                                   # split parts stay where the splitter put them
        cell = val
        s = int(sizes[lab])
        if cell not in cand_h or s >= dom[cell]:
            continue                                   # no body here / this IS the dominant piece
        if cell in expected and mass[cell] - s < 2000:
            continue                                   # the move would starve this expected cell
        ys, xs = np.nonzero(labels == lab)
        cy, cx = float(ys.mean()), float(xs.mean())
        h = _histogram(rgb, labels == lab)
        if h is None:
            continue

        # 1) physical continuation: a piece nearly touching a body belongs to it -- this also
        # re-homes BIG severed parts (a scorpion tail / a sheep's legs cut off by the backdrop
        # keying).  The palette must agree too, so a foreign trinket resting ON a body (a fallen
        # weathervane on a cloud) is not claimed by mere proximity.
        near, best_edge = None, 1e9
        for c in cand_h:
            dm = edge_to(c, ys, xs)
            if dm < best_edge:
                best_edge, near = dm, c
        if near is not None and best_edge < 30 and near != cell:
            sim_near = 1.0 - 0.5 * float(np.abs(h - cand_h[near]).sum())
            if sim_near > 0.55:
                assign[lab] = near
                mass[cell] -= s
                mass[near] += s
                continue

        # 2) otherwise: small floaters only, palette affinity + centroid distance
        if s >= 0.4 * dom[cell]:
            continue                                   # design core, never re-homed
        if cell in expected and mass[cell] - s < 2000:
            continue                                   # the move would starve this expected cell

        def score(c):
            sim = 1.0 - 0.5 * float(np.abs(h - cand_h[c]).sum()) if cand_h[c] is not None else 0.0
            return sim - 0.15 * (np.hypot(cy - cand_c[c][0], cx - cand_c[c][1]) / diag)

        best = max(cand_h, key=score)
        if best != cell and score(best) > score(cell) + 0.02 and s <= 0.5 * dom[best]:
            assign[lab] = best
            mass[cell] -= s
            mass[best] += s
    return assign


def cell_masks(labels, rows, cols, expected=None, rgb=None):
    """Hand every labelled component to the cell (row, col) it overlaps most.  A component is one
    creature (or glow), so it is assigned whole -- a design whose wing overflows into the
    neighbour's cell keeps that wing and the neighbour never receives foreign pixels.  When an
    expected cell stays empty because its design touched (and merged with) the neighbour, the
    merged component is split by erosion and the parts re-assigned.  Detached decorations that
    drifted into the wrong cell are finally re-homed by palette affinity.  -> {cell index: [masks]}"""
    cell_of = _cell_grid(labels.shape, rows, cols)
    n_comp = int(labels.max())
    sizes = np.bincount(labels.ravel(), minlength=n_comp + 1)
    n_cells = rows * cols
    per_cell = _overlap_table(labels, cell_of, n_comp, n_cells)
    assign = {lab: int(per_cell[lab].argmax()) for lab in range(1, n_comp + 1)
              if sizes[lab] >= 24}                 # drop dust specks
    if expected:                                   # repair starved cells (merged touching designs)
        mass = defaultdict(int)
        for lab, cell in assign.items():
            mass[cell] += int(sizes[lab])
        for cell in sorted(expected):
            if mass[cell] >= 2000:
                continue
            cand = sorted((c for c in assign if isinstance(c, (int, np.integer))
                           and per_cell[c, cell] >= 300),
                          key=lambda c: -per_cell[c, cell])
            for c in cand:
                parts = _split_component(labels, c, cell_of, n_cells, cell, labels.shape, rows, cols)
                if parts:
                    mass[cell] -= int(sizes[c])
                    del assign[c]
                    for pc, p in parts:
                        assign[("part", id(p))] = (pc, p)
                        mass[pc] += int(p.sum())
                    break
    if rgb is not None:
        _reassign_floaters(assign, sizes, labels, rgb, cell_of, rows, cols, expected=expected or ())
    masks = defaultdict(list)
    for key, val in assign.items():
        cell, m = val if isinstance(key, tuple) else (val, labels == key)
        masks[cell].append(m)
    return masks


def clean_fragments(rgba):
    """Drop leftover neighbour-design fragments.  Two signatures of atlas bleed:
    1. a disconnected piece far from the main body (> 35% of its size from the body centroid)
       and much smaller than it (< 25% of its area);
    2. a disconnected piece touching the canvas edge that the main body does NOT touch -- a cell
       boundary always clips the overflowing neighbour exactly there.
    Legit detached decorations (orbs, bubbles, crystals, rings) stay: they sit near their body or
    are large, and the main body usually shares their edge contact."""
    a = rgba[:, :, 3]
    h, w = a.shape
    mask = a > 8
    # break thin bridges first: two designs drawn touching in the atlas connect into one component
    # through a few contact pixels; a 2px opening separates them without eating real features
    opened = ndimage.binary_opening(mask, structure=np.ones((3, 3)))
    bridge = mask & ~opened
    lab, n = ndimage.label(mask & ~bridge, structure=CONNECT8)
    if n < 2:
        return rgba
    sizes = np.bincount(lab.ravel(), minlength=n + 1)
    big = int(sizes[1:].argmax()) + 1          # skip label 0 = the transparent background
    by, bx = np.where(lab == big)
    if len(by) == 0:
        return rgba
    body = max(by.max() - by.min(), bx.max() - bx.min())
    cy, cx = float(by.mean()), float(bx.mean())
    body_edges = {by.min() == 0, by.max() == h - 1, bx.min() == 0, bx.max() == w - 1}
    for k in range(1, n + 1):
        if k == big or sizes[k] < 150:
            continue
        ky, kx = np.where(lab == k)
        if len(ky) == 0:
            continue
        d = np.min(np.hypot(ky - cy, kx - cx))
        frag_edges = {ky.min() == 0, ky.max() == h - 1, kx.min() == 0, kx.max() == w - 1}
        edge_clip = bool(frag_edges - body_edges)      # touches an edge the body stays off
        far = d > 0.35 * body and sizes[k] < 0.25 * sizes[big]
        if edge_clip or far:
            rgba[ky, kx] = 0
    return rgba


def trim_scale(rgba, max_side):
    """Crop to the opaque bbox, then premultiplied-Lanczos downscale so the longest side is <= max_side."""
    a = rgba[:, :, 3]
    ys, xs = np.nonzero(a)
    if not len(ys):
        return None
    y0, y1, x0, x1 = int(ys.min()), int(ys.max()) + 1, int(xs.min()), int(xs.max()) + 1
    crop = rgba[y0:y1, x0:x1]
    h, w = crop.shape[:2]
    if max(w, h) > max_side:
        k = max_side / max(w, h)
        nw, nh = max(1, round(w * k)), max(1, round(h * k))
        am = crop[:, :, 3:4].astype(np.float32) / 255.0
        premul = np.dstack([crop[:, :, c:c + 1].astype(np.float32) * am for c in range(3)] + [am * 255.0])
        crop = np.asarray(Image.fromarray(premul.astype(np.uint8), "RGBA").resize((nw, nh), Image.LANCZOS))
    return crop


# --------------------------------------------------------------------------- one atlas
def extract_cells(path, rows, cols, tol, pocket_tol, expected=None):
    """Atlas PNG -> {(row, col): trimmed RGBA uint8 array}.  `expected` lists the cell indices
    the key promises content for (used to repair cells starved by merged touching designs)."""
    im = Image.open(path).convert("RGBA")
    arr = np.asarray(im).astype(np.float32)
    rgb, alpha = arr[:, :, :3], arr[:, :, 3]
    rgb_u8 = np.asarray(im.convert("RGB"))
    bg = background_mask(rgb, alpha, tol, pocket_tol)
    a = np.where(bg, 0, alpha)
    a = np.clip(a * (255.0 / max(float(a.max()), 1.0)), 0, 255).astype(np.uint8)   # atlases cap at 253
    labels, _n = ndimage.label(a > 8, structure=CONNECT8)
    out, h, w = {}, a.shape[0], a.shape[1]
    x_edges = [round(w * c / cols) for c in range(cols + 1)]
    y_edges = [round(h * r / rows) for r in range(rows + 1)]
    for idx, parts in cell_masks(labels, rows, cols, expected=expected, rgb=rgb_u8).items():
        canvas = np.zeros((h, w, 4), dtype=np.uint8)
        for m in parts:                          # labels are disjoint, so plain overwrite is safe
            canvas[m] = np.concatenate([rgb_u8[m], a[m][:, None]], axis=1)
        # clean neighbour bleed inside the cell's own rect, then hard-cut at the boundary: a
        # neighbour design drawn touching this one merges into the same component and can't be
        # separated by component rules -- the cell boundary is the only reliable cut line
        row, col = divmod(idx, cols)
        cx0, cx1 = x_edges[col], x_edges[col + 1]
        cy0, cy1 = y_edges[row], y_edges[row + 1]
        canvas[cy0:cy1, cx0:cx1] = clean_fragments(canvas[cy0:cy1, cx0:cx1])
        margin = 6
        keep = np.zeros((h, w), dtype=bool)
        keep[max(0, cy0 - margin):cy1 + margin, max(0, cx0 - margin):cx1 + margin] = True
        canvas[~keep] = 0
        sprite = trim_scale(canvas, 10 ** 9)     # trim here; the per-target downscale happens below
        if sprite is not None and min(sprite.shape[:2]) >= 8:
            out[idx] = sprite
    return out


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", default=os.path.join(ROOT, "source_art", "scimon_collections"))
    ap.add_argument("--out", default=os.path.join(ROOT, "assets", "scimon"))
    ap.add_argument("--qa", default=None, help="write one QA sheet per collection into this directory")
    ap.add_argument("--max-side", type=int, default=256, help="longest sprite side in px (default 256)")
    ap.add_argument("--tol", type=float, default=14.0, help="background region-grow tolerance")
    ap.add_argument("--pocket-tol", type=float, default=30.0, help="enclosed-pocket keying tolerance")
    ap.add_argument("--families", default=None, help="comma-separated subset of families (for testing)")
    ap.add_argument("--views", default="front,back")
    args = ap.parse_args()

    sys.path.insert(0, ROOT)
    from data import SPECIES

    views = [v.strip().lower() for v in args.views.split(",") if v.strip()]
    only_fams = {f.strip().lower() for f in args.families.split(",")} if args.families else None
    written, skipped, warnings = 0, [], []
    os.makedirs(args.out, exist_ok=True)

    for coll in COLLECTIONS:
        base = os.path.join(args.src, f"Scimon_Collection_{coll}_Front_and_Back")
        all_fams = load_key(os.path.join(base, "FAMILY_STAGE_AND_VIEW_KEY.csv"))
        nrows = rows_per_sheet(all_fams)           # the atlas grid geometry, from the full key
        fams = all_fams
        if only_fams:                              # only touch the atlases the subset needs
            fams = {f: st for f, st in all_fams.items() if f in only_fams}
        need = sorted({s for st in fams.values() for s, _r, _c in st.values()})
        expected = defaultdict(set)                # (sheet, view) -> cell indices the key promises
        for fam, stages in fams.items():
            for stage, (sheet, row, col) in stages.items():
                if fam + STAGE_SUFFIX[stage] in SPECIES:
                    for view in views:
                        expected[(sheet, view)].add(row * 3 + col)
        sheets = {}                                # (sheet, view) -> {cell index: trimmed sprite}
        for view in views:
            folder = "FRONT_VIEWS" if view == "front" else "BACK_VIEWS"
            for sheet in need:
                rows = nrows[sheet]
                path = os.path.join(base, folder, f"C{coll}_Sheet_{sheet:02d}_{view.upper()}.png")
                if not os.path.isfile(path):
                    warnings.append(f"missing atlas {path}")
                    continue
                print(f"[{coll}] extracting {os.path.basename(path)} ({rows} rows) ...", flush=True)
                sheets[(sheet, view)] = extract_cells(path, rows, 3, args.tol, args.pocket_tol,
                                                      expected=expected[(sheet, view)])

        qa = {}                                    # family -> {stage: sprite} for the QA board
        for fam, stages in sorted(fams.items()):
            if only_fams and fam not in only_fams:
                continue
            for stage, (sheet, row, col) in sorted(stages.items()):
                sid = fam + STAGE_SUFFIX[stage]
                if sid not in SPECIES:
                    skipped.append(f"{coll}:{fam}/{stage} (no game species {sid})")
                    continue
                for view in views:
                    sprite = sheets.get((sheet, view), {}).get(row * 3 + col)
                    if sprite is None:
                        warnings.append(f"{coll}:{fam}/{stage}/{view}: empty cell")
                        continue
                    target = trim_scale(sprite, args.max_side)
                    name = f"{sid}-{view}.png"
                    Image.fromarray(target, "RGBA").save(os.path.join(args.out, name), optimize=True)
                    written += 1
                    if view == "front":
                        qa.setdefault(fam, {})[stage] = target

        if args.qa and qa:                         # QA sheet: one row per family, baby/middle/final
            os.makedirs(args.qa, exist_ok=True)
            tile = 110
            board = Image.new("RGBA", (3 * tile, len(qa) * (tile + 8)), (24, 26, 30, 255))
            for r, (fam, stages) in enumerate(sorted(qa.items())):
                for c, stage in enumerate(("baby", "middle", "final")):
                    t = stages.get(stage)
                    if t is None:
                        continue
                    k = min((tile - 6) / t.shape[1], (tile - 6) / t.shape[0])
                    img = Image.fromarray(t, "RGBA").resize(
                        (max(1, round(t.shape[1] * k)), max(1, round(t.shape[0] * k))), Image.LANCZOS)
                    board.alpha_composite(img, (c * tile + (tile - img.width) // 2,
                                                r * (tile + 8) + (tile - img.height) // 2))
            board.save(os.path.join(args.qa, f"qa_collection_{coll}.png"))

    print(f"\nwrote {written} sprites -> {args.out}")
    for s in skipped:
        print("skipped:", s)
    for msg in warnings:
        print("warning:", msg)

    # refresh the game's contact sheet from the art now on disk (dex order, 12 per row)
    from data import SPECIES as ALL
    tile, per_row = 84, 12
    ids = [sid for sid, sp in sorted(ALL.items(), key=lambda kv: kv[1].dex)
           if os.path.isfile(os.path.join(args.out, ALL[sid].front))]
    board = Image.new("RGBA", (per_row * tile, ((len(ids) + per_row - 1) // per_row) * tile), (24, 26, 30, 255))
    for i, sid in enumerate(ids):
        img = Image.open(os.path.join(args.out, ALL[sid].front))
        img.thumbnail((tile - 6, tile - 6), Image.LANCZOS)
        board.alpha_composite(img, ((i % per_row) * tile + (tile - img.width) // 2,
                                    (i // per_row) * tile + (tile - img.height) // 2))
    board.save(os.path.join(args.out, "_contact_sheet.png"))
    print(f"contact sheet -> {os.path.relpath(os.path.join(args.out, '_contact_sheet.png'), ROOT)}")


if __name__ == "__main__":
    main()
