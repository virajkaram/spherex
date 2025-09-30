from pathlib import Path
from astropy.io import fits
from astropy.wcs import WCS


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
