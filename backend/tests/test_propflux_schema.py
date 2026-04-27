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


def test_partial_validation_allows_known_propflux_optional_fields() -> None:
    payload = [
        {
            "title": "785 m² Land available in Le Grand Estate",
            "price": 1095000.0,
            "location": "88 le grand estate",
            "bedrooms": None,
            "bathrooms": None,
            "property_type": "Residential Land",
            "description": "Vacant stand with views",
            "listing_id": "T5421072",
            "source_site": "privateproperty",
            "pool": True,
            "garden": True,
            "electric_fencing": False,
            "laundry": False,
            "alarm": True,
            "study": False,
        }
    ]
    valid, invalid = validate_propflux_payload_partial(payload)

    assert len(valid) == 1
    assert len(invalid) == 0


def test_partial_validation_allows_unknown_extra_fields() -> None:
    payload = [
        {
            "title": "4 Bedroom House in Welbedacht",
            "price": 6250000.0,
            "location": "Welbedacht, Knysna",
            "bedrooms": 4,
            "bathrooms": 4.0,
            "property_type": "House",
            "description": "Immaculate home with views",
            "listing_id": "T5440103",
            "source_site": "privateproperty",
            # Unknown/forward-compatible fields from evolving upstream payloads.
            "job_id": "72e50122",
            "new_marketing_flag": True,
            "custom_notes": "future field should not invalidate record",
        }
    ]
    valid, invalid = validate_propflux_payload_partial(payload)

    assert len(valid) == 1
    assert len(invalid) == 0
