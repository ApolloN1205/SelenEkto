from pathlib import Path
import pytest

rasterio = pytest.importorskip("rasterio")
from rasterio.transform import from_origin
import numpy as np

from selenekto_data.validation import inspect_raster


def test_inspect_raster_reads_metadata_without_claiming_science(tmp_path):
    path = tmp_path / "synthetic.tif"
    data = np.array([[1, 2], [3, 4]], dtype="float32")
    with rasterio.open(path, "w", driver="GTiff", height=2, width=2, count=1,
                       dtype="float32", crs="EPSG:3857", transform=from_origin(0, 10, 5, 5),
                       nodata=-9999) as dst:
        dst.write(data, 1)
    result = inspect_raster(path)
    assert result["width"] == 2
    assert result["height"] == 2
    assert result["resolution_xy"] == [5.0, 5.0]
    assert "Metadata inspection only" in result["warning"]
