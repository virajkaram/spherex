"""
Models for the 'raw' table
"""
from sqlalchemy import Column, Integer, Sequence, Float, VARCHAR
from spherex.tables.base import SPHEREXBase
from geoalchemy2 import Geometry


class ImagesTable(SPHEREXBase):  # pylint: disable=too-few-public-methods
    """
    Raw table in database
    """

    __tablename__ = "images"
    __table_args__ = {"extend_existing": True}

    uimageid = Column(
        Integer,
        Sequence(start=1, name="image_uimageid_seq"),
        autoincrement=True,
        primary_key=True,
    )

    crval1 = Column(Float, nullable=False)
    crval2 = Column(Float, nullable=False)
    savepath = Column(VARCHAR(255), unique=True, nullable=False)
    footprint = Column(Geometry("POLYGON", srid=4326), nullable=False)
    mjdobs = Column(Float, nullable=False)
    detector = Column(Integer, nullable=False)

    ra_column_name = "crval1"
    dec_column_name = "crval2"
    geom_column_name = "footprint"
