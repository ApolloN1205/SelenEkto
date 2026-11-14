import json
from pathlib import Path

import pytest

from selenekto_data.download import DownloadError, download_dataset


class FakeResponse:
    def __init__(self, payload: bytes, status: int = 200):
        self.payload = payload
        self.position = 0
        self.status = status
        self.headers = {"Content-Length": str(len(payload))}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def getcode(self):
        return self.status

    def geturl(self):
        return "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site01/test.tif"

    def read(self, amount=-1):
        if amount < 0:
            amount = len(self.payload) - self.position
        part = self.payload[self.position:self.position + amount]
        self.position += len(part)
        return part


def make_root(tmp_path: Path):
    (tmp_path / "data/manifests").mkdir(parents=True)
    registry = {"schema_version":"1.0","datasets":[{
        "dataset_id":"PGDA_SITE01_LDEM", "download_url":"https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site01/test.tif",
        "local_path":"data/raw/lola/Site01/test.tif", "acquisition_status":"not_downloaded"
    }]}
    (tmp_path / "data/manifests/datasets.json").write_text(json.dumps(registry))
    return tmp_path


def test_download_writes_file_checksum_and_log(tmp_path, monkeypatch):
    root = make_root(tmp_path)
    payload = b"synthetic test payload, not NASA data"
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: FakeResponse(payload))
    dataset = json.loads((root / "data/manifests/datasets.json").read_text())["datasets"][0]
    result = download_dataset(dataset, root, max_bytes=1000)
    path = root / dataset["local_path"]
    assert path.read_bytes() == payload
    assert result["sha256"]
    manifest = json.loads((root / "data/manifests/datasets.json").read_text())
    assert manifest["datasets"][0]["acquisition_status"] == "downloaded"
    log = json.loads((root / "data/manifests/acquisition_log.json").read_text())
    assert log["records"][0]["status"] == "downloaded"


def test_download_refuses_content_length_over_cap(tmp_path, monkeypatch):
    root = make_root(tmp_path)
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: FakeResponse(b"0123456789"))
    dataset = json.loads((root / "data/manifests/datasets.json").read_text())["datasets"][0]
    with pytest.raises(DownloadError, match="exceeding"):
        download_dataset(dataset, root, max_bytes=5)
    assert not (root / dataset["local_path"]).exists()


def test_download_rejects_untrusted_host(tmp_path):
    root = make_root(tmp_path)
    dataset = json.loads((root / "data/manifests/datasets.json").read_text())["datasets"][0]
    dataset["download_url"] = "https://example.com/anything.tif"
    with pytest.raises(DownloadError, match="allowlisted"):
        download_dataset(dataset, root, max_bytes=1000)
