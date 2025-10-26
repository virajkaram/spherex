from spherex.tables._images import ImagesTable, LATEST_QR_VERSION
from spherex.tables.base import SPHEREXBase
import logging
from spherex.database.credentials import DB_USER
from spherex.database.setup import setup_database
from spherex.database.q3c import create_q3c_extension, create_postgis_index
from spherex.database.base_table import BaseTable

logger = logging.getLogger(__name__)

def set_up_q3c(db_name: str, db_table: BaseTable):
    """
    Function to setup q3c extension for a given table in db

    :param db_name: Name of database
    :param db_table: Table to setup q3c extension for
    :return:
    """
    create_q3c_extension(
        db_name=db_name,
        table_name=db_table.__tablename__,
        ra_column_name=db_table.ra_column_name,
        dec_column_name=db_table.dec_column_name,
    )


def set_up_postgis(db_name: str, db_table: BaseTable):
    """
    Function to setup postgis extension for a given table in db

    :param db_name: Name of database
    :param db_table: Table to setup postgis extension for
    :return:
    """
    create_postgis_index(
        db_name=db_name,
        table_name=db_table.__tablename__,
        column_name=db_table.geom_column_name,
    )

def set_up_spherex_databases():
    """
    Setup the winter databases

    :return: None
    """

    if DB_USER is not None:
        setup_database(db_base=SPHEREXBase)

        for table in [
            ImagesTable,
        ]:
            set_up_q3c(db_name=SPHEREXBase.db_name, db_table=table)
            set_up_postgis(db_name=SPHEREXBase.db_name, db_table=table)

    else:
        logger.warning("No database user provided. Skipping WINTER database setup.")
