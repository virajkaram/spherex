from spherex.extract import perform_aperture_photometry_on_list, APERTURE_RADIUS
from spherex.log import get_logger
from spherex.retrieve_files import get_images_within_coordinates
from spherex.plot import plot_spectrum
import argparse
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

OUTPUT_DIR = os.getenv("SPHEREX_OUTPUT_DIR", None)
if OUTPUT_DIR is None:
    raise ValueError("Please provide a valid output directory in the environment variable SPHEREX_OUTPUT_DIR.")

def extract_aperture_photometry(ra, dec, search_radius=5.0,
                                aperture_radius=APERTURE_RADIUS):
    """
    Main function to extract aperture photometry from images within a certain radius of given coordinates.
    """
    xmatch_filenames_df = get_images_within_coordinates(ra=ra, dec=dec,
                                            radius_deg=search_radius)
    logger.info(f"Found {len(xmatch_filenames_df)} files.")

    if len(xmatch_filenames_df) > 0:
        file_paths = [Path(x) for x in xmatch_filenames_df['savepath'].tolist()]
        logger.info(f"Performing aperture photometry on {len(file_paths)} images.")
        photometry_results = perform_aperture_photometry_on_list(ra=ra,
                                                                 dec=dec,
                                                                 filelist=file_paths,
                                                                 aperture_radius=aperture_radius)
        photometry_results.to_csv(f"{OUTPUT_DIR}/spectrum_ra{ra:.5f}_dec{dec:.5f}.csv",
                                  index=False)
        plot_spectrum(photometry_results, ra=ra, dec=dec,
                      output_plotname=f"{OUTPUT_DIR}/spectrum_ra{ra:.5f}_dec{dec:.5f}.pdf")
        logger.info("Aperture photometry completed.")

    else:
        logger.info("No images found to perform aperture photometry.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Perform aperture photometry on images within a certain radius of given coordinates.")
    parser.add_argument("--ra", type=float, required=True, help="Right Ascension in degrees")
    parser.add_argument("--dec", type=float, required=True, help="Declination in degrees")
    parser.add_argument("--search_radius", type=float, default=5.0, help="Search radius in degrees (default: 5.0)")
    parser.add_argument("--aperture_radius", type=float, default=3.0, help="Aperture radius in pixels (default: 3.0)")
    args = parser.parse_args()

    logger = get_logger()

    extract_aperture_photometry(ra=args.ra, dec=args.dec,
                                search_radius=args.search_radius,
                                aperture_radius=args.aperture_radius)

