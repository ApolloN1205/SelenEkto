"""SelenEkto integrated local navigator: Site01 map, existing analyses, candidate actions.

Safe additive milestone. Existing launch_selenekto.py and launch_site_map.py stay intact.
Run: .\\.venv\\Scripts\\python.exe .\\scripts\\launch_dashboard.py
"""
from __future__ import annotations
import csv
import json
import subprocess
import sys
import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path
from tkinter import ttk, messagebox

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from selenekto_data.dashboard_data import (discover_regions,latest_candidate_report,
    read_candidate_comparison,normalized_weight_label)

RAW=ROOT/'data/raw/lola'
PROCESSED=ROOT/'data/processed'


def main():
    try:
        import numpy as np
        import rasterio
        from rasterio.enums import Resampling
        import matplotlib
        matplotlib.use('TkAgg')
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    except ImportError as exc:
        raise SystemExit(f'Dashboard dependency unavailable: {exc}')

    app=tk.Tk();app.title('SELENEKTO  /  LUNAR LANDING SITE NAVIGATOR · PROTOTYPE')
    app.geometry('1280x880');app.minsize(1020,680);app.configure(bg='#111111')
    st=ttk.Style(app);st.theme_use('clam')
    st.configure('.',background='#111111',foreground='#eeeeee',fieldbackground='#242424',font=('Segoe UI',10))
    st.configure('TButton',background='#292929',foreground='#f5f5f5',padding=7)
    st.map('TButton',background=[('active','#484848')]);st.configure('TNotebook.Tab',padding=(16,8))
    st.configure('Treeview',background='#191919',foreground='#ffffff',fieldbackground='#191919',rowheight=24)
    st.configure('Treeview.Heading',background='#333333',foreground='#ffffff')
    ttk.Label(app,text='S E L E N E K T O   /   L U N A R   N A V I G A T O R',font=('Segoe UI',19,'bold')).pack(anchor='w',padx=20,pady=(16,4))
    ttk.Label(app,text='Scientific exploration prototype  ·  NASA PGDA data  ·  JPL Horizons solar ephemerides  ·  NOT a landing-safety certification',wraplength=1190).pack(anchor='w',padx=20)
    notebook=ttk.Notebook(app);notebook.pack(fill='both',expand=True,padx=18,pady=12)
    tabs={}
    for key in ('Overview','Terrain Map','Horizon','Solar & Candidates'):
        frame=ttk.Frame(notebook);tabs[key]=frame;notebook.add(frame,text=key)
    status=tk.StringVar(value='Ready · Only locally installed datasets and generated outputs are shown.')
    ttk.Label(app,textvariable=status,wraplength=1220).pack(anchor='w',padx=20,pady=(0,12))

    def launch(script,*args):
        path=ROOT/'scripts'/script
        if not path.is_file():
            messagebox.showwarning('Module not installed',f'Missing {path.name}. Install its earlier milestone first.');return
        command=[sys.executable,str(path),*map(str,args)]
        try:
            if sys.platform=='win32':
                subprocess.Popen(['cmd.exe','/k',subprocess.list2cmdline(command)],cwd=str(ROOT),creationflags=getattr(subprocess,'CREATE_NEW_CONSOLE',0))
            else:subprocess.Popen(command,cwd=str(ROOT))
        except OSError as exc:messagebox.showerror('Launch failed',str(exc));return
        status.set(f'Started {script}. Check the separate terminal for results and errors.')

    def open_path(path):
        if not path.exists():messagebox.showinfo('Not generated yet',f'No results at: {path}');return
        if sys.platform=='win32':subprocess.Popen(['explorer.exe',str(path)])
        elif sys.platform=='darwin':subprocess.Popen(['open',str(path)])
        else:subprocess.Popen(['xdg-open',str(path)])

    def section(parent,title,body):
        ttk.Label(parent,text=title,font=('Segoe UI',14,'bold')).pack(anchor='w',padx=15,pady=(18,4))
        ttk.Label(parent,text=body,wraplength=1130).pack(anchor='w',padx=15)

    # OVERVIEW
    overview=tabs['Overview']
    section(overview,'Available NASA terrain datasets','The application detects locally downloaded regions; it does not fabricate or fetch additional raster data.')
    regions=discover_regions(RAW)
    ttk.Label(overview,text=('Detected regions: '+', '.join(regions)) if regions else 'No complete raster regions detected.',font=('Segoe UI',12,'bold')).pack(anchor='w',padx=15,pady=14)
    section(overview,'Modules','Terrain map → click to save cells → independent horizons → separate JPL solar timelines → adjustable preference scores. Existing windows remain available.')
    toolbar=ttk.Frame(overview);toolbar.pack(anchor='w',padx=15,pady=12)
    ttk.Button(toolbar,text='Open original terrain + solar viewer',command=lambda:launch('launch_selenekto.py')).pack(side='left',padx=(0,12))
    ttk.Button(toolbar,text='Open original site map',command=lambda:launch('launch_site_map.py')).pack(side='left',padx=(0,12))
    ttk.Button(toolbar,text='Open processed files',command=lambda:open_path(PROCESSED)).pack(side='left')
    section(overview,'Scientific limitations','Site01 is the only region with a verified working data pipeline in this project. Horizon coverage is regional; uncertainty scenarios are not confidence intervals. Scores are user preferences and do not establish safe landing locations.')

    # MAP: genuine embedded map with candidate selection, not just a launcher
    terrain=tabs['Terrain Map']
    path=RAW/'Site01'/'Site01_final_adj_5mpp_surf.tif'
    slope_path=RAW/'Site01'/'Site01_final_adj_5mpp_slp.tif'
    if path.is_file() and slope_path.is_file():
        layers={'Elevation':'surf','Slope':'slp','Elevation uncertainty':'toterr','Slope uncertainty':'slperr','LOLA spot count':'ldec'}
        datasets={}
        for k,suffix in layers.items():
            fp=RAW/'Site01'/f'Site01_final_adj_5mpp_{suffix}.tif'
            if fp.is_file():datasets[k]=rasterio.open(fp)
        ds=datasets['Elevation']
        map_top=ttk.Frame(terrain);map_top.pack(fill='x',padx=12,pady=8)
        selected=tk.StringVar(value='Elevation');chosen={'cell':None};candidates=[]
        ttk.Label(map_top,text='NASA layer').pack(side='left',padx=(0,7))
        dropdown=ttk.Combobox(map_top,textvariable=selected,values=list(datasets),state='readonly',width=24);dropdown.pack(side='left')
        details=tk.StringVar(value='Click a pixel to inspect. Add at least two different locations to compare.')
        ttk.Label(terrain,textvariable=details,wraplength=1200).pack(anchor='w',padx=14,pady=(0,6))
        cols=('name','row','col','elevation_m','slope_deg','elevation_rms_m','lola_spot_count','x_projected_m','y_projected_m')
        tree=ttk.Treeview(terrain,columns=cols,show='headings',height=4)
        for k,head,width in [('name','Candidate',110),('row','Row',60),('col','Column',70),('elevation_m','Elevation m',105),('slope_deg','Slope °',85),('elevation_rms_m','Elevation RMS',110),('lola_spot_count','LOLA spots',90),('x_projected_m','X m',110),('y_projected_m','Y m',110)]:
            tree.heading(k,text=head);tree.column(k,width=width,anchor='center')
        controls=ttk.Frame(terrain);controls.pack(fill='x',padx=12,pady=(0,7))
        fig=Figure(figsize=(11,5.2),dpi=95,facecolor='#171717');ax=fig.add_subplot(111)
        ax.set_facecolor('#171717');ax.tick_params(colors='#eeeeee');ax.set_xlabel('Projected X (metres)',color='#eeeeee');ax.set_ylabel('Projected Y (metres)',color='#eeeeee')
        for spine in ax.spines.values():spine.set_color('#666666')
        extent=[ds.bounds.left,ds.bounds.right,ds.bounds.bottom,ds.bounds.top];cache={}
        def preview(name):
            if name not in cache:
                src=datasets[name];cache[name]=src.read(1,out_shape=(min(src.height,750),min(src.width,750)),resampling=Resampling.average,masked=True)
            return cache[name]
        image=ax.imshow(preview('Elevation'),origin='upper',extent=extent,cmap='gray')
        colorbar=fig.colorbar(image,ax=ax,fraction=.035,pad=.018);colorbar.ax.tick_params(colors='#eeeeee')
        red,=ax.plot([],[],marker='+',color='#f07865',markersize=14,linestyle='none',mew=2)
        dots,=ax.plot([],[],marker='o',color='#f07865',markersize=5,linestyle='none')
        fig.tight_layout();canvas=FigureCanvasTkAgg(fig,master=terrain)
        def val(name,row,col):
            if name not in datasets:return None
            src=datasets[name];v=float(src.read(1,window=((row,row+1),(col,col+1)))[0,0]);return round(v,5) if np.isfinite(v) else None
        def cell_click(event):
            if event.inaxes!=ax or event.xdata is None or event.ydata is None:return
            row,col=ds.index(event.xdata,event.ydata)
            if row<0 or col<0 or row>=ds.height or col>=ds.width:return
            x,y=ds.transform*(col+.5,row+.5)
            chosen['cell']={'row':row,'col':col,'x_projected_m':float(x),'y_projected_m':float(y),
                'elevation_m':val('Elevation',row,col),'slope_deg':val('Slope',row,col),
                'elevation_rms_m':val('Elevation uncertainty',row,col),'slope_rms_deg':val('Slope uncertainty',row,col),
                'lola_spot_count':val('LOLA spot count',row,col)}
            red.set_data([x],[y]);details.set(f'Selected ({row}, {col}) · Elevation {chosen["cell"]["elevation_m"]} m · Slope {chosen["cell"]["slope_deg"]}° · Press Add candidate')
            canvas.draw_idle()
        canvas.mpl_connect('button_press_event',cell_click)
        def change_layer(_=None):
            image.set_data(preview(selected.get()));image.autoscale();canvas.draw_idle()
        dropdown.bind('<<ComboboxSelected>>',change_layer)
        def refresh_candidates():
            for child in tree.get_children():tree.delete(child)
            for rec in candidates:tree.insert('', 'end',values=[rec.get(k) for k in cols])
            dots.set_data([c['x_projected_m'] for c in candidates],[c['y_projected_m'] for c in candidates]);canvas.draw_idle()
        def add():
            if not chosen['cell']:messagebox.showinfo('Select a cell','Click the map first.');return
            d=chosen['cell']
            if any(r['row']==d['row'] and r['col']==d['col'] for r in candidates):
                messagebox.showinfo('Already added','That cell is already a candidate.');return
            rec=dict(d,name=f'Candidate {len(candidates)+1:02d}');candidates.append(rec);refresh_candidates()
            details.set(f'SAVED {rec["name"]} · ({rec["row"]}, {rec["col"]}) · {len(candidates)} candidates')
        def remove():
            indexes=sorted([tree.index(r) for r in tree.selection()],reverse=True)
            for i in indexes:del candidates[i]
            refresh_candidates();details.set(f'{len(candidates)} candidates remaining')
        def write_csv():
            if not candidates:raise ValueError('Select at least one candidate before exporting')
            dest=PROCESSED/'candidate_horizons'/'Site01'/'map_selected_candidates.csv';dest.parent.mkdir(parents=True,exist_ok=True)
            with dest.open('w',newline='',encoding='utf-8') as f:
                wr=csv.DictWriter(f,fieldnames=list(candidates[0]));wr.writeheader();wr.writerows(candidates)
            return dest
        def export():
            try:p=write_csv();details.set(f'Exported {len(candidates)} candidates → {p}')
            except ValueError as exc:messagebox.showinfo('Candidates',str(exc))
        def horizons():
            if len(candidates)<2:messagebox.showinfo('Candidates','Add at least two different cells.');return
            p=write_csv();launch('analyze_candidate_horizons.py','--csv',p,'--max-distance-m','500')
        ttk.Button(controls,text='Add candidate',command=add).pack(side='left',padx=(0,6))
        ttk.Button(controls,text='Remove selected',command=remove).pack(side='left',padx=(0,6))
        ttk.Button(controls,text='Export candidate CSV',command=export).pack(side='left',padx=(0,6))
        ttk.Button(controls,text='Calculate candidate horizons',command=horizons).pack(side='left',padx=(0,6))
        ttk.Button(controls,text='Original map',command=lambda:launch('launch_site_map.py')).pack(side='right')
        tree.pack(fill='x',padx=12,pady=(0,4));canvas.get_tk_widget().pack(fill='both',expand=True,padx=12,pady=3)
        def close():
            for item in datasets.values():item.close()
            app.destroy()
        app.protocol('WM_DELETE_WINDOW',close)
    else:section(terrain,'Site01 raster not installed','Download and validate the genuine NASA PGDA Site01 files before using this map.')

    # HORIZON RESULT VIEW
    horizon=tabs['Horizon'];hp=PROCESSED/'horizon'/'Site01'/'Site01_horizon_5km.json'
    section(horizon,'Reference-point horizon','Read-only view of the existing 360-direction DEM horizon. Its reference location is not transferable to other candidates.')
    horizbar=ttk.Frame(horizon);horizbar.pack(fill='x',padx=14,pady=8)
    ttk.Button(horizbar,text='Open detailed terrain viewer',command=lambda:launch('launch_selenekto.py')).pack(side='left',padx=(0,8))
    ttk.Button(horizbar,text='Open horizon files',command=lambda:open_path(PROCESSED/'horizon'/'Site01')).pack(side='left')
    if hp.is_file():
        try:
            records=json.loads(hp.read_text(encoding='utf-8'))['angles']
            hfig=Figure(figsize=(11,5),dpi=90,facecolor='#171717');ha=hfig.add_subplot(111)
            ha.set_facecolor('#171717');ha.plot([r['grid_azimuth_deg'] for r in records],[r['horizon_angle_deg'] for r in records],color='white',lw=1.4)
            ha.set(xlabel='Grid azimuth (degrees; not true north)',ylabel='Horizon angle (degrees)')
            ha.tick_params(colors='white');ha.xaxis.label.set_color('white');ha.yaxis.label.set_color('white')
            for s in ha.spines.values():s.set_color('#777777')
            hfig.tight_layout();hc=FigureCanvasTkAgg(hfig,master=horizon);hc.get_tk_widget().pack(fill='both',expand=True,padx=14,pady=7)
        except (ValueError,KeyError,TypeError) as exc:section(horizon,'Could not read horizon data',str(exc))
    else:section(horizon,'Horizon not generated',str(hp))

    # SOLAR AND SCORING: manual workflow, real outputs read from disk
    solar=tabs['Solar & Candidates']
    section(solar,'Independent candidate solar timelines','First run candidate horizons from the map tab. Then query JPL for each candidate using the controls below. Network access required; computations open in a separate terminal to keep the interface responsive.')
    opts=ttk.Frame(solar);opts.pack(fill='x',padx=15,pady=12)
    fields=[('UTC date',datetime.now(timezone.utc).strftime('%Y-%m-%d')),('Hours','72'),('Interval (min)','60'),('Sun weight','2'),('Slope weight','1'),('Uncertainty weight','1')]
    entries=[]
    for col,(title,default) in enumerate(fields):
        ttk.Label(opts,text=title).grid(row=0,column=col,sticky='w',padx=6)
        var=tk.StringVar(value=default);entries.append(var);ttk.Entry(opts,textvariable=var,width=15).grid(row=1,column=col,padx=6)
    def calc_solar():
        try:
            datetime.strptime(entries[0].get(),'%Y-%m-%d');hrs=int(entries[1].get());interval=int(entries[2].get())
            if not 1<=hrs<=336 or not 10<=interval<=720:raise ValueError('Hours 1–336; interval 10–720 min')
            sun,slope,err=normalized_weight_label(*(e.get() for e in entries[3:]))
        except ValueError as exc:messagebox.showerror('Invalid inputs',str(exc));return
        needed=PROCESSED/'candidate_horizons'/'Site01'/'Site01_candidate_horizons_500m.json'
        if not needed.is_file():messagebox.showinfo('Candidate horizons missing','Run Calculate candidate horizons on the map tab first.');return
        launch('analyze_candidate_solar.py','--date',entries[0].get(),'--hours',hrs,'--interval-min',interval,
            '--sun-weight',sun,'--slope-weight',slope,'--uncertainty-weight',err)
    cmd=ttk.Frame(solar);cmd.pack(fill='x',padx=15)
    ttk.Button(cmd,text='Calculate independent candidate solar timelines',command=calc_solar).pack(side='left',padx=(0,10))
    ttk.Button(cmd,text='Refresh comparison results',command=lambda:show_report()).pack(side='left',padx=(0,10))
    ttk.Button(cmd,text='Open solar output folder',command=lambda:open_path(PROCESSED/'candidate_solar'/'Site01')).pack(side='left')
    ttk.Label(solar,text='Scores reflect adjustable preferences for this candidate set. No forced winner; no landing-safety prediction.',wraplength=1160).pack(anchor='w',padx=15,pady=10)
    result_cols=('name','clear_sample_fraction','slope_deg','elevation_rms_m','weighted_score')
    report_table=ttk.Treeview(solar,columns=result_cols,show='headings',height=10)
    for col,name in [('name','Candidate'),('clear_sample_fraction','Clear sample fraction'),('slope_deg','Slope (°)'),('elevation_rms_m','Elevation RMS (m)'),('weighted_score','Preference score')]:
        report_table.heading(col,text=name);report_table.column(col,width=185,anchor='center')
    report_status=tk.StringVar(value='No candidate solar comparison loaded.')
    ttk.Label(solar,textvariable=report_status).pack(anchor='w',padx=15,pady=5)
    report_table.pack(fill='both',expand=True,padx=15,pady=8)
    def show_report():
        for child in report_table.get_children():report_table.delete(child)
        file=latest_candidate_report(PROCESSED/'candidate_solar'/'Site01')
        if file is None:report_status.set('No candidate solar report found yet. Run independent solar analysis.');return
        try:rows=read_candidate_comparison(file)
        except (ValueError,json.JSONDecodeError) as exc:report_status.set(f'Could not read {file}: {exc}');return
        for r in rows:report_table.insert('', 'end',values=[r.get(k,'N/A') for k in result_cols])
        report_status.set(f'Loaded {len(rows)} candidates from {file}. Scores are preferences, not safety ratings.')
    show_report()
    app.mainloop()

if __name__=='__main__':main()
