"""Prevent the deleted-QThread regression in successive region downloads.

This static lifecycle check needs no GUI display in CI. The full interaction
must also be smoke-tested in a Windows release executable.
"""
import ast
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / 'src/selenekto_v2/library_view.py'


def test_download_worker_is_cleared_on_qthread_finished():
    tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
    page = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'LibraryPage')
    methods = {node.name: node for node in page.body if isinstance(node, ast.FunctionDef)}
    start = ast.unparse(methods['download_selected'])
    cleanup = ast.unparse(methods['_download_thread_finished'])
    assert 'worker.finished.connect(self._download_thread_finished)' in start
    assert 'worker.finished.connect(worker.deleteLater)' in start
    assert start.index('worker.finished.connect(self._download_thread_finished)') < start.index('worker.finished.connect(worker.deleteLater)')
    assert 'self.worker = None' in cleanup
    assert 'self.download.setEnabled(True)' in cleanup


def test_report_does_not_reenable_button_before_thread_finishes():
    tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
    page = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'LibraryPage')
    report = next(node for node in page.body if isinstance(node, ast.FunctionDef) and node.name == 'download_finished')
    assert 'self.download.setEnabled(True)' not in ast.unparse(report)
