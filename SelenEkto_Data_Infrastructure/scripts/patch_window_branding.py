"""Remove the sidebar logo only; retain desktop/taskbar/window icons.

Backs up first; refuses unrecognised layouts. Safe to run again.
"""
from pathlib import Path
from datetime import datetime, timezone
import py_compile

root = Path(__file__).resolve().parents[1]
path = root / 'scripts' / 'launch_selenekto_v2_controls.py'
if not path.is_file():
    raise SystemExit(f'Launcher missing: {path}')
text = path.read_text(encoding='utf-8')
marker = '        mast=label(\'SelenEkto\')'
start = text.find(marker)
end = text.find('        side.addWidget(mast)', start)
if start < 0 or end < 0:
    raise SystemExit('Launcher layout not recognised; no changes made.')
block = text[start:end]
image_block = '''        if self.logo_path.is_file():
            img=QLabel();pix=QPixmap(str(self.logo_path))
            if not pix.isNull():
                img.setPixmap(pix.scaled(68,68,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
                side.addWidget(img)
'''
if image_block not in block:
    if 'side.addWidget(img)' not in block:
        print('Sidebar already has no logo. Window/application icon preserved.')
        raise SystemExit(0)
    raise SystemExit('Sidebar image code differs from expected source; no changes made.')
new = text.replace(image_block, '', 1)
if new.count('side.addWidget(img)') != 0:
    raise SystemExit('Other sidebar logo placements detected; no changes made.')
backup = path.with_name(path.stem + '_before_icon_polish_' + datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S') + '.py')
backup.write_bytes(path.read_bytes())
path.write_text(new, encoding='utf-8')
try:
    py_compile.compile(str(path), doraise=True)
except Exception as exc:
    path.write_bytes(backup.read_bytes())
    raise SystemExit(f'Syntax error; restored backup. Details: {exc}')
print('Removed logo image from sidebar. Executable/window/taskbar icon code unchanged.')
print('Backup:', backup)
