#!/bin/bash
#SBATCH --job-name=pffdtd_sim
#SBATCH --account=reidb-meng-jhartley
#SBATCH --output=logs/%j/pffdtd.log
#SBATCH --error=logs/%j/pffdtd.log
#SBATCH --time=02:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --qos=bbdefault

set -e

RUN_NAME="first_run"

F_PLASMA=""
F_COLLISION=""
F_CYCLOTRON=""
ANG_E="90.0"
ANG_A="0.0"
T=""

STR_FILE="inputs/dipole_1m"
EXE="build/pffdtd_serial_${BB_CPU}"
# ==========================================================

# Check executable exists
if [ ! -f "$EXE" ]; then
    echo "Error: No executable found."
    exit 1
fi

if [ ! -f "$STR_FILE.str" ]; then
    echo "Error: Could not find .str file."
    exit 1
fi

OUT_DIR="results/${RUN_NAME}"
mkdir -p "$OUT_DIR"

echo "=========================================="
echo "Starting Simulation: ${RUN_NAME}"
echo "Output Directory: ${OUT_DIR}"
echo "=========================================="

echo "Using Executable: ${EXE}"

echo "Start Time: $(date '+%H:%M:%S')" > "${OUT_DIR}/simulation.log"

"$EXE" "${STR_FILE}" "${OUT_DIR}/data" \
    "$F_PLASMA" "$F_COLLISION" "$F_CYCLOTRON" \
    "$ANG_E" "$ANG_A" "$T" \
    >> "${OUT_DIR}/simulation.log" 2>&1

echo "End Time: $(date '+%H:%M:%S')" >> "${OUT_DIR}/simulation.log"

echo "Simulation Complete."
echo "Plotting Results..."

python visualization/plot_voltage.py "${OUT_DIR}/data.vc" --save "${OUT_DIR}/impedance_plot.png"

echo "Done. Results in ${OUT_DIR}"
