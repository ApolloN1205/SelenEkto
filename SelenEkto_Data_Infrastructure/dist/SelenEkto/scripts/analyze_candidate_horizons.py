"""SelenEkto independent candidate horizon comparison. Run from project root.

 .\\.venv\\Scripts\\python.exe .\\scripts\\analyze_candidate_horizons.py

Select CSV exported from Site01 map; runs one horizon per candidate. This is
NOT a global lunar horizon, solar illumination result, or landing safety test.
"""
from __future__ import annotations
import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from selenekto_data.candidate_horizons import parse_candidates, summarize_profile
from selenekto_data.horizon import calculate_horizon


def main():
    parser=argparse.ArgumentParser(description='Independent lunar terrain horizon per candidate')
    parser.add_argument('--csv',type=Path,help='Site01 map CSV; if omitted, shows Windows file picker')
    parser.add_argument('--max-distance-m',type=int,default=500,choices=[500,2000,5000])
    parser.add_argument('--sample-step-m',type=float,default=10.)
    args=parser.parse_args()
    csv_path=args.csv
    if csv_path is None:
        import tkinter as tk
        from tkinter import filedialog
        root=tk.Tk(); root.withdraw()
        csv_path=filedialog.askopenfilename(title='Choose exported Site01 candidate CSV',filetypes=[('CSV','*.csv')])
        root.destroy()
        if not csv_path:
            print('No CSV chosen; nothing changed.');return
    import numpy as np
    import rasterio
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt
    data=ROOT/'data'/'raw'/'lola'/'Site01'
    paths={k:data/f'Site01_final_adj_5mpp_{v}.tif' for k,v in [('dem','surf'),('counts','ldec'),('errors','toterr')]}
    for k,v in paths.items():
        if not v.is_file():
            raise SystemExit(f'Missing {k} NASA DEM layer: {v}')
    with rasterio.open(paths['dem']) as ds:
        transform=ds.transform
        crs=str(ds.crs)
        dem=ds.read(1).astype(float)
        candidates=parse_candidates(csv_path,ds.width,ds.height)
        nodata=ds.nodata
        if nodata is not None:dem[dem==nodata]=np.nan
    with rasterio.open(paths['counts']) as ds: counts=ds.read(1)
    with rasterio.open(paths['errors']) as ds: errors=ds.read(1)
    radius=args.max_distance_m
    out=ROOT/'data'/'processed'/'candidate_horizons'/'Site01'
    out.mkdir(parents=True,exist_ok=True)
    results=[]
    fig,ax=plt.subplots(figsize=(12,5.7),facecolor='#161616')
    ax.set_facecolor('#161616')
    for candidate in candidates:
        row,col=candidate['row'],candidate['col']
        # Exactly target pixel's CENTRE, avoiding ambiguity at borders.
        x,y=transform*(col+.5,row+.5)
        print(f"Calculating {candidate['name']} at row {row}, col {col} ...",flush=True)
        profile=calculate_horizon(dem,transform,x,y,max_distance_m=radius,
             sample_step_m=args.sample_step_m,azimuth_step_deg=1.,
             counts=counts,errors=errors)
        summary=summarize_profile(profile)
        result={**candidate,'x_projected_m':x,'y_projected_m':y,
                'reference_elevation_m':float(dem[row,col]),'summary':summary,'angles':profile}
        results.append(result)
        ax.plot([r['grid_azimuth_deg'] for r in profile],
                [r['horizon_angle_deg'] if r['horizon_angle_deg'] is not None else float('nan') for r in profile],
                label=f"{candidate['name']} ({row}, {col})",lw=1.25)
        print(f"  Mean horizon: {summary['mean_horizon_deg']:.3f}° | max: {summary['maximum_horizon_deg']:.3f}° | zero LOLA spots: {summary['zero_lola_controlling_directions']}/360")
    ax.set(xlabel='Grid-relative azimuth (degrees, clockwise from +Y)',ylabel='Local DEM horizon angle (degrees)',xlim=(0,359))
    ax.grid(alpha=.18);ax.tick_params(colors='white');ax.xaxis.label.set_color('white');ax.yaxis.label.set_color('white')
    for s in ax.spines.values():s.set_color('#777777')
    ax.legend(facecolor='#282828',labelcolor='white',loc='best',fontsize=8)
    fig.tight_layout()
    basename=f'Site01_candidate_horizons_{radius}m'
    png=out/(basename+'.png')
    js=out/(basename+'.json')
    table=out/(basename+'_summary.csv')
    # Save to new filenames to avoid previous PNG overwrite-lock issue.
    fig.savefig(png,dpi=150,facecolor=fig.get_facecolor());plt.close(fig)
    with js.open('w',encoding='utf-8') as fh:
        json.dump({'generated_utc':datetime.now(timezone.utc).isoformat(),
                   'source_csv':str(csv_path),'site':'Site01',
                   'settings':{'max_distance_m':radius,'sample_step_m':args.sample_step_m,
                               'azimuth_step_deg':1,'grid_azimuth_reference':'clockwise from projected +Y'},
                   'limitations':['Local DEM only; NOT sunlight visibility or landing safety',
                     'Results are sensitive to observer position and assumed elevation',
                     'The short local model may miss distant obstructions',
                     'Per-candidate horizon errors are not independently propagated'],
                   'candidates':results},fh,indent=2,allow_nan=False)
    summary_fields=['name','row','col','reference_elevation_m',*results[0]['summary']]
    with table.open('w',encoding='utf-8',newline='') as fh:
        writer=csv.DictWriter(fh,fieldnames=summary_fields)
        writer.writeheader()
        for c in results:
            writer.writerow({k:c.get(k,c['summary'].get(k)) for k in summary_fields})
    print('\nCreated independent candidate profiles:')
    print(f'  Figure: {png}')
    print(f'  Summary: {table}')
    print(f'  Detailed JSON: {js}')
    print('WARNING: DEM-limited directional horizons, NOT landing suitability or dated Sun visibility.')

if __name__=='__main__':main()
