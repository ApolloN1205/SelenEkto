"""SELENEKTO 2.0 — PySide6 map-first desktop shell.

New launcher; does not modify the original desktop viewers.
Requires PySide6, matplotlib, rasterio and numpy in the active venv.
"""
from __future__ import annotations
import csv
import json
import subprocess
import sys
import traceback
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from selenekto_v2.core import (SUFFIXES, METRICS,region_names,region_health,raster_overview,
    read_cell,validate_name,load_candidates,save_candidates,comparable)

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QFrame,QLabel,QVBoxLayout,QHBoxLayout,
 QComboBox,QPushButton,QListWidget,QListWidgetItem,QStackedWidget,QTableWidget,QTableWidgetItem,
 QSplitter,QInputDialog,QMessageBox,QAbstractItemView,QLineEdit,QTextEdit,QHeaderView,
 QSpinBox,QDateEdit,QFormLayout,QGroupBox,QScrollArea,QDialog)
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as Canvas
import numpy as np
from selenekto_v2.region_data import load_profiles, METRIC_COLUMNS, metric_value

BG='#080A0D';PANEL='#141820';BORDER='#303846';FG='#EEF1F5';MUTED='#A6B0C0';ACCENT='#E77F71'
STYLE=f"""
QMainWindow,QWidget {{ background:{BG};color:{FG};font-family:'Segoe UI';font-size:12px; }}
QFrame#sidebar,QGroupBox,QTableWidget,QListWidget,QTextEdit {{background:{PANEL};border:1px solid {BORDER};border-radius:7px;}}
QPushButton {{background:#252B35;border:1px solid #3D4858;border-radius:5px;padding:9px;color:{FG};}}
QPushButton:hover {{background:#343D4C;}} QPushButton:disabled {{color:#77808C;}}
QComboBox,QLineEdit,QSpinBox,QDateEdit {{background:#10151C;color:{FG};selection-background-color:#4C5A6E;border:1px solid #5E6C7E;border-radius:4px;padding:7px;}}
QComboBox QAbstractItemView {{background:#111820;color:{FG};selection-background-color:#354255;selection-color:white;border:1px solid #5E6C7E;outline:none;}}
QTableWidget {{gridline-color:#343B49;selection-background-color:#39475C;selection-color:white;alternate-background-color:#19202A;}}
QHeaderView::section {{background:#262E3B;color:{FG};padding:7px;border:1px solid #3B4757;}}
QListWidget::item {{padding:11px;border-radius:5px;}} QListWidget::item:selected {{background:#354255;color:#FFFFFF;}}
QGroupBox {{margin-top:12px;padding:12px;}} QGroupBox::title {{subcontrol-origin:margin;left:10px;padding:0 5px;}}
QScrollBar:vertical {{background:#131922;width:11px;}} QScrollBar::handle:vertical {{background:#465367;border-radius:5px;}}
"""

def label(t,small=False):
    x=QLabel(t);x.setWordWrap(True)
    if small:x.setStyleSheet(f'color:{MUTED};font-size:11px;')
    return x

def btn(text,action):
    b=QPushButton(text);b.clicked.connect(action);return b

class Plot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fig=Figure(figsize=(7,5),dpi=100,facecolor=BG)
        self.ax=self.fig.add_subplot(111)
        self.ax.set_facecolor(BG)
        self.canvas=Canvas(self.fig)
        lay=QVBoxLayout(self);lay.setContentsMargins(0,0,0,0);lay.addWidget(self.canvas)
        self.setMinimumHeight(300)
    def reset(self,title):
        self.ax.clear();self.ax.set_facecolor(BG)
        self.ax.set_title(title,color=FG,fontsize=12,pad=12)
        self.ax.tick_params(colors=MUTED,labelsize=9)
        for spine in self.ax.spines.values():spine.set_color('#627080')
    def finish(self):
        self.fig.tight_layout();self.canvas.draw_idle()

