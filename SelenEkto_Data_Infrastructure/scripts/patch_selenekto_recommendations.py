"""Non-destructively extend the active SelenEkto PySide6 launcher with preferences.
Run from the infrastructure folder. Backs up the original; refuses unknown layouts.
"""
from pathlib import Path
from datetime import datetime, timezone
import py_compile

root = Path(__file__).resolve().parents[1]
path = root / 'scripts' / 'launch_selenekto_v2_controls.py'
if not path.is_file():
    raise SystemExit(f"Launcher not found: {path}")
text = path.read_text(encoding='utf-8')
if 'def open_preference_comparison(self):' in text:
    print('Already installed; launcher not modified.')
    raise SystemExit(0)
import_anchor = 'import numpy as np\n'
button_anchor = "        top.addWidget(btn('Compare chosen candidate data',self.compare_metrics))\n"
method_anchor = '    def show_region_comparison(self):\n'
for anchor in (import_anchor, button_anchor, method_anchor):
    if text.count(anchor) != 1:
        raise SystemExit('Unknown launcher version; safe patch stopped. Missing/duplicated anchor: ' + repr(anchor))

method = '''    def open_preference_comparison(self):
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
            details.setPlainText('\\n'.join(detail_lines))
        for spin in widgets.values(): spin.valueChanged.connect(update)
        choose_winner.toggled.connect(update)
        update()
        dialog.exec()

'''
text = text.replace(import_anchor, import_anchor + 'from selenekto_v2.recommendations import CRITERIA, DEFAULT_WEIGHTS, evaluate\n', 1)
text = text.replace(button_anchor, button_anchor + "        top.addWidget(btn('Adjust comparison priorities',self.open_preference_comparison))\n", 1)
text = text.replace(method_anchor, method + method_anchor, 1)
backup = path.with_name(path.stem + '_pre_recommendations_' + datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S') + '.py')
backup.write_bytes(path.read_bytes())
path.write_text(text, encoding='utf-8')
try:
    py_compile.compile(str(path), doraise=True)
except Exception as exc:
    path.write_bytes(backup.read_bytes())
    raise SystemExit(f'Launcher failed syntax check and was restored from backup: {exc}')
print(f'Installed preference comparison successfully. Backup: {backup.name}')
