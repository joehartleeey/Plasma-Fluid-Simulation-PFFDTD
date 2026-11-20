#! /bin/bash
#SBATCH --time=5:0
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --qos=bbdefault
#SBATCH --output=logs/compile/%A-%a.out

module purge; module load bluebear

module load bear-apps/2025b
module load foss/2025b

make serial
