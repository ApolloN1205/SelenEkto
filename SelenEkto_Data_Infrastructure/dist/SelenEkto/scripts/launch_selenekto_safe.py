"""Lightweight SelenEkto launcher: no raster, Matplotlib or network work at startup.

Starts a small Tk window and logs each selected app's stdout/stderr. If the
latest repaired GUI displays a black screen, return here and try the previously
confirmed integrated dashboard without replacing any source file.
"""
from __future__ import annotations
import subprocess, sys, tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox
ROOT=Path(__file__).resolve().parents[1]
APP_SCRIPTS = [
    ('Original integrated dashboard (previously worked)', 'launch_dashboard.py'),
    ('Unified multi-region dashboard', 'launch_unified_dashboard.py'),
    ('Repaired dashboard (experimental)', 'launch_selenekto_repaired.py'),
    ('Multi-region map and names', 'launch_multiregion.py'),
    ('Site01 solar/horizon viewer', 'launch_selenekto.py'),
]

def main():
    root=tk.Tk()
    root.title('SELENEKTO / SAFE LAUNCHER')
    root.geometry('730x470')
    root.configure(bg='#090909')
    text='#f1f1f1'; bg='#090909'; panel='#202020'
    style=ttk.Style(root); style.theme_use('clam')
    style.configure('TButton', background=panel, foreground=text, padding=9)
    style.map('TButton', background=[('active','#444444')])
    tk.Label(root,text='SELENEKTO  /  SELECT APPLICATION',bg=bg,fg=text,font=('Segoe UI',17,'bold')).pack(anchor='w',padx=22,pady=(20,8))
    tk.Label(root,text='Safe launcher: does not load rasters, plot maps or contact NASA during startup.',bg=bg,fg='#bbbbbb').pack(anchor='w',padx=22,pady=(0,14))
    info=tk.StringVar(value='Ready. Choose an installed application below.')
    def start(filename):
        script=ROOT/'scripts'/filename
        if not script.exists():
            messagebox.showerror('Missing script',f'Not installed: {script}')
            return
        logdir=ROOT/'data/processed/logs';logdir.mkdir(parents=True,exist_ok=True)
        log=logdir/(filename.replace('.py','')+'.log')
        # Redirect long-lived child output to disk, do not block the Tk event loop.
        with log.open('ab') as stream:
            kwargs={'cwd':str(ROOT),'stdin':subprocess.DEVNULL,'stdout':stream,'stderr':subprocess.STDOUT}
            if sys.platform=='win32': kwargs['creationflags']=getattr(subprocess,'CREATE_NEW_CONSOLE',0)
            try: proc=subprocess.Popen([sys.executable,'-u',str(script)],**kwargs)
            except OSError as exc:
                messagebox.showerror('Launch failed',str(exc));return
        info.set(f'Started {filename} (PID {proc.pid}). Log: {log}')
    for label,fn in APP_SCRIPTS:
        available=(ROOT/'scripts'/fn).is_file()
        ttk.Button(root,text=(label if available else label+'  [not installed]'),
                   command=lambda f=fn:start(f),state='normal' if available else 'disabled').pack(fill='x',padx=22,pady=3)
    tk.Label(root,textvariable=info,bg=bg,fg='#e4a18d',wraplength=680,justify='left').pack(fill='x',padx=22,pady=15)
    tk.Label(root,text='If a child window is black, close it and use another launcher. Check data/processed/logs for errors.',bg=bg,fg='#bbbbbb',wraplength=680,justify='left').pack(anchor='w',padx=22)
    root.mainloop()
if __name__=='__main__':main()
