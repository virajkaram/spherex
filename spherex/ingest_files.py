from sqlalchemy.exc import IntegrityError
from spherex.tables import set_up_winter_databases
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
import pandas as pd
import argparse


logger = logging.getLogger(__name__)


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
    Ingest data into the winter databases
    """
    logger.info(f"Ingesting images from directory: {dir_path}")
    file_list = np.sort(glob(str(dir_path / "*/*/*/*.fits")))
    file_list = [Path(f) for f in file_list]
    for file_path in tqdm(file_list):
        if 'cutout' in file_path.name.lower():
            continue
        logger.debug(f"Processing file: {file_path}")
        ingest_single_file_into_table(file_path, ImagesTable)
        logger.debug(f"Finished processing file: {file_path}")


def ingest_images_from_file(file_path: Path):
    """
    Read records written to a parquet file and ingest them into the database.
    :param file_path:
    :return:
    """
    logger.info(f"Ingesting images from parquet file: {file_path}")
    df = pd.read_parquet(file_path)
    for idx, row in tqdm(df.iterrows()):
        new_values = row.to_dict()
        insert_record_into_table(new_entry=new_values, sql_table=ImagesTable,
                                 returning_keys="uimageid")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest FITS files into the WINTER database.")
    parser.add_argument("--data_dir", type=str, required=False,
                        help="Directory containing FITS files to ingest.")
    parser.add_argument("--parquet_file", type=str, required=False,
                        help="Parquet file containing records to ingest.")
    args = parser.parse_args()
    if args.data_dir is None and args.parquet_file is None:
        parser.error("Either --data_dir or --parquet_file must be provided.")
    logger = get_logger()
    set_up_winter_databases()
    data_dir = Path(args.data_dir) if args.data_dir else None
    parquet_file = Path(args.parquet_file) if args.parquet_file else None
    if parquet_file is not None:
        ingest_images_from_file(parquet_file)
    if data_dir is not None:
        ingest_images_from_directory(data_dir)

    logger.info("Finished ingesting data into the database.")
