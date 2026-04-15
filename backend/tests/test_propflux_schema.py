from pathlib import Path

import pytest
from app.schemas.propflux_listing import (
    load_propflux_file,
    load_propflux_payload,
    validate_propflux_payload_partial,
)

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


def test_partial_validation_mixed_payload() -> None:
    payload = load_propflux_payload(FIXTURE_DIR / "mixed_valid_invalid.json")
    valid, invalid = validate_propflux_payload_partial(payload)
    assert len(valid) == 1
    assert len(invalid) == 2
    assert invalid[0].record_index == 1
