from sqlalchemy.exc import IntegrityError
from spherex.tables import set_up_spherex_databases
from pathlib import Path
import logging
import numpy as np
from spherex.parse_headers import get_record_from_file
from spherex.tables import BaseTable
from spherex.database.transactions import _insert_in_table
from typing import Type
from glob import glob
from spherex.tables import ImagesTable
from spherex.log import get_logger
from tqdm import tqdm
import argparse
from mpi4py import MPI
from time import time


logger = logging.getLogger(__name__)


comm = MPI.COMM_WORLD # Initialize the MPI communicator
rank = comm.Get_rank() # The rank of the current process
size = comm.Get_size()  # Total number of processes


def insert_record_into_table(new_entry: dict, sql_table: Type[BaseTable],
                             returning_keys=None):
    """
    Insert a record into a given SQL table
    """
    try:
        _insert_in_table(new_entry=new_entry, sql_table=sql_table,
                         returning_keys=returning_keys)
        logger.debug(f"Inserted record {new_entry} into table {sql_table.__tablename__}")
    except IntegrityError as e:
        logger.debug(f"Found duplicate entry for record: {new_entry}, skipping.")


def ingest_single_file_into_table(file_path: Path, table: Type[BaseTable]):
    """
    Ingest a single file into a given SQL table
    """
    logger.debug(f"Ingesting file {file_path} into table {table.__tablename__}")
    # Insert into table with sqlalchemy
    new_values = get_record_from_file(file_path=file_path)
    if new_values is None:
        logger.warning(f"Could not extract record from file {file_path}. Skipping.")
        return
    insert_record_into_table(new_entry=new_values, sql_table=table,
                             returning_keys="uimageid")
    logger.debug(f"Finished ingesting file {file_path} into table {table.__tablename__}")



def ingest_images_from_directory(dir_path: Path):
    """
    Ingest data into the winter databases.
    This takes one directory file and ingests all files in the subdetector folders in it
    e.g. dir_path = /base_path/2025W17_4B, code looks for all fits files in
    the lvl2b../<1>, <2> and so on subfolders.
    """
    logger.info(f"Ingesting images from directory: {dir_path}")
    file_list = np.sort(glob(str(dir_path / "*/*/*.fits")))
    file_list = [Path(f) for f in file_list]

    for file_path in tqdm(file_list):
        if 'cutout' in file_path.name.lower():
            continue
        logger.debug(f"Processing file: {file_path}")
        ingest_single_file_into_table(file_path, ImagesTable)
        logger.debug(f"Finished processing file: {file_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest FITS files into the WINTER database.")
    parser.add_argument("--data_dir", type=str,
                        required=False,
                        default="/mnt/home/kde10/ceph/spherex/spherex_data/level2",
                        help="Directory containing FITS files to ingest.")
    parser.add_argument("--completed_logfile", type=str, required=False,
                        default="completed_weeks.txt",)
    args = parser.parse_args()

    if args.data_dir is None and args.parquet_file is None:
        parser.error("--data_dir must be provided.")
    logger = get_logger()
    set_up_spherex_databases()
    data_dir = Path(args.data_dir) if args.data_dir else None

    completed_logfile = Path(args.completed_logfile) if args.completed_logfile else None
    if completed_logfile is None or not completed_logfile.exists():
        completed_weeks = []
    else:
        completed_weeks = np.loadtxt(completed_logfile, dtype=str).tolist()

    if data_dir is not None:
        sub_dirs = data_dir.glob("*")
        tasks = [(sub_dir,) for sub_dir in sub_dirs if
                 sub_dir.name not in completed_weeks]

        start = time()
        for i, task in enumerate(tasks):
            if i % size != rank:
                continue
            week_dir = task[0]
            logger.info(f"Rank {rank} processing directory: {week_dir}")
            ingest_images_from_directory(week_dir)
            with open(completed_logfile, 'a') as f:
                f.write(f"{week_dir.name}\n")
            logger.info(f"Rank {rank} finished directory: {week_dir}")
        end = time()

    logger.info(f"Finished ingesting data into the database in "
                f"{end - start:.2f} seconds.")
