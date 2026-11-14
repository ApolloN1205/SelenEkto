"""SelenEkto Site01 interactive DEM map, local desktop feature.

Run from SelenEkto_Data_Infrastructure root:
  .\\.venv\\Scripts\\python.exe .\\scripts\\launch_site_map.py
"""
from __future__ import annotations
import csv
import subprocess
import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from selenekto_data.site_map import xy_to_cell, terrain_record, centre_xy
from selenekto_data.candidate_compare import comparison_series
from selenekto_data.candidate_store import CandidateStore

LAYERS = {
    'Elevation (m)': ('elevation_m', 'surf'),
    'Slope (degrees)': ('slope_deg', 'slp'),
    'Elevation RMS error (m)': ('elevation_rms_m', 'toterr'),
    'Slope RMS error (degrees)': ('slope_rms_deg', 'slperr'),
    'LOLA spot count': ('lola_spot_count', 'ldec'),
}
DATA = ROOT / 'data' / 'raw' / 'lola' / 'Site01'


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
        raise SystemExit(f'Missing map dependency: {exc}. Run pip install rasterio matplotlib numpy')

    paths = {}
    for name, (_, suffix) in LAYERS.items():
        p = DATA / f'Site01_final_adj_5mpp_{suffix}.tif'
        if not p.is_file():
            raise SystemExit(f'Missing NASA terrain layer: {p}')
        paths[name] = p
    datasets = {name: rasterio.open(path) for name, path in paths.items()}
    try:
        reference = datasets['Elevation (m)']
        for name, ds in datasets.items():
            if (ds.width, ds.height, ds.transform, ds.crs) != (reference.width, reference.height, reference.transform, reference.crs):
                raise SystemExit(f'Raster grid mismatch in {name}; cannot compare cells.')

        root = tk.Tk()
        root.title('SELENEKTO / LUNAR SITE MAP')
        root.geometry('1180x840')
        root.minsize(980, 650)
        root.configure(bg='#101010')
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('.', background='#101010', foreground='#eeeeee', fieldbackground='#252525', font=('Segoe UI', 10))
        style.configure('TButton', padding=6, background='#303030', foreground='#eeeeee')
        style.configure('Treeview', background='#191919', fieldbackground='#191919', foreground='#eeeeee', rowheight=24)
        style.configure('Treeview.Heading', background='#303030', foreground='#eeeeee')
        style.map('Treeview', background=[('selected', '#555555')])

        top = ttk.Frame(root)
        top.pack(fill='x', padx=20, pady=(16, 8))
        ttk.Label(top, text='SELENEKTO / SITE01 TERRAIN MAP', font=('Segoe UI', 19, 'bold')).pack(anchor='w')
        ttk.Label(top, text='NASA PGDA Connecting Ridge · 5 m/pixel local DEM · Click to inspect and save candidate points · NOT landing safety', wraplength=1100).pack(anchor='w')
        header_row = ttk.Frame(root)
        header_row.pack(fill='x', padx=20, pady=5)
        selected_layer = tk.StringVar(value='Elevation (m)')
        ttk.Label(header_row, text='Layer:').pack(side='left', padx=(0, 8))
        selector = ttk.Combobox(header_row, textvariable=selected_layer, values=list(LAYERS), state='readonly', width=29)
        selector.pack(side='left')
        detail = tk.StringVar(value='Click the terrain map to inspect a grid cell.')
        ttk.Label(header_row, textvariable=detail, wraplength=730).pack(side='left', padx=20)

        fig = Figure(figsize=(9.7, 5.8), dpi=100, facecolor='#161616')
        ax = fig.add_subplot(111)
        ax.set_facecolor('#161616')
        ax.tick_params(colors='#dddddd')
        for s in ax.spines.values(): s.set_color('#777777')
        ax.set_xlabel('Projected X (m)', color='#dddddd')
        ax.set_ylabel('Projected Y (m)', color='#dddddd')
        extent = (reference.bounds.left, reference.bounds.right, reference.bounds.bottom, reference.bounds.top)
        preview_cache = {}
        def preview(layer):
            if layer not in preview_cache:
                ds = datasets[layer]
                h = min(800, ds.height)
                w = min(800, ds.width)
                preview_cache[layer] = ds.read(1, out_shape=(h,w), resampling=Resampling.average, masked=True)
            return preview_cache[layer]
        img = ax.imshow(preview(selected_layer.get()), extent=extent, origin='upper', cmap='gray', interpolation='nearest')
        cbar = fig.colorbar(img, ax=ax, fraction=.037, pad=.02)
        cbar.ax.tick_params(colors='#dddddd')
        cbar.set_label(selected_layer.get(), color='#dddddd')
        selected_marker, = ax.plot([], [], marker='+', markersize=14, mew=1.7, color='#ef745b', linestyle='none')
        saved_markers, = ax.plot([], [], marker='o', markersize=4, color='#ef745b', linestyle='none')
        ax.set_aspect('equal')
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=root)
        # The map is packed LAST below the candidate controls, so the buttons
        # always remain visible on shorter Windows displays.
        map_widget = canvas.get_tk_widget()

        chosen = None
        store = CandidateStore()
        saved = store.records
        columns = ('name','row','col','elevation_m','slope_deg','elevation_rms_m','lola_spot_count')
        table = ttk.Treeview(root, columns=columns, show='headings', height=5)
        for col, label, width in [('name','Candidate',145),('row','Row',65),('col','Col',65),('elevation_m','Elevation m',105),('slope_deg','Slope °',85),('elevation_rms_m','Elevation RMS m',130),('lola_spot_count','LOLA spots',95)]:
            table.heading(col, text=label)
            table.column(col, width=width, anchor='center')
        # Table is packed after the toolbar below, before the expandable map.

        def read_cell(row, col):
            values = {}
            for name, (key, _) in LAYERS.items():
                ds = datasets[name]
                v = float(ds.read(1, window=((row,row+1),(col,col+1)))[0,0])
                values[key] = None if (not np.isfinite(v) or (ds.nodata is not None and v == ds.nodata)) else v
            return terrain_record(row, col, values, reference.transform)

        def on_click(event):
            nonlocal chosen
            if event.inaxes != ax or event.xdata is None or event.ydata is None:
                return
            cell = xy_to_cell(reference.transform, event.xdata, event.ydata, reference.width, reference.height)
            if cell is None:
                return
            chosen = read_cell(*cell)
            selected_marker.set_data([chosen['x_projected_m']],[chosen['y_projected_m']])
            detail.set(f"row {chosen['row']}, col {chosen['col']}  |  height {chosen['elevation_m']} m  |  slope {chosen['slope_deg']}°  |  elevation RMS {chosen['elevation_rms_m']} m  |  LOLA spots {chosen['lola_spot_count']}")
            canvas.draw_idle()
        canvas.mpl_connect('button_press_event', on_click)

        def layer_change(_=None):
            img.set_data(preview(selected_layer.get()))
            img.autoscale()
            cbar.set_label(selected_layer.get(), color='#dddddd')
            canvas.draw_idle()
        selector.bind('<<ComboboxSelected>>', layer_change)

        def update_saved():
            for item in table.get_children(): table.delete(item)
            for record in saved:
                table.insert('', 'end', values=[record.get(k) for k in columns])
            saved_markers.set_data([r['x_projected_m'] for r in saved], [r['y_projected_m'] for r in saved])
            canvas.draw_idle()

        def add():
            if chosen is None:
                messagebox.showinfo('Select a cell', 'Click on the terrain map first.')
                return
            try:
                record = store.add(chosen)
            except ValueError as exc:
                messagebox.showinfo('Candidate selection', str(exc))
                return
            update_saved()
            status.set(f"SAVED {record['name']} at row {record['row']}, col {record['col']}  |  {len(saved)} candidate(s) saved")
            table.selection_set(table.get_children()[-1])
            table.see(table.get_children()[-1])

        def remove():
            indices = sorted([table.index(k) for k in table.selection()], reverse=True)
            if not indices:
                messagebox.showinfo('Remove candidate', 'Select a row in the candidate table first.')
                return
            store.remove_positions(indices)
            update_saved()
            status.set(f'{len(saved)} candidate(s) saved')

        def export():
            if not saved:
                messagebox.showinfo('No candidates', 'Add a candidate point before exporting.')
                return
            path = filedialog.asksaveasfilename(title='Export selected candidate cells', defaultextension='.csv', filetypes=[('CSV', '*.csv')], initialfile='Site01_candidates.csv')
            if not path: return
            with open(path, 'w', newline='', encoding='utf-8') as fh:
                writer = csv.DictWriter(fh, fieldnames=list(saved[0]))
                writer.writeheader()
                writer.writerows(saved)
            status.set(f'Exported {len(saved)} candidate(s) to {path}')
            messagebox.showinfo('Exported', f'Exported {len(saved)} selected cell(s) to:\n{path}\n\nNo landing safety has been inferred.')

        def compare():
            if len(saved) < 2:
                messagebox.showinfo('Add more candidates', 'Select and save at least two map cells before comparing.')
                return
            names, metrics = comparison_series(saved)
            window = tk.Toplevel(root)
            window.title('SELENEKTO / CANDIDATE TERRAIN COMPARISON')
            window.geometry('1120x820')
            window.configure(bg='#101010')
            ttk.Label(window, text='SELENEKTO / CANDIDATE COMPARISON', font=('Segoe UI', 17, 'bold')).pack(anchor='w', padx=16, pady=(12, 3))
            ttk.Label(window, text='Site01 map-cell measurements only. No safety or sunlight ranking. Lower slope or uncertainty alone does not establish suitability.', wraplength=1060).pack(anchor='w', padx=16)
            chart = Figure(figsize=(10.2, 6.8), dpi=100, facecolor='#161616')
            fields = [
                ('elevation_m', 'Elevation (m)'),
                ('slope_deg', 'Slope (degrees)'),
                ('elevation_rms_m', 'Elevation RMS error (m)'),
                ('lola_spot_count', 'LOLA spots per cell'),
            ]
            from matplotlib.ticker import MaxNLocator
            for idx, (key, title) in enumerate(fields):
                subplot = chart.add_subplot(2, 2, idx + 1)
                subplot.set_facecolor('#1c1c1c')
                values = metrics[key]
                known_x = [i for i, v in enumerate(values) if v is not None]
                known_y = [values[i] for i in known_x]
                subplot.bar(known_x, known_y, color='#bbbbbb', edgecolor='#eeeeee', linewidth=.5)
                subplot.set_title(title, color='#ffffff', fontsize=10)
                subplot.set_xticks(range(len(names)))
                subplot.set_xticklabels(names, rotation=30, ha='right', fontsize=8, color='#eeeeee')
                subplot.tick_params(axis='y', colors='#dddddd')
                subplot.yaxis.set_major_locator(MaxNLocator(nbins=5))
                for spine in subplot.spines.values(): spine.set_color('#666666')
                for i, value in enumerate(values):
                    if value is None:
                        subplot.text(i, 0, 'N/A', ha='center', va='bottom', color='#ef745b', fontsize=9)
                subplot.grid(axis='y', alpha=.15)
            chart.tight_layout(pad=3)
            compare_canvas = FigureCanvasTkAgg(chart, master=window)
            compare_canvas.draw()
            compare_canvas.get_tk_widget().pack(fill='both', expand=True, padx=14, pady=9)
            ttk.Label(window, text='Observation count 0 means no directly recorded LOLA spots in that pixel. The data may be interpolated. RMS values are not confidence intervals.', wraplength=1060).pack(anchor='w', padx=16, pady=(0, 12))

        status = tk.StringVar(value='No candidates saved. Click the terrain image, then use Add selected cell above it.')
        actions = ttk.Frame(root)
        actions.pack(fill='x', padx=20, pady=(8, 4))
        ttk.Button(actions, text='Add selected cell', command=add).pack(side='left', padx=(0, 8))
        ttk.Button(actions, text='Remove candidate', command=remove).pack(side='left', padx=(0, 8))
        ttk.Button(actions, text='Export candidate CSV', command=export).pack(side='left', padx=(0, 8))
        ttk.Button(actions, text='Compare candidates', command=compare).pack(side='left', padx=(0, 8))

        def analyze_horizons():
            if len(saved) < 2:
                messagebox.showinfo('Candidate horizons', 'Add at least two different cells before analysis.')
                return
            script = ROOT / 'scripts' / 'analyze_candidate_horizons.py'
            if not script.is_file():
                messagebox.showwarning('Candidate horizons not installed',
                    'Install the Candidate Horizons add-on first (scripts/analyze_candidate_horizons.py).')
                return
            path = ROOT / 'data' / 'processed' / 'candidate_horizons' / 'Site01' / 'map_selected_candidates.csv'
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('w', newline='', encoding='utf-8') as fh:
                writer = csv.DictWriter(fh, fieldnames=list(saved[0]))
                writer.writeheader()
                writer.writerows(saved)
            # Run externally so intensive horizon calculations don't freeze Tkinter.
            command = [sys.executable, str(script), '--csv', str(path), '--max-distance-m', '500']
            if sys.platform == 'win32':
                subprocess.Popen(['cmd.exe', '/k', subprocess.list2cmdline(command)], cwd=str(ROOT),
                                 creationflags=getattr(subprocess, 'CREATE_NEW_CONSOLE', 0))
            else:
                subprocess.Popen(command, cwd=str(ROOT))
            status.set('Started candidate horizon analysis (500 m). Check its terminal and the output folder.')
            messagebox.showinfo('Analysis started',
                'Each saved location will get its own terrain horizon.\n'
                'Results: data/processed/candidate_horizons/Site01/\n'
                'A separate terminal shows progress. This is NOT a solar or safety analysis.')

        ttk.Button(actions, text='Analyze candidate horizons', command=analyze_horizons).pack(side='left', padx=(0, 8))
        def open_viewer():
            path = ROOT / 'scripts' / 'launch_selenekto.py'
            if not path.exists():
                messagebox.showerror('Viewer missing', f'Could not find {path}')
                return
            subprocess.Popen([sys.executable, str(path)], cwd=str(ROOT))
        ttk.Button(actions, text='Open terrain + solar viewer', command=open_viewer).pack(side='right')
        ttk.Label(root, textvariable=status, wraplength=1100).pack(anchor='w', padx=20, pady=(2, 4))
        table.pack(fill='x', padx=20, pady=(2, 4))
        map_widget.pack(fill='both', expand=True, padx=20, pady=5)
        ttk.Label(root, text='Site01 DEM only. Candidate points are not validated landing sites. Horizon outputs are local, not global illumination.', wraplength=1100).pack(anchor='w', padx=20, pady=(0, 6))
        def close():
            for ds in datasets.values(): ds.close()
            root.destroy()
        root.protocol('WM_DELETE_WINDOW', close)
        root.mainloop()
    finally:
        for ds in datasets.values():
            if not ds.closed: ds.close()

if __name__ == '__main__':
    main()