class Main(QMainWindow):
    def __init__(self):
        super().__init__();self.setWindowTitle('SELENEKTO 2.0 / LUNAR NAVIGATOR')
        self.resize(1460,900)
        self.records=[];self.selected_cell=None;self.active_arr=None;self.active_dims=None
        self.layer='Elevation';self.region=None;self.map_img=None;self.marker=None
        try:self.records=load_candidates(ROOT)
        except Exception as exc:self.records=[];QTimer.singleShot(0,lambda e=str(exc):self.warn('Could not load candidate store',e))
        outer=QWidget();self.setCentralWidget(outer);layout=QHBoxLayout(outer)
        sidebar=QFrame();sidebar.setObjectName('sidebar');sidebar.setFixedWidth(206)
        side=QVBoxLayout(sidebar)
        mast=label('S E L E N E K T O');mast.setStyleSheet(f'font-size:17px;font-weight:bold;color:{FG};')
        side.addWidget(mast);side.addWidget(label('LUNAR LANDING-SITE NAVIGATOR',True))
        self.nav=QListWidget();self.nav.setSpacing(3)
        for item in ['Explorer','Illumination','Compare','Data Health','Settings']:
            self.nav.addItem(item)
        side.addWidget(self.nav);side.addStretch()
        side.addWidget(label('Experimental terrain & illumination models. Not a landing safety determination.',True))
        self.pages=QStackedWidget();layout.addWidget(sidebar);layout.addWidget(self.pages,1)
        self.pages.addWidget(self.make_explorer())
        self.pages.addWidget(self.make_illumination())
        self.pages.addWidget(self.make_compare())
        self.pages.addWidget(self.make_health())
        self.pages.addWidget(self.make_settings())
        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.nav.setCurrentRow(0)
        self.statusBar().showMessage('Ready. Select an installed region, then click the terrain.',10000)
        self.refresh_regions();self.refresh_candidates();self.refresh_health()

    def warn(self,heading,message):
        QMessageBox.warning(self,heading,str(message))
        self.statusBar().showMessage(f'{heading}: {message}',12000)

    def make_explorer(self):
        w=QWidget();l=QVBoxLayout(w)
        l.addWidget(label('EXPLORER  /  NASA PGDA TERRAIN'))
        bar=QHBoxLayout();l.addLayout(bar)
        bar.addWidget(label('Region'))
        self.region_box=QComboBox();bar.addWidget(self.region_box,2)
        bar.addWidget(label('Layer'))
        self.layer_box=QComboBox();self.layer_box.addItems(SUFFIXES);bar.addWidget(self.layer_box,2)
        bar.addWidget(btn('Refresh datasets',self.refresh_regions))
        self.region_box.currentIndexChanged.connect(self.change_map)
        self.layer_box.currentIndexChanged.connect(self.change_map)
        self.cell_info=label('Click a valid terrain pixel to inspect its data.',True);l.addWidget(self.cell_info)
        actions=QHBoxLayout();l.addLayout(actions)
        actions.addWidget(btn('Add named candidate',self.add_candidate))
        actions.addWidget(btn('Rename selected candidate',self.rename_candidate))
        actions.addWidget(btn('Remove selected',self.remove_candidate))
        actions.addWidget(btn('Save candidates',self.persist))
        split=QSplitter(Qt.Orientation.Vertical);l.addWidget(split,1)
        self.mapplot=Plot();split.addWidget(self.mapplot)
        self.mapplot.canvas.mpl_connect('button_press_event',self.on_map_click)
        self.candidate_table=QTableWidget();self.configure_candidates_table(self.candidate_table)
        split.addWidget(self.candidate_table);split.setSizes([630,200])
        return w

    def configure_candidates_table(self,table):
        table.setColumnCount(7);table.setHorizontalHeaderLabels(['Name','Region','Row','Col','Elevation (m)','Slope (°)','LOLA spots'])
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setAlternatingRowColors(True)

    def refresh_regions(self):
        old=self.region_box.currentText() if hasattr(self,'region_box') else ''
        options=[]
        for region in region_names(ROOT):
            try:
                if region_health(ROOT,region)['status']=='ready':options.append(region)
            except Exception:pass
        self.region_box.blockSignals(True);self.region_box.clear();self.region_box.addItems(options)
        if old in options:self.region_box.setCurrentText(old)
        self.region_box.blockSignals(False)
        if options:self.change_map()
        else:self.cell_info.setText('No complete aligned NASA regions found. See Data Health for missing layers.')

    def change_map(self,*_):
        region=self.region_box.currentText();layer=self.layer_box.currentText()
        if not region or not layer:return
        self.selected_cell=None
        try:
            arr,dims=raster_overview(ROOT,region,layer)
            self.active_arr,self.active_dims=arr,dims;self.region,self.layer=region,layer
            self.mapplot.reset(f'{region}  /  {layer}')
            valid=arr[np.isfinite(arr)]
            if valid.size:
                lo,hi=np.percentile(valid,[2,98])
                if hi<=lo:hi=lo+1
                self.map_img=self.mapplot.ax.imshow(arr,cmap='gray',origin='upper',vmin=lo,vmax=hi,interpolation='nearest')
            else:
                self.map_img=self.mapplot.ax.imshow(arr,cmap='gray',origin='upper',interpolation='nearest')
            self.mapplot.ax.set_xlabel('Overview column',color=MUTED)
            self.mapplot.ax.set_ylabel('Overview row',color=MUTED)
            self.draw_saved_markers()
            self.mapplot.finish()
            self.cell_info.setText(f'{region} / {layer}. Overview is downsampled for navigation; click reads full-resolution NASA cells.')
        except Exception as exc:self.warn('Could not load terrain',exc)

    def draw_saved_markers(self):
        if self.active_dims is None or self.active_arr is None:return
        height,width=self.active_dims;oh,ow=self.active_arr.shape
        cells=[r for r in self.records if r['region']==self.region]
        for r in cells:
            xx=(r['col']+.5)*ow/width-.5;yy=(r['row']+.5)*oh/height-.5
            self.mapplot.ax.plot(xx,yy,'o',markerfacecolor='none',markeredgecolor=ACCENT,ms=8,mew=1.5)
        if self.selected_cell:
            r=self.selected_cell
            xx=(r['col']+.5)*ow/width-.5;yy=(r['row']+.5)*oh/height-.5
            self.mapplot.ax.plot(xx,yy,'+',color='#F5A36C',ms=17,mew=2)

    def on_map_click(self,event):
        if event.inaxes is not self.mapplot.ax or event.xdata is None or self.active_dims is None:return
        height,width=self.active_dims;oh,ow=self.active_arr.shape
        col=min(width-1,max(0,int((event.xdata+.5)*width/ow)))
        row=min(height-1,max(0,int((event.ydata+.5)*height/oh)))
        try:
            cell=read_cell(ROOT,self.region,row,col)
            self.selected_cell=cell
            txt=f'{self.region} · row {row}, col {col}  |  ' + '  ·  '.join(f'{key}: {cell.get(key):.3f}' if cell.get(key) is not None else f'{key}: NoData' for key in ['elevation_m','slope_deg','elevation_rms_m','lola_spot_count'])
            self.cell_info.setText(txt)
            self.change_map_preserve_selection()
        except Exception as exc:self.warn('Cell inspection failed',exc)

    def change_map_preserve_selection(self):
        try:
            self.mapplot.reset(f'{self.region}  /  {self.layer}')
            arr=self.active_arr;v=arr[np.isfinite(arr)]
            if len(v):lo,hi=np.percentile(v,[2,98]);hi=max(hi,lo+1e-9);self.mapplot.ax.imshow(arr,cmap='gray',vmin=lo,vmax=hi,interpolation='nearest')
            else:self.mapplot.ax.imshow(arr,cmap='gray')
            self.draw_saved_markers();self.mapplot.finish()
        except Exception as exc:self.warn('Map redraw failed',exc)

    def persist(self):
        try:path=save_candidates(ROOT,self.records);self.statusBar().showMessage(f'Saved {len(self.records)} named candidates: {path}',10000)
        except Exception as exc:self.warn('Candidate save failed',exc)

    def add_candidate(self):
        if not self.selected_cell:self.warn('Select a location','Click on the lunar terrain image first.');return
        if self.selected_cell.get('elevation_m') is None:self.warn('NoData','This pixel has no valid elevation. Choose another cell.');return
        proposed=f'{self.region} candidate {len(self.records)+1:02d}'
        name,ok=QInputDialog.getText(self,'Name lunar candidate','Candidate name:',QLineEdit.EchoMode.Normal,proposed)
        if not ok:return
        try:
            new={**self.selected_cell,'name':validate_name(name)}
            if any((r['region'],r['row'],r['col'])==(new['region'],new['row'],new['col']) for r in self.records):
                raise ValueError('This exact cell is already saved; rename it instead')
            self.records.append(new);self.persist();self.refresh_candidates();self.change_map_preserve_selection()
        except Exception as exc:self.warn('Could not add candidate',exc)

    def selected_record_indices(self,table):
        return sorted(set(idx.row() for idx in table.selectionModel().selectedRows()))

    def rename_candidate(self):
        idx=self.selected_record_indices(self.candidate_table)
        if len(idx)!=1:self.warn('Select one candidate','Select exactly one row to rename.');return
        rec=self.records[idx[0]];name,ok=QInputDialog.getText(self,'Rename candidate','New name:',text=rec['name'])
        if ok:
            try:rec['name']=validate_name(name);self.persist();self.refresh_candidates()
            except Exception as exc:self.warn('Cannot rename candidate',exc)

    def remove_candidate(self):
        idx=self.selected_record_indices(self.candidate_table)
        if not idx:return
        for i in reversed(idx):del self.records[i]
        self.persist();self.refresh_candidates();self.change_map_preserve_selection()

    def refresh_candidates(self):
        if not hasattr(self,'candidate_table'):return
        def fill(table):
            table.setRowCount(len(self.records))
            for i,r in enumerate(self.records):
                for j,key in enumerate(['name','region','row','col','elevation_m','slope_deg','lola_spot_count']):
                    v=r.get(key);table.setItem(i,j,QTableWidgetItem('NoData' if v is None else f'{v:.3f}' if isinstance(v,float) else str(v)))
        fill(self.candidate_table)
        if hasattr(self,'compare_table'):fill(self.compare_table)
        if hasattr(self,'left_box'):
            for box in (self.left_box,self.right_box):
                selected=box.currentIndex();box.clear()
                for r in self.records:box.addItem(f"{r['name']} ({r['region']})")
                if self.records:box.setCurrentIndex(min(selected,len(self.records)-1))

    def make_compare(self):
        w=QWidget();l=QVBoxLayout(w)
        l.addWidget(label('COMPARE  /  SELECT THE CANDIDATES YOU WANT'))
        l.addWidget(label('Ctrl+click multiple rows. Metrics are observations, not suitability ratings.',True))
        self.compare_table=QTableWidget();self.configure_candidates_table(self.compare_table);self.compare_table.setMaximumHeight(230)
        l.addWidget(self.compare_table)
        top=QHBoxLayout();l.addLayout(top)
        top.addWidget(btn('Compare chosen candidate data',self.compare_metrics))
        top.addWidget(label('Side-by-side imagery:',True));self.left_box=QComboBox();self.right_box=QComboBox();top.addWidget(self.left_box);top.addWidget(self.right_box)
        self.comp_layer=QComboBox();self.comp_layer.addItems(SUFFIXES);top.addWidget(self.comp_layer)
        top.addWidget(btn('Show image comparison',self.compare_images))
        detail=QHBoxLayout();l.addLayout(detail)
        detail.addWidget(label('Candidate measurement:'))
        self.candidate_metric=QComboBox()
        self.candidate_metric.addItems(['Slope (degrees)','Elevation (metres)','Elevation RMS (metres)','Slope RMS (degrees)','LOLA spots per pixel'])
        detail.addWidget(self.candidate_metric)
        detail.addWidget(btn('Compare ALL region JSON statistics',self.show_region_comparison))
        self.compare_status=label('Select two or more named candidates above. Region averages are available separately.',True);l.addWidget(self.compare_status)
        self.compare_plot=Plot();l.addWidget(self.compare_plot,1)
        return w

    def compare_metrics(self):
        indices=self.selected_record_indices(self.compare_table)
        try:
            records=comparable(self.records,indices)
            mapping={
                'Slope (degrees)':('slope_deg','degrees'),
                'Elevation (metres)':('elevation_m','metres'),
                'Elevation RMS (metres)':('elevation_rms_m','RMS metres'),
                'Slope RMS (degrees)':('slope_rms_deg','RMS degrees'),
                'LOLA spots per pixel':('lola_spot_count','spots/pixel'),
            }
            field, unit=mapping[self.candidate_metric.currentText()]
            values=[r.get(field) if r.get(field) is not None else np.nan for r in records]
            if not any(np.isfinite(v) for v in values):
                self.warn('No candidate measurements','All selected candidates have NoData for this layer.');return
            self.compare_plot.fig.clear()
            ax=self.compare_plot.fig.add_subplot(111);ax.set_facecolor(BG)
            names=[f"{r['name']} ({r['region']})" for r in records]
            bars=ax.bar(range(len(records)),values,color='#BFC9D6',width=.65)
            ax.set_xticks(range(len(records)),names,rotation=15,ha='right',fontsize=9)
            ax.set_ylabel(unit,color=MUTED)
            ax.set_title('Candidate pixel / '+self.candidate_metric.currentText(),color=FG)
            ax.tick_params(colors=MUTED)
            for spine in ax.spines.values():spine.set_color(BORDER)
            for bar,value in zip(bars,values):
                if np.isfinite(value):
                    ax.annotate(f'{value:.3f}',(bar.get_x()+bar.get_width()/2,bar.get_height()),
                                textcoords='offset points',xytext=(0,4),ha='center',color=FG,fontsize=9)
            self.compare_plot.fig.tight_layout();self.compare_plot.canvas.draw_idle()
            self.compare_status.setText(f'{len(records)} named cells compared using full-resolution per-pixel {unit}. NoData omitted.')
        except Exception as exc:self.warn('Comparison unavailable',exc)

    def show_region_comparison(self):
        try:
            profiles=load_profiles(ROOT/'data/catalog/region_profiles')
            if not profiles:
                self.warn('No region JSON profiles','First run scripts/build_all_region_json.py and scripts/prepare_region_data.py.');return
            dialog=QDialog(self)
            dialog.setWindowTitle('SELENEKTO / REGION DATA COMPARISON')
            dialog.resize(1180,760)
            layout=QVBoxLayout(dialog)
            layout.addWidget(label('REGION-WIDE NASA TERRAIN STATISTICS (NOT individual landing-candidate readings)'))
            controls=QHBoxLayout();layout.addLayout(controls)
            controls.addWidget(label('Plot region metric:'))
            metric_box=QComboBox();metric_box.addItems(METRIC_COLUMNS.keys());controls.addWidget(metric_box,2)
            controls.addWidget(label('Ctrl+click rows to choose regions for graph.',True),3)
            table=QTableWidget();table.setColumnCount(3+len(METRIC_COLUMNS))
            table.setHorizontalHeaderLabels(['Region','Name','Status']+list(METRIC_COLUMNS))
            table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
            table.setAlternatingRowColors(True)
            table.setRowCount(len(profiles))
            for i,p in enumerate(profiles):
                row=[p.get('site_code','?'),p.get('region_name',''),p.get('availability','unknown')]
                row.extend(metric_value(p,m) for m in METRIC_COLUMNS)
                for j,value in enumerate(row):
                    item=QTableWidgetItem('NoData' if value is None else f'{value:.3f}' if isinstance(value,(int,float)) else str(value))
                    item.setData(Qt.ItemDataRole.UserRole, i)
                    table.setItem(i,j,item)
            table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            table.setSortingEnabled(True)
            layout.addWidget(table,2)
            chart=Plot();layout.addWidget(chart,3)
            def plot_rows():
                selected=sorted({table.item(i.row(),0).data(Qt.ItemDataRole.UserRole)
                                 for i in table.selectionModel().selectedRows()})
                if not selected:selected=list(range(len(profiles)))
                m=metric_box.currentText()
                selected=[i for i in selected if metric_value(profiles[i],m) is not None]
                chart.fig.clear();ax=chart.fig.add_subplot(111);ax.set_facecolor(BG)
                if selected:
                    values=[metric_value(profiles[i],m) for i in selected]
                    names=[profiles[i].get('site_code','?') for i in selected]
                    ax.bar(range(len(selected)),values,color='#BFC9D6',width=.7)
                    ax.set_xticks(range(len(selected)),names,rotation=45,ha='right',fontsize=8)
                else:
                    ax.text(.5,.5,'No valid region data for this metric',ha='center',va='center',color=FG,transform=ax.transAxes)
                ax.set_title(m+' / region-wide summary',color=FG)
                ax.tick_params(colors=MUTED)
                for spine in ax.spines.values():spine.set_color(BORDER)
                chart.fig.tight_layout();chart.canvas.draw_idle()
            metric_box.currentIndexChanged.connect(plot_rows)
            table.itemSelectionChanged.connect(plot_rows)
            plot_rows()
            layout.addWidget(label('Mean/min/max are full-raster statistics; medians are approximate spatial samples. Missing data is not zero.',True))
            dialog.exec()
        except Exception as exc:self.warn('Region data comparison unavailable',exc)

    def compare_images(self):
        if len(self.records)<2:self.warn('Add candidates','Save two or more candidates to compare local images.');return
        left,right=self.left_box.currentIndex(),self.right_box.currentIndex()
        if left==right:self.warn('Choose different locations','Select two different candidates.');return
        layer=self.comp_layer.currentText()
        self.compare_plot.fig.clear()
        try:
            for j,r in enumerate((self.records[left],self.records[right])):
                import rasterio
                from rasterio.windows import Window
                from rasterio.enums import Resampling
                from selenekto_v2.core import region_files
                with rasterio.open(region_files(ROOT,r['region'])[layer]) as ds:
                    radius=120
                    x0=max(0,int(r['col'])-radius);y0=max(0,int(r['row'])-radius)
                    ww=min(2*radius+1,ds.width-x0);hh=min(2*radius+1,ds.height-y0)
                    win=Window(x0,y0,ww,hh)
                    arr=ds.read(1,window=win,masked=True,resampling=Resampling.nearest)
                    values=np.asarray(arr.data,dtype=float)
                    values[np.ma.getmaskarray(arr)|~np.isfinite(values)]=np.nan
                ax=self.compare_plot.fig.add_subplot(1,2,j+1)
                ax.set_facecolor(BG)
                v=values[np.isfinite(values)]
                if len(v):lo,hi=np.percentile(v,[2,98]);ax.imshow(values,cmap='gray',vmin=lo,vmax=max(hi,lo+1e-9))
                else:ax.imshow(values,cmap='gray')
                ax.plot(r['col']-x0,r['row']-y0,'+',color=ACCENT,ms=13,mew=2)
                ax.set_title(f"{r['name']} / {r['region']}",color=FG,fontsize=11)
                ax.tick_params(colors=MUTED)
            self.compare_plot.fig.tight_layout();self.compare_plot.canvas.draw_idle()
            self.compare_status.setText(f'Same 5 m/pixel spatial scale; separate local cutouts from the {layer} layers.')
        except Exception as exc:self.compare_plot.reset('Comparison could not load');self.compare_plot.finish();self.warn('Image comparison failed',exc)

    def make_illumination(self):
        w=QWidget();l=QVBoxLayout(w)
        l.addWidget(label('ILLUMINATION  /  TERRAIN HORIZON & SUN POSITIONS'))
        l.addWidget(label('Use existing verified Site01 solar viewer. Multi-region solar modelling requires independent horizons and reference-frame checks.',True))
        actions=QHBoxLayout();l.addLayout(actions)
        actions.addWidget(btn('Open working solar + horizon viewer',self.open_solar))
        actions.addWidget(btn('Show reference horizon graph',self.show_horizon))
        actions.addWidget(btn('Open candidate solar results folder',self.open_solar_results))
        self.solar_status=label('The original Site01 solar viewer remains available without modification.',True);l.addWidget(self.solar_status)
        self.solarplot=Plot();l.addWidget(self.solarplot,1)
        self.solarplot.reset('Load Site01 horizon results to view the 360° terrain profile');self.solarplot.finish()
        return w

    def open_solar(self):
        script=ROOT/'scripts/launch_selenekto.py'
        if not script.exists():self.warn('Missing solar viewer',f'Not found: {script}');return
        try:subprocess.Popen([sys.executable,str(script)],cwd=ROOT)
        except Exception as exc:self.warn('Solar viewer could not start',exc)

    def open_solar_results(self):
        path=ROOT/'data/processed/candidate_solar'
        if path.exists():
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        else:self.warn('No results yet','Run candidate solar calculations in the existing viewer first.')

    def show_horizon(self):
        path=ROOT/'data/processed/horizon/Site01/Site01_horizon_5km.json'
        try:
            d=json.loads(path.read_text(encoding='utf-8'))
            angles=d['angles'];az=[x['grid_azimuth_deg'] for x in angles];e=[x['horizon_angle_deg'] for x in angles]
            self.solarplot.reset('Site01 terrain horizon / grid-relative azimuth')
            self.solarplot.ax.plot(az,e,color=FG,lw=1.4)
            self.solarplot.ax.set_xlabel('Azimuth relative to projected grid +Y (°)',color=MUTED)
            self.solarplot.ax.set_ylabel('Horizon angle (°)',color=MUTED)
            self.solarplot.finish()
            self.solar_status.setText('Local DEM-limited reference horizon; not an illumination timeline or landing-safety assessment.')
        except Exception as exc:self.warn('Horizon result unavailable',exc)

    def make_health(self):
        w=QWidget();l=QVBoxLayout(w);l.addWidget(label('DATA HEALTH / INSTALLED NASA REGIONS'))
        line=QHBoxLayout();l.addLayout(line)
        line.addWidget(btn('Refresh data health',self.refresh_health))
        line.addWidget(btn('Open JSON region profiles',self.open_profiles))
        self.health_summary=label('',True);line.addWidget(self.health_summary)
        self.health_table=QTableWidget();self.health_table.setColumnCount(3)
        self.health_table.setHorizontalHeaderLabels(['Region','Status','Details'])
        self.health_table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch)
        self.health_table.setColumnWidth(0,120);self.health_table.setColumnWidth(1,140)
        l.addWidget(self.health_table,1)
        l.addWidget(label('Ready = readable and geometrically aligned. It does not mean all pixels contain valid data.',True))
        return w

    def refresh_health(self):
        if not hasattr(self,'health_table'):return
        names=region_names(ROOT);self.health_table.setRowCount(len(names));counts={}
        for i,r in enumerate(names):
            result=region_health(ROOT,r);counts[result['status']]=counts.get(result['status'],0)+1
            for j,k in enumerate(('region','status','details')):
                self.health_table.setItem(i,j,QTableWidgetItem(str(result[k])))
        self.health_summary.setText(' · '.join(f'{v} {k}' for k,v in sorted(counts.items())) or 'No regions discovered')

    def open_profiles(self):
        folder=ROOT/'data/catalog/region_profiles'
        if not folder.exists():self.warn('No region profiles','Run scripts/build_all_region_json.py first.');return
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def make_settings(self):
        w=QWidget();l=QVBoxLayout(w)
        l.addWidget(label('SETTINGS  /  SCIENTIFIC TRANSPARENCY'))
        content=QTextEdit();content.setReadOnly(True)
        content.setPlainText('SELENEKTO 2.0\n\n'
           'Data source: NASA/GSFC PGDA LOLA 5m/pixel GeoTIFFs.\n'
           'The original TIFFs remain authoritative; JSON region profiles contain summary statistics.\n'
           'Map overviews are downsampled; clicked cell values come from full-resolution TIFFs.\n'
           'Candidate names and measurements are saved to data/catalog/named_candidates.json.\n'
           'Terrain horizon calculations are local DEM-limited estimates.\n'
           'RMS elevation perturbation scenarios are not confidence intervals.\n'
           'Solar timelines require NASA JPL ephemeris availability and validated lunar geometry.\n'
           'Scores or imagery cannot establish actual landing safety.\n\n'
           'This first PySide6 UI provides a reliable explorer and comparison shell.\n'
           'The existing solar viewer is launched separately rather than claiming a new independent multi-region solar backend.\n')
        l.addWidget(content,1)
        l.addWidget(label('Project folder: '+str(ROOT),True));return w


def main():
    app=QApplication(sys.argv);app.setStyle('Fusion');app.setStyleSheet(STYLE)
    window=Main();window.show();return app.exec()

if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception:
        log=ROOT/'data/processed/logs/selenekto_v2_crash.log';log.parent.mkdir(parents=True,exist_ok=True)
        log.write_text(traceback.format_exc(),encoding='utf-8')
        print('SelenEkto v2 failed; see',log,file=sys.stderr)
        traceback.print_exc();raise
