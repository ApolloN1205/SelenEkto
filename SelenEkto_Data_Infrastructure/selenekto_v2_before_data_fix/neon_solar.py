"""Read previously generated real SelenEkto solar/horizon JSON and plot in dark/neon style."""
from __future__ import annotations
import json
from pathlib import Path


def parse_saved_result(path:Path):
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    if isinstance(data.get('records'),list):
        records=data['records']
        if not records or not all('timestamp_utc' in r and 'altitude_deg' in r and 'baseline_horizon_deg' in r for r in records):
            raise ValueError('The solar JSON is missing timestamp, Sun altitude, or horizon values')
        return {'kind':'solar', 'title':'Site01 / JPL Sun & terrain horizon', 'lines':[
            {'name':'Sun altitude / JPL Horizons','color':'#FFE347','values':[r['altitude_deg'] for r in records]},
            {'name':'Modelled terrain horizon','color':'#BFC5CF','values':[r['baseline_horizon_deg'] for r in records]},
        ], 'labels':[r['timestamp_utc'] for r in records],
            'lower':[r.get('low_scenario_horizon_deg') for r in records],
            'upper':[r.get('high_scenario_horizon_deg') for r in records]}
    if isinstance(data.get('candidate_timelines'),list):
        timelines=data['candidate_timelines']
        if not timelines: raise ValueError('Candidate solar comparison has no timelines')
        names=[];lines=[];labels=[]
        palette=['#FFE347','#84E7E0','#D9A5FF','#FF8D83','#A8E58D','#8FACFF']
        for i, candidate in enumerate(timelines):
            records=candidate.get('records') or []
            if not records:continue
            if not labels: labels=[r['timestamp_utc'] for r in records]
            if len(records)!=len(labels):raise ValueError('Candidate timelines have different sample counts')
            name=candidate.get('candidate',{}).get('name',f'Candidate {i+1}')
            lines.append({'name':f'{name} / Sun clearance', 'color':palette[i%len(palette)],
                          'values':[r['clearance_deg'] for r in records]})
        if not lines:raise ValueError('No valid candidate timelines')
        return {'kind':'clearance','title':'Candidate sunlight clearance / JPL Horizons',
                'lines':lines,'labels':labels,'lower':None,'upper':None}
    if isinstance(data.get('angles'),list):
        records=data['angles']
        if not records:raise ValueError('Empty terrain horizon')
        return {'kind':'horizon','title':f"{data.get('site','Unknown')} / terrain horizon",'lines':[
            {'name':'Terrain horizon', 'color':'#C3CCD7','values':[r['horizon_angle_deg'] for r in records]}],
            'labels':[str(r['grid_azimuth_deg']) for r in records], 'lower':None, 'upper':None}
    raise ValueError('Unsupported JSON: choose Site01_solar_timeline.json, candidate_solar_comparison.json, or a terrain horizon JSON')
