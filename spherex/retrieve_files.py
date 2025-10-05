import argparse
import logging
from spherex.tables import ImagesTable
from spherex.database.transactions import select_from_table
from spherex.database.constraints import DBQueryConstraints
from spherex.log import get_logger


logger = logging.getLogger(__name__)

def get_images_within_coordinates(ra: float, dec: float):
    """
    Retrieve files within a certain radius of given coordinates from the database.

    :param ra: Right Ascension in degrees
    :param dec: Declination in degrees
    :return: List of file paths
    """
    constraints = DBQueryConstraints()
    constraints.add_postgis_within_constraint(ra=ra,
                                              dec=dec,
                                              footprint_column_name='footprint')

    results = select_from_table(sql_table=ImagesTable,
                                db_constraints=constraints,
                                output_columns=['savepath']
                                )

    # replace 'kde10' with '' in savepaths
    results['savepath'] = results['savepath'].str.replace('kde10', '', regex=False)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Retrieve files within a certain radius of given coordinates.")
    parser.add_argument("--ra", type=float, required=True, help="Right Ascension in degrees")
    parser.add_argument("--dec", type=float, required=True, help="Declination in degrees")
    args = parser.parse_args()

    results = get_images_within_coordinates(ra=args.ra, dec=args.dec)
    logger = get_logger()
    logger.info(f"Found {len(results)} files containing RA={args.ra}, Dec={args.dec}.")