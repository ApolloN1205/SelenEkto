"""Audit all installed/partial NASA PGDA regions; produces a JSON and CSV report.
Read-only: never downloads, deletes or changes the NASA rasters.
"""
from __future__ import annotations
import csv,json,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from selenekto_data.unified_regions import REGIONS,region_files
from selenekto_data.region_audit import classify_region


def main():
    raw=ROOT/'data/raw/lola'
    dest=ROOT/'data/processed/data_audit'
    dest.mkdir(parents=True,exist_ok=True)
    results=[]
    print('SELENEKTO / NASA REGION DATA AUDIT')
    for region, name in REGIONS.items():
        result=classify_region(raw,region,region_files(raw,region))
        result['name']=name
        results.append(result)
        print(f'{region:9} {result["status"]:23} | '+', '.join(f'{k}:{v["status"]}' for k,v in result['layers'].items()))
    report={'created_utc':datetime.now(timezone.utc).isoformat(), 'regions':results,
            'notes':['Sampled NoData fractions are approximate, based on sparse raster reads.',
                     'A valid file can have legitimate NoData pixels.',
                     'Incomplete regions need missing files; invalid or misaligned files need investigation before replacing.']}
    jsonpath=dest/'region_audit.json';csvpath=dest/'region_audit.csv'
    jsonpath.write_text(json.dumps(report,indent=2),encoding='utf-8')
    with csvpath.open('w',encoding='utf-8',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=['region','name','region_status','layer','layer_status','sampled_missing_percent','path','reason'])
        writer.writeheader()
        for item in results:
            for layer, data in item['layers'].items():
                writer.writerow({'region':item['region'],'name':item['name'],'region_status':item['status'],
                                 'layer':layer,'layer_status':data['status'],
                                 'sampled_missing_percent':data.get('sampled_missing_percent',''),
                                 'path':data['path'],'reason':data.get('reason','')})
    print('\nSaved:',jsonpath,'and',csvpath)
    print('READY:',sum(r['status']=='ready' for r in results), '/', len(results))
    print('No files were modified.')
if __name__=='__main__':main()
