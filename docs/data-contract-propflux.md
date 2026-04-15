# PropFlux Data Contract (Pre-Week-1)

## Supported Input

- File format: JSON
- Root structure: **array of objects**
- Source scope: PropFlux-style listings only

Any non-array root object is rejected.

## Required Fields

- `title` (string)
- `price` (number)
- `location` (string)
- `bedrooms` (integer)
- `bathrooms` (number)
- `property_type` (string)
- `description` (string)

## Optional Fields

- `agent_name` (string | null)
- `agent_phone` (string | null)
- `agency_name` (string | null)
- `listing_id` (string | null)
- `date_posted` (date ISO string `YYYY-MM-DD` | null)
- `erf_size` (number | null)
- `floor_size` (number | null)
- `rates_and_taxes` (number | null)
- `levies` (number | null)
- `garages` (integer | null)
- `parking` (integer | null)
- `en_suite` (integer | null)
- `lounges` (integer | null)
- `backup_power` (boolean | null)
- `security` (boolean | null)
- `pets_allowed` (boolean | null)

## Supported Metadata Fields

The schema also supports common PropFlux metadata:

- `listing_url` (string | null)
- `suburb` (string | null)
- `city` (string | null)
- `province` (string | null)
- `is_auction` (boolean | null)
- `is_private_seller` (boolean | null)
- `source_site` (string | null)
- `scraped_at` (datetime ISO string | null)

## Validation Rules

- Unknown fields are rejected.
- Per-record validation errors include array index context.
- Ingestion uses **partial-accept** mode:
  - valid records are normalized and stored
  - invalid records are persisted in rejected-record storage with deterministic errors
- Non-array root payloads fail the job immediately.

## Storage Model

Ingestion persists data into three stores:

- `raw_listings`: immutable source payloads per record
- `listings`: canonical normalized records (deduplicated)
- `rejected_listings`: invalid records with `error_code` and `error_detail`

## Idempotency Rules

- Preferred dedup key: `(source_site, listing_id)` when both values exist.
- Fallback dedup key: normalized content hash (`source_hash`).
- Re-ingesting the same listing updates canonical data instead of duplicating rows.

## Example

Use `backend/tests/fixtures/propflux/valid_listings.json` as canonical valid sample input.
