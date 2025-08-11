"""
Module to export data to a database table
"""

import logging
from typing import Type

import pandas as pd
from sqlalchemy import Insert, column

from spherex.database.base_table import BaseTable
from spherex.database.engine import get_engine

logger = logging.getLogger(__name__)


def _insert_in_table(
    new_entry: dict,
    sql_table: Type[BaseTable],
    returning_keys: list[str] | str = None,
) -> pd.DataFrame:
    """
    Export a list of fields in value dict to a database table

    :param new_entry: dictionary/DataBlock/other dictonary-like object to export
    :param sql_table: table of DB to export to
    :param returning_keys: keys to return (default: all)
    :return:
    """
    if not isinstance(returning_keys, list):
        returning_keys = [returning_keys]

    db_name = sql_table.db_name

    stmt = (
        Insert(sql_table)
        .values(new_entry)
        .returning(*[column(x) for x in returning_keys])
    )

    engine = get_engine(db_name=db_name)

    with engine.connect() as conn:
        res = conn.execute(stmt)
        conn.commit()

    return pd.DataFrame(res.fetchall())
