"""Run from infrastructure root after candidate horizon CSV analysis.

Example:
 .\\.venv\\Scripts\\python.exe .\\scripts\\analyze_candidate_solar.py --date 2026-11-14 --hours 72
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
from selenekto_data.candidate_solar import (candidate_geography,fetch_candidate_sun,
       evaluate_candidate,timeline_statistics,normalized_scores)
from selenekto_data.solar import project_north_offset


def main():
    ap=argparse.ArgumentParser(description='SelenEkto experimental per-candidate solar timelines and transparent site scoring')
    ap.add_argument('--date',default='2026-11-14',help='UTC YYYY-MM-DD')
    ap.add_argument('--hours',type=int,default=72)
    ap.add_argument('--interval-min',type=int,default=60)
    ap.add_argument('--horizons-json',type=Path,default=ROOT/'data/processed/candidate_horizons/Site01/Site01_candidate_horizons_500m.json')
    ap.add_argument('--sun-weight',type=float,default=2)
    ap.add_argument('--slope-weight',type=float,default=1)
    ap.add_argument('--uncertainty-weight',type=float,default=1)
    args=ap.parse_args()
    from datetime import timedelta
    try:
        start=datetime.strptime(args.date,'%Y-%m-%d').replace(tzinfo=timezone.utc)
    except ValueError:
        ap.error('Date must be YYYY-MM-DD')
    if not args.horizons_json.is_file():
        ap.error(f'Missing candidate horizons file: {args.horizons_json}. First run Analyze candidate horizons in the map.')
    d=json.loads(args.horizons_json.read_text(encoding='utf-8'))
    candidates=d.get('candidates',[])
    if not candidates:
        ap.error('Candidate horizon JSON has no candidates')
    import rasterio
    from rasterio.transform import rowcol
    data=ROOT/'data/raw/lola/Site01'
    dempath=data/'Site01_final_adj_5mpp_surf.tif'
    slppath=data/'Site01_final_adj_5mpp_slp.tif'
    errpath=data/'Site01_final_adj_5mpp_toterr.tif'
    for p in (dempath,slppath,errpath):
        if not p.is_file():ap.error(f'Missing raster {p}')
    with rasterio.open(dempath) as ds:
        wkt=ds.crs.to_wkt(); transform=ds.transform; width,height=ds.width,ds.height
    with rasterio.open(slppath) as ds: slopes=ds.read(1)
    with rasterio.open(errpath) as ds: errors=ds.read(1)
    out=ROOT/'data/processed/candidate_solar/Site01'/start.strftime('%Y-%m-%d')
    out.mkdir(parents=True,exist_ok=True)
    detailed=[]; comparison=[]
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt
    fig,ax=plt.subplots(figsize=(11,5),facecolor='#181818');ax.set_facecolor('#181818')
    for i,c in enumerate(candidates,1):
        row,col=int(c['row']),int(c['col'])
        if not (0<=row<height and 0<=col<width):
            raise ValueError(f'Invalid pixel for {c["name"]}')
        if len(c.get('angles',[])) < 2:raise ValueError(f'Missing candidate horizon at {c["name"]}')
        x,y=transform*(col+0.5,row+0.5)
        lat,lon=candidate_geography(wkt,x,y)
        elevation=float(c['reference_elevation_m'])
        print(f'[{i}/{len(candidates)}] {c["name"]}: requesting JPL Horizons at {lat:.6f}, {lon:.6f}...',flush=True)
        positions,source=fetch_candidate_sun(lat,lon,elevation,start,args.hours,args.interval_min)
        offset=project_north_offset(wkt,lat,lon)
        evaluated=evaluate_candidate(positions,c['angles'],offset)
        summary=timeline_statistics(evaluated)
        stats={'name':c['name'],'row':row,'col':col,'latitude_deg':lat,'longitude_east_deg':lon,
            'clear_sample_fraction':summary['clear_sample_fraction'],'slope_deg':float(slopes[row,col]),
            'elevation_rms_m':float(errors[row,col]),'summary':summary}
        comparison.append(stats)
        detailed.append({'candidate':stats,'source':source,'north_to_grid_offset_deg':offset,'records':evaluated})
        ax.plot([datetime.fromisoformat(r['timestamp_utc'].replace('Z','+00:00')) for r in evaluated],
                [r['clearance_deg'] for r in evaluated],label=c['name'],lw=1.2)
        print(f'  Above modelled terrain: {summary["clear_samples"]}/{summary["sample_count"]} sampled instants')
    weights={'clear_sample_fraction':args.sun_weight,'slope_deg':args.slope_weight,'elevation_rms_m':args.uncertainty_weight}
    scored=normalized_scores(comparison,weights)
    results={'generated_utc':datetime.now(timezone.utc).isoformat(),'date_utc':args.date,
             'settings':{'hours':args.hours,'interval_minutes':args.interval_min,'weights':weights,
                         'candidate_horizon_json':str(args.horizons_json)},
             'method':'Sun-centre against each candidate independent DEM-limited baseline horizon, sampled in time',
             'limitations':['No candidate-specific horizon uncertainty bands in this milestone',
                 'Local DEM search radius only; distant terrain not modelled',
                 'No landing safety inference; no eclipse/reflection/solar disc model',
                 'Fraction of sampled instants is not necessarily uninterrupted illumination or true sunlight duty cycle',
                 'MOON_ME lunar coordinate frame and true-north alignment need independent validation',
                 'Scoring is user preference across this particular candidate set, not a scientific landing suitability score'],
             'comparison':scored,'candidate_timelines':detailed}
    target=out/'candidate_solar_comparison.json'
    target.write_text(json.dumps(results,indent=2,allow_nan=False),encoding='utf-8')
    csvpath=out/'candidate_solar_summary.csv'
    cols=['name','row','col','latitude_deg','longitude_east_deg','clear_sample_fraction','slope_deg','elevation_rms_m','weighted_score']
    with csvpath.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=cols);writer.writeheader()
        for r in scored:writer.writerow({k:r[k] for k in cols})
    ax.axhline(0,color='#ddd',ls=':',lw=1)
    ax.set(xlabel='UTC date/time',ylabel='Sun altitude minus local horizon (degrees)',title='Independent candidate Sun/terrain clearance · experimental')
    ax.tick_params(colors='white');ax.title.set_color('white');ax.xaxis.label.set_color('white');ax.yaxis.label.set_color('white')
    for s in ax.spines.values():s.set_color('#999')
    ax.legend(facecolor='#303030',labelcolor='white');fig.autofmt_xdate();fig.tight_layout()
    png=out/'candidate_solar_clearance.png'
    fig.savefig(png,dpi=160,facecolor=fig.get_facecolor());plt.close(fig)
    print(f'\nSaved:\n  {target}\n  {csvpath}\n  {png}')
    print('NOTE: Scores are adjustable preferences, NOT recommended safe landing sites.')

if __name__=='__main__':main()
