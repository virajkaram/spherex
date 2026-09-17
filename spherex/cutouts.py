import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
from spherex.utils import get_image_coords_from_file
import numpy as np
import pandas as pd
from astropy.io import fits
from astropy.wcs import WCS
from astropy.stats import sigma_clipped_stats
from photutils.aperture import CircularAperture, CircularAnnulus
from astropy.visualization import AsinhStretch, ImageNormalize
from matplotlib.backends.backend_pdf import PdfPages
import argparse
from pathlib import Path
import logging
from spherex.retrieve_files import get_images_within_coordinates


logger = logging.getLogger(__name__)

logger.setLevel('WARNING')


def get_observation_log(filelist, ra, dec):
    """
    Build a dataframe describing where (ra, dec) falls on each file in filelist.

    For each file, records the pixel position (x, y) of (ra, dec) and the
    wavelength at that pixel, using the same 'W' WCS key used for wavelength
    calibration in extract.aperture_photometry_on_file. Files where (ra, dec)
    falls outside the image bounds are skipped. The result is sorted by
    wavelength.

    :param filelist: list of FITS file paths.
    :param ra: Right Ascension in degrees.
    :param dec: Declination in degrees.
    :return: DataFrame with columns file_index, filename, x, y, wavelength_um,
        sorted by wavelength_um.
    """
    records = []
    for idx, filename in enumerate(filelist):
        try:
            x, y = get_image_coords_from_file(ra, dec, filename)
            with fits.open(filename, memmap=False) as hdul:
                wave_wcs = WCS(hdul[1].header, hdul, key='W')
                lam, dlam = wave_wcs.wcs_pix2world(x, y, 0)
            records.append({
                "file_index": idx,
                "filename": filename,
                "x": x,
                "y": y,
                "wavelength_um": float(lam),
            })
        except ValueError as e:
            logger.warning(f"Skipping {filename}: {e}")
        except Exception as e:
            logger.warning(f"Failed to build observation log entry for {filename}: {e}")

    observation_log = pd.DataFrame(records,
                                   columns=["file_index", "filename", "x", "y", "wavelength_um"])
    if len(observation_log) > 0:
        observation_log = observation_log.sort_values("wavelength_um").reset_index(drop=True)
    return observation_log


