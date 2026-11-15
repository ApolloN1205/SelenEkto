"""SelenEkto 2.0 — PySide6 map-first desktop shell.

New launcher; does not modify the original desktop viewers.
Requires PySide6, matplotlib, rasterio and numpy in the active venv.
"""
from __future__ import annotations
import csv
import json
import subprocess
import sys
import traceback
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from selenekto_v2.core import (SUFFIXES, METRICS,region_names,region_health,raster_overview,
    read_cell,validate_name,load_candidates,save_candidates,comparable)

from selenekto_v2.library_view import LibraryPage
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QDateTime
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QFrame,QLabel,QVBoxLayout,QHBoxLayout,
 QComboBox,QPushButton,QListWidget,QListWidgetItem,QStackedWidget,QTableWidget,QTableWidgetItem,
 QSplitter,QInputDialog,QMessageBox,QAbstractItemView,QLineEdit,QTextEdit,QHeaderView,
 QSpinBox,QDateEdit,QDateTimeEdit,QFormLayout,QGroupBox,QScrollArea,QDialog,QCheckBox)
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as Canvas
import numpy as np
from selenekto_v2.recommendations import CRITERIA, DEFAULT_WEIGHTS, evaluate
from selenekto_v2.actual_regions import refresh_saved_candidates
from selenekto_v2.neon_solar import parse_saved_result
from selenekto_v2.region_data import load_profiles, METRIC_COLUMNS, metric_value
from selenekto_v2.illumination_controls import calculate_candidate_timeline, calculate_candidate_horizon, explain_error
from selenekto_v2.settings_store import (DEFAULTS, THEMES, ACCENTS, load_settings, save_settings, theme_stylesheet)

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

class SolarWorker(QThread):
    success=Signal(object,object)
    failure=Signal(str)
    def __init__(self, root, record, start, hours, interval):
        super().__init__()
        self.root=root;self.record=dict(record);self.start_utc=start;self.hours=hours;self.interval=interval
    def run(self):
        try:
            result,path=calculate_candidate_timeline(self.root,self.record,self.start_utc,self.hours,self.interval)
            self.success.emit(result,str(path))
        except Exception as exc:
            log=self.root/'data/processed/logs/last_candidate_solar_error.log'
            log.parent.mkdir(parents=True,exist_ok=True)
            log.write_text(traceback.format_exc(),encoding='utf-8')
            self.failure.emit(explain_error(exc)+f"\n\nFull error log: {log}")

class HorizonWorker(QThread):
    success=Signal(object,object)
    failure=Signal(str)
    def __init__(self,root,record):
        super().__init__()
        self.root=root;self.record=dict(record)
    def run(self):
        try:
            result,path=calculate_candidate_horizon(self.root,self.record)
            self.success.emit(result,str(path))
        except Exception as exc:
            log=self.root/'data/processed/logs/last_candidate_horizon_error.log'
            log.parent.mkdir(parents=True,exist_ok=True)
            log.write_text(traceback.format_exc(),encoding='utf-8')
            self.failure.emit(explain_error(exc)+f"\n\nFull error log: {log}")

