"""Persistent, validated desktop preferences. No scientific data is modified."""
from __future__ import annotations
import json
import os
from pathlib import Path

DEFAULTS = {
    'theme': 'Obsidian',
    'accent': 'Neon yellow',
    'font_size': 12,
    'default_layer': 'Slope',
    'solar_duration_hours': 72,
    'solar_interval_minutes': 60,
    'confirm_candidate_removal': True,
}
THEMES = ('Obsidian', 'Graphite')
ACCENTS = {'Neon yellow': '#FFE347', 'Coral': '#E77F71', 'Ice blue': '#5EC8F8', 'Aurora LOLA': '#C4A1FF', 'Crimson': '#E54864'}
LAYER_NAMES = ('Elevation', 'Slope', 'Elevation uncertainty', 'Slope uncertainty', 'LOLA observations')

def normalize(values):
    result = dict(DEFAULTS)
    if not isinstance(values, dict):
        return result
    if values.get('theme') in THEMES: result['theme'] = values['theme']
    if values.get('accent') in ACCENTS: result['accent'] = values['accent']
    if values.get('default_layer') in LAYER_NAMES: result['default_layer'] = values['default_layer']
    for name, low, high in [('font_size',10,17), ('solar_duration_hours',1,336), ('solar_interval_minutes',10,720)]:
        number = values.get(name)
        if type(number) is int and low <= number <= high: result[name] = number
    if type(values.get('confirm_candidate_removal')) is bool:
        result['confirm_candidate_removal'] = values['confirm_candidate_removal']
    return result

def settings_path(root):
    return Path(root) / 'data' / 'config' / 'desktop_settings.json'

def load_settings(root):
    path = settings_path(root)
    if not path.exists(): return dict(DEFAULTS)
    try: return normalize(json.loads(path.read_text(encoding='utf-8')))
    except (ValueError, OSError, UnicodeError): return dict(DEFAULTS)

def save_settings(root, settings):
    path = settings_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    validated = normalize(settings)
    tmp = path.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(validated, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    os.replace(tmp, path)
    return path


def theme_stylesheet(base_style, settings):
    s = normalize(settings)
    accent = ACCENTS[s['accent']]
    style = base_style
    if s['theme'] == 'Graphite':
        for old,new in [('#080A0D','#1A1D23'),('#141820','#272C35'),('#303846','#485362'),('#10151C','#222833'),('#111820','#252B36')]:
            style=style.replace(old,new)
    # SELENEKTO_FINAL_CONSOLIDATION_V1: deep Obsidian palette, preserving accent colours and Graphite.
    if s['theme'] == 'Obsidian':
        style += """
        QMainWindow, QWidget { background-color: #06070A; color: #F1F2F5; }
        QFrame#sidebar, QGroupBox, QTableWidget, QListWidget, QTextEdit, QScrollArea {
            background-color: #0D1016; border: 1px solid #252B35;
        }
        QPushButton { background-color: #161B24; color: #F1F2F5; border: 1px solid #343E4B; }
        QPushButton:hover { background-color: #222A36; }
        QComboBox, QLineEdit, QSpinBox, QDateEdit, QDateTimeEdit {
            background-color: #0C1016; color: #F1F2F5; border: 1px solid #384251;
        }
        QComboBox QAbstractItemView { background-color: #10141D; color: #F1F2F5; }
        QHeaderView::section { background-color: #151A23; color: #F1F2F5; }
        QTableWidget { alternate-background-color: #121722; }
        QListWidget::item:selected { background-color: #222B3A; color: white; }
        """
    style += f'''\nQMainWindow,QWidget {{font-size:{s['font_size']}px;}}\nQPushButton:focus,QComboBox:focus,QLineEdit:focus,QSpinBox:focus,QDateTimeEdit:focus {{border:1px solid {accent};}}\nQListWidget::item:selected {{border-left:3px solid {accent};}}\nQCheckBox::indicator:checked {{background:{accent};border:1px solid {accent};}}\n'''
    return style
