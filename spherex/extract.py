from pathlib import Path
import numpy as np
import pandas as pd
from astropy.io import fits
from astropy.wcs import WCS
from photutils.aperture import CircularAperture, aperture_photometry
import logging
import warnings
warnings.filterwarnings("ignore", category=UserWarning, append=True)

logger = logging.getLogger(__name__)

APERTURE_RADIUS = 2  # pixels

# --- Bitmask for SPHEREx bad flags ---
BITMASK = (
    (1 << 0)  | (1 << 1)  | (1 << 2)  |
    (1 << 6)  | (1 << 7)  | (1 << 9)  |
    (1 << 10) | (1 << 11) | (1 << 15)
)


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


def aperture_photometry_on_file(x: float, y: float,
                                filepath: Path,
                                aperture_radius: float = APERTURE_RADIUS
                                ):
    lam, dlam, flux_jy, flux_err_jy, is_masked = np.nan, np.nan, np.nan, np.nan, True
    try:
        with fits.open(filepath, memmap=False) as hdul:
            flux_img = hdul["IMAGE"].data
            var_img = hdul["VARIANCE"].data
            flags_img = hdul["FLAGS"].data
            zodi_img = hdul["ZODI"].data
            flux_img -= zodi_img

            logger.info(f"Median of the zodiacal subtracted image"
                         f" is {np.nanmedian(flux_img):.3e}")

            aperture = CircularAperture([(x, y)], r=aperture_radius)

            # Evaluate mask across full image shape
            mask = aperture.to_mask(method="center")[0]
            aper_mask = mask.to_image(shape=flags_img.shape)
            aper_flags = flags_img[aper_mask.astype(bool)]
            is_flagged = np.any(aper_flags & BITMASK)

            # Photometry
            flux_tbl = aperture_photometry(flux_img, aperture)
            var_tbl = aperture_photometry(var_img, aperture)
            flux = flux_tbl["aperture_sum"][0]
            flux_err = np.sqrt(var_tbl["aperture_sum"][0])

            wave_wcs = WCS(hdul[1].header, hdul, key='W')
            lam, dlam = wave_wcs.wcs_pix2world(x, y, 0)

            arcsec_per_pix = 6.15
            pix_area_sr = (arcsec_per_pix / 3600 * np.pi / 180) ** 2
            flux_jy = flux * pix_area_sr * 1e6
            flux_err_jy = flux_err * pix_area_sr * 1e6
    except Exception as e:
        logger.error(f"Failed on {filepath}: {e}")

    return lam, dlam, flux_jy, flux_err_jy, is_flagged


def perform_aperture_photometry_on_list(ra: float, dec: float,
                                        filelist: list,
                                        aperture_radius: float = APERTURE_RADIUS) -> pd.DataFrame:
    results = []
    logger.info(f"Running aperture photometry for RA={ra}, Dec={dec} on {len(filelist)} files.")
    for filepath in filelist:
        try:
            x, y = get_image_coords_from_file(ra, dec, filepath)
            lam, dlam, flux_jy_val, flux_err_jy_val, is_masked = aperture_photometry_on_file(x, y, filepath,
                                                                                             aperture_radius=aperture_radius)
            results.append({
                "file": filepath.name,
                "wavelength_um": lam,
                "bandwidth_um": dlam,
                "flux_jy": flux_jy_val,
                "flux_err_jy": flux_err_jy_val,
                "flagged": is_masked
            })
            logger.info(f"Processed {filepath}: λ={lam:.3f} µm, Flux={flux_jy_val:.3e} Jy {'(FLAGGED)' if is_masked else ''}")
        except ValueError as ve:
            logger.warning(f"Skipping {filepath}: {ve}")
        except Exception as e:
            logger.error(f"Error processing {filepath}: {e}")
    results_df = pd.DataFrame(results)
    return results_df
