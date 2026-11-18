# Build Guide

Three ways to build PF-FDTD, all compiling the same sources with `g++`
(or MSVC via CMake). They differ in platform support and maintenance,
not in the code they produce. Pick by platform below; the full
reference for every method follows.

## Recommended approach

### If you're on Linux — use the Makefile

This is the maintained build: the one that tracks the source tree and
the one verified in the "Verifying the build" section below.

```bash
# Prerequisites (Debian/Ubuntu; most distros ship gcc and make already)
sudo apt install build-essential cmake   # cmake only needed for the tests

# Build the single-threaded version FIRST — see "Serial first" below
make serial

# Once a first case runs, build the parallel (OpenMP) version for speed
make

# Or a debug build, for stack traces and -O0 behaviour
make debug
```

**Serial first.** A new user should start with `make serial`, not the
parallel build, even though `make` (parallel) is the Makefile's
default:

- *Nothing extra to install or go wrong.* Serial needs no OpenMP and
  no `libomp-dev` — one less thing to fail on a first build.
- *First runs are small.* The 4000-iteration dipole case takes about
  2 minutes serial; threads buy little on a small grid and their
  overhead eats into the gain.
- *A baseline to check against.* Serial output is deterministic and
  single-threaded. Parallel output matches it bit-for-bit at one
  thread (verified on the dipole case, see below) — so run serial
  first, keep that output, and compare any parallel run against it.
  Multi-threaded runs have not been bit-compared here, which is
  itself a reason not to make them your first run.

Move to the parallel build when runs work and grids grow: same
results, less wall-clock time. That is what the parallel version is
for — production runs, not first runs.

Binaries land in the repo root: `pffdtd_parallel`, `pffdtd_serial`,
`pffdtd_debug`. Release flags are `-O3 -march=native -DNDEBUG`, so
the binary is tuned to the machine it was built on — rebuild after
moving to different hardware.

If the parallel build fails with an OpenMP error, install
`libomp-dev` (`sudo apt install libomp-dev`) and retry; if you don't
need threads, `make serial` sidesteps OpenMP entirely. `make clean`
removes the binaries, `make help` lists every target.

Run a first case with (see "Running a first case" for the arguments
and the fail-safe warning):

```bash
./pffdtd_serial dipole out 2000000 0.1 0 0 0 100
```

### If you're on Windows — use CMake

The Makefile assumes a Unix shell and `make`, and the `.bat` files
only build the parallel binary, so CMake is the Windows route: it
produces all four targets and handles both compilers.

**Option A — MinGW-w64 (closest to the Linux build):**

```powershell
# Install MinGW-w64 and CMake (e.g. choco install mingw cmake),
# then make sure g++ and cmake are on PATH
mkdir build; cd build
cmake .. -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release
cmake --build . --target pffdtd_release    # serial first — see "Serial first" above
cmake --build . --target pffdtd_parallel   # then parallel, for speed
```

**Option B — Visual Studio (MSVC):**

Install Visual Studio Community with "Desktop development with C++",
then from a Developer Command Prompt:

```powershell
mkdir build; cd build
cmake ..
cmake --build . --config Release --target pffdtd_release
cmake --build . --config Release --target pffdtd_parallel
```

Binaries land in `build/bin/<target>/`. Run the serial one first
from a terminal in the repo root so the `.str` input file is found:

```powershell
.\build\bin\release\pffdtd_release.exe dipole out 2000000 0.1 0 0 0 100
```

If CMake reports OpenMP not found, the `pffdtd_parallel` target is
skipped — build `pffdtd_release` (serial, same flags minus OpenMP)
instead, or install a MinGW-w64 that ships OpenMP.

**Fallback — the `.bat` files:** if you have MinGW but no CMake and
no `make`, double-click `compile.bat` (it checks `g++` is on `PATH`)
or `compile_manual.bat` (same build, but it adds a hard-coded MinGW
location, `C:\mingw64\mingw64\bin`, to `PATH` first — edit that line
if your MinGW lives elsewhere). Both build the parallel binary only,
as `pffdtd_parallel.exe`. This is a convenience shortcut, not a
maintained build — see "Why three build systems?" below.

### If you're on macOS

Either route works in principle, with one caveat: `make` ships with
the Xcode command-line tools, but Apple's `g++` is Clang, which has
no OpenMP by default. So:

```bash
make serial     # works with the stock toolchain
```

For the parallel build, install real GCC (`brew install gcc`) and
point the Makefile at it, e.g. `make parallel CXX=g++-14` (version
number as installed), or use the CMake route, which detects Clang
and OpenMP the same way it does on Linux. Neither macOS path has
been verified on this machine — the verification below is Linux-only.

## Why three build systems?

They accumulated, one per need, rather than being designed as a set.
The timeline, from the repo history:

- **2021 — stub.** The repository was created with a README only. No
  code, no build.
- **January 28, 2026 — Makefile (the original).** The full codebase
  (v1.8.2) was imported with documentation and the Makefile as "the
  build system." This is the Linux-native route, written for the
  machine the code was developed on, and it has been updated at every
  step since — OpenMP in February, checkpointing in November.
- **January 28, 2026 — CMake (same day, deliberate).** Added in its
  own commit, "Add cross-platform CMake build system and build
  guide," with MSVC/GCC/Clang compatibility for Windows (MinGW/MSVC)
  plus Linux/macOS. The reasoning was collaboration: a contributor
  on Windows or in an IDE (Visual Studio, CLion) shouldn't need
  `make` to build the code. It defines four targets
  (debug/release/profile/parallel) and the unit tests, which the
  Makefile doesn't.
