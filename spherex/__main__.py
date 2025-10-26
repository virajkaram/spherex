import pandas as pd
from spherex.extract import extract_aperture_photometry, APERTURE_RADIUS
from spherex.tables import LATEST_QR_VERSION
from spherex.log import get_logger
from spherex.utils import get_timetagged_output_dir, BASE_OUTPUT_DIR
import argparse
import logging
from pathlib import Path
from tqdm import tqdm

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Perform aperture photometry on "
                                                 "images within a certain radius "
                                                 "of given coordinates.")
    parser.add_argument("--ra", type=float, help="Right Ascension in degrees")
    parser.add_argument("--dec", type=float, help="Declination in degrees")
    parser.add_argument("--name", type=str,
                        help="Source name", default="source")
    parser.add_argument("--filename", type=str,
                        help="File name with multiple sources")
    parser.add_argument("--aperture_radius", type=float,
                        default=APERTURE_RADIUS,
                        help="Aperture radius in pixels (default: 3.0)")
    parser.add_argument("--loglevel", type=str, default="INFO",)
    parser.add_argument("--plot_cutouts", action="store_true",)
    parser.add_argument("--output_dir_name", type=str, default=None)
    parser.add_argument("--name_key", type=str, default="name",)
    parser.add_argument("--ra_key", type=str, default="ra",)
    parser.add_argument("--dec_key", type=str, default="dec",)
    parser.add_argument("--qr_version", type=int,
                        default=LATEST_QR_VERSION)
    args = parser.parse_args()

    logger = get_logger(level=args.loglevel)

    if args.output_dir_name is None:
        output_directory = get_timetagged_output_dir(BASE_OUTPUT_DIR)
    else:
        output_directory = Path(BASE_OUTPUT_DIR) / args.output_dir_name
        output_directory.mkdir(parents=True, exist_ok=True)

    if (args.filename is None) and ((args.ra is None) or (args.dec is None)):
        parser.error("Either --filename or both --ra and --dec must be provided.")

    if args.filename is not None:
        source_data = pd.read_csv(args.filename)
        for col in [args.name_key, args.ra_key, args.dec_key]:
            if col not in source_data.columns:
                raise ValueError(f"Input file must contain column: {col}")

        logger.info(f"Processing {len(source_data)} sources from {args.filename}")
        for idx, row in tqdm(source_data.iterrows(), total=len(source_data)):
            extract_aperture_photometry(ra=row['ra'], dec=row['dec'],
                                        aperture_radius=args.aperture_radius,
                                        name=row['name'],
                                        output_dir=output_directory,
                                        plot_cutouts=args.plot_cutouts,
                                        qr_version=args.qr_version,
                                        )

    if (args.ra is not None) and (args.dec is not None):
        extract_aperture_photometry(ra=args.ra, dec=args.dec,
                                    aperture_radius=args.aperture_radius,
                                    name=args.name,
                                    output_dir=output_directory,
                                    plot_cutouts=args.plot_cutouts,
                                    qr_version=args.qr_version,
                                    )

    logger.info(f"Output directory: {output_directory}")
