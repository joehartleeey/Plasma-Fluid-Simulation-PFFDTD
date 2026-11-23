

import argparse
import math
import sys

METAL = (1, 1, 1)     # Perfect Electrical Conductor


class Config:
    """Simulation configuration"""

    def __init__(self, sx, sy, sz, dx, dy, dz):
        self.sx, self.sy, self.sz = sx, sy, sz
        self.dx, self.dy, self.dz = dx, dy, dz

        self.sources = [] # (x, y, z, field, type, param)
        self.er1 = 1.0
        self.er2 = 1.0
        self.cells = [] # (x, y, z, erx, ery, erz)
        self.output = {
            "iter": 10,
            "flags": (1,1,0,0,0,0), # E, B, Ue, Ne, Ui, Ni
            "lower": (1,1,1),
            "upper": (sx - 1, sy - 1, sz - 1),
        }

    def to_str(self, header=""):
        """
        Generates the str to copy into a file
        """
        lines = [f"//{header}"]
        lines.append("//Grid Parameters")
        lines.append(f"{self.sx}  {self.sy}  {self.sz}")
        lines.append(f"{self.dx:.6e}  {self.dy:.6e}  {self.dz:.6e}")
        lines.append("//Source Parameters")
        lines.append(str(len(self.sources)))
        for x, y, z, field, stype, param in self.sources:
            lines.append(f"{x}  {y}  {z}  {field}  {stype}  {param:.6e}")
        lines.append("//Dielectric Parameters")
        lines.append(f"{self.er1:.6e}")
        lines.append(f"{self.er2:.6e}")
        lines.append("//Antenna Structure")
        lines.append(str(len(self.cells)))
        for x, y, z, erx, ery, erz in self.cells:
            lines.append(f"{x}  {y}  {z}  {erx}  {ery}  {erz}")
        lines.append("//Output Field Info")
        it, (e, b, ue, ne, ui, ni) = self.output["iter"], self.output["flags"]
        lines.append(f"{it}  {e}  {b}  {ue}  {ne}  {ui}  {ni}")
        lo, up = self.output["lower"], self.output["upper"]
        lines.append(f"{lo[0]}  {lo[1]}  {lo[2]}")
        lines.append(f"{up[0]}  {up[1]}  {up[2]}")
        return "\n".join(lines) + "\n"

    def validate(self):
        errors = []
        for name, s in (("sx", self.sx), ("sy", self.sy), ("sz", self.sz)):
            if not (10 <= s <= 2048):
                errors.append(f"Grid dimension {name}={s} outside 10-2048")
        for name, d in (("dx", self.dx), ("dy", self.dy), ("dz", self.dz)):
            if d <= 0:
                errors.append(f"Grid spacing {name}={d} must be > 0")
        if not (1 <= len(self.sources) <= 100):
            errors.append(f"Number of sources ({len(self.sources)}) outside 1-100")
        bounds = (self.sx, self.sy, self.sz)
        for i, (x, y, z, field, stype, param) in enumerate(self.sources, 1):
            for coord, b, ax in zip((x, y, z), bounds, "xyz"):
                if not (1 <= coord <= b - 1):
                    errors.append(f"Source {i} coordinate {ax}={coord} outside 1-{b-1}")
            if field not in (1, 2, 3):
                errors.append(f"Source {i} field={field} invalid (1=Ex, 2=Ey, 3=Ez)")
            if stype not in range(1, 8):
                errors.append(f"Source {i} type={stype} invalid (1-7)")
            if stype in (1, 2, 3, 7) and param <= 0:
                errors.append(f"Source {i} frequency parameter must be > 0")
        if not self.cells:
            errors.append("Antenna structure is empty (n_cells must be >= 1)")
        if len(self.cells) > 100000:
            errors.append("n_cells exceeds 100,000 limit")
        seen = set()
        for (x, y, z, _, _, _) in self.cells:
            for coord, b, ax in zip((x, y, z), bounds, "xyz"):
                if not (1 <= coord <= b - 1):
                    errors.append(f"Antenna cell at ({x},{y},{z}) out of bounds")
            key = (x, y, z)
            if key in seen:
                errors.append(f"Duplicate antenna cell at {key}")
            seen.add(key)
        lo, up = self.output["lower"], self.output["upper"]
        if any(l >= u for l, u in zip(lo, up)):
            errors.append("Output region lower corner must be < upper corner")
        return errors

def put_line(cfg, points, mat, thickness=0):
    
    (x0, y0, z0), (x1, y1, z1) = points
    
    n = max(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0))
    
    for i in range(n + 1):
        t = 0 if n == 0 else i / n
        x = round(x0 + (x1 - x0) * t)
        y = round(y0 + (y1 - y0) * t)
        z = round(z0 + (z1 - z0) * t)
        add_cell(cfg, x, y, z, mat, thickness)

