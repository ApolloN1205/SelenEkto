"""Public terrain profiles must be portable and free of local machine paths."""
import json
import re
from pathlib import Path

PROFILE_DIR = Path(__file__).resolve().parents[1] / "data" / "catalog" / "region_profiles"
PRIVATE_PATH = re.compile(r"(?i)(?:[a-z]:[\\/]+users[\\/]+|/users/|/home/)")


def walk(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item)
    elif isinstance(value, str):
        yield value


def test_public_profiles_do_not_contain_personal_folders():
    profiles = sorted(PROFILE_DIR.glob("*_terrain_profile.json"))
    assert profiles, "No source terrain profiles found"
    for path in profiles:
        data = json.loads(path.read_text(encoding="utf-8"))
        for value in walk(data):
            assert not PRIVATE_PATH.search(value), f"Private local path in {path.name}"


def test_public_raster_references_are_project_relative():
    profiles = sorted(PROFILE_DIR.glob("*_terrain_profile.json"))
    for path in profiles:
        data = json.loads(path.read_text(encoding="utf-8"))
        for layer in data.get("layers", {}).values():
            if not isinstance(layer, dict):
                continue
            refs = layer.get("source_paths", [])
            if isinstance(refs, list):
                for value in refs:
                    if isinstance(value, str) and "data/raw/lola" in value:
                        assert value.startswith("data/raw/lola/"), path.name
            for key, value in layer.items():
                if key == "path" and isinstance(value, str) and "data/raw/lola" in value:
                    assert value.startswith("data/raw/lola/"), path.name
