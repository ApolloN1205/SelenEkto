import json
from pathlib import Path

from selenekto_data.catalog import get_site, list_sites, validate_catalog
from selenekto_data.registry import list_datasets, datasets_for_site

ROOT = Path(__file__).resolve().parents[1]


def test_thirteen_candidate_regions_are_present():
    sites = list_sites(ROOT)
    assert len(sites) == 13
    assert {s["name"] for s in sites} >= {
        "Faustini Rim A", "Peak Near Shackleton", "Connecting Ridge",
        "Connecting Ridge Extension", "de Gerlache Rim 1", "de Gerlache Rim 2",
        "de Gerlache-Kocher Massif", "Haworth", "Malapert Massif",
        "Leibnitz Beta Plateau", "Nobile Rim 1", "Nobile Rim 2", "Amundsen Rim"
    }


def test_known_coordinates_match_nasa_data_book_table():
    site = get_site("Connecting Ridge", ROOT)
    assert site["latitude_deg"] == -89.4632
    assert site["longitude_as_published_deg"] == -137.49
    assert site["coordinate_source"]["table"] == "A2.1-1 Lunar South Pole Features"
    assert site["coordinate_role"] == "representative_region_centre"


def test_catalogue_is_consistent():
    assert validate_catalog(ROOT) == []


def test_pgda_register_only_contains_explicit_six_site_download_listing():
    records = list_datasets(ROOT)
    assert len(records) == 36
    assert len({r["dataset_id"] for r in records}) == 36
    assert {r["site_code"] for r in records} == {"Site01", "Site04", "Site07", "Site11", "Site20", "Site23"}
    assert len(datasets_for_site("Site01", ROOT)) == 6
    assert all("pgda.gsfc.nasa.gov/data/LOLA_5mpp/" in r["download_url"] for r in records)
