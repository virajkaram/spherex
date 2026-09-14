#!/bin/bash
#SBATCH --job-name=extract_spherex_spectra_quasars
#SBATCH --output=logs/extract_spherex_spectra_quasars_%j.out
#SBATCH --error=logs/extract_spherex_spectra_quasars_%j.err
#SBATCH --time=120:00:00
#SBATCH --cpus-per-task=1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --partition=cca

source /mnt/home/vkarambelkar/.bashrc
module load modules/2.3-20240529
module load python/3.10.13
module load openmpi python-mpi
module load gcc/13.2.0
source /mnt/home/vkarambelkar/spherex/.venv/bin/activate

spherex
echo "Starting extraction of spectra"
mpirun -np $SLURM_NTASKS python /mnt/home/vkarambelkar/spherex/spherex/main_mpi.py --filename /mnt/home/vkarambelkar/spherex_targets/DR16Q_spherex_sample_higher-z_icut19_smallersample.csv --output_dir_name DR16Q_spherex_sample_higher-z_icut19_smallersample --name_key 'name' --ra_key 'ra' --dec_key 'dec'
echo "Ingestion of images completed"