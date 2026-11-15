"""Independent local horizons and dated JPL Sun timelines for selected region-tagged cells.
Separate worker: never blocks the Tkinter dashboard. Reuses established backend modules.
"""
from __future__ import annotations
import argparse,csv,json,sys
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from selenekto_data.unified_regions import REGIONS,region_files,validate_region
from selenekto_data.horizon import calculate_horizon
from selenekto_data.candidate_solar import candidate_geography,fetch_candidate_sun,evaluate_candidate,timeline_statistics,normalized_scores
from selenekto_data.solar import project_north_offset

def main():
    import numpy as np,rasterio
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt
    p=argparse.ArgumentParser()
    p.add_argument('--csv',type=Path,default=ROOT/'data/processed/unified/selected_candidates.csv')
    p.add_argument('--date',default=datetime.now(timezone.utc).strftime('%Y-%m-%d'))
    p.add_argument('--hours',type=int,default=72);p.add_argument('--interval-min',type=int,default=60)
    p.add_argument('--radius',type=int,default=500)
    p.add_argument('--solar',action='store_true',help='Query JPL Horizons at each candidate (needs internet)')
    p.add_argument('--sun-weight',type=float,default=2);p.add_argument('--slope-weight',type=float,default=1)
    p.add_argument('--uncertainty-weight',type=float,default=1)
    args=p.parse_args()
    start=datetime.strptime(args.date,'%Y-%m-%d').replace(tzinfo=timezone.utc)
    if not args.csv.is_file():p.error('Candidate CSV missing; export from dashboard first')
    with args.csv.open(encoding='utf-8',newline='') as handle:records=list(csv.DictReader(handle))
    if not records:p.error('No candidate rows')
    if len(records)>12:p.error('Maximum 12 candidates per analysis to limit JPL usage and memory')
    if not 100<=args.radius<=5000:p.error('radius must be 100–5000 metres')
    out=ROOT/'data/processed/unified'/args.date;out.mkdir(parents=True,exist_ok=True)
    profiles=[];comparisons=[];cache={};fig,ax=plt.subplots(figsize=(11,5))
    try:
        for i,rec in enumerate(records,1):
            region=rec['region'];name=rec['name'];row=int(rec['row']);col=int(rec['col'])
            if region not in REGIONS:raise ValueError(f'Unknown region {region}')
            if region not in cache:
                files=validate_region(ROOT/'data/raw/lola',region)
                with rasterio.open(files['Elevation']) as ds:
                    transform=ds.transform;wkt=ds.crs.to_wkt();data=ds.read(1);height,width=data.shape
                    if ds.nodata is not None:data=np.where(data==ds.nodata,np.nan,data)
                extra={}
                for k in ('LOLA counts','Elevation uncertainty'):
                    with rasterio.open(files[k]) as ds:extra[k]=ds.read(1)
                cache[region]=(data,transform,wkt,extra)
            dem,transform,wkt,extra=cache[region]
            if not (0<=row<dem.shape[0] and 0<=col<dem.shape[1]):raise ValueError(f'{name}: cell outside region')
            x,y=transform*(col+.5,row+.5)
            print(f'[{i}/{len(records)}] {region}: {name} cell ({row},{col})',flush=True)
            horizon=calculate_horizon(dem,transform,x,y,max_distance_m=args.radius,sample_step_m=10.,azimuth_step_deg=1.,counts=extra['LOLA counts'],errors=extra['Elevation uncertainty'])
            profile={'region':region,'name':name,'row':row,'col':col,'horizon':horizon}
            profiles.append(profile)
            ax.plot([r['grid_azimuth_deg'] for r in horizon],[r['horizon_angle_deg'] for r in horizon],label=f'{region}: {name}',lw=1)
            if args.solar:
                lat,lon=candidate_geography(wkt,x,y)
                print(f'   Requesting JPL Horizons: lat {lat:.5f}, lon {lon:.5f}',flush=True)
                observations,source=fetch_candidate_sun(lat,lon,float(dem[row,col]),start,args.hours,args.interval_min)
                offset=project_north_offset(wkt,lat,lon)
                samples=evaluate_candidate(observations,horizon,offset)
                stats=timeline_statistics(samples)
                profile['solar_source']=source;profile['samples']=samples;profile['solar_summary']=stats
                comparisons.append({'region':region,'name':name,'latitude_deg':lat,'longitude_deg':lon,'clear_sample_fraction':stats['clear_sample_fraction'],'slope_deg':float(rec['slope_deg']),'elevation_rms_m':float(rec['elevation_rms_m'])})
        ax.set(xlabel='Grid-relative azimuth (degrees)',ylabel='DEM-limited local horizon angle (degrees)')
        ax.legend(fontsize=7);fig.tight_layout();png=out/'candidate_horizons.png';fig.savefig(png,dpi=140)
    finally:plt.close(fig)
    if comparisons:
        weights={'clear_sample_fraction':args.sun_weight,'slope_deg':args.slope_weight,'elevation_rms_m':args.uncertainty_weight}
        scored=normalized_scores(comparisons,weights)
        summary=out/'candidate_comparison.csv'
        with summary.open('w',encoding='utf-8',newline='') as file:
            cols=['region','name','latitude_deg','longitude_deg','clear_sample_fraction','slope_deg','elevation_rms_m','weighted_score']
            writer=csv.DictWriter(file,fieldnames=cols,extrasaction='ignore');writer.writeheader();writer.writerows(scored)
    result={'generated_utc':datetime.now(timezone.utc).isoformat(),'radius_m':args.radius,'date':args.date,'hours':args.hours,
       'solar_requested':args.solar,'note':'Local DEM-only horizons. JPL Sun centre estimates are experimental; not landing-safety assessments. Preference scores are relative to this candidate set.',
       'candidates':profiles,'comparison':comparisons}
    (out/'candidate_analysis.json').write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
    print('OUTPUT:',out,flush=True)
if __name__=='__main__':main()
