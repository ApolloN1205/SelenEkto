"""Portable candidate calculations must not conceal errors behind log-write failures."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from selenekto_v2.worker_logging import write_worker_exception


def test_worker_log_saves_exception(tmp_path):
    root = tmp_path / "portable"
    target = write_worker_exception(root, "last_candidate_solar_error.log", ValueError("example JPL error"))
    assert target == root / "data" / "processed" / "logs" / "last_candidate_solar_error.log"
    assert "example JPL error" in target.read_text(encoding="utf-8")


def test_worker_log_falls_back_when_app_is_read_only(tmp_path, monkeypatch):
    import selenekto_v2.worker_logging as logs

    root = tmp_path / "readonly"
    local = tmp_path / "user-writable"
    monkeypatch.setenv("LOCALAPPDATA", str(local))
    old_write = Path.write_text

    def fail_in_installation(self, *args, **kwargs):
        if str(self).startswith(str(root)):
            raise PermissionError("installation is read-only")
        return old_write(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_in_installation)
    target = logs.write_worker_exception(root, "last_candidate_solar_error.log", RuntimeError("original failure"))
    assert target == local / "SelenEkto" / "logs" / "last_candidate_solar_error.log"
    assert "original failure" in target.read_text(encoding="utf-8")


def test_worker_log_does_not_mask_failure_if_all_writes_fail(tmp_path, monkeypatch):
    def fail_write(self, *args, **kwargs):
        raise PermissionError("write blocked")

    monkeypatch.setattr(Path, "write_text", fail_write)
    target = write_worker_exception(tmp_path, "last_candidate_horizon_error.log", ValueError("original error"))
    assert target is None
