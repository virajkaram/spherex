from pathlib import Path
from astropy.io import fits
from astropy.wcs import WCS
from astropy.time import Time
import os


BASE_OUTPUT_DIR = os.getenv("SPHEREX_OUTPUT_DIR", None)
if BASE_OUTPUT_DIR is None:
    raise ValueError("Please provide a valid output directory in the environment variable SPHEREX_OUTPUT_DIR.")


def get_image_coords_from_file(ra: float, dec: float, filepath: Path):
    with fits.open(filepath, memmap=False) as hdulist:
        header = hdulist[1].header
        wcs = WCS(header)
        x, y = wcs.world_to_pixel_values(ra, dec)
        naxis1 = header.get("NAXIS1", 2048)
        naxis2 = header.get("NAXIS2", 2048)
        if 0 <= x < naxis1 and 0 <= y < naxis2:
            return x, y
        else:
            raise ValueError("Coordinates are outside image bounds.")


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