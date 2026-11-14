"""SelenEkto multi-region terrain explorer. Does not overwrite the integrated dashboard."""
from __future__ import annotations
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk,messagebox,simpledialog
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from selenekto_data.multiregion import SITE_NAMES,SUFFIXES,discover,region_paths,validate_grid,record_metrics,safe_candidate_record,export_candidates,normalize_candidate_name,rename_candidate
RAW=ROOT/'data/raw/lola'
OUT=ROOT/'data/processed/multiregion'

def main():
    import rasterio
    from rasterio.enums import Resampling
    import numpy as np
    import matplotlib
    matplotlib.use('TkAgg')
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    app=tk.Tk();app.title('SELENEKTO / MULTI-REGION EXPLORER · NASA LOLA');app.geometry('1200x835');app.minsize(980,700)
    app.configure(bg='#151515')
    st=ttk.Style(app);st.theme_use('clam')
    st.configure('.',background='#151515',foreground='#eeeeee',fieldbackground='#222222',font=('Segoe UI',10))
    st.configure('TButton',padding=6,background='#2c2c2c',foreground='#eeeeee')
    st.configure('Treeview',background='#202020',foreground='#eee',fieldbackground='#202020',rowheight=22)
    st.configure('Treeview.Heading',background='#353535',foreground='#eee')
    ttk.Label(app,text='S E L E N E K T O   /   M U L T I - R E G I O N',font=('Segoe UI',18,'bold')).pack(anchor='w',padx=16,pady=(12,3))
    ttk.Label(app,text='NASA LOLA 5mpp terrain · Real locally installed regions only · Exploratory results; not landing-safety assessments').pack(anchor='w',padx=16)
    regions=discover(RAW)
    status=tk.StringVar(value='Select an installed region; choose map cells to build a comparison list.')
    toolbar=ttk.Frame(app);toolbar.pack(fill='x',padx=14,pady=10)
    ttk.Label(toolbar,text='Region').pack(side='left',padx=(0,8))
    region_var=tk.StringVar(value=regions[0]['id'] if regions else '')
    selector=ttk.Combobox(toolbar,width=35,textvariable=region_var,state='readonly',values=[r['id']+' · '+r['name'] for r in regions])
    if regions:selector.set(regions[0]['id']+' · '+regions[0]['name'])
    selector.pack(side='left',padx=(0,14))
    ttk.Label(toolbar,text='Layer').pack(side='left',padx=(0,6))
    layer_var=tk.StringVar(value='Elevation')
    layer_selector=ttk.Combobox(toolbar,width=23,textvariable=layer_var,state='readonly',values=list(SUFFIXES));layer_selector.pack(side='left')
    def original():
        launcher=ROOT/'scripts/launch_dashboard.py'
        if not launcher.is_file():messagebox.showinfo('Unavailable','Original dashboard is not installed');return
        subprocess.Popen([sys.executable,str(launcher)],cwd=ROOT)
    ttk.Button(toolbar,text='Original dashboard',command=original).pack(side='right')
    ttk.Label(app,textvariable=status,wraplength=1140).pack(anchor='w',padx=16)
    cols=['region','name','row','col','elevation_m','slope_deg','elevation_rms_m','lola_spot_count']
    tree=ttk.Treeview(app,show='headings',columns=cols,height=5)
    for k in cols:
        tree.heading(k,text=k.replace('_',' ').title());tree.column(k,width=115,anchor='center')
    controls=ttk.Frame(app);controls.pack(fill='x',padx=14,pady=(6,4))
    active={'datasets':{},'region':None,'selected':None,'image':None,'colourbar':None}
    candidates=[]
    fig=Figure(figsize=(10,5),dpi=90,facecolor='#171717');ax=fig.add_subplot(111)
    ax.set_facecolor('#171717');ax.tick_params(colors='white')
    for spine in ax.spines.values():spine.set_color('#888')
    selected_mark,=ax.plot([],[],color='#f66d65',marker='+',markersize=17,linestyle='None',mew=2)
    saved_marks,=ax.plot([],[],color='#f66d65',marker='o',markersize=5,linestyle='None')
    canvas=FigureCanvasTkAgg(fig,master=app)
    def close_ds():
        for ds in active['datasets'].values():ds.close()
        active['datasets']={}
    def refresh_table():
        for row in tree.get_children():tree.delete(row)
        for record in candidates:tree.insert('','end',values=[record.get(k,'') for k in cols])
        region=active['region']
        shown=[r for r in candidates if r['region']==region]
        saved_marks.set_data([r['x_projected_m'] for r in shown],[r['y_projected_m'] for r in shown])
        canvas.draw_idle()
    def change_region(_=None):
        name=region_var.get().split(' · ')[0]
        if name not in SITE_NAMES:return
        close_ds()
        paths=region_paths(RAW,name)
        try:
            validate_grid(rasterio,paths)
            for k,p in paths.items():
                if p.is_file():active['datasets'][k]=rasterio.open(p)
        except Exception as exc:
            close_ds();messagebox.showerror('Invalid region rasters',str(exc));return
        active['region']=name;active['selected']=None
        selected_mark.set_data([],[])
        layer_selector['values']=list(active['datasets'])
        if layer_var.get() not in active['datasets']:layer_var.set('Elevation')
        render_layer()
        status.set(f'{name}: {SITE_NAMES[name]} · {len(active["datasets"])} real raster layers loaded. Click a cell, then Add candidate.')
        refresh_table()
    def render_layer(_=None):
        name=layer_var.get();ds=active['datasets'].get(name)
        if ds is None:return
        preview=ds.read(1,out_shape=(min(ds.height,800),min(ds.width,800)),resampling=Resampling.average,masked=True)
        if active['image'] is not None:
            active['image'].remove();active['image']=None
        # Shared geometry validated on region load.
        active['image']=ax.imshow(preview,cmap='gray',origin='upper',extent=[ds.bounds.left,ds.bounds.right,ds.bounds.bottom,ds.bounds.top])
        ax.set_title(f'{active["region"]} / {name}',color='white');ax.set_xlabel('Projected X (m)',color='white');ax.set_ylabel('Projected Y (m)',color='white')
        if active['colourbar'] is not None:active['colourbar'].remove()
        active['colourbar']=fig.colorbar(active['image'],ax=ax,fraction=.035,pad=.02);active['colourbar'].ax.tick_params(colors='white')
        fig.tight_layout();canvas.draw_idle()
    def click(event):
        if event.inaxes is not ax or event.xdata is None or event.ydata is None:return
        ds=active['datasets'].get('Elevation')
        if ds is None:return
        row,col=ds.index(event.xdata,event.ydata)
        if not (0<=row<ds.height and 0<=col<ds.width):return
        x,y=ds.transform*(col+.5,row+.5)
        metrics=record_metrics(active['datasets'],row,col)
        active['selected']=safe_candidate_record(active['region'],'',row,col,x,y,metrics)
        selected_mark.set_data([x],[y]);canvas.draw_idle()
        status.set(f'{active["region"]} ({row},{col}) elevation {metrics["elevation_m"]} m · slope {metrics["slope_deg"]}° · press Add candidate')
    def add():
        selected=active['selected']
        if selected is None:messagebox.showinfo('Choose a point','Click a terrain cell first.');return
        if any(r['region']==selected['region'] and r['row']==selected['row'] and r['col']==selected['col'] for r in candidates):
            messagebox.showinfo('Duplicate','This region/cell is already saved.');return
        proposed=f'{selected["region"]} Point {1+sum(c["region"]==selected["region"] for c in candidates):02d}'
        name=simpledialog.askstring('Name this location','Give this selected location a memorable name:',initialvalue=proposed,parent=app)
        if name is None:return  # Cancel does not save
        try:
            label=normalize_candidate_name(name)
            if any(c['region']==selected['region'] and c['name'].casefold()==label.casefold() for c in candidates):
                raise ValueError('A candidate in this region already has that name')
        except ValueError as exc:
            messagebox.showwarning('Invalid name',str(exc));return
        rec={**selected,'name':label}
        candidates.append(rec);refresh_table();status.set(f'SAVED {rec["name"]} · {len(candidates)} total candidate(s) across regions')
    def rename():
        selection=tree.selection()
        if len(selection)!=1:
            messagebox.showinfo('Choose a candidate','Select exactly one candidate row to rename.');return
        idx=tree.index(selection[0]);old=candidates[idx]['name']
        value=simpledialog.askstring('Rename candidate','New candidate name:',initialvalue=old,parent=app)
        if value is None:return
        try:rename_candidate(candidates,idx,value)
        except (ValueError,IndexError) as exc:
            messagebox.showwarning('Invalid name',str(exc));return
        refresh_table();status.set(f'Renamed {old} → {candidates[idx]["name"]}')
    def remove():
        rows=tree.selection();keys={tree.index(i) for i in rows}
        candidates[:]=[rec for i,rec in enumerate(candidates) if i not in keys]
        refresh_table();status.set(f'{len(candidates)} candidates remain')
    def export():
        if not candidates:messagebox.showinfo('None selected','Add at least one point.');return
        target=OUT/'selected_candidates_all_regions.csv'
        export_candidates(target,candidates);status.set(f'Exported {len(candidates)} candidate cells to {target}')
        messagebox.showinfo('CSV exported',str(target)+'\n\nCross-region horizon and solar calculations are NOT yet supported by the Site01-only analysis scripts.')
    ttk.Button(controls,text='Add candidate',command=add).pack(side='left',padx=4)
    ttk.Button(controls,text='Rename selected',command=rename).pack(side='left',padx=4)
    ttk.Button(controls,text='Remove selected',command=remove).pack(side='left',padx=4)
    ttk.Button(controls,text='Export region-tagged CSV',command=export).pack(side='left',padx=4)
    ttk.Label(controls,text='Name each point when adding it. Export keeps names and region IDs.').pack(side='left',padx=15)
    tree.pack(fill='x',padx=14,pady=4)
    canvas.get_tk_widget().pack(fill='both',expand=True,padx=14,pady=5)
    canvas.mpl_connect('button_press_event',click)
    selector.bind('<<ComboboxSelected>>',change_region)
    layer_selector.bind('<<ComboboxSelected>>',render_layer)
    def onclose():close_ds();app.destroy()
    app.protocol('WM_DELETE_WINDOW',onclose)
    if regions:change_region()
    else:status.set('No installed regions. Run the NASA downloader for Site04, or check Site01 terrain file locations.')
    app.mainloop()
if __name__=='__main__':main()
