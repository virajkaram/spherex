#!/bin/bash
#SBATCH --job-name=extract_spherex_spectra_irtf_20250906
#SBATCH --output=logs/extract_spherex_spectra_irtf_20250906_%j.out
#SBATCH --error=logs/extract_spherex_spectra_irtf_20250906_%j.err
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
echo "Starting extraction of spectra"
mpirun -np $SLURM_NTASKS python spherex/main_mpi.py --filename irtf_20250906_targets.csv --output_dir_name irtf_20250906_targets
echo "Ingestion of images completed"