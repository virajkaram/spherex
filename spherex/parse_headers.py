from astropy.io import fits
from pathlib import Path
from astropy.wcs import WCS
import pandas as pd
from glob import glob
import logging
import argparse
from tqdm import tqdm
from spherex.tables._images import LATEST_QR_VERSION

logger = logging.getLogger(__name__)


def header_to_polygon_wkt(header: fits.Header) -> str:
    w = WCS(header)
    nx = header["NAXIS1"]
    ny = header["NAXIS2"]

    # pixel coords for corners, closed loop
    pixels = [(0, 0), (nx, 0), (nx, ny), (0, ny), (0, 0)]
    ras, decs = w.all_pix2world(pixels, 0).T

    # WKT polygon: lon lat order
    coords_str = ", ".join(f"{ra} {dec}" for ra, dec in zip(ras, decs))
    return f"POLYGON(({coords_str}))"


def get_record_from_file(file_path: str | Path):
    """
    Extract relevant header information from a FITS file to create a record.
    :param file_path:
    :return:
    """

    image_hdulist = fits.open(file_path)
    footprint_polygon = header_to_polygon_wkt(image_hdulist[1].header)
    new_values = {
        "savepath": file_path.as_posix(),
        "crval1": image_hdulist[1].header['CRVAL1'],
        "crval2": image_hdulist[1].header['CRVAL2'],
        "footprint": footprint_polygon,
        "mjdobs": image_hdulist[1].header.get('MJD-OBS'),
        "detector": image_hdulist[1].header.get('DETECTOR'),
        "qr_version": LATEST_QR_VERSION,
    }
    image_hdulist.close()
    return new_values


def write_records_for_directory(dir_path: str | Path, out_path: str | Path):
    """
    Write records for all FITS files in a directory to a parquet file.
    :param dir_path:
    :param out_path:
    :return:
    """
    dir_path = Path(dir_path)
    out_path = Path(out_path)
    file_list = sorted(glob(str(dir_path / "*/*/*/*.fits")))
    records = []
    for file_path in tqdm(file_list):
        if 'cutout' in file_path.lower():
            continue
        try:
            rec = get_record_from_file(Path(file_path))
            records.append(rec)
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    df = pd.DataFrame(records)
    df.to_parquet(out_path, index=False)
    logger.info(f"Wrote {len(records)} records to {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse FITS headers and write records to parquet.")
    parser.add_argument("--input_dir",
                        type=str, required=True, help="Directory containing FITS files.")
    parser.add_argument("--output_file",
                        type=str,
                        help="Output parquet file path.",
                        default="spherex_records.parquet"
                        )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    write_records_for_directory(args.input_dir, args.output_file)
