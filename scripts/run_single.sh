#!/bin/bash
#SBATCH --job-name=pffdtd_sim
#SBATCH --account=reidb-meng-jhartley
#SBATCH --output=logs/pffdtd-%j.log
#SBATCH --error=logs/pffdtd-%j.log
#SBATCH --time=02:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --mem=16276M
#SBATCH --cpus-per-task=1
#SBATCH --qos=bbdefault

set -e

RUN_NAME="${SLURM_JOB_NAME}_$(date +%Y%m%dT%H%M%S)"

F_PLASMA="5.3e6"
F_COLLISION="0.27"
F_CYCLOTRON="18.7"
ANG_E="22.0"
ANG_A="0.0"
T=""

STR_FILE="inputs/dipole_1m"
EXE="build/pffdtd_serial_${BB_CPU}"
# ==========================================================

# Check executable exists
if [ ! -f "$EXE" ]; then
    echo "[$(date -Iseconds)] Error: No executable found."
    exit 1
fi

if [ ! -f "$STR_FILE.str" ]; then
    echo "[$(date -Iseconds)] Error: Could not find .str file."
    exit 1
fi

OUT_DIR="results/${RUN_NAME}"
mkdir -p "$OUT_DIR"

echo "[$(date -Iseconds)] Starting Simulation: ${RUN_NAME} with output directory: ${OUT_DIR}"
echo "[$(date -Iseconds)] Using Executable: ${EXE}"

echo "[$(date -Iseconds)] Start Time"
./${EXE} "${STR_FILE}" "${OUT_DIR}/data" "$F_PLASMA" "$F_COLLISION" "$F_CYCLOTRON" "$ANG_E" "$ANG_A" "$T"
echo "[$(date -Iseconds)] End Time"

echo "[$(date -Iseconds)] Simulation Complete."
echo "[$(date -Iseconds)] Results in ${OUT_DIR}"