- **February 8, 2026 — `.bat` files (Windows convenience).** Added
  with the OpenMP parallelization update, alongside other Windows
  scripts (`run_simulation.bat`, `run_tests.bat`,
  `benchmark_compare.bat`). That work was done and tested on Windows
  under MinGW, and the `.bat` files were the quickest way to build
  the new parallel binary there: double-click, get
  `pffdtd_parallel.exe`. `compile_manual.bat` is the fallback for
  when MinGW isn't on `PATH` at all.

So each one answered a real question at the time — Linux workflow,
cross-platform/IDE coverage, Windows one-click build — and nobody
ever consolidated them afterward. The cost is maintenance: a new
source file has to be added to all three by hand (see the
maintainer note below), and the two later ones went stale when
checkpointing was ported to `main` in November 2026 — the file was
added to the Makefile only, and CMake and the `.bat` files silently
broke until someone tried them. The `.bat` files are the redundant
pair: CMake covers the same Windows users with more targets, and
they are the likeliest candidates for removal if the set ever
shrinks.

## All methods — reference

### Method 1 — Makefile

```bash
make            # parallel (OpenMP) build, the default
make serial     # single-threaded build — use this first (see "Serial first")
make debug      # -O0 -g build with symbols
make profile    # -O2 -g -pg build for gprof
make clean      # remove the binaries
make help       # list targets
```

`CXX` can be overridden on the command line
(`make parallel CXX=g++-14`).

### Method 2 — CMake

```bash
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . --target pffdtd_release    # or pffdtd_parallel,
                                           # pffdtd_debug, pffdtd_profile
```

`cmake --build .` builds everything, including the unit tests.
Add `-G "MinGW Makefiles"` on Windows with MinGW; with MSVC, pass
`--config Release` (or `Debug`) to the build command instead of
`-DCMAKE_BUILD_TYPE`.

### Method 3 — `compile.bat` / `compile_manual.bat`

Parallel build only, MinGW only, `pffdtd_parallel.exe`. See the
Windows fallback in "Recommended approach" above.

## Verifying the build

All three methods were verified on Linux on 2026-11-17, after the
build-list fix that added `checkpoint.cpp` to CMake and the `.bat`
files:

- Makefile: `make serial`, `make parallel`, `make debug`,
  `make profile` — all exit 0, all produce working ELF executables.
- CMake: `pffdtd_debug`, `pffdtd_release`, `pffdtd_profile`,
  `pffdtd_parallel` — all build; the unit tests build and pass (1/1).
- `.bat` files: the `g++` commands they contain were run verbatim on
  Linux and link successfully. The batch wrappers themselves
  (MinGW `PATH` handling) were not executed on Windows.

## Running a first case

From the repo root, with a short run (see the fail-safe note below):

```bash
./pffdtd_serial dipole out 2000000 0.1 0 0 0 100
```

Arguments: input-file prefix, output-file prefix, plasma frequency
(Hz), collision frequency, cyclotron frequency, E-field angle,
antenna angle, T. Output is `out.vc` (voltage/current per
iteration) and `out.fd` (fields).

**Fail-safe note:** the shipped `dipole.str` sets Max Iteration to
640000, which is roughly 5 hours at serial speed. For a first test,
edit the `//Fail Safe Parameters` value in your `.str` file down to
e.g. 4000 first (the 4000-iteration dipole case is the validated
reference). The antenna generator (`scripts/antenna_generator.py`)
inherits the same value from its template.

**Checkpointing:** pass a checkpoint interval in steps as `argv[16]`
(the seven `argv[9..15]` slots are the sheath line's options and are
unused on `main`, so pad them with zeros):

```bash
./pffdtd_serial dipole out 2000000 0.1 0 0 0 100 0 0 0 0 0 0 0 5000
```

A `data.ckpt` file is written every 5000 steps; killing the run and
re-running the same command resumes from it bit-identically.
Checkpointing is off when the interval is 0 or absent.

## Tests

```bash
# CMake only; downloads googletest on first configure (needs internet)
cd build
cmake --build . --target unit_tests
./tests/unit_tests
```

## Troubleshooting

- **Link errors mentioning `ckpt_*`** (e.g. `undefined reference to
  'ckpt_write'`) mean the build's source list is stale: every method
  must list `src/io/checkpoint.cpp`. This happened in November 2026
  when checkpointing was ported to `main` and only the Makefile was
  updated — the fix is one line in each of `CMakeLists.txt`,
  `compile.bat`, and `compile_manual.bat`.
- **OpenMP not found** (CMake): install `libomp-dev` (Linux) or use a
  MinGW-w64 install that ships OpenMP; or build the serial target.
- **CMake not found / compiler not found**: add the tool to `PATH`
  (Windows) or install `build-essential` / `cmake` (Linux).
- **Parallel build fails on macOS**: Apple Clang has no OpenMP by
  default — use `make serial`, or install GCC via Homebrew (see the
  macOS note above).

## Maintainer note — keeping the three builds in sync

The source list lives in three places: `Makefile` (`SOURCES`),
`CMakeLists.txt` (`SOURCES`), and the `g++` command line in
`compile.bat` and `compile_manual.bat`. When a source file is added
or removed, update all three (four files) and re-verify each method
builds, as in the "Verifying the build" section above. The
November 2026 checkpoint port is the cautionary example: the file
was added to the Makefile only, and the other two builds silently
went stale until someone tried them.

## Supersedes

This guide replaces `archive/dev_docs/CROSS_PLATFORM_BUILD.md`,
which covered CMake only, predates the Makefile targets and
checkpointing, and gives a run example that does not match the
current command line.
