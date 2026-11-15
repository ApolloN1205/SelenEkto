"""Safe, repeatable SelenEkto clean-install repair. Keeps original project data intact."""
from __future__ import annotations

import ast
import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def backup_and_write(path: Path, updated: str) -> bool:
    previous = path.read_text(encoding='utf-8')
    if previous == updated:
        print('Already current:', path.relative_to(ROOT))
        return False
    ast.parse(updated, filename=str(path))
    backup = path.with_name(path.stem + '_before_clean_install_' + datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f') + path.suffix)
    shutil.copy2(path, backup)
    path.write_text(updated, encoding='utf-8')
    try:
        py_compile.compile(str(path), doraise=True)
    except Exception:
        shutil.copy2(backup, path)
        raise
    print('Updated:', path.relative_to(ROOT), '| backed up:', backup.name)
    return True


def patch_launcher(source: str) -> str:
    marker = 'SELENEKTO_CLEAN_INSTALL_MISSING_DATA_V1'
    if marker in source:
        return source
    anchor = "        self.cell_info=label('Click a valid terrain pixel to inspect its data.',True);l.addWidget(self.cell_info)"
    replacement = """        # SELENEKTO_CLEAN_INSTALL_MISSING_DATA_V1
        self.no_data_notice=QLabel('');self.no_data_notice.setWordWrap(True)
        self.no_data_notice.setStyleSheet('background:#24202A;color:#F7DBA5;border:1px solid #8B6948;border-radius:7px;padding:12px;')
        self.no_data_notice.hide();l.addWidget(self.no_data_notice)
""" + anchor
    if source.count(anchor) != 1:
        raise ValueError('Launcher Explorer layout differs from supported version; no files changed.')
    source = source.replace(anchor, replacement, 1)
    old = "        if options:self.change_map()\n        else:self.cell_info.setText('No complete aligned NASA regions found. See Data Health for missing layers.')"
    new = """        if options:
            self.no_data_notice.hide()
            self.change_map()
        else:
            self.active_arr=None;self.active_dims=None;self.region=None;self.layer=None
            message=('No complete, aligned full-resolution NASA terrain region is installed in this application. '
                     'This is expected for the lightweight Windows download.\\n\\n'
                     'Open Data Library to browse slope previews, then choose Download selected region '
                     'to install its NASA TIFF layers. Once downloaded, return here and click Refresh datasets.\\n\\n'
                     'LM8 has reported missing data; Site20 and Site23 have reported alignment problems '
                     'and should not be used for scientific comparisons until validated.')
            self.no_data_notice.setText(message)
            self.no_data_notice.show()
            self.cell_info.setText('Full-resolution slope map unavailable. See the explanation above and Data Library.')
            self.mapplot.reset('Slope map not installed')
            self.mapplot.ax.text(.5,.55,'Slope map not installed',transform=self.mapplot.ax.transAxes,
                                 horizontalalignment='center',verticalalignment='center',color='#F7DBA5',fontsize=15)
            self.mapplot.ax.text(.5,.43,'Open Data Library for offline slope previews',
                                 transform=self.mapplot.ax.transAxes,horizontalalignment='center',
                                 verticalalignment='center',color='#C4CAD2',fontsize=10)
            self.mapplot.finish()"""
    if source.count(old) != 1:
        raise ValueError('Launcher refresh_regions differs from supported version; no files changed.')
    return source.replace(old, new, 1)


def patch_library(source: str) -> str:
    marker = 'SELENEKTO_LIBRARY_EXPLICIT_STATUS_V1'
    if marker in source:
        return source
    old = "        self.status.setText(f'Local layers detected: {info[\"present_layers\"]}/5 (not yet validated).'+(f'  WARNING: {note}' if note else ''))"
    new = """        # SELENEKTO_LIBRARY_EXPLICIT_STATUS_V1
        if note:
            status = f'WARNING: {note}. Local NASA TIFF layers: {info["present_layers"]}/5. Do not use for measurements until validated.'
        elif info['present_layers'] == 5:
            status = 'Five NASA layers found locally. Integrity and alignment must still be checked in Data Health.'
        else:
            status = (f'Offline preview mode — {info["present_layers"]}/5 NASA layers installed. '
                      'Slope previews remain available without full-resolution data. '
                      'For detailed maps, candidate measurements and horizon calculations, click Download selected region. '
                      'Downloads require an internet connection and can be large.')
        self.status.setText(status)"""
    if source.count(old) != 1:
        raise ValueError('Data Library status code differs from supported version; no files changed.')
    source = source.replace(old, new, 1)
    # Retain updated slope text if already present, otherwise remove stale elevation-only advice.
    source = source.replace('Run the preview-generation script on a machine holding its elevation TIFF.',
                            'This preview was not included with the lightweight application.')
    return source


def patch_builder(source: str) -> str:
    marker = 'SELENEKTO_RELEASE_DIAGNOSTIC_V1'
    if marker in source:
        return source
    anchor = "    print('Portable directory:',dest)"
    inject = """    # SELENEKTO_RELEASE_DIAGNOSTIC_V1
    # The release entrypoint reports startup errors through a native Windows dialog.
    # Do not copy the developer's massive NASA TIFF folder into a public build.
    for accidental in dest.rglob('*.tif'):
        if accidental.is_file():
            raise RuntimeError(f'Unexpected TIFF included in release: {accidental}')
    for accidental in dest.rglob('*.tiff'):
        if accidental.is_file():
            raise RuntimeError(f'Unexpected TIFF included in release: {accidental}')
""" + anchor
    if source.count(anchor) != 1:
        raise ValueError('Release builder differs from supported version; no files changed.')
    return source.replace(anchor, inject, 1)


def main() -> None:
    launcher = ROOT / 'scripts' / 'launch_selenekto_v2_controls.py'
    library = ROOT / 'src' / 'selenekto_v2' / 'library_view.py'
    builder = ROOT / 'scripts' / 'build_windows_release.py'
    entry = ROOT / 'release' / 'selenekto_entry.py'
    for p in (launcher, library, builder):
        if not p.is_file():
            raise FileNotFoundError(f'Missing application file: {p}. Install the previous Offline Library update first.')
    if not entry.is_file():
        raise FileNotFoundError(f'Missing release entrypoint: {entry}')
    updates = [(launcher, patch_launcher(launcher.read_text(encoding='utf-8'))),
               (library, patch_library(library.read_text(encoding='utf-8'))),
               (builder, patch_builder(builder.read_text(encoding='utf-8')))]
    # Parse all changes before writing any, and refuse incompatible source versions.
    for path, content in updates:
        ast.parse(content, filename=str(path))
    for path, content in updates:
        backup_and_write(path, content)
    print('Clean-install UI and error reporting patch applied. Next: rebuild and smoke test a copied release.')


if __name__ == '__main__':
    main()
