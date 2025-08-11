"""
Base class for models
"""

import os

from sqlalchemy.orm import DeclarativeBase

from spherex.database.base_table import BaseTable

DB_NAME = os.getenv("DB_NAME", "spherex")


class SPHEREXBase(DeclarativeBase, BaseTable):
    """
    Parent class for summer database
    """

    db_name = DB_NAME
