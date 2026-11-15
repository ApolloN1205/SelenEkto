"""PySide6 offline regional catalogue + explicit selective NASA dataset acquisition UI."""
from __future__ import annotations
import importlib.util
import sys
import traceback
from pathlib import Path
from PySide6.QtCore import Qt,QThread,Signal
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QListWidget,QPushButton,
  QTextEdit,QMessageBox,QSplitter,QScrollArea,QFrame)
from PySide6.QtGui import QPixmap
from .offline_library import REGIONS,LAYERS,KNOWN_ISSUES,catalogue_status,preview_path,generate_preview
# SELENEKTO_FINAL_CONSOLIDATION_V1
REGIONS = tuple(region for region in REGIONS if region not in {'LM8', 'Site20', 'Site23'})


class DownloadWorker(QThread):
    finished_report=Signal(str,bool)
    def __init__(self,root,region):
        super().__init__();self.root=Path(root);self.region=region
    def run(self):
        lines=[];complete=True
        try:
            # Use project's existing verified-source downloader; do not call sys.executable,
            # because in a frozen app that path is SelenEkto.exe, not Python.
            path=self.root/'scripts'/'download_pgda_real.py'
            if not path.is_file(): raise FileNotFoundError('NASA downloader not included: '+str(path))
            spec=importlib.util.spec_from_file_location('selenekto_pgda_downloader',path)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            for layer in LAYERS:
                ok,result=module.download_one(self.region,layer)
                lines.append(f'{layer}: {result.get("status", "unknown")}'+(' — '+str(result.get('error')) if result.get('error') else ''))
                complete=complete and ok
            lines.append('All layers present. Check Data Health for raster alignment before analysis.' if complete else 'Some layers remain unavailable. See failures above.')
        except Exception:
            complete=False;lines.append(traceback.format_exc())
        self.finished_report.emit('\n'.join(lines),complete)

class LibraryPage(QWidget):
    def __init__(self,root,on_updated=None,parent=None):
        super().__init__(parent);self.root=Path(root);self.on_updated=on_updated;self.worker=None
        layout=QVBoxLayout(self);layout.setSpacing(12)
        heading=QLabel('SelenEkto / Data Library');heading.setStyleSheet('font-size:20px;font-weight:600;')
        layout.addWidget(heading)
        tagline=QLabel('Browse the 24 currently included lunar regions offline. Slope previews use genuine NASA slope rasters in degrees (fixed 0–30° grayscale). They are visual references, not landing-safety assessments. Download original NASA layers for new pixel-level analysis.')
        tagline.setWordWrap(True);layout.addWidget(tagline)
        split=QSplitter();layout.addWidget(split,1)
        self.list=QListWidget();self.list.addItems(REGIONS);self.list.setMinimumWidth(170);split.addWidget(self.list)
        right=QWidget();v=QVBoxLayout(right);split.addWidget(right)
        self.title=QLabel('');self.title.setStyleSheet('font-size:16px;font-weight:600;');v.addWidget(self.title)
        self.status=QLabel('');self.status.setWordWrap(True);v.addWidget(self.status)
        self.preview=QLabel('');self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter);self.preview.setMinimumHeight(220)
        self.preview.setStyleSheet('background:#1B202A;border:1px solid #374150;border-radius:8px;color:#CDD4DE;')
        self.preview.setScaledContents(False);v.addWidget(self.preview,1)
        row=QHBoxLayout();v.addLayout(row)
        self.download=QPushButton('Download selected region (NASA)');row.addWidget(self.download)
        self.download.clicked.connect(self.download_selected)
        refresh=QPushButton('Refresh library');row.addWidget(refresh);refresh.clicked.connect(self.refresh)
        self.log=QTextEdit();self.log.setReadOnly(True);self.log.setMaximumHeight(105);v.addWidget(self.log)
        footer=QLabel('Three unreliable regions (LM8, Site20 and Site23) are excluded from the current release catalogue. Full-resolution NASA layers are required for new maps, measurements and horizons.')
        footer.setWordWrap(True);v.addWidget(footer)
        self.list.currentRowChanged.connect(self.refresh)
        self.list.setCurrentRow(0);self.refresh()
    def selected(self):
        text=self.list.currentItem().text() if self.list.currentItem() else ''
        return text if text in REGIONS else None
    def refresh(self,*args):
        region=self.selected()
        if not region:return
        info=catalogue_status(self.root,region)
        self.title.setText(region)
        note=KNOWN_ISSUES.get(region,'')
        # SELENEKTO_LIBRARY_EXPLICIT_STATUS_V1
        if note:
            status = f'WARNING: {note}. Local NASA TIFF layers: {info["present_layers"]}/5. Do not use for measurements until validated.'
        elif info['present_layers'] == 5:
            status = 'Five NASA layers found locally. Integrity and alignment must still be checked in Data Health.'
        else:
            status = (f'Offline preview mode — {info["present_layers"]}/5 NASA layers installed. '
                      'Slope previews remain available without full-resolution data. '
                      'For detailed maps, candidate measurements and horizon calculations, click Download selected region. '
                      'Downloads require an internet connection and can be large.')
        self.status.setText(status)
        p=preview_path(self.root,region)
        if p.exists():
            pix=QPixmap(str(p))
            if not pix.isNull():
                self.preview.setPixmap(pix.scaled(720,400,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
                return
        self.preview.clear()
        self.preview.setText('No lightweight preview installed for this region.\nRun the slope preview generator where that region’s slope TIFF is installed.\nThe region remains listed so it is discoverable offline.')
    def download_selected(self):
        if self.worker and self.worker.isRunning():return
        region=self.selected()
        if not region:return
        note=KNOWN_ISSUES.get(region)
        text=f'Download five original NASA terrain layers for {region}?\n\nThis may require hundreds of MB, depending on the region. Existing valid files are skipped.\nSource: NASA PGDA.'
        if note:text+='\n\nWarning: '+note+'; do not assume downloaded data is usable.'
        if QMessageBox.question(self,'Download original NASA data',text)!=QMessageBox.StandardButton.Yes:return
        self.download.setEnabled(False);self.log.setPlainText(f'Downloading {region}…')
        self.worker=DownloadWorker(self.root,region)
        self.worker.finished_report.connect(self.download_finished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()
    def download_finished(self,report,complete):
        self.download.setEnabled(True);self.log.setPlainText(report)
        self.refresh()
        if callable(self.on_updated):self.on_updated()
        QMessageBox.information(self,'Download finished' if complete else 'Download incomplete',report)
