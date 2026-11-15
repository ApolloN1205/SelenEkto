"""Standalone Qt solar/horizon results viewer. No model data is fabricated."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from selenekto_v2.neon_solar import parse_saved_result
from PySide6.QtWidgets import QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QFileDialog,QLabel,QComboBox
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
import numpy as np

class Viewer(QMainWindow):
    def __init__(self):
        super().__init__();self.setWindowTitle('SELENEKTO / NEON SOLAR + HORIZON');self.resize(1180,730)
        self.setStyleSheet('QWidget {background:#080B10;color:#EDF2FA;font:12px Segoe UI;} QPushButton,QComboBox {background:#1B2531;color:#EDF2FA;border:1px solid #566477;padding:9px;} QComboBox QAbstractItemView {background:#121820;color:white;}')
        w=QWidget();self.setCentralWidget(w);l=QVBoxLayout(w)
        row=QHBoxLayout();l.addLayout(row)
        row.addWidget(QLabel('S E L E N E K T O    /    SOLAR & HORIZON'))
        b=QPushButton('Open results JSON');b.clicked.connect(self.pick);row.addWidget(b)
        self.status=QLabel('Choose an exported real solar or horizon JSON file.');l.addWidget(self.status)
        self.fig=Figure(facecolor='#080B10');self.canvas=FigureCanvasQTAgg(self.fig);l.addWidget(self.canvas,1)
        self.note=QLabel('Yellow = JPL Sun altitude (if present). Grey = modelled terrain horizon. Shading = sensitivity scenarios, not confidence bounds.');l.addWidget(self.note)
        self.load_default()
    def load_default(self):
        for p in [ROOT/'data/processed/solar/Site01/Site01_solar_timeline.json',ROOT/'data/processed/horizon/Site01/Site01_horizon_5km.json']:
            if p.is_file():self.show_file(p);return
    def pick(self):
        fn,_=QFileDialog.getOpenFileName(self,'Select solar/horizon analysis JSON',str(ROOT/'data/processed'),'JSON (*.json)')
        if fn:self.show_file(Path(fn))
    def show_file(self,p):
        try:
            result=parse_saved_result(p);self.fig.clear();ax=self.fig.add_subplot(111)
            ax.set_facecolor('#0C121A');x=np.arange(len(result['labels']))
            for line in result['lines']:
                ax.plot(x,line['values'],color=line['color'],linewidth=2,label=line['name'])
            low,high=result['lower'],result['upper']
            if low and high and all(v is not None for v in low+high):
                ax.fill_between(x,low,high,alpha=.23,color='#B0BAC8',label='±1 RMS sensitivity scenarios')
            if result['kind']=='clearance':ax.axhline(0,color='#8E99A9',linestyle='--',linewidth=1)
            ax.set_title(result['title'],color='#F3F7FC',pad=15)
            step=max(1,len(x)//9)
            ax.set_xticks(x[::step],[v[5:16].replace('T',' ') if result['kind']!='horizon' else v for v in result['labels'][::step]],rotation=28,ha='right')
            ax.set_xlabel('Grid azimuth (°)' if result['kind']=='horizon' else 'UTC date / time',color='#B9C2CF')
            ax.set_ylabel('Angle (degrees)',color='#B9C2CF')
            ax.tick_params(colors='#CED6E0');ax.grid(alpha=.16,color='#A5B7C9')
            for s in ax.spines.values():s.set_color('#536174')
            ax.legend(facecolor='#1A2532',labelcolor='#EAF1F8',edgecolor='#536174')
            self.fig.tight_layout();self.canvas.draw_idle();self.status.setText(f'Loaded: {p.name} ({result["kind"]})')
        except Exception as exc:self.status.setText(f'Could not load {p.name}: {exc}')

if __name__=='__main__':
    app=QApplication(sys.argv);w=Viewer();w.show();sys.exit(app.exec())
