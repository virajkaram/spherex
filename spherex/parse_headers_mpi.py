from astropy.io import fits
from pathlib import Path
from astropy.wcs import WCS
import pandas as pd
from glob import glob
import logging
import argparse
from tqdm import tqdm
from mpi4py import MPI
from spherex.tables._images import LATEST_QR_VERSION

logger = logging.getLogger(__name__)


def header_to_polygon_wkt(header: fits.Header) -> str:
    """Convert FITS header WCS info to a WKT polygon."""
    w = WCS(header)
    nx, ny = header["NAXIS1"], header["NAXIS2"]
    pixels = [(0, 0), (nx, 0), (nx, ny), (0, ny), (0, 0)]
    ras, decs = w.all_pix2world(pixels, 0).T
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
    new_values = image_hdulist[1].header.to_dict()
    # Replace - by _ in keys
    for key in list(new_values.keys()):
        if '-' in key:
            new_key = key.replace('-', '_')
            new_values[new_key] = new_values.pop(key)
    new_values["footprint"] = footprint_polygon
    new_values["savepath"] = file_path.as_posix()
    new_values["qr_version"] = LATEST_QR_VERSION

    image_hdulist.close()
    return new_values


def process_files(file_list):
    """Process a list of FITS files and return a DataFrame."""
    records = []
    for file_path in tqdm(file_list, disable=True):  # disable tqdm on worker ranks
        if "cutout" in file_path.lower():
            continue
        try:
            rec = get_record_from_file(Path(file_path))
            records.append(rec)
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    return pd.DataFrame(records)


def write_records_for_directory(dir_path: str | Path, out_path: str | Path):
    """Distribute FITS processing across MPI ranks and write combined parquet."""
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    dir_path = Path(dir_path)
    out_path = Path(out_path)

    # Rank 0 collects file list and distributes
    if rank == 0:
        file_list = sorted(glob(str(dir_path / "*/*/*/*.fits")))
        logger.info(f"Found {len(file_list)} FITS files.")
    else:
        file_list = None

    # Broadcast the file list
    file_list = comm.bcast(file_list, root=0)

    # Divide files among ranks
    chunk = file_list[rank::size]

    # Each rank processes its chunk
    local_df = process_files(chunk)

    # Gather all dataframes at root
    gathered = comm.gather(local_df, root=0)

    # Root combines and writes
    if rank == 0:
        combined = pd.concat(gathered, ignore_index=True)
        combined.to_parquet(out_path, index=False)
        logger.info(f"Wrote {len(combined)} records to {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse FITS headers in parallel with MPI.")
    parser.add_argument("--input_dir", type=str,
                        help="Directory containing FITS files.",
                        default="/mnt/home/spherex/ceph/spherex_data_qr2/level2/")
    parser.add_argument("--output_file", type=str, default="spherex_records_qr2.parquet",
                        help="Output parquet file path.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    write_records_for_directory(args.input_dir, args.output_file)
