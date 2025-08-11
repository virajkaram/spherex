import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import argparse
from astropy.io import fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
from astropy.io.fits import Header
from astropy import units as u
from photutils.aperture import CircularAperture, aperture_photometry
from tqdm import tqdm

# --- Parse arguments ---
parser = argparse.ArgumentParser(description="Extract SPHEREx spectrum at given RA, Dec.")
parser.add_argument("--ra", type=float, required=True, help="Right Ascension in degrees")
parser.add_argument("--dec", type=float, required=True, help="Declination in degrees")
parser.add_argument("--radius", type=float, default=5.0, help="Search radius in degrees (default: 5.0)")
args = parser.parse_args()

RA_TARGET = args.ra
DEC_TARGET = args.dec
SEARCH_RADIUS_DEG = args.radius

# --- Output filenames ---
name_stub = f"ra{RA_TARGET:.5f}_dec{DEC_TARGET:.5f}".replace('.', 'p')
OUTPUT_TABLE = f"spectrum_{name_stub}.txt"
OUTPUT_PLOT = f"spectrum_{name_stub}.pdf"

# --- Config ---
INDEX_JSON = "spherex_fits_image_wcs_index.json"
APERTURE_RADIUS = 2  # pixels

# --- Bitmask for SPHEREx bad flags ---
exclude_mask = (
    (1 << 0)  | (1 << 1)  | (1 << 2)  |
    (1 << 6)  | (1 << 7)  | (1 << 9)  |
    (1 << 10) | (1 << 11) | (1 << 15)
)

# --- Load index ---
print("Loading index...")
with open(INDEX_JSON, "r") as f:
    index = json.load(f)
print(f"Index has {len(index)} entries.")

# --- Filter entries by proximity to target ---
print(f"Filtering entries within {SEARCH_RADIUS_DEG}° of target...")
ra_vals, dec_vals, idxs = [], [], []
for i, e in enumerate(index):
    try:
        ra = float(e.get("crval1"))
        dec = float(e.get("crval2"))
        if np.isfinite(ra) and np.isfinite(dec):
            ra_vals.append(ra)
            dec_vals.append(dec)
            idxs.append(i)
    except Exception:
        continue

coord_all = SkyCoord(ra=np.array(ra_vals) * u.deg, dec=np.array(dec_vals) * u.deg)
coord_target = SkyCoord(ra=RA_TARGET * u.deg, dec=DEC_TARGET * u.deg)
separations = coord_all.separation(coord_target).deg
keep_mask = separations <= SEARCH_RADIUS_DEG
coarse_filtered = [index[idxs[i]] for i in np.where(keep_mask)[0]]

print(f"{len(coarse_filtered)} candidates within {SEARCH_RADIUS_DEG}° of target.")

# --- Validate pixel coverage via WCS ---
valid_entries = []
for entry in tqdm(coarse_filtered, desc="Validating WCS coverage"):
    try:
        wcs = WCS(Header(entry["wcs_header"]))
        x, y = wcs.world_to_pixel(coord_target)
        naxis1 = entry["wcs_header"].get("NAXIS1", 2048)
        naxis2 = entry["wcs_header"].get("NAXIS2", 2048)
        if 0 <= x < naxis1 and 0 <= y < naxis2:
            entry["pixel_coords"] = (x, y)
            valid_entries.append(entry)
    except Exception:
        continue

if not valid_entries:
    print("No valid FITS files cover this target.")
    exit(0)

print(f"{len(valid_entries)} FITS files cover the target.")

# --- Extract spectrum ---
records = []
for entry in valid_entries:
    fpath = entry["file"]
    x, y = entry["pixel_coords"]
    print(f"Trying file: {fpath}, pixel: ({x:.2f}, {y:.2f})")

    try:
        with fits.open(fpath, memmap=False) as hdul:
            flux_img = hdul["IMAGE"].data
            var_img = hdul["VARIANCE"].data
            flags_img = hdul["FLAGS"].data
            aperture = CircularAperture([(x, y)], r=APERTURE_RADIUS)

            # Evaluate mask across full image shape
            mask = aperture.to_mask(method="center")[0]
            aper_mask = mask.to_image(shape=flags_img.shape)
            aper_flags = flags_img[aper_mask.astype(bool)]
            is_flagged = np.any(aper_flags & exclude_mask)

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

            records.append({
                "wavelength_um": lam,
                "bandwidth_um": dlam,
                "flux_jy": flux_jy,
                "flux_err_jy": flux_err_jy,
                "flagged": is_flagged,
                "file": os.path.basename(fpath)
            })
            print(f"λ = {lam:.3f} µm, Flux = {flux_jy:.3e} Jy", "(FLAGGED)" if is_flagged else "")

    except Exception as e:
        print(f"Failed on {fpath}: {e}")
        continue

# --- Save spectrum ---
df = pd.DataFrame(records)
df = df.sort_values("wavelength_um")
df.to_csv(OUTPUT_TABLE, sep="\t", index=False)
print(f"Spectrum saved to {OUTPUT_TABLE}")

# --- Plot spectrum with flagged points ---
plt.figure(figsize=(8, 5))
unflagged = df[~df["flagged"]]
flagged = df[df["flagged"]]

plt.errorbar(unflagged["wavelength_um"], unflagged["flux_jy"],
             yerr=unflagged["flux_err_jy"], fmt='.', capsize=3, label="Unflagged", color='black')
plt.scatter(flagged["wavelength_um"], flagged["flux_jy"],
            color='red', marker='x', s=40, label="Flagged")

plt.yscale("log")
plt.xlabel("Wavelength (µm)")
plt.ylabel("Flux (Jy)")
plt.title(f"SPHEREx Spectrum at RA={RA_TARGET:.6f}, Dec={DEC_TARGET:.6f}")
plt.grid(True, which="both", linestyle="--", alpha=0.5)
plt.legend()
plt.tight_layout()
plt.savefig(OUTPUT_PLOT)
print(f"Plot saved to {OUTPUT_PLOT}")