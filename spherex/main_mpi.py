import pandas as pd
from spherex.extract import (perform_aperture_photometry_on_list,
                             APERTURE_RADIUS, ANNULUS_R_IN, ANNULUS_R_OUT)
from spherex.cutouts import make_cutout_plots_from_filelist
from spherex.log import get_logger
from spherex.retrieve_files import get_images_within_coordinates
from spherex.plot import plot_spectrum
import argparse
import logging
import os
from pathlib import Path
from astropy.time import Time
from mpi4py import MPI


comm = MPI.COMM_WORLD # Initialize the MPI communicator
rank = comm.Get_rank() # The rank of the current process
size = comm.Get_size()  # Total number of processes

logger = logging.getLogger(__name__)

BASE_OUTPUT_DIR = os.getenv("SPHEREX_OUTPUT_DIR", None)
if BASE_OUTPUT_DIR is None:
    raise ValueError("Please provide a valid output directory in the environment variable SPHEREX_OUTPUT_DIR.")

def get_timetagged_output_dir(base_output_dir: str | Path) -> Path:
    """
    Create a time-tagged output directory within the base output directory.
    """
    base_output_dir = Path(base_output_dir)
    current_time = Time.now()
    timetag = current_time.strftime("%Y%m%dT%H%M%S")
    output_dir = base_output_dir / f"request_{timetag}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def extract_aperture_photometry(ra, dec,
                                aperture_radius=APERTURE_RADIUS,
                                annulus_inner_radius=ANNULUS_R_IN,
                                annulus_outer_radius=ANNULUS_R_OUT,
                                name="source",
                                output_dir: Path=get_timetagged_output_dir(BASE_OUTPUT_DIR),
                                plot_cutouts: bool=False,
                                ):
    """
    Main function to extract aperture photometry from images within a certain radius of given coordinates.
    """
    xmatch_filenames_df = get_images_within_coordinates(ra=ra, dec=dec)
    logger.debug(f"Found {len(xmatch_filenames_df)} files.")

    if len(xmatch_filenames_df) > 0:
        file_paths = [Path(x) for x in xmatch_filenames_df['savepath'].tolist()]
        logger.debug(f"Performing aperture photometry on {len(file_paths)} images.")
        photometry_results = perform_aperture_photometry_on_list(ra=ra,
                                                                 dec=dec,
                                                                 filelist=file_paths,
                                                                 aperture_radius=aperture_radius,
                                                                 annulus_inner_radius=annulus_inner_radius,
                                                                 annulus_outer_radius=annulus_outer_radius,
                                                                 )
        photometry_filename = output_dir / f"spectrum_{name}_ra{ra:.5f}_dec{dec:.5f}.csv"
        photometry_results.to_csv(photometry_filename,
                                  index=False)
        plot_spectrum(photometry_results, ra=ra, dec=dec,
                      output_plotname=f"{output_dir}/spectrum_{name}_ra{ra:.5f}_dec{dec:.5f}.pdf")

        if plot_cutouts:
            cutout_plotname = Path(output_dir) / f"cutouts_{name}_ra{ra:.5f}_dec{dec:.5f}.pdf"
            photometry_results = pd.read_csv(photometry_filename)
            if len(photometry_results) > 0:
                output_plotname = cutout_plotname.as_posix()
                text_strings = [f"{round(row['wavelength_um'], 3)} um" for idx, row in photometry_results.iterrows()]
                make_cutout_plots_from_filelist(photometry_results['file'].to_list(),
                                                ra, dec,
                                                output_plotname,
                                                title_text=text_strings,
                                                aperture_radius=aperture_radius,
                                                annulus_r_in=annulus_inner_radius,
                                                annulus_r_out=annulus_outer_radius,
                                                )
                logger.info(f"Saved cutout plots to {output_plotname}")
        logger.debug("Aperture photometry completed.")

    else:
        logger.debug("No images found to perform aperture photometry.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Perform aperture photometry on "
                                                 "images within a certain radius "
                                                 "of given coordinates.")
    parser.add_argument("--filename", type=str,
                        help="File name with multiple sources")
    parser.add_argument("--aperture_radius", type=float, default=3.0,
                        help="Aperture radius in pixels (default: 3.0)")
    parser.add_argument("--loglevel", type=str, default="INFO",)
    parser.add_argument("--plot_cutouts", action="store_true",)
    parser.add_argument("--output_dir_name", type=str, default=None)
    args = parser.parse_args()

    logger = get_logger(level=args.loglevel)

    if args.output_dir_name is None:
        output_directory = get_timetagged_output_dir(BASE_OUTPUT_DIR)
    else:
        output_directory = Path(BASE_OUTPUT_DIR) / args.output_dir_name
        output_directory.mkdir(parents=True, exist_ok=True)

    if (args.filename is None):
        parser.error("--filename must be provided.")

    if args.filename is not None:
        source_data = pd.read_csv(args.filename)
        assert set(["ra", "dec", "name"]) == set(list(source_data.columns)), \
            "Input file must contain columns: ra, dec, name"

        logger.info(f"Processing {len(source_data)} sources from {args.filename}")

        tasks = [(row['ra'], row['dec'], args.aperture_radius, row['name'], output_directory, args.plot_cutouts)
                 for idx, row in source_data.iterrows()]
        for i, task in enumerate(tasks):
            if i % size != rank:
                continue
            ra, dec, aperture_radius, name, output_dir, plot_cutouts = task
            logger.info(f"Rank {rank} processing source: {name} (RA={ra}, Dec={dec})")
            extract_aperture_photometry(ra=ra, dec=dec,
                                        aperture_radius=aperture_radius,
                                        name=name,
                                        output_dir=output_dir,
                                        plot_cutouts=plot_cutouts
                                        )

    logger.info(f"Output directory: {output_directory}")
