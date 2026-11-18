#!/usr/bin/env python3
"""Generate PFFDTD ``.str`` input files for different antenna geometries.

Starting point: the ``main`` branch (latest pure PFFDTD, checkpointing now
ported as 5b4853a) and its canonical ``dipole.str`` template. Geometry is
data, not code: an antenna is a list of grid cells in the
``//Antenna Structure`` section of the ``.str`` file, parsed by
``src/io/file_handler.cpp`` (``setup2``).

Cell-code semantics -- read from the parser, NOT from docs/INPUT_FORMAT.md,
which describes them backwards:
    code 1  -> 1/Er = 0   (that E-component is killed: PEC along that axis)
    code 2  -> 1/Er = 1/Er1   (dielectric 1, Er1 from the .str header)
    code 3  -> 1/Er = 1/Er2   (dielectric 2)
    code 0  -> 1/Er = 1   (free space / plasma, component untouched)
So a z-directed thin wire is ``0 0 1`` (only Ez killed), an x-directed
wire is ``1 0 0``, a y-directed wire is ``0 1 0``. A diagonal / corner
cell that joins two directions gets both codes, e.g. ``1 0 1``.

Everything except the source line and the antenna section is copied
byte-for-byte from the template, so grid, dielectrics, fail-safe and
output settings stay identical to the validated dipole case.

Usage:
    python3 antenna_generator.py dipole --axis z --length 14
    python3 antenna_generator.py dipole --axis x --length 26 --out dipole_x26.str
    python3 antenna_generator.py monopole --length 13
    python3 antenna_generator.py loop --side 20
    python3 antenna_generator.py inverted-v --length 13 --rise 6   # --length = cells per arm; total 27
    python3 antenna_generator.py --all          # one .str per geometry
    python3 antenna_generator.py --check dipole_z14.str   # re-parse & report

Limitations, stated plainly:
  * No CAD / mesh import: every geometry is voxelised onto the grid
    (dx = 0.04 m in the template, so one cell = 4 cm).
  * No ground plane exists in the .str format, so "monopole" here is a
    half-length vertical element fed at its base, not a monopole over a
    ground plane. Compare it against the full dipole, not against theory
    for a grounded monopole.
  * The feed source sits on an antenna cell, exactly as in dipole.str
    (source at 35,35,33, on the wire). Its field component follows the
    feed segment direction: Ez (field 3) for a z-feed, Ex (field 1) for
    an x-feed, Ey (field 2) for a y-feed.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_TEMPLATE = HERE.parent / "dipole.str"

# Centre of the template dipole / grid centre (35, 35, 33 is the feed).
CX, CY, CZ = 35, 35, 33

CODE = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}


def parse_template(path: Path):
    """Split a .str file into (head, source_line, dielectric, antenna, tail).

    head = everything up to and including the '//Source Parameters' count
    line; antenna/tail split at '//Antenna Structure' / '//Output Field Info'.
    """
    lines = path.read_text().splitlines()
    # Locate section markers.
    src_i = next(i for i, l in enumerate(lines) if l.startswith("//Source"))
    ant_i = next(i for i, l in enumerate(lines) if l.startswith("//Antenna"))
    out_i = next(i for i, l in enumerate(lines) if l.startswith("//Output"))
    grid_i = next(i for i, l in enumerate(lines) if l.startswith("//Grid"))
    grid = tuple(int(v) for v in lines[grid_i + 1].split())
    head = lines[: src_i + 2]          # through the '1' (n_sources) line
    source_line = lines[src_i + 2]
    dielectric = lines[src_i + 3: ant_i]  # '//Dielectric...' through Er2
    n_cells = int(lines[ant_i + 1])
    antenna = [tuple(int(v) for v in l.split()) for l in lines[ant_i + 2: ant_i + 2 + n_cells]]
    tail = lines[out_i:]
    return grid, head, source_line, dielectric, antenna, tail


def build_str(grid, head, source_line, dielectric, tail, cells, source):
    """Reassemble a .str file with a new antenna section and source line."""
    sx, sy, sz = grid
    for (x, y, z, *_c) in cells:
        if not (0 < x < sx and 0 < y < sy and 0 < z < sz):
            raise ValueError(f"antenna cell {(x, y, z)} outside grid {grid}")
    if len({(x, y, z) for x, y, z, *_ in cells}) != len(cells):
        raise ValueError("duplicate antenna cells")
    sx_, sy_, sz_, field, _type, param = source
    if not (0 < sx_ < sx and 0 < sy_ < sy and 0 < sz_ < sz):
        raise ValueError(f"source {source[:3]} outside grid {grid}")
    out = list(head)
    out.append(f"{sx_}\t{sy_}\t{sz_}\t{field}\t{_type}\t{param}")
    out.extend(dielectric)
    out.append("//Antenna Structure")
    out.append(str(len(cells)))
    out.extend("\t".join(str(v) for v in c) for c in cells)
    out.extend(tail)
    return "\n".join(out) + "\n"


def line(axis: str, length: int, centre=(CX, CY, CZ)):
    """Straight wire of `length` cells along `axis`, centred on `centre`."""
    if length < 2:
        raise ValueError("length must be >= 2")
    cx, cy, cz = centre
    start = {"x": cx, "y": cy, "z": cz}[axis] - length // 2
    cells = []
    for k in range(length):
        pos = [cx, cy, cz]
        pos["xyz".index(axis)] = start + k
        cells.append((*pos, *CODE[axis]))
    return cells


def dipole(axis: str, length: int):
    cells = line(axis, length)
    field = {"x": 1, "y": 2, "z": 3}[axis]
    return cells, (CX, CY, CZ, field, 5, 100000000)


def monopole(length: int):
    """Half-length vertical element fed at its base (z = CZ upward).

    No ground plane in the format: this is a truncated dipole, see header.
    """
    if length < 2:
        raise ValueError("length must be >= 2")
    cells = [(CX, CY, CZ + k, *CODE["z"]) for k in range(length)]
    return cells, (CX, CY, CZ, 3, 5, 100000000)


def square_loop(side: int):
    """Square loop of `side` cells per side, in the x-z plane at y = CY.

    Bottom/top edges run along x (code 1 0 0), sides along z (0 0 1),
    corners join both (1 0 1). Feed is at the centre of the bottom edge,
    driven on Ex (field 1).
    """
    if side < 4:
        raise ValueError("side must be >= 4")
    x0, x1 = CX - side // 2, CX - side // 2 + side - 1
    z0, z1 = CZ - side // 2, CZ - side // 2 + side - 1
    cells = []
    for x in range(x0, x1 + 1):
        code = (1, 0, 1) if x in (x0, x1) else CODE["x"]
        cells.append((x, CY, z0, *code))          # bottom edge
        cells.append((x, CY, z1, *code))          # top edge
    for z in range(z0 + 1, z1):
        cells.append((x0, CY, z, *CODE["z"]))     # left edge
        cells.append((x1, CY, z, *CODE["z"]))     # right edge
    cells.sort()
    return cells, (CX, CY, z0, 1, 5, 100000000)


def inverted_v(arm: int, rise: int):
    """Inverted-V: two staircase arms of `arm` cells each from the feed
    (total 2*arm + 1 cells), rising `rise` cells over each arm (x-z plane).

    Diagonal cells carry code 1 0 1 (both Ex and Ez killed): a staircase
    approximation, not a true diagonal wire.
    """
    if arm < 2:
        raise ValueError("arm must be >= 2")
    if not (0 < rise < arm):
        raise ValueError("rise must be between 1 and arm - 1")
    cells = [(CX, CY, CZ, 1, 0, 1)]  # feed cell
    for side in (-1, 1):
        for k in range(1, arm + 1):
            x = CX + side * k
            z = CZ + (rise * k) // arm
            cells.append((x, CY, z, 1, 0, 1))
    cells = sorted(set(cells))
    return cells, (CX, CY, CZ, 3, 5, 100000000)


GEOMETRIES = {
    "dipole": ("Straight wire, any axis/length", dipole),
    "monopole": ("Half-length vertical element, fed at base", monopole),
    "loop": ("Square loop in the x-z plane", square_loop),
    "inverted-v": ("Two staircase arms from a central feed", inverted_v),
}


def check(path: Path):
    """Re-parse a generated .str the way file_handler.cpp does and report."""
    grid, head, source_line, _d, antenna, _t = parse_template(path)
    # Simulate setup2's switch: code -> 1/Er per component.
    def inv(code, er=(1.2, 3.2)):
        return {1: 0.0, 2: 1 / er[0], 3: 1 / er[1]}.get(code, 1.0)

    kinds = {}
    for (_x, _y, _z, a, b, c) in antenna:
        kinds[(a, b, c)] = kinds.get((a, b, c), 0) + 1
    print(f"{path.name}: grid={grid} source=({source_line.strip()}) "
          f"cells={len(antenna)}")
    for code, n in sorted(kinds.items()):
        print(f"  code {code}: {n} cells -> 1/Er = "
              f"({inv(code[0])}, {inv(code[1])}, {inv(code[2])})")
    xs = [c[0] for c in antenna]; ys = [c[1] for c in antenna]; zs = [c[2] for c in antenna]
    print(f"  extent x {min(xs)}..{max(xs)}  y {min(ys)}..{max(ys)}  "
          f"z {min(zs)}..{max(zs)}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("geometry", nargs="?", choices=list(GEOMETRIES),
                    help="geometry to generate")
    ap.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    ap.add_argument("--axis", default="z", choices="xyz")
    ap.add_argument("--length", type=int, default=26)
    ap.add_argument("--side", type=int, default=20)
    ap.add_argument("--rise", type=int, default=6)
    ap.add_argument("--out", type=Path, help="output .str (default: <geometry>_<params>.str)")
    ap.add_argument("--all", action="store_true", help="generate one .str per geometry")
    ap.add_argument("--check", type=Path, help="re-parse and report on a .str file")
    args = ap.parse_args(argv)

    if args.check:
        check(args.check)
        return 0

    grid, head, _src, dielectric, _ant, tail = parse_template(args.template)
    jobs = []
    if args.all:
        jobs = [
            ("dipole_z26", *dipole("z", 26)),
            ("dipole_z14", *dipole("z", 14)),
            ("dipole_x26", *dipole("x", 26)),
            ("dipole_y26", *dipole("y", 26)),
            ("monopole_z13", *monopole(13)),
            ("loop_s20", *square_loop(20)),
            ("invertedv_27r6", *inverted_v(13, 6)),
        ]
    elif args.geometry is None:
        ap.error("give a geometry, --all, or --check")
    elif args.geometry == "dipole":
        jobs = [(f"dipole_{args.axis}{args.length}", *dipole(args.axis, args.length))]
    elif args.geometry == "monopole":
        jobs = [(f"monopole_z{args.length}", *monopole(args.length))]
    elif args.geometry == "loop":
        jobs = [(f"loop_s{args.side}", *square_loop(args.side))]
    elif args.geometry == "inverted-v":
        jobs = [(f"invertedv_{2 * args.length + 1}r{args.rise}", *inverted_v(args.length, args.rise))]

    for name, cells, source in jobs:
        out = args.out if (args.out and not args.all) else Path(f"{name}.str")
        out.write_text(build_str(grid, head, _src, dielectric, tail, cells, source))
        print(f"wrote {out} ({len(cells)} cells, source {source[:3]} field {source[3]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
