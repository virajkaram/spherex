import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import logging
matplotlib.use('Agg')  # Use non-interactive backend

logger = logging.getLogger(__name__)

def plot_spectrum(photometry_df: pd.DataFrame, ra: float, dec: float,
                    output_plotname: str):
    fig = plt.figure(figsize=(8, 5))
    unflagged = photometry_df[~photometry_df["flagged"]]
    flagged = photometry_df[photometry_df["flagged"]]

    plt.errorbar(unflagged["wavelength_um"], unflagged["flux_jy"],
                 yerr=unflagged["flux_err_jy"], fmt='.', capsize=3, label="Unflagged",
                 color='black')
    plt.scatter(flagged["wavelength_um"], flagged["flux_jy"],
                color='red', marker='x', s=40, label="Flagged")

    plt.yscale("log")
    plt.xlabel("Wavelength (µm)")
    plt.ylabel("Flux (Jy)")
    plt.title(f"SPHEREx Spectrum at RA={ra:.6f}, Dec={dec:.6f}")
    plt.grid(True, which="both", linestyle="--", alpha=0.5)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_plotname)
    plt.close(fig)
