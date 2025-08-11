"""
Module to define PSQL database tables using sqlalchemy
"""

import logging
import os
from sqlalchemy import inspect

logger = logging.getLogger(__name__)


DB_NAME = os.getenv("DB_NAME", "spherex")


class BaseTable:
    """
    Parent class for database tables. Tables should inherit from this
    and DeclarativeBase.
    """

    @property
    def __tablename__(self):
        raise NotImplementedError


    @property
    def __db_name__(self):
        raise NotImplementedError

    def get_primary_key(self) -> str:
        """
        Function to get primary key of table
        Returns:
        primary key
        """
        return inspect(self.__class__).primary_key[0].name
