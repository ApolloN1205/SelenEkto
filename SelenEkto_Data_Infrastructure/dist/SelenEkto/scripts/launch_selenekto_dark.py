"""SelenEkto unified lunar explorer: 27-region discovery, map layers, named candidates,
terrain comparison, candidate horizons and real dated solar analysis through worker.
Does not overwrite the prior dashboard.
"""
from __future__ import annotations
import sys,subprocess,json,csv,tkinter as tk
from pathlib import Path
from tkinter import ttk,messagebox,simpledialog
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from selenekto_data.region_audit import describe_pixel
from selenekto_data.unified_regions import (REGIONS,SUFFIXES,region_files,installed_regions,
 validate_region,validate_name,read_metrics,export_candidates,slope_comparison)
RAW=ROOT/'data/raw/lola';OUT=ROOT/'data/processed/unified'
BG='#090909';PANEL='#171717';FG='#f5f5f5';ACCENT='#f07865'

def main():
    import numpy as np,rasterio
    from rasterio.enums import Resampling
    import matplotlib
    matplotlib.use('TkAgg')
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    app=tk.Tk();app.title('SELENEKTO / LUNAR LANDING SITE NAVIGATOR');app.geometry('1330x890');app.minsize(1050,700);app.configure(bg=BG)
    st=ttk.Style(app);st.theme_use('clam')
    st.configure('.',background=BG,foreground=FG,font=('Segoe UI',10));st.configure('TFrame',background=BG)
    st.configure('TButton',background='#343434',foreground=FG,padding=7);st.map('TButton',background=[('active','#555555')])
    st.configure('Treeview',background='#242424',foreground=FG,fieldbackground='#242424',rowheight=24)
    st.configure('Treeview.Heading',background='#363636',foreground=FG)
    st.configure('TNotebook.Tab',background=PANEL,foreground=FG,padding=(15,9))
    st.configure('TEntry',fieldbackground='#090909',foreground=FG,insertcolor=FG,background='#090909',bordercolor='#4b4b4b')
    st.configure('TCombobox',fieldbackground='#090909',foreground=FG,background='#171717',selectbackground='#444444',selectforeground=FG,arrowcolor=FG)
    st.map('TCombobox',fieldbackground=[('readonly','#090909')],foreground=[('readonly',FG)],selectbackground=[('readonly','#444444')])
    st.configure('TNotebook',background='#090909',borderwidth=0)
    st.configure('TNotebook.Tab',background='#171717',foreground='#eaeaea',padding=(19,11),borderwidth=0)
    st.map('TNotebook.Tab',background=[('selected','#393939'),('active','#292929')],foreground=[('selected','#ffffff'),('active','#ffffff')])
    st.map('Treeview',background=[('selected','#4d4d4d')],foreground=[('selected','#ffffff')])
    app.option_add('*TCombobox*Listbox.background','#090909')
    app.option_add('*TCombobox*Listbox.foreground','#ffffff')
    app.option_add('*TCombobox*Listbox.selectBackground','#444444')
    app.option_add('*TCombobox*Listbox.selectForeground','#ffffff')
    tk.Label(app,text='S E L E N E K T O   /   L U N A R   N A V I G A T O R',bg=BG,fg=FG,font=('Segoe UI',18,'bold')).pack(anchor='w',padx=18,pady=(14,2))
    tk.Label(app,text='NASA PGDA lunar south pole | 27 catalogue regions | Site comparison | Experimental local DEM and JPL solar analysis',bg=BG,fg='#bdbdbd').pack(anchor='w',padx=18)
    tabs=ttk.Notebook(app);tabs.pack(fill='both',expand=True,padx=14,pady=9)
    map_tab=ttk.Frame(tabs);comparison_tab=ttk.Frame(tabs);analysis_tab=ttk.Frame(tabs)
    tabs.add(map_tab,text='TERRAIN MAP');tabs.add(comparison_tab,text='COMPARE');tabs.add(analysis_tab,text='SOLAR + HORIZONS')
    audit_tab=ttk.Frame(tabs);tabs.add(audit_tab,text='DATA HEALTH')
    message=tk.StringVar(value='Choose an installed region and click the image to select a candidate cell.')
    tk.Label(app,textvariable=message,bg=BG,fg=ACCENT,anchor='w').pack(fill='x',padx=18,pady=(0,10))
    installed=installed_regions(RAW);selected={'candidate':None};state={'region':None,'datasets':{},'image':None,'colorbar':None};records=[]
    bar=ttk.Frame(map_tab);bar.pack(fill='x',padx=10,pady=8)
    def ask_dark_name(title,prompt,initialvalue=''):
        """Black, high-contrast modal input dialog for candidate names."""
        dialog=tk.Toplevel(app)
        dialog.title(title);dialog.configure(bg=BG)
        dialog.transient(app);dialog.resizable(False,False)
        dialog.geometry('460x180')
        tk.Label(dialog,text=prompt,bg=BG,fg=FG,font=('Segoe UI',11)).pack(anchor='w',padx=18,pady=(16,7))
        name=tk.StringVar(value=initialvalue)
        entry=tk.Entry(dialog,textvariable=name,bg='#090909',fg='#ffffff',insertbackground='#ffffff',
                       highlightbackground='#666666',highlightcolor=ACCENT,relief='flat',font=('Segoe UI',11))
        entry.pack(fill='x',padx=18,ipady=7)
        result={'value':None}
        def finish(ok):
            if ok:result['value']=name.get()
            dialog.destroy()
        row=tk.Frame(dialog,bg=BG);row.pack(anchor='e',padx=18,pady=15)
        tk.Button(row,text='Cancel',command=lambda:finish(False),bg=PANEL,fg=FG,activebackground='#333',
                  activeforeground=FG,relief='flat',padx=13,pady=5).pack(side='left',padx=5)
        tk.Button(row,text='Save name',command=lambda:finish(True),bg='#343434',fg=FG,activebackground='#555',
                  activeforeground=FG,relief='flat',padx=13,pady=5).pack(side='left')
        dialog.bind('<Return>',lambda event:finish(True));dialog.bind('<Escape>',lambda event:finish(False))
        dialog.update_idletasks()
        dialog.grab_set();entry.focus_set();entry.selection_range(0,'end')
        app.wait_window(dialog)
        return result['value']

    def dark_select(parent,var,choices,width=20):
        # A readonly themed combobox is more reliably dark than an OS-native OptionMenu on Windows.
        w=ttk.Combobox(parent,textvariable=var,values=choices,state='readonly',width=width,style='TCombobox')
        return w
    tk.Label(bar,text='Region',fg=FG,bg=BG).pack(side='left',padx=5)
    reg=tk.StringVar(value=installed[0] if installed else 'None installed')
    regions_menu=dark_select(bar,reg,installed if installed else ['None installed'],width=17);regions_menu.pack(side='left')
    tk.Label(bar,text='Map layer',fg=FG,bg=BG).pack(side='left',padx=(20,5))
    layer=tk.StringVar(value='Elevation');layers_menu=dark_select(bar,layer,list(SUFFIXES),width=23);layers_menu.pack(side='left')
    def open_folder():
        OUT.mkdir(parents=True,exist_ok=True)
        if sys.platform=='win32':subprocess.Popen(['explorer.exe',str(OUT)])
    def download_all():
        if not messagebox.askyesno('NASA bulk download',
            'Download all 27 listed NASA PGDA regions (5 GeoTIFF layers per region)?\n\nThis could require several GB of disk space and considerable download time. Completed files are kept if interrupted.'):
            return
        cmd=[sys.executable,str(ROOT/'scripts/download_all_pgda_regions.py'),'--all']
        if sys.platform=='win32':
            subprocess.Popen(['cmd.exe','/k',subprocess.list2cmdline(cmd)],cwd=str(ROOT),creationflags=getattr(subprocess,'CREATE_NEW_CONSOLE',0))
        else:subprocess.Popen(cmd,cwd=str(ROOT))
        message.set('NASA downloader opened in separate terminal. Relaunch dashboard to load newly downloaded regions.')
    ttk.Button(bar,text='DOWNLOAD ALL 27 NASA REGIONS',command=download_all).pack(side='right',padx=4)
    ttk.Button(bar,text='Open outputs',command=open_folder).pack(side='right',padx=4)
    ttk.Button(bar,text='Open original dashboard',command=lambda:subprocess.Popen([sys.executable,str(ROOT/'scripts/launch_dashboard.py')],cwd=ROOT) if (ROOT/'scripts/launch_dashboard.py').is_file() else messagebox.showinfo('Unavailable','Original dashboard is not installed')).pack(side='right',padx=4)
    info=tk.StringVar(value='Click the image, then choose Add candidate. Values are read from the NASA rasters.')
    tk.Label(map_tab,textvariable=info,bg=BG,fg='#e6e6e6',anchor='w').pack(fill='x',padx=14,pady=5)
    controls=ttk.Frame(map_tab);controls.pack(fill='x',padx=12,pady=4)
    columns=['region','name','row','col','elevation_m','slope_deg','elevation_rms_m','slope_rms_deg','lola_spot_count']
    def make_tree(parent,height=5):
        t=ttk.Treeview(parent,show='headings',columns=columns,height=height,selectmode='extended')
        for key in columns:
            t.heading(key,text=key.replace('_',' ').title());t.column(key,width=115,anchor='center',stretch=True)
        return t
    table=make_tree(map_tab,4);table.pack(fill='x',padx=14,pady=4)
    fig=Figure(figsize=(9.8,5),dpi=90,facecolor=BG);ax=fig.add_subplot(111);ax.set_facecolor(BG)
    ax.tick_params(colors=FG);ax.set_xlabel('Projected X (m)',color=FG);ax.set_ylabel('Projected Y (m)',color=FG)
    marker,=ax.plot([],[],marker='+',color=ACCENT,markersize=17,mew=2.5,linestyle='none')
    dots,=ax.plot([],[],marker='o',color=ACCENT,markersize=5,linestyle='none')
    canvas=FigureCanvasTkAgg(fig,master=map_tab);canvas.get_tk_widget().pack(fill='both',expand=True,padx=12,pady=5)
    def close_data():
        for ds in state['datasets'].values():ds.close()
        state['datasets']={}
    def redraw_candidates():
        for key in table.get_children():table.delete(key)
        for record in records:table.insert('', 'end',values=[record.get(k,'') for k in columns])
        here=[r for r in records if r['region']==state['region']]
        dots.set_data([r['x_projected_m'] for r in here],[r['y_projected_m'] for r in here]);canvas.draw_idle()
        refresh_compare()
    def render(*_):
        ds=state['datasets'].get(layer.get())
        if ds is None:return
        thumb=ds.read(1,out_shape=(min(760,ds.height),min(760,ds.width)),resampling=Resampling.average,masked=True)
        if state['image'] is not None:state['image'].remove()
        extent=[ds.bounds.left,ds.bounds.right,ds.bounds.bottom,ds.bounds.top]
        state['image']=ax.imshow(thumb,origin='upper',extent=extent,cmap='gray')
        if state['colorbar'] is not None:state['colorbar'].remove()
        state['colorbar']=fig.colorbar(state['image'],ax=ax,fraction=.035,pad=.025);state['colorbar'].ax.tick_params(colors=FG)
        ax.set_title(f'{state["region"]} · {REGIONS[state["region"]]} / {layer.get()}',color=FG)
        fig.tight_layout();canvas.draw_idle()
    def change_region(*_):
        region=reg.get()
        if region not in installed:return
        close_data()
        try:
            for name,path in validate_region(RAW,region).items():state['datasets'][name]=rasterio.open(path)
        except Exception as exc:messagebox.showerror('Invalid NASA data',str(exc));return
        state['region']=region;selected['candidate']=None;marker.set_data([],[])
        render();redraw_candidates();info.set(f'{region}: {REGIONS[region]} · 5 NASA layers available · Click to inspect')
    def select_cell(event):
        if event.inaxes is not ax or event.xdata is None or event.ydata is None:return
        ds=state['datasets'].get('Elevation')
        if ds is None:return
        row,col=ds.index(event.xdata,event.ydata)
        if not (0<=row<ds.height and 0<=col<ds.width):return
        x,y=ds.transform*(col+.5,row+.5)
        rec={'region':state['region'],'name':'','row':row,'col':col,'x_projected_m':float(x),'y_projected_m':float(y),**read_metrics(state['datasets'],row,col)}
        selected['candidate']=rec;marker.set_data([x],[y]);canvas.draw_idle()
        info.set(f'SELECTED {state["region"]}: ({row},{col}) | Elevation {rec["elevation_m"]} m | Slope {rec["slope_deg"]}° | {describe_pixel({k:rec[k] for k in ("elevation_m","slope_deg","elevation_rms_m","slope_rms_deg","lola_spot_count")})} | Click Add candidate')
    canvas.mpl_connect('button_press_event',select_cell)
    def add():
        r=selected['candidate']
        if r is None:messagebox.showinfo('Select','Click a location on the map first');return
        if any(c['region']==r['region'] and c['row']==r['row'] and c['col']==r['col'] for c in records):messagebox.showinfo('Duplicate','Cell already saved');return
        label=ask_dark_name('Name candidate','Candidate name:',initialvalue=f'{r["region"]} Point {len(records)+1:02d}')
        if label is None:return
        try:name=validate_name(label)
        except ValueError as exc:messagebox.showerror('Invalid name',str(exc));return
        records.append({**r,'name':name});redraw_candidates();info.set(f'SAVED: {name} ({r["region"]})')
    def rename():
        indexes=table.selection()
        if len(indexes)!=1:messagebox.showinfo('Select','Select one row to rename');return
        index=table.index(indexes[0]);name=ask_dark_name('Rename candidate','New name:',initialvalue=records[index]['name'])
        if name is None:return
        try:records[index]['name']=validate_name(name)
        except ValueError as exc:messagebox.showerror('Invalid name',str(exc));return
        redraw_candidates()
    def remove():
        positions=sorted([table.index(i) for i in table.selection()],reverse=True)
        for index in positions:del records[index]
        redraw_candidates()
    def export():
        if not records:messagebox.showinfo('Candidates','Add candidates first');return None
        path=export_candidates(OUT/'selected_candidates.csv',records)
        message.set(f'Exported {len(records)} candidate(s) to {path}');return path
    ttk.Button(controls,text='Add candidate',command=add).pack(side='left',padx=4)
    ttk.Button(controls,text='Rename',command=rename).pack(side='left',padx=4)
    ttk.Button(controls,text='Remove',command=remove).pack(side='left',padx=4)
    ttk.Button(controls,text='Export CSV',command=export).pack(side='left',padx=4)
    reg.trace_add('write',change_region);layer.trace_add('write',render)
    # Comparisons remain independent of solar availability.
    tk.Label(comparison_tab,text='TERRAIN COMPARISON — all saved regions',bg=BG,fg=FG,font=('Segoe UI',14,'bold')).pack(anchor='w',padx=15,pady=12)
    tk.Label(comparison_tab,text='Each value is sampled at the actual candidate cell. Preferences are relative and do NOT imply landing safety.',bg=BG,fg='#ccc').pack(anchor='w',padx=15)
    cmp_tree=make_tree(comparison_tab,11);cmp_tree.pack(fill='x',padx=15,pady=12)
    chart_fig=Figure(figsize=(10,5),dpi=90,facecolor=BG);cax=chart_fig.add_subplot(111);cax.set_facecolor(BG)
    chart_canvas=FigureCanvasTkAgg(chart_fig,master=comparison_tab);chart_canvas.get_tk_widget().pack(fill='both',expand=True,padx=12)
    def refresh_compare():
        for key in cmp_tree.get_children():cmp_tree.delete(key)
        for record in records:cmp_tree.insert('','end',values=[record.get(k,'') for k in columns])
        cax.clear();cax.set_facecolor(BG);cax.tick_params(colors=FG)
        valid=[r for r in records if r.get('slope_deg') is not None]
        if valid:
            cax.bar(range(len(valid)),[r['slope_deg'] for r in valid],color='#9c9c9c')
            cax.set_xticks(range(len(valid)),[r['name'] for r in valid],rotation=25,ha='right')
        cax.set_ylabel('Terrain slope (degrees)',color=FG);cax.set_title('Slopes at selected locations',color=FG)
        chart_fig.tight_layout();chart_canvas.draw_idle()
    # Background analysis via standalone worker, accessible in installed scripts.
    tk.Label(analysis_tab,text='CANDIDATE-SPECIFIC HORIZONS & SOLAR POSITION',bg=BG,fg=FG,font=('Segoe UI',14,'bold')).pack(anchor='w',padx=15,pady=(16,5))
    tk.Label(analysis_tab,text='Calculate independent 360° horizons. Optional live JPL Horizons gives dated Sun positions for every candidate. No Site01 reuse.',bg=BG,fg='#ccc').pack(anchor='w',padx=15)
    settings=ttk.Frame(analysis_tab);settings.pack(anchor='w',padx=15,pady=15)
    from datetime import datetime,timezone
    fields=[('UTC date',datetime.now(timezone.utc).strftime('%Y-%m-%d')),('Hours','72'),('Step minutes','60'),('Radius metres','500'),('Sun weight','2'),('Slope weight','1'),('Uncertainty weight','1')]
    vars=[]
    for i,(title,default) in enumerate(fields):
        tk.Label(settings,text=title,bg=BG,fg=FG).grid(row=0,column=i,padx=5,sticky='w')
        var=tk.StringVar(value=default);vars.append(var)
        ttk.Entry(settings,textvariable=var,width=15).grid(row=1,column=i,padx=5)
    solar_status=tk.StringVar(value='No analysis submitted. First add named candidates on the map.')
    tk.Label(analysis_tab,textvariable=solar_status,bg=BG,fg=ACCENT,wraplength=1000).pack(anchor='w',padx=15,pady=5)
    def run_analysis(with_sun):
        if not records:messagebox.showinfo('Candidates','Add at least one candidate');return
        try:
            datetime.strptime(vars[0].get(),'%Y-%m-%d')
            hours,interval,radius=int(vars[1].get()),int(vars[2].get()),int(vars[3].get())
            weights=[float(v.get()) for v in vars[4:]]
            if not (1<=hours<=336 and 10<=interval<=720 and 100<=radius<=5000 and all(w>=0 for w in weights) and sum(weights)>0):raise ValueError('Invalid range')
        except ValueError:
            messagebox.showerror('Inputs','Date YYYY-MM-DD; hours 1–336; interval 10–720; radius 100–5000; nonnegative weights with positive total.');return
        path=export()
        cmd=[sys.executable,str(ROOT/'scripts/analyze_multiregion_candidates.py'),'--csv',str(path),'--date',vars[0].get(),'--hours',str(hours),'--interval-min',str(interval),'--radius',str(radius),'--sun-weight',str(weights[0]),'--slope-weight',str(weights[1]),'--uncertainty-weight',str(weights[2])]
        if with_sun:cmd.append('--solar')
        try:
            if sys.platform=='win32':subprocess.Popen(['cmd.exe','/k',subprocess.list2cmdline(cmd)],cwd=str(ROOT),creationflags=getattr(subprocess,'CREATE_NEW_CONSOLE',0))
            else:subprocess.Popen(cmd,cwd=str(ROOT))
            solar_status.set('Calculation started in a separate terminal. Check progress/errors there and open outputs when complete.')
        except OSError as exc:messagebox.showerror('Failed',str(exc))
    actions=ttk.Frame(analysis_tab);actions.pack(anchor='w',padx=15,pady=7)
    ttk.Button(actions,text='Calculate candidate horizons',command=lambda:run_analysis(False)).pack(side='left',padx=6)
    ttk.Button(actions,text='Calculate LIVE solar + horizons',command=lambda:run_analysis(True)).pack(side='left',padx=6)
    ttk.Button(actions,text='Open analysis outputs',command=open_folder).pack(side='left',padx=6)
    tk.Label(analysis_tab,text='Latest solar comparison (load after the separate worker finishes):',bg=BG,fg=FG).pack(anchor='w',padx=20,pady=(15,4))
    report_cols=('region','name','clear_sample_fraction','slope_deg','elevation_rms_m','weighted_score')
    report=ttk.Treeview(analysis_tab,show='headings',columns=report_cols,height=9)
    for key in report_cols:
        report.heading(key,text=key.replace('_',' ').title());report.column(key,width=165,anchor='center')
    report.pack(fill='x',padx=18,pady=6)
    def refresh_report():
        path=OUT/vars[0].get()/'candidate_comparison.csv'
        for item in report.get_children():report.delete(item)
        if not path.is_file():
            solar_status.set('No solar comparison CSV found for this date yet; run LIVE analysis first.')
            return
        try:
            with path.open(newline='',encoding='utf-8') as file:
                rows=list(csv.DictReader(file))
            for rec in rows:report.insert('','end',values=[rec.get(k,'') for k in report_cols])
            solar_status.set(f'Loaded {len(rows)} real candidate-specific solar results from {path}')
        except Exception as exc:messagebox.showerror('Could not read comparison',str(exc))
    ttk.Button(analysis_tab,text='Refresh dated solar comparison',command=refresh_report).pack(anchor='w',padx=18,pady=5)
    tk.Label(analysis_tab,text='Interpretation: Sun centre above horizon means modelled local terrain clearance at the sampled instant.\nNASA DEM coverage is finite and uncertain; scores express chosen preferences, not validated landing conditions.',bg=BG,fg='#bdbdbd',justify='left').pack(anchor='w',padx=20,pady=12)

    # Local data inventory: no false claims that the complete NASA catalogue is installed.
    tk.Label(audit_tab,text='NASA DATA HEALTH — DOWNLOADS, ALIGNMENT & NODATA',bg=BG,fg=FG,font=('Segoe UI',14,'bold')).pack(anchor='w',padx=15,pady=(14,6))
    tk.Label(audit_tab,text='Missing raster files are not the same as NoData pixels. The audit is read-only and samples each raster sparsely.',bg=BG,fg='#c9c9c9').pack(anchor='w',padx=15,pady=(0,8))
    a_cols=('region','status','missing','invalid','nodata_sample')
    health=ttk.Treeview(audit_tab,columns=a_cols,show='headings',height=20)
    for key,width in zip(a_cols,(140,230,170,170,210)):
        health.heading(key,text=key.replace('_',' ').title());health.column(key,width=width,anchor='center')
    health.pack(fill='both',expand=True,padx=15,pady=8)
    health_note=tk.StringVar(value='Press Audit data to scan local NASA GeoTIFFs. Large files are sampled without reading all pixels.')
    tk.Label(audit_tab,textvariable=health_note,bg=BG,fg=ACCENT,wraplength=1000).pack(anchor='w',padx=15,pady=5)
    def audit_now():
        try:
            from selenekto_data.region_audit import classify_region
            for key in health.get_children(): health.delete(key)
            good=0
            for region in REGIONS:
                result=classify_region(RAW,region,region_files(RAW,region))
                missing=sum(x['status']=='missing_file' for x in result['layers'].values())
                invalid=sum(x['status'] in ('invalid_file','grid_mismatch') for x in result['layers'].values())
                nodata=sum(x['status']=='sample_only_nodata' for x in result['layers'].values())
                good+=result['status']=='ready'
                health.insert('','end',values=(region,result['status'],missing,invalid,nodata))
            health_note.set(f'{good}/{len(REGIONS)} regions ready by overview sampling. See the full audit report for sampled NoData percentages.')
        except Exception as exc:
            messagebox.showerror('Data audit failed',str(exc))
    def detailed_audit():
        cmd=[sys.executable,str(ROOT/'scripts/audit_pgda_regions.py')]
        if sys.platform=='win32':subprocess.Popen(['cmd.exe','/k',subprocess.list2cmdline(cmd)],cwd=str(ROOT),creationflags=getattr(subprocess,'CREATE_NEW_CONSOLE',0))
        else:subprocess.Popen(cmd,cwd=str(ROOT))
    audit_controls=ttk.Frame(audit_tab);audit_controls.pack(anchor='w',padx=15,pady=8)
    ttk.Button(audit_controls,text='Audit installed data',command=audit_now).pack(side='left',padx=5)
    ttk.Button(audit_controls,text='Export full CSV / JSON audit',command=detailed_audit).pack(side='left',padx=5)
    ttk.Button(audit_controls,text='Retry missing downloads',command=download_all).pack(side='left',padx=5)

    def onclose():close_data();app.destroy()
    app.protocol('WM_DELETE_WINDOW',onclose)
    if installed:change_region()
    else:message.set('No complete region installed. Use the bulk NASA downloader then reopen the dashboard.')
    app.mainloop()
if __name__=='__main__':main()