def make_cutout_plot_for_file(filename, ra=None, dec=None, x=None, y=None,
                              ax = None,
                              half_width=10,
                              annulus_r_in=None,
                              annulus_r_out=None,
                              aperture_radius = None,
                              n_sigma=3,
                              title_text=None,
                              ):
    """
    Make a cutout plot from a FITS file at given RA, Dec coordinates.
    :param filename:
    :param ra:
    :param dec:
    :param ax:
    :return:
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(6, 6))

    try:
        hdul = fits.open(filename)
        flux_img = hdul[1].data
        flags_img = hdul[2].data

        if x is None or y is None:
            if ra is None or dec is None:
                raise ValueError("Either (x, y) or (ra, dec) must be provided.")

        if x is None or y is None:
            x, y = get_image_coords_from_file(ra=ra, dec=dec, filepath=filename)

        x = int(np.round(x))
        y = int(np.round(y))

        ny, nx = flux_img.shape
        x_min = max(0, x - half_width)
        x_max = min(nx, x + half_width)
        y_min = max(0, y - half_width)
        y_max = min(ny, y + half_width)

        cutout_flux = flux_img[y_min:y_max, x_min:x_max]

        _, median, std = sigma_clipped_stats(cutout_flux, sigma=3.0)
        vmin = median - n_sigma * std
        vmax = median + n_sigma * std
        norm = ImageNormalize(vmin=vmin, vmax=vmax, stretch=AsinhStretch())

        ax.imshow(cutout_flux, origin='lower', cmap='Greys', norm=norm)
        ax.set_xlabel("X Pixel")
        ax.set_ylabel("Y Pixel")

        if title_text is not None:
            ax.set_title(title_text, fontsize=10)

        # Overlay aperture and annulus
        if aperture_radius is not None:
            aperture = CircularAperture((x - x_min, y - y_min), r=aperture_radius)
            aperture.plot(ax=ax, color='red', lw=1.5, label='Aperture')

        if annulus_r_in is not None:
            annulus = CircularAnnulus((x - x_min, y - y_min),
                                      r_in=annulus_r_in,
                                      r_out=annulus_r_out)

            annulus.plot(ax=ax, color='blue', lw=1.5, label='Annulus')
        hdul.close()
        ax.legend()
        return ax
    except Exception as e:
        print(f"Failed to create cutout plot for {filename}: {e}")
        raise e


def make_cutout_plots_from_filelist(filelist, ra, dec, output_plotname,
                                    half_width=10,
                                    annulus_r_in=None,
                                    annulus_r_out=None,
                                    aperture_radius = None,
                                    n_sigma=3,
                                    title_text: str | list=None,
                                    ):
    """
    Make a multi-page pdf with each page showing 4x4 cutout plots, ordered by
    wavelength (see get_observation_log).
    :param filelist:
    :param ra:
    :param dec:
    :param output_plotname:
    :param n_sigma: normalize the display range to +/- n_sigma about the
        sigma-clipped median of each cutout.
    :return:
    """
    n_plots_per_page = 16
    n_rows = 4
    n_cols = 4

    if isinstance(title_text, str):
        title_text = [title_text] * len(filelist)
    elif isinstance(title_text, list):
        if len(title_text) != len(filelist):
            raise ValueError("Length of title_text list must match length of filelist.")

    observation_log = get_observation_log(filelist, ra, dec)

    with PdfPages(output_plotname) as pdf:
        for i in range(0, len(observation_log), n_plots_per_page):
            fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 15))
            axes = axes.flatten()

            for j in range(n_plots_per_page):
                ax = axes[j]
                ax.axis('off')  # Turn off axis by default
                row_idx = i + j
                if row_idx < len(observation_log):
                    row = observation_log.iloc[row_idx]
                    filename = row["filename"]
                    if title_text is None:
                        file_title = f"{row['wavelength_um']:.3f} um"
                    else:
                        file_title = title_text[row["file_index"]]
                    try:
                        make_cutout_plot_for_file(filename, x=row["x"], y=row["y"], ax=ax,
                                                  half_width=half_width,
                                                  annulus_r_in=annulus_r_in, annulus_r_out=annulus_r_out,
                                                  aperture_radius=aperture_radius,
                                                  n_sigma=n_sigma,
                                                  title_text=file_title,
                                                  )
                    except Exception as e:
                        ax.text(0.5, 0.5, f"Error:\n{e}", ha='center', va='center', color='red')
                else:
                    ax.text(0.5, 0.5, "No Data", ha='center', va='center', color='gray')

            plt.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)
    print(f"Cutout plots saved to {output_plotname}")
    return output_plotname


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate cutout plots from FITS files.")
    parser.add_argument("--ra", type=float, required=True, help="Right Ascension in degrees.")
    parser.add_argument("--dec", type=float, required=True, help="Declination in degrees.")
    parser.add_argument("--half_width", type=int, default=10, help="Half width of the cutout in pixels.")
    parser.add_argument("--n_sigma", type=float, default=3,
                        help="Normalize the display range to +/- n_sigma about the sigma-clipped median.")
    parser.add_argument("--output", type=str, default="cutout_plots.pdf",
                        help="Output PDF file for cutout plots.")
    args = parser.parse_args()

    xmatch_filenames_df = get_images_within_coordinates(ra=args.ra, dec=args.dec)
    file_paths = [Path(x) for x in xmatch_filenames_df['savepath'].tolist()]
    logger.info(f"Making cutout plots from {len(file_paths)} files.")
    make_cutout_plots_from_filelist(file_paths, args.ra, args.dec, args.output,
                                    half_width=args.half_width, n_sigma=args.n_sigma)