class Main(QMainWindow):
    def __init__(self):
        super().__init__();self.setWindowTitle('SelenEkto · Lunar Navigator')
        self.logo_path=ROOT/'assets/branding/logo.png'
        if self.logo_path.is_file():
            icon=QIcon(str(self.logo_path))
            if not icon.isNull():
                self.setWindowIcon(icon)
                QApplication.instance().setWindowIcon(icon)
        self.resize(1460,900)
        self.records=[];self.selected_cell=None;self.active_arr=None;self.active_dims=None
        self.preferences=load_settings(ROOT)
        self.layer='Slope';self.region=None;self.map_img=None;self.marker=None;self.solar_worker=None;self.horizon_worker=None
        try:self.records=load_candidates(ROOT)
        except Exception as exc:self.records=[];QTimer.singleShot(0,lambda e=str(exc):self.warn('Could not load candidate store',e))
        outer=QWidget();self.setCentralWidget(outer);layout=QHBoxLayout(outer)
        sidebar=QFrame();sidebar.setObjectName('sidebar');sidebar.setFixedWidth(206)
        side=QVBoxLayout(sidebar)
        mast=label('SelenEkto');mast.setStyleSheet(f'font-size:19px;font-weight:bold;color:{FG};')
        side.addWidget(mast);side.addWidget(label('LUNAR LANDING-SITE NAVIGATOR',True))
        self.nav=QListWidget();self.nav.setSpacing(3)
        for item in ['Explorer','Illumination','Compare','Data Health','Settings']:
            self.nav.addItem(item)
        self.nav.addItem('Data Library')
        side.addWidget(self.nav);side.addStretch()
        side.addWidget(label('Experimental terrain & illumination models. Not a landing safety determination.',True))
        self.pages=QStackedWidget();layout.addWidget(sidebar);layout.addWidget(self.pages,1)
        self.pages.addWidget(self.make_explorer())
        self.pages.addWidget(self.make_illumination())
        self.pages.addWidget(self.make_compare())
        self.pages.addWidget(self.make_health())
        self.pages.addWidget(self.make_settings())
        self.library_page=LibraryPage(ROOT,on_updated=self._library_updated)
        self.pages.addWidget(self.library_page)
        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.nav.setCurrentRow(0)
        self.statusBar().showMessage('Ready. Select an installed region, then click the terrain.',10000)
        self.refresh_regions();self.refresh_candidates();self.refresh_health()
        self.apply_preferences()

    def warn(self,heading,message):
        QMessageBox.warning(self,heading,str(message))
        self.statusBar().showMessage(f'{heading}: {message}',12000)

    def make_explorer(self):
        w=QWidget();l=QVBoxLayout(w)
        l.addWidget(label('SelenEkto / Explorer / NASA PGDA terrain'))
        bar=QHBoxLayout();l.addLayout(bar)
        bar.addWidget(label('Region'))
        self.region_box=QComboBox();bar.addWidget(self.region_box,2)
        bar.addWidget(label('Layer'))
        self.layer_box=QComboBox();self.layer_box.addItems(SUFFIXES);bar.addWidget(self.layer_box,2)
        if self.preferences['default_layer'] in SUFFIXES:self.layer_box.setCurrentText(self.preferences['default_layer'])
        bar.addWidget(btn('Refresh datasets',self.refresh_regions))
        bar.addWidget(btn('Zoom in',lambda:self.zoom_map(0.65)))
        bar.addWidget(btn('Zoom out',lambda:self.zoom_map(1.5)))
        bar.addWidget(btn('Fit map',self.fit_map))
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
        self.mapplot.canvas.mpl_connect('scroll_event',self.on_map_scroll)
        l.addWidget(label('Mouse wheel over map to zoom · Zoom buttons above · Fit map resets the view.', True))
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

    def zoom_map(self,factor,anchor=None):
        if self.active_arr is None:return
        ax=self.mapplot.ax
        (left,right),(top,bottom)=ax.get_xlim(),ax.get_ylim()
        cx=(left+right)/2 if anchor is None else anchor[0]
        cy=(top+bottom)/2 if anchor is None else anchor[1]
        width=abs(right-left)*factor;height=abs(bottom-top)*factor
        width=max(3,min(width,self.active_arr.shape[1]*2))
        height=max(3,min(height,self.active_arr.shape[0]*2))
        ax.set_xlim(cx-width/2,cx+width/2)
        # Preserve inverted image row axis.
        ax.set_ylim(cy+height/2,cy-height/2)
        self.mapplot.canvas.draw_idle()

    def on_map_scroll(self,event):
        if event.inaxes is not self.mapplot.ax or event.xdata is None:return
        if event.button=='up':factor=.75
        elif event.button=='down':factor=1.33
        else:return
        self.zoom_map(factor,(event.xdata,event.ydata))

    def fit_map(self):
        if self.active_arr is None:return
        h,w=self.active_arr.shape
        self.mapplot.ax.set_xlim(-.5,w-.5)
        self.mapplot.ax.set_ylim(h-.5,-.5)
        self.mapplot.canvas.draw_idle()

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
            previous_xlim=self.mapplot.ax.get_xlim()
            previous_ylim=self.mapplot.ax.get_ylim()
            self.mapplot.reset(f'{self.region}  /  {self.layer}')
            arr=self.active_arr;v=arr[np.isfinite(arr)]
            if len(v):lo,hi=np.percentile(v,[2,98]);hi=max(hi,lo+1e-9);self.mapplot.ax.imshow(arr,cmap='gray',vmin=lo,vmax=hi,interpolation='nearest')
            else:self.mapplot.ax.imshow(arr,cmap='gray')
            self.draw_saved_markers()
            self.mapplot.ax.set_xlim(previous_xlim);self.mapplot.ax.set_ylim(previous_ylim)
            self.mapplot.finish()
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
        if self.preferences['confirm_candidate_removal']:
            reply=QMessageBox.question(self,'Remove named candidates',f'Remove {len(idx)} saved candidate(s)? This cannot be undone.',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:return
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
        if hasattr(self,'solar_candidate'):
            previous=self.solar_candidate.currentData()
            self.solar_candidate.blockSignals(True)
            self.solar_candidate.clear()
            for i,r in enumerate(self.records):
                self.solar_candidate.addItem(f"{r['name']}  ·  {r['region']} ({r['row']}, {r['col']})",i)
            if previous is not None:
                for i in range(self.solar_candidate.count()):
                    if self.solar_candidate.itemData(i)==previous:self.solar_candidate.setCurrentIndex(i);break
            self.solar_candidate.blockSignals(False)

    def make_compare(self):
        w=QWidget();l=QVBoxLayout(w)
        l.addWidget(label('SelenEkto / Compare selected sites'))
        l.addWidget(label('Ctrl+click multiple rows. Metrics are observations, not suitability ratings.',True))
        self.compare_table=QTableWidget();self.configure_candidates_table(self.compare_table);self.compare_table.setMaximumHeight(230)
        l.addWidget(self.compare_table)
        top=QHBoxLayout();l.addLayout(top)
        top.addWidget(btn('Compare chosen candidate data',self.compare_metrics))
        top.addWidget(btn('Adjust comparison priorities',self.open_preference_comparison))
        top.addWidget(btn('Refresh saved pixel data',self.refresh_candidate_data))
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

    def refresh_candidate_data(self):
        try:
            result=refresh_saved_candidates(ROOT)
            self.records=load_candidates(ROOT)
            self.refresh_candidates()
            self.compare_status.setText(f"Refreshed {result['updated']}/{result['count']} candidate cells from actual NASA GeoTIFFs. Unavailable: {result['unavailable']}.")
            if result['errors']:self.warn('Missing NASA data', '\n'.join(result['errors'][:8]))
        except Exception as exc:self.warn('Candidate data refresh failed',exc)

    def compare_metrics(self):
        indices=self.selected_record_indices(self.compare_table)
        if len(indices)<2:
            self.warn('Choose candidates', 'Select at least two rows in Compare. Hold Ctrl while clicking each row, then choose a metric.');return
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
                self.warn('Measurements unavailable',f'No selected candidate has a valid {self.candidate_metric.currentText()} reading. Open Data Health to check the five NASA layers for each region; then select Refresh saved pixel data in Compare. Region-wide averages cannot substitute for this specific pixel.');return
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
            missing=[r['name'] for r,v in zip(records,values) if not np.isfinite(v)]
            note=(' Missing NASA reading for: '+', '.join(missing)+'. Check Data Health and use Refresh saved pixel data.' if missing else ' All selected values available.')
            self.compare_status.setText(f'{len(records)} named cells compared using full-resolution per-pixel {unit}.'+note)
        except Exception as exc:self.warn('Comparison unavailable',explain_error(exc))

    def open_preference_comparison(self):
        """A relative, transparent comparison of selected named candidates."""
        indices = self.selected_record_indices(self.compare_table)
        if len(indices) < 2:
            self.warn('Choose candidates', 'Ctrl+click at least two named candidates in the Compare table first.')
            return
        records = [self.records[i] for i in indices]
        dialog = QDialog(self)
        dialog.setWindowTitle('SelenEkto / Adjustable comparison')
        dialog.resize(850, 610)
        layout = QVBoxLayout(dialog)
        layout.addWidget(label('Adjust relative priorities. This is NOT a landing safety or success score.'))
        controls = QFormLayout()
        widgets = {}
        for name in CRITERIA:
            spin = QSpinBox(); spin.setRange(0, 10); spin.setValue(DEFAULT_WEIGHTS[name])
            controls.addRow(name, spin); widgets[name] = spin
        layout.addLayout(controls)
        choose_winner = QCheckBox('Highlight highest preference score (optional; not a safety recommendation)')
        choose_winner.setChecked(False)
        layout.addWidget(choose_winner)
        feedback = label('', True); layout.addWidget(feedback)
        table = QTableWidget(); table.setColumnCount(4)
        table.setHorizontalHeaderLabels(['Candidate', 'Region', 'Relative index', 'Data status'])
        table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(table, 1)
        details = QTextEdit(); details.setReadOnly(True); details.setMaximumHeight(150)
        layout.addWidget(details)
        def update():
            try:
                weights = {name: widget.value() for name, widget in widgets.items()}
                result = evaluate(records, weights)
            except ValueError as exc:
                feedback.setText(str(exc)); table.setRowCount(0); details.clear(); return
            rows = result['rows']; table.setRowCount(len(rows))
            scored = [r for r in rows if r['score'] is not None]
            highest = max((r['score'] for r in scored), default=None)
            tied = sum(r['score'] == highest for r in scored) > 1 if highest is not None else False
            for i, r in enumerate(rows):
                score_text = 'No score' if r['score'] is None else f"{r['score']:.2f} / 100"
                status = 'Missing: ' + ', '.join(r['missing']) if r['missing'] else 'Complete for selected priorities'
                if choose_winner.isChecked() and highest is not None and r['score'] == highest and not tied:
                    status = 'Highest relative preference · ' + status
                for j, item in enumerate((r['name'], r['region'], score_text, status)):
                    table.setItem(i, j, QTableWidgetItem(item))
            feedback.setText(f"{len(scored)}/{len(rows)} candidates have all weighted measurements. "
                + ('No overall winner selected.' if not choose_winner.isChecked() else
                   'Tied highest scores; no unique leader.' if tied else 'Highest relative preference highlighted.'))
            detail_lines = [result['explanation'], '']
            for r in rows:
                detail_lines.append(f"{r['name']} ({r['region']}): " +
                    ('MISSING '+', '.join(r['missing']) if r['missing'] else
                     '; '.join(f"{name}: {v['reading']:g} {v['units']} (weight {v['weight']})"
                               for name, v in r['criteria'].items())))
            details.setPlainText('\n'.join(detail_lines))
        for spin in widgets.values(): spin.valueChanged.connect(update)
        choose_winner.toggled.connect(update)
        update()
        dialog.exec()

    def show_region_comparison(self):
        try:
            profiles=load_profiles(ROOT/'data/catalog/region_profiles')
            if not profiles:
                self.warn('No region JSON profiles','First run scripts/build_all_region_json.py and scripts/prepare_region_data.py.');return
            dialog=QDialog(self)
            dialog.setWindowTitle('SelenEkto / Region Data Comparison')
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
        except Exception as exc:self.compare_plot.reset('Comparison could not load');self.compare_plot.finish();self.warn('Image comparison failed',explain_error(exc))

    def make_illumination(self):
        w=QWidget();l=QVBoxLayout(w)
        l.addWidget(label('SelenEkto / Solar & Horizon'))
        l.addWidget(label('Select a named lunar candidate and UTC start time. The Sun line uses live JPL Horizons data for that candidate, NOT a reused Site01 solar timeline.',True))
        config=QHBoxLayout();l.addLayout(config)
        config.addWidget(label('Lunar candidate'))
        self.solar_candidate=QComboBox();self.solar_candidate.setMinimumWidth(230);config.addWidget(self.solar_candidate,3)
        config.addWidget(btn('Refresh sites',self.refresh_candidates))
        config.addWidget(label('Start (UTC)'))
        self.solar_date=QDateTimeEdit();self.solar_date.setDisplayFormat('yyyy-MM-dd HH:mm');self.solar_date.setCalendarPopup(True)
        self.solar_date.setDateTime(QDateTime.currentDateTimeUtc());config.addWidget(self.solar_date,2)
        config2=QHBoxLayout();l.addLayout(config2)
        config2.addWidget(label('Duration (hours)'))
        self.solar_hours=QSpinBox();self.solar_hours.setRange(1,336);self.solar_hours.setValue(self.preferences['solar_duration_hours']);config2.addWidget(self.solar_hours)
        config2.addWidget(label('Interval (minutes)'))
        self.solar_step=QSpinBox();self.solar_step.setRange(10,720);self.solar_step.setValue(self.preferences['solar_interval_minutes']);config2.addWidget(self.solar_step)
        self.solar_run=btn('Calculate selected site (JPL)',self.calculate_selected_solar)
        config2.addWidget(self.solar_run)
        actions=QHBoxLayout();l.addLayout(actions)
        actions.addWidget(btn('Load latest saved solar',self.load_latest_solar))
        actions.addWidget(btn('Open analysis JSON',self.pick_solar_json))
        actions.addWidget(btn('Show Site01 reference horizon (Site01 only)',self.show_horizon))
        self.horizon_run=btn('Calculate SELECTED candidate horizon (offline)',self.calculate_selected_horizon)
        actions.addWidget(self.horizon_run)
        l.addWidget(label('Neon yellow = Sun altitude · grey = candidate terrain horizon · negative clearance means Sun centre is below modelled horizon. Not a verified landing-safety model.',True))
        self.solar_status=label('Select a saved candidate. The analysis uses that region’s actual raster data and requires an internet connection to JPL.',True)
        l.addWidget(self.solar_status)
        self.solarplot=Plot();l.addWidget(self.solarplot,1)
        self.solarplot.reset('Solar & horizon results');self.solarplot.finish()
        return w

    def calculate_selected_solar(self):
        index=self.solar_candidate.currentData()
        if index is None or index>=len(self.records):
            self.warn('No lunar candidate selected','Go to Explorer, click a valid terrain cell and save it with a name. Then return to Illumination and select it.');return
        if self.solar_worker and self.solar_worker.isRunning():
            self.warn('Solar calculation running','One solar calculation is already in progress.');return
        from datetime import timezone
        date=self.solar_date.dateTime().toPython().replace(tzinfo=timezone.utc)
        self.solar_worker=SolarWorker(ROOT,self.records[index],date,self.solar_hours.value(),self.solar_step.value())
        self.solar_worker.success.connect(self.solar_finished)
        self.solar_worker.failure.connect(self.solar_failed)
        self.solar_run.setEnabled(False)
        rec=self.records[index]
        self.solar_status.setText(f"Calculating {rec['name']} ({rec['region']}): reading DEM, calculating its horizon and requesting JPL Sun positions…")
        try:
            self.solar_worker.start()
        except Exception as exc:
            self.solar_run.setEnabled(True)
            self.warn('Could not start solar analysis',explain_error(exc))

    def calculate_selected_horizon(self):
        index=self.solar_candidate.currentData()
        if index is None or index>=len(self.records):
            self.warn('No lunar candidate selected','Save a named location in Explorer, then select it here.');return
        if self.horizon_worker is not None and self.horizon_worker.isRunning():
            self.warn('Horizon calculation running','One horizon calculation is already in progress.');return
        rec=dict(self.records[index])
        self.horizon_worker=HorizonWorker(ROOT,rec)
        self.horizon_worker.success.connect(self.horizon_finished)
        self.horizon_worker.failure.connect(self.horizon_failed)
        self.horizon_run.setEnabled(False)
        self.solar_status.setText(f"Calculating {rec['name']} ({rec['region']}) horizon using that region's DEM. No JPL connection needed.")
        try:self.horizon_worker.start()
        except Exception as exc:
            self.horizon_run.setEnabled(True)
            self.warn('Could not start horizon analysis',explain_error(exc))

    def horizon_finished(self,result,path):
        self.horizon_run.setEnabled(True)
        records=result['angles']
        self.plot_solar_result({'kind':'horizon',
            'title':f"{result['candidate']['name']} / {result['candidate']['region']} / terrain horizon",
            'labels':[r['grid_azimuth_deg'] for r in records],
            'lines':[{'name':'Calculated horizon (grid azimuth)','color':'#BEC8D5',
                      'values':[r['horizon_angle_deg'] for r in records]}],
            'lower':None,'upper':None},Path(path))
        self.solar_status.setText(f"Calculated this candidate's own terrain horizon: {path}. No Sun position or uncertainty band was calculated.")

    def horizon_failed(self,message):
        self.horizon_run.setEnabled(True)
        self.solar_status.setText(message)
        self.warn('Candidate horizon unavailable',message)

    def solar_finished(self,result,path):
        self.solar_run.setEnabled(True)
        records=result['records']
        self.plot_solar_result({'kind':'solar','title':f"{result['candidate']['name']} / {result['candidate']['region']} / JPL solar timeline",
            'labels':[r['timestamp_utc'] for r in records],
            'lines':[{'name':'Sun altitude / JPL','color':'#FFE347','values':[r['altitude_deg'] for r in records]},
                     {'name':'Candidate horizon','color':'#BEC8D5','values':[r['baseline_horizon_deg'] for r in records]}],
            'lower':None,'upper':None},Path(path))
        summary=result['summary']
        self.solar_status.setText(f"{result['candidate']['name']} ({result['candidate']['region']}): Sun centre above modelled horizon at {summary['clear_samples']}/{summary['sample_count']} sampled times. JSON: {path}. No uncertainty band calculated for this candidate.")

    def solar_failed(self,message):
        self.solar_run.setEnabled(True)
        self.solar_status.setText(message)
        self.warn('Solar analysis unavailable',message)

    def load_latest_solar(self):
        base=ROOT/'data/processed'
        paths=[]
        for folder in ('solar_v2','solar','candidate_solar'):
            if (base/folder).exists():paths += list((base/folder).rglob('*.json'))
        # Only actual solar records can be plotted as solar data.
        for path in sorted(paths,key=lambda p:p.stat().st_mtime,reverse=True):
            try:
                data=parse_saved_result(path)
                if data['kind'] in ('solar','clearance'):
                    self.plot_solar_result(data,path);return
            except Exception:continue
        self.solar_status.setText('No saved JPL solar timeline found. Select a named candidate above and click Calculate selected site (JPL).')

    def pick_solar_json(self):
        from PySide6.QtWidgets import QFileDialog
        chosen,_=QFileDialog.getOpenFileName(self,'Open solar or horizon result',str(ROOT/'data/processed'),'JSON (*.json)')
        if not chosen:return
        try:self.plot_solar_result(parse_saved_result(Path(chosen)),Path(chosen))
        except Exception as exc:self.warn('Could not read analysis JSON',exc)

    def plot_solar_result(self,data,path):
        self.solarplot.reset(data['title'].replace('SELENEKTO','SelenEkto'))
        ax=self.solarplot.ax
        x=np.arange(len(data['labels']))
        for line in data['lines']:
            ax.plot(x,line['values'],lw=2.2,color=line['color'],label=line['name'])
        lower,upper=data.get('lower'),data.get('upper')
        if lower is not None and upper is not None and len(lower)==len(x) and len(upper)==len(x):
            try:
                lo=np.array([np.nan if v is None else float(v) for v in lower])
                hi=np.array([np.nan if v is None else float(v) for v in upper])
                ax.fill_between(x,lo,hi,color='#AAB4C1',alpha=.26,label='RMS sensitivity scenarios')
            except (ValueError,TypeError):pass
        if data['kind']=='clearance':ax.axhline(0,color='#8B97A8',linestyle='--')
        step=max(1,len(x)//9)
        labels=data['labels']
        ax.set_xticks(x[::step])
        ax.set_xticklabels([str(v) if data['kind']=='horizon' else str(v)[5:16].replace('T',' ') for v in labels[::step]],rotation=25,ha='right',fontsize=8)
        ax.set_xlabel('Grid azimuth (degrees)' if data['kind']=='horizon' else 'UTC date/time',color=MUTED)
        ax.set_ylabel('Angle (degrees)',color=MUTED)
        ax.grid(color='#718092',alpha=.2)
        ax.legend(facecolor=PANEL,labelcolor=FG,edgecolor=BORDER,fontsize=9)
        self.solarplot.finish()
        self.solar_status.setText(f'Loaded actual saved result: {path.name} · {data["kind"]} · not a verified landing-safety model')

    def show_horizon(self):
        path=ROOT/'data/processed/horizon/Site01/Site01_horizon_5km.json'
        try:self.plot_solar_result(parse_saved_result(path),path)
        except Exception as exc:self.warn('Reference horizon unavailable',exc)

    def _library_updated(self):
        self.refresh_regions()
        self.refresh_health()

    def make_health(self):
        w=QWidget();l=QVBoxLayout(w);l.addWidget(label('SelenEkto / Data Health / installed NASA regions'))
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
        w=QWidget();outer=QVBoxLayout(w)
        outer.addWidget(label('SelenEkto / Settings'))
        outer.addWidget(label('Your preferences are stored locally and restored when you reopen SelenEkto. Scientific source data is never changed.',True))
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner=QWidget();l=QVBoxLayout(inner);l.setSpacing(16)
        appearance=QGroupBox('Appearance');form=QFormLayout(appearance)
        self.setting_theme=QComboBox();self.setting_theme.addItems(THEMES);self.setting_theme.setCurrentText(self.preferences['theme'])
        self.setting_accent=QComboBox();self.setting_accent.addItems(ACCENTS);self.setting_accent.setCurrentText(self.preferences['accent'])
        self.setting_font=QSpinBox();self.setting_font.setRange(10,17);self.setting_font.setSuffix(' px');self.setting_font.setValue(self.preferences['font_size'])
        form.addRow('Dark theme',self.setting_theme);form.addRow('Accent colour',self.setting_accent);form.addRow('Interface text size',self.setting_font)
        l.addWidget(appearance)
        explorer=QGroupBox('Explorer');form=QFormLayout(explorer)
        self.setting_layer=QComboBox();self.setting_layer.addItems(SUFFIXES);self.setting_layer.setCurrentText(self.preferences['default_layer'])
        form.addRow('Default map layer',self.setting_layer);l.addWidget(explorer)
        illumination=QGroupBox('Illumination defaults');form=QFormLayout(illumination)
        self.setting_hours=QSpinBox();self.setting_hours.setRange(1,336);self.setting_hours.setSuffix(' hours');self.setting_hours.setValue(self.preferences['solar_duration_hours'])
        self.setting_interval=QSpinBox();self.setting_interval.setRange(10,720);self.setting_interval.setSuffix(' minutes');self.setting_interval.setValue(self.preferences['solar_interval_minutes'])
        form.addRow('Timeline duration',self.setting_hours);form.addRow('Sample interval',self.setting_interval);l.addWidget(illumination)
        candidates=QGroupBox('Saved candidates');form=QFormLayout(candidates)
        self.setting_confirm=QCheckBox('Ask before deleting named candidates');self.setting_confirm.setChecked(self.preferences['confirm_candidate_removal'])
        form.addRow(self.setting_confirm);l.addWidget(candidates)
        l.addWidget(label('Notes: changing timeline defaults does not alter existing JPL results. Changing the default map layer does not alter raster values. These preferences do not affect scientific calculations.',True))
        actions=QHBoxLayout()
        actions.addWidget(btn('Save and apply settings',self.save_preferences))
        actions.addWidget(btn('Restore defaults',self.reset_preferences))
        l.addLayout(actions);l.addStretch()
        self.setting_status=label('Settings are stored in data/config/desktop_settings.json',True);l.addWidget(self.setting_status)
        scroll.setWidget(inner);outer.addWidget(scroll,1)
        return w

    def save_preferences(self):
        values={
            'theme':self.setting_theme.currentText(),
            'accent':self.setting_accent.currentText(),
            'font_size':self.setting_font.value(),
            'default_layer':self.setting_layer.currentText(),
            'solar_duration_hours':self.setting_hours.value(),
            'solar_interval_minutes':self.setting_interval.value(),
            'confirm_candidate_removal':self.setting_confirm.isChecked(),
        }
        try:
            path=save_settings(ROOT,values)
            self.preferences=load_settings(ROOT)
            self.apply_preferences()
            self.setting_status.setText(f'Saved preferences: {path}')
            self.statusBar().showMessage('Settings saved and applied',6000)
        except OSError as exc:
            self.warn('Settings could not be saved',f'Check that data/config is writable. Details: {exc}')

    def reset_preferences(self):
        defaults=dict(DEFAULTS)
        self.setting_theme.setCurrentText(defaults['theme'])
        self.setting_accent.setCurrentText(defaults['accent'])
        self.setting_font.setValue(defaults['font_size'])
        self.setting_layer.setCurrentText(defaults['default_layer'])
        self.setting_hours.setValue(defaults['solar_duration_hours'])
        self.setting_interval.setValue(defaults['solar_interval_minutes'])
        self.setting_confirm.setChecked(defaults['confirm_candidate_removal'])
        self.save_preferences()

    def apply_preferences(self):
        app=QApplication.instance()
        app.setStyleSheet(theme_stylesheet(STYLE,self.preferences))
        desired=self.preferences['default_layer']
        if hasattr(self,'layer_box') and self.layer_box.currentText()!=desired:
            self.layer_box.setCurrentText(desired)
        if hasattr(self,'solar_hours'):self.solar_hours.setValue(self.preferences['solar_duration_hours'])
        if hasattr(self,'solar_step'):self.solar_step.setValue(self.preferences['solar_interval_minutes'])


def main():
    # A distinct Windows application ID makes the taskbar group SelenEkto rather than generic Python.
    if sys.platform=='win32':
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('SelenEkto.LunarNavigator.Desktop.v2')
        except Exception:pass
    app=QApplication(sys.argv)
    app.setApplicationName('SelenEkto')
    app.setApplicationDisplayName('SelenEkto')
    app.setOrganizationName('SelenEkto')
    logo=ROOT/'assets/branding/logo.png'
    if logo.is_file():
        icon=QIcon(str(logo))
        if not icon.isNull():app.setWindowIcon(icon)
    app.setStyle('Fusion');app.setStyleSheet(STYLE)
    window=Main();window.show();return app.exec()

if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception:
        log=ROOT/'data/processed/logs/selenekto_v2_crash.log';log.parent.mkdir(parents=True,exist_ok=True)
        log.write_text(traceback.format_exc(),encoding='utf-8')
        print('SelenEkto v2 failed; see',log,file=sys.stderr)
        traceback.print_exc();raise
