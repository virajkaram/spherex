import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
from spherex.utils import get_image_coords_from_file
import numpy as np
from astropy.io import fits
from photutils.aperture import CircularAperture, CircularAnnulus
from astropy.visualization import (PercentileInterval, AsinhStretch,
                                   ImageNormalize)
from matplotlib.backends.backend_pdf import PdfPages
import argparse
from pathlib import Path
import logging
from spherex.retrieve_files import get_images_within_coordinates


logger = logging.getLogger(__name__)
def make_cutout_plot_for_file(filename, ra=None, dec=None, x=None, y=None,
                              ax = None,
                              half_width=10,
                              annulus_r_in=None,
                              annulus_r_out=None,
                              aperture_radius = None,
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

        norm = ImageNormalize(cutout_flux,
                              interval=PercentileInterval(99.5),
                              stretch=AsinhStretch())

        im = ax.imshow(cutout_flux, origin='lower', cmap='Greys', norm=norm)
        ax.set_xlabel("X Pixel")
        ax.set_ylabel("Y Pixel")
        plt.colorbar(im, ax=ax, label='Flux')

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
                                    title_text: str | list=None,
                                    ):
    """
    Make a multi-page pdf with each page showing 4x4 cutout plots.
    :param filelist:
    :param ra:
    :param dec:
    :param output_plotname:
    :return:
    """
    n_plots_per_page = 16
    n_rows = 4
    n_cols = 4

    if isinstance(title_text, str):
        title_text = [title_text] * len(filelist)
    elif title_text is None:
        title_text = [""] * len(filelist)
    elif isinstance(title_text, list):
        if len(title_text) != len(filelist):
            raise ValueError("Length of title_text list must match length of filelist.")
    with PdfPages(output_plotname) as pdf:
        for i in range(0, len(filelist), n_plots_per_page):
            fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 15))
            axes = axes.flatten()

            for j in range(n_plots_per_page):
                ax = axes[j]
                ax.axis('off')  # Turn off axis by default
                if i + j < len(filelist):
                    filename = filelist[i + j]
                    try:
                        x, y = get_image_coords_from_file(ra, dec, filename)
                        make_cutout_plot_for_file(filename, x=x, y=y, ax=ax, half_width=half_width,
                                                  annulus_r_in=annulus_r_in, annulus_r_out=annulus_r_out,
                                                    aperture_radius=aperture_radius, title_text=title_text[i + j],
                                                  )
                    except ValueError as e:
                        logger.warning(f"Skipping {filename}: {e}")
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
    parser.add_argument("--output", type=str, default="cutout_plots.pdf",
                        help="Output PDF file for cutout plots.")
    args = parser.parse_args()

    xmatch_filenames_df = get_images_within_coordinates(ra=args.ra, dec=args.dec)
    file_paths = [Path(x) for x in xmatch_filenames_df['savepath'].tolist()]
    logger.info(f"Making cutout plots from {len(file_paths)} files.")
    make_cutout_plots_from_filelist(file_paths, args.ra, args.dec, args.output)
