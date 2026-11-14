"""SelenEkto repaired single-window dashboard. Preserves all older launchers.
UI: dark region/layer chooser, candidate selection, explicit compare, side-by-side maps,
local horizon + optional JPL solar worker, visible data health and task diagnostics.
"""
from __future__ import annotations
import csv, json, subprocess, sys, tkinter as tk
from datetime import datetime, timezone
from pathlib import Path
from tkinter import ttk, messagebox

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from selenekto_data.unified_regions import REGIONS, SUFFIXES, region_files, validate_region, read_metrics, validate_name, export_candidates
from selenekto_data.region_audit import classify_region
from selenekto_data.repair_utils import candidate_display, comparable_candidates, valid_value, save_path

RAW = ROOT / 'data/raw/lola'
OUT = ROOT / 'data/processed/unified'
BG, PANEL, TEXT, DIM, ACCENT = '#090909', '#1a1a1a', '#f1f1f1', '#bdbdbd', '#eb7765'
FIELDS = ('region', 'name', 'row', 'col', 'elevation_m', 'slope_deg', 'elevation_rms_m', 'slope_rms_deg', 'lola_spot_count')


def main():
    import numpy as np
    import rasterio
    from rasterio.enums import Resampling
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

    app = tk.Tk()
    app.title('SELENEKTO / REPAIRED LUNAR NAVIGATOR')
    app.geometry('1440x910')
    app.minsize(1080, 720)
    app.configure(bg=BG)
    style = ttk.Style(app)
    style.theme_use('clam')
    style.configure('TFrame', background=BG)
    style.configure('TLabel', background=BG, foreground=TEXT)
    style.configure('TButton', background='#303030', foreground=TEXT, padding=7)
    style.map('TButton', background=[('active', '#505050')], foreground=[('disabled', '#888888')])
    style.configure('TNotebook', background=BG)
    style.configure('TNotebook.Tab', background=PANEL, foreground=TEXT, padding=(17, 10))
    style.map('TNotebook.Tab', background=[('selected', '#404040'), ('active', '#333333')], foreground=[('selected', '#ffffff')])
    style.configure('Treeview', background='#202020', fieldbackground='#202020', foreground=TEXT, rowheight=25)
    style.configure('Treeview.Heading', background='#353535', foreground=TEXT)
    style.map('Treeview', background=[('selected', '#474747')], foreground=[('selected', '#ffffff')])
    style.configure('TCombobox', fieldbackground=BG, foreground=TEXT, background=PANEL, arrowcolor=TEXT)
    style.map('TCombobox', fieldbackground=[('readonly', BG)], foreground=[('readonly', TEXT)])
    style.configure('TEntry', fieldbackground=BG, foreground=TEXT, insertcolor=TEXT)
    for key, val in {'background': BG, 'foreground': TEXT, 'selectBackground': '#444444', 'selectForeground': '#ffffff'}.items():
        app.option_add('*TCombobox*Listbox.' + key, val)
    app.option_add('*Dialog.msg.font', 'Segoe UI 10')

    def label(parent, text, **kwargs):
        return tk.Label(parent, text=text, bg=BG, fg=TEXT, **kwargs)

    def dark_input(title, prompt, previous=''):
        window = tk.Toplevel(app)
        window.title(title)
        window.configure(bg=BG)
        window.geometry('440x175')
        window.transient(app)
        window.resizable(False, False)
        label(window, prompt).pack(anchor='w', padx=16, pady=(16, 8))
        var = tk.StringVar(value=previous)
        box = tk.Entry(window, textvariable=var, bg=BG, fg=TEXT, insertbackground=TEXT,
                       highlightbackground='#777777', font=('Segoe UI', 11))
        box.pack(fill='x', padx=16, ipady=5)
        result = [None]
        def finish(ok):
            if ok: result[0] = var.get()
            window.destroy()
        controls = tk.Frame(window, bg=BG)
        controls.pack(side='bottom', anchor='e', padx=14, pady=15)
        tk.Button(controls, text='Cancel', command=lambda: finish(False), bg=PANEL, fg=TEXT).pack(side='left', padx=4)
        tk.Button(controls, text='Save', command=lambda: finish(True), bg='#373737', fg=TEXT).pack(side='left', padx=4)
        window.bind('<Return>', lambda _: finish(True))
        window.bind('<Escape>', lambda _: finish(False))
        window.grab_set()
        box.focus_set()
        box.selection_range(0, 'end')
        app.wait_window(window)
        return result[0]

    header = label(app, 'S E L E N E K T O   /   L U N A R   N A V I G A T O R', font=('Segoe UI', 17, 'bold'))
    header.pack(anchor='w', padx=16, pady=(10, 3))
    status = tk.StringVar(value='Ready. Select a region and a valid pixel to begin.')
    tk.Label(app, textvariable=status, bg=BG, fg=ACCENT, anchor='w').pack(side='bottom', fill='x', padx=18, pady=9)
    tabs = ttk.Notebook(app)
    tabs.pack(fill='both', expand=True, padx=14, pady=6)
    map_tab, cmp_tab, solar_tab, health_tab = [ttk.Frame(tabs) for _ in range(4)]
    for tab, title in zip((map_tab, cmp_tab, solar_tab, health_tab), ('TERRAIN MAP', 'COMPARE', 'SOLAR + HORIZONS', 'DATA HEALTH')):
        tabs.add(tab, text=title)

    records = []
    selected = {'value': None}
    state = {'region': None, 'rasters': {}, 'im': None, 'bar': None}
    active_task = {'proc': None, 'log': None}

    def region_list():
        ready = []
        for region in REGIONS:
            try:
                validate_region(RAW, region)
                ready.append(region)
            except (OSError, ValueError):
                continue
        return ready

    toolbar = ttk.Frame(map_tab)
    toolbar.pack(fill='x', padx=9, pady=7)
    label(toolbar, 'Region').pack(side='left', padx=4)
    region = tk.StringVar()
    region_box = ttk.Combobox(toolbar, textvariable=region, state='readonly', width=16)
    region_box.pack(side='left', padx=3)
    label(toolbar, 'Layer').pack(side='left', padx=(15, 4))
    layer = tk.StringVar(value='Elevation')
    layer_box = ttk.Combobox(toolbar, textvariable=layer, state='readonly', values=list(SUFFIXES), width=24)
    layer_box.pack(side='left', padx=3)
    title_var = tk.StringVar(value='Click the image to inspect a cell, then Add named candidate.')
    tk.Label(map_tab, textvariable=title_var, bg=BG, fg=DIM, anchor='w').pack(fill='x', padx=14, pady=3)
    map_controls = ttk.Frame(map_tab)
    map_controls.pack(fill='x', padx=12, pady=3)

    tree = ttk.Treeview(map_tab, columns=FIELDS, show='headings', selectmode='extended', height=4)
    for k in FIELDS:
        tree.heading(k, text=k.replace('_', ' ').title())
        tree.column(k, anchor='center', width=113, stretch=True)
    tree.pack(fill='x', padx=12, pady=6)
    map_fig = Figure(figsize=(10, 5), dpi=90, facecolor=BG)
    ax = map_fig.add_subplot(111)
    ax.set_facecolor(BG)
    ax.tick_params(colors=TEXT)
    marker, = ax.plot([], [], '+', markersize=17, markeredgewidth=2.5, color=ACCENT)
    points, = ax.plot([], [], 'o', markersize=5, color=ACCENT)
    map_canvas = FigureCanvasTkAgg(map_fig, master=map_tab)
    map_canvas.get_tk_widget().pack(fill='both', expand=True, padx=9, pady=5)

    def close_rasters():
        for ds in state['rasters'].values():
            ds.close()
        state['rasters'].clear()

    def persist():
        if records:
            export_candidates(save_path(ROOT), records)
        else:
            p = save_path(ROOT)
            if p.exists(): p.unlink()

    def load_saved():
        p = save_path(ROOT)
        if p.exists():
            try:
                with p.open(encoding='utf-8-sig', newline='') as h:
                    for r in csv.DictReader(h):
                        if r.get('region') in REGIONS:
                            for col in ('row', 'col'): r[col] = int(r[col])
                            for col in ('x_projected_m', 'y_projected_m', 'elevation_m', 'slope_deg', 'elevation_rms_m', 'slope_rms_deg', 'lola_spot_count'):
                                r[col] = valid_value(r.get(col))
                            records.append(r)
            except Exception as exc:
                status.set(f'Saved candidate CSV could not be loaded: {exc}')

    def refresh_rows():
        tree.delete(*tree.get_children())
        for i, r in enumerate(records):
            tree.insert('', 'end', iid=str(i), values=[r.get(k) if r.get(k) is not None else 'NoData' for k in FIELDS])
        here = [r for r in records if r['region'] == state['region']]
        points.set_data([r['x_projected_m'] for r in here], [r['y_projected_m'] for r in here])
        map_canvas.draw_idle()
        refresh_compare_choices()

    def render(*_):
        ds = state['rasters'].get(layer.get())
        if ds is None: return
        thumb = ds.read(1, out_shape=(min(ds.height, 680), min(ds.width, 680)),
                        resampling=Resampling.average, masked=True)
        if state['im'] is not None: state['im'].remove()
        if state['bar'] is not None: state['bar'].remove()
        ax.set_facecolor(BG)
        extent = (ds.bounds.left, ds.bounds.right, ds.bounds.bottom, ds.bounds.top)
        state['im'] = ax.imshow(thumb, extent=extent, origin='upper', cmap='gray')
        state['bar'] = map_fig.colorbar(state['im'], ax=ax, fraction=.035, pad=.025)
        state['bar'].ax.tick_params(colors=TEXT)
        ax.set_title(f'{state["region"]} / {REGIONS[state["region"]]} — {layer.get()}', color=TEXT)
        ax.set_xlabel('Projected X (m)', color=TEXT)
        ax.set_ylabel('Projected Y (m)', color=TEXT)
        map_fig.tight_layout()
        map_canvas.draw_idle()

    def switch_region(*_):
        r = region.get()
        if r not in REGIONS: return
        close_rasters()
        try:
            files = validate_region(RAW, r)
            for name, path in files.items():
                state['rasters'][name] = rasterio.open(path)
            state['region'] = r
            selected['value'] = None
            marker.set_data([], [])
            render()
            refresh_rows()
            status.set(f'Loaded {r} / {REGIONS[r]}: all five layers are present and aligned.')
        except Exception as exc:
            status.set(f'{r} failed: {exc}')
            messagebox.showerror('Region could not load', str(exc))

    def scan_map():
        choices = region_list()
        region_box['values'] = choices
        if choices:
            if region.get() not in choices: region.set(choices[0])
            switch_region()
        else:
            close_rasters()
            status.set('No complete NASA region found. Open DATA HEALTH for missing file details.')
        return choices

    def click_map(event):
        if event.inaxes is not ax or event.xdata is None or event.ydata is None: return
        ds = state['rasters'].get('Elevation')
        if ds is None: return
        row, col = ds.index(event.xdata, event.ydata)
        if not (0 <= row < ds.height and 0 <= col < ds.width): return
        x, y = ds.transform * (col + .5, row + .5)
        metrics = read_metrics(state['rasters'], row, col)
        candidate = dict(region=state['region'], name='', row=row, col=col,
                         x_projected_m=float(x), y_projected_m=float(y), **metrics)
        selected['value'] = candidate
        marker.set_data([x], [y])
        map_canvas.draw_idle()
        missing = [k for k, v in metrics.items() if v is None]
        title_var.set(f'({row}, {col}): Elevation {metrics["elevation_m"]} m | Slope {metrics["slope_deg"]}° | Missing: {", ".join(missing) if missing else "none"}')

    map_canvas.mpl_connect('button_press_event', click_map)

    def add_candidate():
        rec = selected['value']
        if not rec:
            messagebox.showinfo('Choose a cell', 'Click a terrain cell first.')
            return
        if rec['elevation_m'] is None:
            messagebox.showwarning('NoData', 'This cell has no usable elevation; choose another cell.')
            return
        if any(r['region'] == rec['region'] and r['row'] == rec['row'] and r['col'] == rec['col'] for r in records):
            messagebox.showinfo('Already saved', 'This region and cell are already in your candidates.')
            return
        name = dark_input('Name candidate', 'Name this location:', f'{rec["region"]} Candidate {len(records)+1:02d}')
        if name is None: return
        try: name = validate_name(name)
        except ValueError as exc:
            messagebox.showerror('Invalid name', str(exc))
            return
        records.append({**rec, 'name': name})
        persist(); refresh_rows()
        status.set(f'Saved {candidate_display(records[-1])}. Candidates persist after restart.')

    def selected_indices():
        return [int(i) for i in tree.selection()]

    def rename_candidate():
        indices = selected_indices()
        if len(indices) != 1:
            messagebox.showinfo('Choose one', 'Select exactly one row in the candidate table.')
            return
        old = records[indices[0]]
        answer = dark_input('Rename candidate', 'New candidate name:', old['name'])
        if answer is None: return
        try: old['name'] = validate_name(answer)
        except ValueError as exc:
            messagebox.showerror('Invalid name', str(exc))
            return
        persist(); refresh_rows()

    def remove_candidates():
        for index in sorted(selected_indices(), reverse=True):
            del records[index]
        persist(); refresh_rows()
        status.set('Selected candidates removed.')

    for txt, fn in [('Add named candidate', add_candidate), ('Rename selected', rename_candidate),
                    ('Remove selected', remove_candidates), ('Refresh regions', scan_map)]:
        ttk.Button(map_controls, text=txt, command=fn).pack(side='left', padx=4)
    region_box.bind('<<ComboboxSelected>>', switch_region)
    layer_box.bind('<<ComboboxSelected>>', render)

    # Explicit comparison selection: no need to compare every saved candidate.
    label(cmp_tab, 'COMPARE SELECTED CANDIDATES', font=('Segoe UI', 14, 'bold')).pack(anchor='w', padx=14, pady=10)
    label(cmp_tab, 'Select two or more candidates. The two image panels can be chosen independently.').pack(anchor='w', padx=14)
    cmp_top = ttk.Frame(cmp_tab)
    cmp_top.pack(fill='x', padx=14, pady=8)
    names = tk.Listbox(cmp_top, selectmode='extended', height=6, exportselection=False,
                       bg=PANEL, fg=TEXT, selectbackground='#555555', selectforeground=TEXT, width=55)
    names.pack(side='left', padx=(0, 12))
    cmp_buttons = ttk.Frame(cmp_top)
    cmp_buttons.pack(side='left')
    compare_fig = Figure(figsize=(12, 6), dpi=88, facecolor=BG)
    compare_canvas = FigureCanvasTkAgg(compare_fig, master=cmp_tab)
    compare_canvas.get_tk_widget().pack(fill='both', expand=True, padx=12, pady=4)
    options = ttk.Frame(cmp_tab)
    options.pack(fill='x', padx=14, pady=5)
    left_name, right_name, compare_layer = tk.StringVar(), tk.StringVar(), tk.StringVar(value='Slope')
    label(options, 'Left image').pack(side='left', padx=5)
    left_box = ttk.Combobox(options, textvariable=left_name, state='readonly', width=35)
    left_box.pack(side='left', padx=5)
    label(options, 'Right image').pack(side='left', padx=5)
    right_box = ttk.Combobox(options, textvariable=right_name, state='readonly', width=35)
    right_box.pack(side='left', padx=5)
    label(options, 'Layer').pack(side='left', padx=5)
    cmp_layer_box = ttk.Combobox(options, textvariable=compare_layer, state='readonly', values=list(SUFFIXES), width=21)
    cmp_layer_box.pack(side='left', padx=5)
    selection_map = {}

    def refresh_compare_choices():
        names.delete(0, 'end')
        selection_map.clear()
        for i, rec in enumerate(records):
            text = f'{i+1:02d} / {candidate_display(rec)}'
            names.insert('end', text)
            selection_map[text] = i
        values = list(selection_map)
        left_box['values'] = right_box['values'] = values
        if left_name.get() not in selection_map: left_name.set(values[0] if values else '')
        if right_name.get() not in selection_map: right_name.set(values[1] if len(values) > 1 else (values[0] if values else ''))
        if len(values) >= 2 and not names.curselection():
            names.selection_set(0, 1)

    def compare_chart():
        try: chosen = comparable_candidates(records, list(names.curselection()))
        except ValueError as exc:
            messagebox.showinfo('Select candidates', str(exc))
            return
        compare_fig.clear()
        axs = compare_fig.subplots(2, 2)
        for ax, key, title in zip(axs.flat, ('slope_deg', 'elevation_m', 'elevation_rms_m', 'lola_spot_count'),
                                  ('Slope (°)', 'Elevation (m)', 'Elevation RMS error (m)', 'LOLA spots per cell')):
            vals = [valid_value(r.get(key)) for r in chosen]
            ax.set_facecolor(PANEL)
            ax.bar(range(len(vals)), [v if v is not None else 0 for v in vals], color='#a8a8a8')
            for i, val in enumerate(vals):
                if val is None: ax.text(i, 0, 'NoData', color=ACCENT, ha='center', va='bottom')
            ax.set_xticks(range(len(vals)), [r['name'] for r in chosen], rotation=15, ha='right')
            ax.set_title(title, color=TEXT)
            ax.tick_params(colors=TEXT)
        compare_fig.tight_layout()
        compare_canvas.draw_idle()
        status.set(f'Comparing {len(chosen)} explicitly selected candidates. Missing values are labelled.')

    def compare_images():
        if left_name.get() not in selection_map or right_name.get() not in selection_map:
            messagebox.showinfo('Select images', 'Choose a candidate for each image panel.')
            return
        a, b = [records[selection_map[v]] for v in (left_name.get(), right_name.get())]
        if a is b:
            messagebox.showinfo('Different sites', 'Choose two different candidates for a side-by-side comparison.')
            return
        kind = compare_layer.get()
        compare_fig.clear()
        axes = compare_fig.subplots(1, 2)
        for ax, rec in zip(axes, (a, b)):
            path = region_files(RAW, rec['region'])[kind]
            try:
                with rasterio.open(path) as ds:
                    rr, cc = int(rec['row']), int(rec['col'])
                    pad = 100  # 500m half-width at 5m/pixel; local cell neighbourhood
                    r0, r1 = max(0, rr-pad), min(ds.height, rr+pad+1)
                    c0, c1 = max(0, cc-pad), min(ds.width, cc+pad+1)
                    window = rasterio.windows.Window(c0, r0, c1-c0, r1-r0)
                    tile = ds.read(1, window=window, masked=True)
                    if np.ma.count(tile) == 0:
                        ax.text(.5, .5, 'NO VALID PIXELS', ha='center', color=ACCENT, transform=ax.transAxes)
                    else:
                        image = ax.imshow(tile, cmap='gray', origin='upper')
                        compare_fig.colorbar(image, ax=ax, fraction=.043)
                    ax.plot(cc-c0, rr-r0, marker='+', color=ACCENT, markersize=12, markeredgewidth=2)
                    ax.set_title(f'{rec["name"]} / {rec["region"]}\n{kind}', color=TEXT)
            except Exception as exc:
                ax.text(.1, .5, str(exc)[:80], color=ACCENT, transform=ax.transAxes)
            ax.set_facecolor(PANEL)
            ax.tick_params(colors=TEXT)
        compare_fig.tight_layout()
        compare_canvas.draw_idle()
        status.set('Two local image cutouts shown at the same 5 m/pixel scale (where data are available).')

    ttk.Button(cmp_buttons, text='Compare selected metrics', command=compare_chart).pack(fill='x', pady=4)
    ttk.Button(cmp_buttons, text='Show side-by-side images', command=compare_images).pack(fill='x', pady=4)
    ttk.Button(cmp_buttons, text='Select all', command=lambda: names.selection_set(0, 'end')).pack(fill='x', pady=4)

    # Worker runs in background process; status is polled and full output logged rather than silently failing.
    label(solar_tab, 'INDEPENDENT TERRAIN HORIZONS + DATED SUN POSITION', font=('Segoe UI', 14, 'bold')).pack(anchor='w', padx=15, pady=13)
    label(solar_tab, 'Select candidates in COMPARE first. Only these locations will be analysed. Uses JPL Horizons when LIVE solar is selected.').pack(anchor='w', padx=15)
    fields = [('UTC date', datetime.now(timezone.utc).strftime('%Y-%m-%d')), ('Hours', '72'), ('Step min', '60'),
              ('Radius m', '500'), ('Sun weight', '2'), ('Slope weight', '1'), ('Uncertainty weight', '1')]
    form = ttk.Frame(solar_tab)
    form.pack(anchor='w', padx=15, pady=14)
    entries = []
    for i, (title, value) in enumerate(fields):
        label(form, title).grid(row=0, column=i, padx=5, sticky='w')
        var = tk.StringVar(value=value)
        ttk.Entry(form, textvariable=var, width=16).grid(row=1, column=i, padx=5)
        entries.append(var)
    progress = tk.StringVar(value='No analysis running.')
    tk.Label(solar_tab, textvariable=progress, bg=BG, fg=ACCENT, wraplength=1100, justify='left').pack(anchor='w', padx=17, pady=5)
    result_cols = ('region', 'name', 'clear_sample_fraction', 'slope_deg', 'elevation_rms_m', 'weighted_score')
    results = ttk.Treeview(solar_tab, columns=result_cols, show='headings', height=11)
    for k in result_cols:
        results.heading(k, text=k.replace('_', ' ').title())
        results.column(k, width=160, anchor='center')
    results.pack(fill='x', padx=15, pady=8)

    def worker_status():
        proc = active_task['proc']
        if proc is None: return
        if proc.poll() is None:
            app.after(1500, worker_status)
            return
        active_task['proc'] = None
        if active_task['log']:
            active_task['log'].close()
            active_task['log'] = None
        logpath = OUT / 'last_analysis.log'
        summary = logpath.read_text(encoding='utf-8', errors='replace')[-1000:] if logpath.exists() else ''
        if proc.returncode == 0:
            progress.set('Analysis completed successfully. Click Load results. Log: ' + str(logpath))
        else:
            progress.set(f'Analysis FAILED (exit {proc.returncode}). Error: {summary[-450:]}')
            messagebox.showerror('Analysis failed', f'Worker exit {proc.returncode}.\n\n{summary[-650:]}')

    def selected_compare_candidates():
        try: return comparable_candidates(records, list(names.curselection()))
        except ValueError as exc:
            messagebox.showinfo('Candidate selection', 'Open COMPARE and select two or more candidates first.\n' + str(exc))
            return None

    def execute_analysis(live):
        if active_task['proc'] is not None:
            messagebox.showinfo('Running', 'An analysis is already running. Check its status before starting another.')
            return
        chosen = selected_compare_candidates()
        if not chosen: return
        try:
            datetime.strptime(entries[0].get(), '%Y-%m-%d')
            hrs, minutes, radius = [int(e.get()) for e in entries[1:4]]
            weights = [float(e.get()) for e in entries[4:]]
            if not (1 <= hrs <= 336 and 10 <= minutes <= 720 and 100 <= radius <= 5000 and
                    all(v >= 0 for v in weights) and sum(weights) > 0): raise ValueError('Outside allowed range')
        except ValueError as exc:
            messagebox.showerror('Invalid inputs', 'Use date YYYY-MM-DD, hours 1–336, step 10–720, radius 100–5000 and nonnegative weights. ' + str(exc))
            return
        OUT.mkdir(parents=True, exist_ok=True)
        selection_path = OUT / 'analysis_selection.csv'
        export_candidates(selection_path, chosen)
        cmd = [sys.executable, '-u', str(ROOT / 'scripts/analyze_multiregion_candidates.py'), '--csv', str(selection_path),
               '--date', entries[0].get(), '--hours', str(hrs), '--interval-min', str(minutes), '--radius', str(radius),
               '--sun-weight', str(weights[0]), '--slope-weight', str(weights[1]), '--uncertainty-weight', str(weights[2])]
        if live: cmd.append('--solar')
        if not (ROOT / 'scripts/analyze_multiregion_candidates.py').exists():
            messagebox.showerror('Missing worker', 'The candidate analysis worker is not installed.')
            return
        log = (OUT / 'last_analysis.log').open('w', encoding='utf-8')
        try:
            proc = subprocess.Popen(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        except Exception as exc:
            log.close(); messagebox.showerror('Unable to start worker', str(exc)); return
        active_task.update(proc=proc, log=log)
        progress.set(f'Running {len(chosen)} independent candidate horizons' + (' + live JPL solar.' if live else '.') + ' Progress is logged.')
        app.after(1200, worker_status)

    def load_analysis():
        p = OUT / entries[0].get() / 'candidate_comparison.csv'
        results.delete(*results.get_children())
        if not p.exists():
            progress.set(f'No dated solar results at {p}. Run LIVE solar; horizon-only mode writes horizon JSON and PNG, not comparison scores.')
            return
        try:
            with p.open(newline='', encoding='utf-8') as h: rows = list(csv.DictReader(h))
            for row in rows: results.insert('', 'end', values=[row.get(k, '') for k in result_cols])
            progress.set(f'Loaded {len(rows)} candidate-specific solar summaries from {p}.')
        except Exception as exc:
            messagebox.showerror('Results could not load', str(exc))

    commandbar = ttk.Frame(solar_tab)
    commandbar.pack(anchor='w', padx=14, pady=8)
    for title, fn in [('Calculate selected horizons', lambda: execute_analysis(False)),
                      ('Calculate LIVE candidate Sun + horizon', lambda: execute_analysis(True)),
                      ('Load dated results', load_analysis),
                      ('Open analysis folder', lambda: subprocess.Popen(['explorer.exe', str(OUT)]) if sys.platform == 'win32' else None)]:
        ttk.Button(commandbar, text=title, command=fn).pack(side='left', padx=5)
    label(solar_tab, 'A clear Sun-centre sample does not establish landing safety. Finite DEM coverage, NoData and lunar coordinate conventions remain limitations.').pack(anchor='w', padx=15, pady=9)

    # Data health: populated on demand AND initially; list regions even if not installed.
    label(health_tab, 'NASA DATA HEALTH / ALL 27 CATALOGUE REGIONS', font=('Segoe UI', 14, 'bold')).pack(anchor='w', padx=14, pady=12)
    label(health_tab, 'A missing GeoTIFF, corrupt file, grid mismatch and NoData pixel are different conditions.').pack(anchor='w', padx=14)
    health_cols = ('region', 'status', 'missing', 'invalid', 'sample_nodata', 'details')
    health = ttk.Treeview(health_tab, columns=health_cols, show='headings', height=19)
    for k, width in zip(health_cols, (95, 180, 70, 70, 115, 600)):
        health.heading(k, text=k.replace('_', ' ').title())
        health.column(k, width=width, anchor='w' if k == 'details' else 'center')
    health.pack(fill='both', expand=True, padx=13, pady=6)
    audit_status = tk.StringVar(value='Health audit pending.')
    tk.Label(health_tab, textvariable=audit_status, bg=BG, fg=ACCENT).pack(anchor='w', padx=14, pady=5)
    audit_controls = ttk.Frame(health_tab)
    audit_controls.pack(fill='x', padx=14, pady=7)
    audit_results = []
    audit_queue = list(REGIONS)
    def step_audit():
        if not audit_queue:
            ready = sum(1 for row in audit_results if row['status'] == 'ready')
            audit_status.set(f'Audit complete. {ready} of {len(REGIONS)} regions ready. Missing files shown separately from NoData.')
            return
        reg = audit_queue.pop(0)
        try:
            report = classify_region(RAW, reg, region_files(RAW, reg))
            layers = report['layers']
            missing = [k for k, v in layers.items() if v['status'] == 'missing_file']
            invalid = [k for k, v in layers.items() if v['status'] in ('invalid_file', 'grid_mismatch')]
            nodata = [k for k, v in layers.items() if v['status'] == 'sample_only_nodata']
            reasons = []
            if missing: reasons.append('Missing: ' + ', '.join(missing))
            if invalid: reasons.append('Invalid: ' + ', '.join(invalid))
            if nodata: reasons.append('NoData sample: ' + ', '.join(nodata))
            if not reasons: reasons.append('5 files readable and aligned; sample shows usable pixels')
            row = {'region': reg, 'status': report['status'], 'missing': len(missing), 'invalid': len(invalid),
                   'sample_nodata': len(nodata), 'details': '; '.join(reasons)}
        except Exception as exc:
            row = {'region': reg, 'status': 'audit_error', 'missing': '?', 'invalid': '?',
                   'sample_nodata': '?', 'details': str(exc)[:240]}
        audit_results.append(row)
        health.insert('', 'end', values=[row[k] for k in health_cols])
        audit_status.set(f'Auditing regions: {len(audit_results)}/{len(REGIONS)}')
        app.after(5, step_audit)

    def audit_again():
        audit_results.clear()
        audit_queue[:] = list(REGIONS)
        health.delete(*health.get_children())
        app.after(5, step_audit)

    def audit_export():
        if not audit_results:
            messagebox.showinfo('Run audit', 'No audit results available yet.')
            return
        OUT.mkdir(parents=True, exist_ok=True)
        p = OUT / 'data_health.csv'
        with p.open('w', newline='', encoding='utf-8') as h:
            writer = csv.DictWriter(h, fieldnames=health_cols)
            writer.writeheader(); writer.writerows(audit_results)
        status.set(f'Data health exported: {p}')

    def start_downloader():
        script = ROOT / 'scripts/download_all_pgda_regions.py'
        if not script.is_file():
            messagebox.showerror('Missing downloader', 'download_all_pgda_regions.py is not installed.')
            return
        if not messagebox.askyesno('NASA downloads', 'Download missing NASA PGDA rasters for all catalogue regions? This may need several gigabytes. Existing valid rasters will be skipped.'):
            return
        cmd = [sys.executable, '-u', str(script), '--all']
        try:
            if sys.platform == 'win32':
                subprocess.Popen(['cmd.exe', '/k', subprocess.list2cmdline(cmd)], cwd=ROOT,
                                 creationflags=getattr(subprocess, 'CREATE_NEW_CONSOLE', 0))
            else:
                subprocess.Popen(cmd, cwd=ROOT)
            audit_status.set('Downloader launched in its own terminal. Click Refresh data health after it finishes.')
        except OSError as exc:
            messagebox.showerror('Downloader failed to start', str(exc))

    for text, fn in [('Refresh data health', audit_again), ('Export audit CSV', audit_export),
                     ('Retry missing downloads (corrected URLs)', start_downloader), ('Refresh available regions', scan_map)]:
        ttk.Button(audit_controls, text=text, command=fn).pack(side='left', padx=5)

    def close():
        close_rasters()
        app.destroy()
    app.protocol('WM_DELETE_WINDOW', close)
    load_saved()
    scan_map()
    refresh_rows()
    app.after(200, step_audit)
    app.mainloop()

if __name__ == '__main__':
    main()
