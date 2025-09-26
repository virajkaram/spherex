#!/bin/bash
#SBATCH --job-name=ingest_spherex_images
#SBATCH --output=logs/ingest_spherex_images_%j.out
#SBATCH --error=logs/ingest_spherex_images_%j.err
#SBATCH --time=48:00:00
#SBATCH --cpus-per-task=1
#SBATCH --nodes=5
#SBATCH --ntasks-per-node=6
#SBATCH --partition=cca

source /mnt/home/vkarambelkar/.bashrc
module load modules/2.3-20240529
module load python/3.10.13
module load openmpi python-mpi
source /mnt/home/vkarambelkar/spherex/.venv/bin/activate

ingest_spherex
echo "Starting ingestion of images"
mpirun -np $SLURM_NTASKS python spherex/ingest_files_mpi.py
echo "Ingestion of images completed"