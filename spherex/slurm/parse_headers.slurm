#!/bin/bash
#SBATCH --job-name=parse_spherex_headers
#SBATCH --output=logs/parse_spherex_headers_%j.out
#SBATCH --error=logs/parse_spherex_headers_%j.err
#SBATCH --time=48:00:00
#SBATCH --cpus-per-task=1
#SBATCH --nodes=5
#SBATCH --ntasks-per-node=6
#SBATCH --partition=cca

source /mnt/home/vkarambelkar/.bashrc
module load modules/2.3-20240529
module load python/3.10.13
module load openmpi python-mpi
module load gcc/13.2.0
source /mnt/home/vkarambelkar/spherex/.venv/bin/activate

spherex
echo "Starting parsing of images"
mpirun -np $SLURM_NTASKS python spherex/parse_headers_mpi.py
echo "Parsing of images completed"