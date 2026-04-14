from pathlib import Path

import pytest
from app.schemas.propflux_listing import load_propflux_file

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "propflux"


def test_load_propflux_valid_fixture() -> None:
    listings = load_propflux_file(FIXTURE_DIR / "valid_listings.json")
    assert len(listings) == 1
    assert listings[0].title == "3 Bedroom House in Blanco"


@pytest.mark.parametrize(
    "fixture_name",
    [
        "invalid_missing_required.json",
        "invalid_wrong_type.json",
        "invalid_non_array.json",
    ],
)
def test_load_propflux_invalid_fixtures_raise(fixture_name: str) -> None:
    with pytest.raises(ValueError):
        load_propflux_file(FIXTURE_DIR / fixture_name)
