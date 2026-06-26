#!/usr/bin/env python3
"""
Upload SPHEREx spectra to IRTOM.

Reads files matching spectrum_<name>_*.csv from a folder, converts columns to
the TOM format, and uploads each as a spherex data product.

Usage:
    python upload_spherex.py /path/to/folder --token <api_token>

CSV columns expected: wavelength_um, flux_bkgsub_jy, flux_bkgsub_err_jy, mjd
Flux is converted from Jy to uJy on upload.
"""

import os
import glob
import argparse

import requests
import pandas as pd
from astropy.time import Time

BASE_URL = os.getenv('TOM_BASE_URL', None)
TMP_FILE = 'spectrum_tmp.csv'
token = os.environ.get('TOM_API_TOKEN', None)
if token is None or BASE_URL is None:
    raise ValueError('TOM_API_TOKEN or TOM_BASE_URL environment variable not set')

def get_target_id(session, name):
    resp = session.get(f'{BASE_URL}/api/targets/', params={'name': name})
    resp.raise_for_status()
    results = resp.json().get('results', [])
    if not results:
        raise ValueError(f'No target found with name: {name}')
    return results[0]['id']


def upload_spectrum(session, target_id, csv_path):
    with open(csv_path, 'rb') as f:
        resp = session.post(
            f'{BASE_URL}/api/dataproducts/',
            data={'target': target_id, 'data_product_type': 'spherex'},
            files={'file': (os.path.basename(csv_path), f, 'text/csv')},
        )
    resp.raise_for_status()
    return resp.json()


def process_file(filepath, session):
    # Extract target name: spectrum_<name>_*.csv
    basename = os.path.basename(filepath)
    name = basename.split('_')[1]

    print(f'Processing {basename} -> target: {name}')

    df = pd.read_csv(filepath)

    # Convert flux from Jy to uJy
    out = pd.DataFrame({
        'wavelength': df['wavelength_um'],
        'flux':       df['flux_bkgsub_jy'] * 1e6,
        'flux_error': df['flux_bkgsub_err_jy'] * 1e6,
        'mjd':        df['mjd'],
    })

    # Use mean MJD as representative DATE-OBS
    date_obs = Time(df['mjd'].mean(), format='mjd').isot

    with open(TMP_FILE, 'w') as f:
        f.write(f'# DATE-OBS: {date_obs}\n')
        f.write('# FACILITY: SPHEREx\n')
        out.to_csv(f, index=False)

    target_id = get_target_id(session, name)
    result = upload_spectrum(session, target_id, TMP_FILE)
    print(f'  Uploaded successfully for {name}.')


def main():
    parser = argparse.ArgumentParser(description='Upload SPHEREx spectra to IRTOM')
    parser.add_argument('folder', help='Folder containing spectrum_<name>_*.csv files')
    args = parser.parse_args()

    session = requests.Session()
    session.headers.update({'Authorization': f'Token {token}'})

    files = sorted(glob.glob(os.path.join(args.folder, 'spectrum_*.csv')))
    if not files:
        print(f'No spectrum_*.csv files found in {args.folder}')
        return

    print(f'Found {len(files)} file(s)')
    errors = []
    for filepath in files:
        try:
            process_file(filepath, session)
        except Exception as e:
            print(f'  ERROR: {e}')
            errors.append((filepath, e))

    if errors:
        print(f'\n{len(errors)} file(s) failed:')
        for path, err in errors:
            print(f'  {os.path.basename(path)}: {err}')
    else:
        print('\nAll files uploaded successfully.')

    if os.path.exists(TMP_FILE):
        os.remove(TMP_FILE)


if __name__ == '__main__':
    main()
