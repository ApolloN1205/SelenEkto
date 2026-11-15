"""SelenEkto first local desktop application. Run from infrastructure root.

This UI explores modelled terrain obstruction for hypothetical or imported
projected-GRID directions. It does NOT compute the actual position of the Sun.
"""
from __future__ import annotations
import csv
import json
import threading
from datetime import datetime, timezone
import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from selenekto_data.visibility import read_site_results, classify_sky_position, evaluate_csv
from selenekto_data.solar import fetch_sun_positions, project_north_offset, convert_to_grid, evaluate_solar_timeline, save_solar_results

HORIZON = ROOT / 'data/processed/horizon/Site01/Site01_horizon_5km.json'
UNCERTAINTY = ROOT / 'data/processed/horizon/Site01/Site01_horizon_uncertainty_5km.json'


def main():
    try:
        report, points, uncert = read_site_results(HORIZON, UNCERTAINTY if UNCERTAINTY.exists() else None)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        raise SystemExit(f'SelenEkto cannot load Site01 reports: {exc}\nRun the horizon and uncertainty scripts first.')

    import matplotlib
    matplotlib.use('TkAgg')
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

    app=tk.Tk()
    app.title('SELENEKTO  /  LUNAR TERRAIN EXPLORER')
    app.geometry('1160x760')
    app.configure(bg='#111111')
    style=ttk.Style(app)
    style.theme_use('clam')
    style.configure('.', background='#111111', foreground='#efefef', fieldbackground='#1e1e1e', font=('Segoe UI', 10))
    style.configure('TFrame', background='#111111')
    style.configure('TLabel', background='#111111', foreground='#ededed')
    style.configure('TButton', background='#292929', foreground='#eeeeee', padding=7)
    style.map('TButton', background=[('active','#404040')])
    style.configure('TScale', background='#111111')

    header=ttk.Frame(app)
    header.pack(fill='x', padx=24,pady=(18,6))
    ttk.Label(header,text='SELENEKTO  /  CONNECTING RIDGE',font=('Segoe UI',19,'bold')).pack(anchor='w')
    ttk.Label(header,text='NASA PGDA Site01  ·  5 km local DEM horizon  ·  Experimental / NOT landing safety',font=('Segoe UI',10)).pack(anchor='w',pady=(3,0))
    ttk.Label(header,text='GRID azimuth clockwise from projected +Y (NOT north). Sky position is manual or from an external, correctly transformed CSV.',wraplength=1100).pack(anchor='w',pady=(5,0))

    control=ttk.Frame(app)
    control.pack(fill='x',padx=24,pady=8)
    direction=tk.DoubleVar(value=0)
    altitude=tk.DoubleVar(value=2)
    status=tk.StringVar()

    ttk.Label(control,text='Grid direction (°)').grid(row=0,column=0,sticky='w')
    ttk.Label(control,text='Sky altitude (°)').grid(row=0,column=1,sticky='w',padx=(20,0))
    dir_entry=ttk.Entry(control,textvariable=direction,width=14)
    dir_entry.grid(row=1,column=0,sticky='w')
    alt_entry=ttk.Entry(control,textvariable=altitude,width=14)
    alt_entry.grid(row=1,column=1,sticky='w',padx=(20,0))
    ttk.Label(control,textvariable=status,font=('Segoe UI',11,'bold')).grid(row=1,column=2,sticky='w',padx=25)

    fig=Figure(figsize=(10.6,4.6),dpi=100,facecolor='#161616')
    ax=fig.add_subplot(111)
    ax.set_facecolor('#161616')
    ax.tick_params(colors='#dddddd')
    for spine in ax.spines.values(): spine.set_color('#777777')
    ax.set_xlabel('Projected grid azimuth (degrees)',color='#dddddd')
    ax.set_ylabel('Terrain horizon / sky altitude (degrees)',color='#dddddd')
    ax.grid(color='#444444',alpha=.35)
    xs=[p[0] for p in points]
    ax.plot(xs,[p[1] for p in points],color='#ffffff',label='Baseline horizon',lw=1.6)
    if uncert:
        ax.fill_between(xs,[p[1] for p in uncert],[p[2] for p in uncert],color='#aaaaaa',alpha=.25,label='±RMS deterministic scenarios')
    marker,=ax.plot([],[],marker='o',markersize=8,color='#ee704d',linestyle='none',label='Selected sky position')
    ax.legend(facecolor='#292929',edgecolor='#777777',labelcolor='#eeeeee',loc='upper right')
    ax.set_xlim(0,360)
    canvas=FigureCanvasTkAgg(fig,master=app)
    canvas.get_tk_widget().pack(fill='both',expand=True,padx=24,pady=8)

    def update(*_):
        try:
            result=classify_sky_position(points,uncert,direction.get(),altitude.get())
            marker.set_data([result['grid_direction_deg']],[result['sky_altitude_deg']])
            y=[p[1] for p in points]+[result['sky_altitude_deg']]
            if uncert:y += [p[1] for p in uncert]+[p[2] for p in uncert]
            ax.set_ylim(min(y)-2,max(y)+2)
            status.set(f"{result['status']}  |  baseline {result['baseline_horizon_deg']:.2f}°")
            canvas.draw_idle()
        except (ValueError,tk.TclError):
            status.set('Enter valid direction (°) and sky altitude (-90 to +90°)')
    ttk.Button(control,text='Evaluate',command=update).grid(row=1,column=3,padx=8)
    update()

    # Actual JPL Horizons ephemeris (network required), then compare with DEM horizon.
    solar_box=ttk.LabelFrame(app,text='SOLAR ILLUMINATION  /  JPL HORIZONS (experimental)',padding=10)
    solar_box.pack(fill='x', padx=24, pady=6)
    date_utc=tk.StringVar(value=datetime.now(timezone.utc).strftime('%Y-%m-%d'))
    hours=tk.StringVar(value='72')
    interval=tk.StringVar(value='60')
    solar_state=tk.StringVar(value='No ephemeris loaded. This module requires access to the JPL Horizons API.')
    ttk.Label(solar_box,text='Start date (UTC)').grid(row=0,column=0,sticky='w')
    ttk.Entry(solar_box,textvariable=date_utc,width=15).grid(row=1,column=0,sticky='w',padx=(0,12))
    ttk.Label(solar_box,text='Duration (hours)').grid(row=0,column=1,sticky='w')
    ttk.Entry(solar_box,textvariable=hours,width=10).grid(row=1,column=1,sticky='w',padx=(0,12))
    ttk.Label(solar_box,text='Step (minutes)').grid(row=0,column=2,sticky='w')
    ttk.Entry(solar_box,textvariable=interval,width=10).grid(row=1,column=2,sticky='w',padx=(0,12))
    ttk.Label(solar_box,textvariable=solar_state,wraplength=1080).grid(row=2,column=0,columnspan=6,sticky='w',pady=(9,0))

    def show_solar_timeline(rows, metadata):
        solar_state.set(f"Downloaded {len(rows)} JPL Horizons time samples. Exported JSON + CSV. This is preliminary modelled obstruction, not verified illumination.")
        w=tk.Toplevel(app)
        w.title('SELENEKTO / SOLAR TIMELINE (EXPERIMENTAL)')
        w.geometry('1050x670')
        w.configure(bg='#111111')
        title=ttk.Label(w,text='SITE01  /  ESTIMATED SUN VISIBILITY',font=('Segoe UI',16,'bold'))
        title.pack(anchor='w',padx=20,pady=(15,3))
        ttk.Label(w,text='JPL Horizons solar elevation minus locally modelled terrain horizon · grid orientation transformed from lunar north · NOT certified illumination',wraplength=990).pack(anchor='w',padx=20)
        f=Figure(figsize=(10,4.6),dpi=100,facecolor='#161616')
        a=f.add_subplot(111)
        a.set_facecolor('#161616')
        x=list(range(len(rows)))
        a.plot(x,[r['altitude_deg'] for r in rows],label='JPL Sun altitude',color='#FFE347',lw=2.6)
        a.plot(x,[r['baseline_horizon_deg'] for r in rows],label='Modelled terrain horizon',color='#AFBCCB',lw=1.7)
        if uncert:
            a.fill_between(x,[r['low_scenario_horizon_deg'] for r in rows],[r['high_scenario_horizon_deg'] for r in rows],alpha=.22,color='#AAB7CC',label='±1 RMS perturbation scenarios')
        a.set_ylabel('Altitude / terrain horizon (degrees)',color='#eeeeee')
        a.set_xlabel('UTC date/time',color='#eeeeee')
        a.grid(color='#444444',alpha=.35)
        a.tick_params(colors='#dddddd')
        for spine in a.spines.values():spine.set_color('#777777')
        tickstep=max(1,len(rows)//7)
        ticks=list(range(0,len(rows),tickstep))
        a.set_xticks(ticks,[rows[i]['timestamp_utc'][5:16].replace('T',' ') for i in ticks],rotation=22,ha='right')
        a.legend(facecolor='#292929',edgecolor='#777777',labelcolor='#eeeeee')
        f.tight_layout()
        chart=FigureCanvasTkAgg(f,master=w)
        chart.get_tk_widget().pack(fill='both',expand=True,padx=15,pady=10)
        clear=sum('ABOVE' in r['status'] for r in rows)
        blocked=sum('BELOW' in r['status'] for r in rows)
        ambiguous=len(rows)-clear-blocked
        ttk.Label(w,text=f'{clear} above all modelled scenarios · {blocked} below all modelled scenarios · {ambiguous} scenario-dependent or baseline-only classifications',wraplength=990).pack(anchor='w',padx=20,pady=(0,10))

    def run_solar():
        try:
            start=datetime.strptime(date_utc.get().strip(),'%Y-%m-%d').replace(tzinfo=timezone.utc)
            span=int(hours.get()); step=int(interval.get())
            if not (1 <= span <= 336 and 10 <= step <= 720):
                raise ValueError('Duration must be 1–336 hours and interval 10–720 minutes')
        except (ValueError,tk.TclError) as exc:
            messagebox.showerror('Invalid solar settings',str(exc));return
        solar_button.config(state='disabled')
        solar_state.set('Contacting JPL Horizons and mapping solar directions onto lunar DEM grid...')
        def work():
            try:
                raw,meta=fetch_sun_positions(start,span,step)
                offset=project_north_offset(report['crs_wkt'])
                rows=evaluate_solar_timeline(convert_to_grid(raw,offset),points,uncert)
                meta['grid_north_offset_deg']=offset
                meta['site'] = 'Site01 Connecting Ridge'
                meta['observer_elevation_m']=report['reference_elevation_m']
                meta['model_limitations']=['PGDA DEM horizon only; no direct illumination validation',
                    'Uncertainty scenarios not confidence intervals','Local DEM cannot capture distant obstructions',
                    'MOON_ME frame consistency of Horizons geodetic coordinates not independently validated']
                save_solar_results(rows,meta,ROOT/'data/processed/solar/Site01')
                def done():
                    solar_button.config(state='normal')
                    show_solar_timeline(rows,meta)
                app.after(0,done)
            except Exception as exc:
                detail=str(exc)
                def failed():
                    solar_button.config(state='normal')
                    solar_state.set('Solar calculation unavailable. Check internet, JPL response and coordinate inputs.')
                    messagebox.showerror('Solar calculation failed',detail)
                app.after(0,failed)
        threading.Thread(target=work,daemon=True).start()
    solar_button=ttk.Button(solar_box,text='Calculate dated Sun timeline',command=run_solar)
    solar_button.grid(row=1,column=3,padx=(10,0),sticky='w')

    footer=ttk.Frame(app)
    footer.pack(fill='x',padx=24,pady=(0,18))
    def import_positions():
        path=filedialog.askopenfilename(title='Import grid-relative sky-position CSV',filetypes=[('CSV files','*.csv')])
        if not path:return
        try:
            results=evaluate_csv(path,points,uncert)
            out=Path(path).with_name(Path(path).stem+'_selenekto_evaluated.csv')
            with out.open('w',encoding='utf-8',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=list(results[0]))
                writer.writeheader(); writer.writerows(results)
            messagebox.showinfo('CSV evaluated',f'Analysed {len(results)} timestamped rows.\nSaved: {out}\n\nExternal sky directions must already be rotated into the local projected-grid convention.')
        except (ValueError,OSError,KeyError) as exc:
            messagebox.showerror('CSV error',str(exc))
    ttk.Button(footer,text='Import & evaluate sky-position CSV',command=import_positions).pack(side='left')
    ttk.Button(footer,text='Open horizon output folder',command=lambda: __import__('os').startfile(HORIZON.parent)).pack(side='left',padx=10)
    ttk.Label(footer,text='Terrain and illumination are experimental · NOT landing safety',font=('Segoe UI',9)).pack(side='right')
    app.mainloop()

if __name__=='__main__':
    main()
