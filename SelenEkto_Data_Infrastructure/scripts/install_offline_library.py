"""Safely integrate Data Library into current SelenEkto launcher and Windows release builder."""
from pathlib import Path
from datetime import datetime,timezone
import py_compile
ROOT=Path(__file__).resolve().parents[1]


def update(path,edits):
    if not path.is_file():raise FileNotFoundError(f'Missing: {path}')
    original=path.read_text(encoding='utf-8');text=original
    if 'self.library_page=LibraryPage(' in text or "Data Library'" in text:
        print(f'Already patched: {path.name}');return False
    for old,new in edits:
        if text.count(old)!=1:
            raise ValueError(f'Unrecognised or changed file {path}: expected exactly one occurrence of {old!r}; refusing to edit')
        text=text.replace(old,new,1)
    backup=path.with_name(path.stem+'_before_offline_library_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')+'.py')
    backup.write_bytes(path.read_bytes())
    path.write_text(text,encoding='utf-8')
    try:py_compile.compile(str(path),doraise=True)
    except Exception:
        path.write_bytes(backup.read_bytes());raise
    print(f'Patched: {path}\nBackup: {backup}')
    return True


def main():
    launcher=ROOT/'scripts'/'launch_selenekto_v2_controls.py'
    update(launcher,[
        ('from PySide6.QtCore import Qt,', 'from selenekto_v2.library_view import LibraryPage\nfrom PySide6.QtCore import Qt,'),
        ('        side.addWidget(self.nav);side.addStretch()', "        self.nav.addItem('Data Library')\n        side.addWidget(self.nav);side.addStretch()"),
        ('        self.pages.addWidget(self.make_settings())', '        self.pages.addWidget(self.make_settings())\n        self.library_page=LibraryPage(ROOT,on_updated=self._library_updated)\n        self.pages.addWidget(self.library_page)'),
        ('    def make_health(self):', '''    def _library_updated(self):
        self.refresh_regions()
        self.refresh_health()

    def make_health(self):'''),
    ])
    builder=ROOT/'scripts'/'build_windows_release.py'
    if not builder.is_file():
        print('Release builder not present; offline UI installed, preview packaging skipped.')
        return
    text=builder.read_text(encoding='utf-8')
    if "dest/'data'/'catalog'/'previews'" in text:
        print('Preview packaging already enabled.')
    else:
        update(builder,[
           ("    (dest/'data'/'raw'/'lola').mkdir(parents=True,exist_ok=True)",
            "    preview_folder = root/'data'/'catalog'/'previews'\n    if preview_folder.is_dir():\n        shutil.copytree(preview_folder, dest/'data'/'catalog'/'previews', dirs_exist_ok=True)\n    (dest/'data'/'raw'/'lola').mkdir(parents=True,exist_ok=True)"),
        ])
    print('NEXT: generate previews from local TIFFs, then build. Do not distribute a local data junction.')
if __name__=='__main__':main()