def add_cell(cfg, x, y, z, mat, thickness=0):
    if thickness == 0:
        cfg.cells.append((x, y, z, *mat))
        return
    for ox in range(-thickness, thickness + 1):
        for oy in range(-thickness, thickness + 1):
            for oz in range(-thickness, thickness + 1):
                cfg.cells.append((x + ox, y + oy, z + oz, *mat))

def dedupe(cfg):
    seen = {}
    for cell in cfg.cells:
        seen.setdefault(cell[:3], cell)
    cfg.cells = list(seen.values())

def build_dipole(cfg, length, axis, center, mat=METAL, thickness=0):
    
    c = {"x": 0, "y": 1, "z": 2}[axis]
    
    half = length // 2

    lo = [center[0] + (0 if i != c else -half - 1) for i in range(3)]
    hi = [center[0] + (0 if i != c else half) for i in range(3)]

    put_line(cfg, ((lo[0], lo[1], lo[2]), (hi[0], hi[1], hi[2])), mat, thickness)

    cfg.cells = [(x, y, z, *m) for (x, y, z, *m) in cfg.cells if (x, y, z) != tuple(center)]

    return center

def main():
    ap = argparse.ArgumentParser(description="Generate PF-FDTD .str input files.")
    ap.add_argument("antenna", choices=["dipole"], default="dipole")
    ap.add_argument("-o", "--output", default=None, help="output .str filename")
    ap.add_argument("--nx", type=int, default=100)
    ap.add_argument("--ny", type=int, default=100)
    ap.add_argument("--nz", type=int, default=100)
    ap.add_argument("--dx", type=float, default=1.0e-3)
    ap.add_argument("--dy", type=float, default=1.0e-3)
    ap.add_argument("--dz", type=float, default=1.0e-3)

    # Source parameters (defaults: 10 MHz sine on Ez at grid center)
    ap.add_argument("--src-pos", default=None, help="source x,y,z (grid coords)")
    ap.add_argument("--src-field", type=int, default=3, choices=[1, 2, 3])
    ap.add_argument("--src-type", type=int, default=1, choices=range(1, 8), help="1 sin, 2 pulse, 3 raised-cos, 4 gauss, 5 gauss-deriv, 6 DC, 7 sinc")
    ap.add_argument("--src-param", type=float, default=1.0e7)
    ap.add_argument("--er1", type=float, default=1.0)
    ap.add_argument("--er2", type=float, default=1.0)
    ap.add_argument("--output-region", default=None, help="7 values: iter E B Ue Ne Ui Ni lower(3) upper(3); or use --iter and --region")
    ap.add_argument("--iter", type=int, default=10, help="iterations between outputs")
    ap.add_argument("--flags", default="1 1 0 0 0 0", help="E B Ue Ne Ui Ni flags")
    ap.add_argument("--region", default=None, help="lower3 upper3, e.g. '1,1,1 63,63,63' or '30,30,30 34,34,34'")

    # Antenna geometry
    ap.add_argument("--length", type=int, default=20, help="elements in cells (dipole/monopole)")
    ap.add_argument("--axis", default="z", choices=["x", "y", "z"])
    ap.add_argument("--cx", type=int, default=None, help="center x (defaults to grid center)")
    ap.add_argument("--cy", type=int, default=None)
    ap.add_argument("--cz", type=int, default=None)
    ap.add_argument("--thickness", type=int, default=0, help="wire/line cross-section half-thickness")

    args = ap.parse_args()

    cfg = Config(args.nx, args.ny, args.nz, args.dx, args.dy, args.dz)
    cfg.er1, cfg.er2 = args.er1, args.er2

    center = [
        args.cx if args.cx is not None else args.nx // 2,
        args.cy if args.cy is not None else args.ny // 2,
        args.cz if args.cz is not None else args.nz // 2,
    ]

    # --- build antenna ---
    if args.antenna == "dipole":
        feed = build_dipole(cfg, args.length, args.axis, center, thickness=args.thickness)
    
    # --- source at feed ---
    if args.src_pos:
        sx, sy, sz = [int(v) for v in args.src_pos.split(",")]
    else:
        sx, sy, sz = feed
    cfg.sources.append((sx, sy, sz, args.src_field, args.src_type, args.src_param))

    # --- output config ---
    cfg.output["iter"] = args.iter
    cfg.output["flags"] = tuple(int(v) for v in args.flags.split())
    if args.region:
        try:
            lo, up = [tuple(int(v) for v in part.split(",")) for part in args.region.split()]
            cfg.output["lower"], cfg.output["upper"] = lo, up
        except ValueError:
            ap.error("--region format: 'lower_x,lower_y,lower_z upper_x,upper_y,upper_z'")

        # --- validate and write ---
    errors = cfg.validate()
    if errors:
        for e in errors:
            print("ERROR: " + e, file=sys.stderr)
        sys.exit(1)

    text = cfg.to_str(header=f"PF-FDTD input: {args.antenna} antenna")
    if args.output:
        with open(args.output, "w") as f:
            f.write(text)
        print(f"Wrote {args.output} ({len(cfg.cells)} cells)")
    else:
        sys.stdout.write(text)

if __name__ == "__main__":
    main()