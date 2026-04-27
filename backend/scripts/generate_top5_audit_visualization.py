from __future__ import annotations

import argparse
import html
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import plotly.graph_objects as go
from app.db.session import SessionLocal
from app.models.listing import Listing
from app.models.score_result import ScoreResult
from app.services.scoring import (
    _build_comp_index,
    _confidence_signal,
    _feature_density_signal,
    _gross_yield_assumption,
    _load_scoring_config,
    _resolve_comp_context,
)
from matplotlib import pyplot as plt
from sqlalchemy import select


def _load_top_listings(job_id: int, limit: int) -> list[dict[str, Any]]:
    with SessionLocal() as db:
        score_rows = db.scalars(
            select(ScoreResult)
            .where(ScoreResult.job_id == job_id)
            .order_by(ScoreResult.score.desc())
            .limit(limit)
        ).all()

        records: list[dict[str, Any]] = []
        for score_row in score_rows:
            listing = db.get(Listing, score_row.listing_id)
            if listing is None:
                continue
            explanation = score_row.explanation or {}
            records.append(
                {
                    "listing_id": listing.id,
                    "score": float(score_row.score),
                    "confidence": float(score_row.confidence),
                    "model_version": score_row.model_version,
                    "price": float(listing.price),
                    "property_type": listing.property_type,
                    "city": listing.city,
                    "suburb": listing.suburb,
                    "province": listing.province,
                    "bedrooms": listing.bedrooms,
                    "bathrooms": listing.bathrooms,
                    "floor_size": listing.floor_size,
                    "date_posted": listing.date_posted,
                    "rates_and_taxes": listing.rates_and_taxes,
                    "levies": listing.levies,
                    "signals": explanation.get("signals", []),
                }
            )
        return records


def _signal_matrix(records: list[dict[str, Any]]) -> tuple[list[str], list[dict[str, Any]]]:
    signal_names: list[str] = []
    if records:
        signal_names = [row["name"] for row in records[0]["signals"]]

    matrix: list[dict[str, Any]] = []
    for record in records:
        by_name = {row["name"]: float(row["normalized_score"]) for row in record["signals"]}
        matrix.append(
            {
                "listing_id": record["listing_id"],
                "signal_scores": [by_name.get(name, 0.0) for name in signal_names],
            }
        )
    return signal_names, matrix


def _safe_ratio(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return numerator / denominator


def _compute_audit_inputs(job_id: int, records: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    selected_ids = {int(record["listing_id"]) for record in records}
    config = _load_scoring_config()
    advanced_v2_cfg = config.get("advanced_v2", {})
    comps_cfg = advanced_v2_cfg.get("comps", {})
    roi_cfg = advanced_v2_cfg.get("roi", {})
    fallback_order = list(
        comps_cfg.get("fallback_order", ["suburb", "city", "province", "global"])
    )
    include_bedrooms = bool(comps_cfg.get("include_bedrooms", True))
    include_bathrooms = bool(comps_cfg.get("include_bathrooms", True))
    minimum_cohort_size = int(comps_cfg.get("minimum_cohort_size", 12))
    stale_inventory_days = int(config.get("rules", {}).get("stale_inventory_days", 90))

    with SessionLocal() as db:
        all_listings = db.scalars(select(Listing).where(Listing.job_id == job_id)).all()

    comp_index = _build_comp_index(
        all_listings,
        fallback_order,
        include_bedrooms=include_bedrooms,
        include_bathrooms=include_bathrooms,
    )
    listing_map = {
        int(listing.id): listing for listing in all_listings if int(listing.id) in selected_ids
    }
    now_date = datetime.now(UTC).date()
    details: dict[int, dict[str, Any]] = {}

    for listing_id, listing in listing_map.items():
        comp_level, comparable, fallback_penalty = _resolve_comp_context(
            listing=listing,
            comp_index=comp_index,
            fallback_order=fallback_order,
            minimum_cohort_size=minimum_cohort_size,
            include_bedrooms=include_bedrooms,
            include_bathrooms=include_bathrooms,
        )
        comp_prices = [row.price for row in comparable if row.price is not None]
        comp_ppsqm = [
            row.price / row.floor_size
            for row in comparable
            if row.price is not None and row.floor_size is not None and row.floor_size > 0
        ]
        comp_median_price = float(np.median(comp_prices)) if comp_prices else None
        comp_median_ppsqm = float(np.median(comp_ppsqm)) if comp_ppsqm else None
        listing_ppsqm = (
            float(listing.price / listing.floor_size)
            if listing.floor_size is not None and listing.floor_size > 0
            else None
        )
        days_on_market = (
            max(0, (now_date - listing.date_posted).days)
            if listing.date_posted is not None
            else None
        )
        confidence = _confidence_signal(listing)
        feature_value = _feature_density_signal(listing)

        transaction_cost_pct = float(roi_cfg.get("transaction_cost_pct", 0.08))
        vacancy_allowance_pct = float(roi_cfg.get("vacancy_allowance_pct", 0.05))
        maintenance_pct = float(roi_cfg.get("maintenance_pct", 0.04))
        management_pct = float(roi_cfg.get("management_pct", 0.08))
        insurance_pct = float(roi_cfg.get("insurance_pct", 0.01))
        gross_yield = _gross_yield_assumption(listing.property_type)
        effective_purchase_price = float(listing.price) * (1.0 + transaction_cost_pct)
        annual_rent = float(listing.price) * gross_yield
        monthly_fixed_costs = float(listing.rates_and_taxes or 0.0) + float(listing.levies or 0.0)
        annual_fixed_costs = monthly_fixed_costs * 12.0
        annual_variable_costs = annual_rent * (vacancy_allowance_pct + management_pct)
        annual_asset_costs = effective_purchase_price * (maintenance_pct + insurance_pct)
        annual_costs = annual_fixed_costs + annual_variable_costs + annual_asset_costs
        net_yield = _safe_ratio(annual_rent - annual_costs, effective_purchase_price)

        details[listing_id] = {
            "price_vs_comp_inputs": {
                "listing_price": float(listing.price),
                "comp_median_price": comp_median_price,
                "comp_level": comp_level,
                "cohort_size": len(comparable),
                "fallback_penalty": round(float(fallback_penalty), 4),
            },
            "size_vs_comp_inputs": {
                "listing_floor_size": (
                    float(listing.floor_size) if listing.floor_size is not None else None
                ),
                "listing_ppsqm": listing_ppsqm,
                "comp_median_ppsqm": comp_median_ppsqm,
                "comp_level": comp_level,
            },
            "time_on_market_inputs": {
                "date_posted": listing.date_posted.isoformat() if listing.date_posted else None,
                "days_on_market": days_on_market,
                "stale_inventory_days": stale_inventory_days,
            },
            "feature_value_inputs": {
                "bedrooms": int(listing.bedrooms or 0),
                "bathrooms": float(listing.bathrooms or 0.0),
                "floor_size": float(listing.floor_size) if listing.floor_size is not None else None,
                "calculated_feature_signal": round(float(feature_value), 4),
            },
            "confidence_inputs": {
                "required_fields_present": {
                    "date_posted": listing.date_posted is not None,
                    "floor_size": bool(listing.floor_size and listing.floor_size > 0),
                    "erf_size": bool(listing.erf_size and listing.erf_size > 0),
                    "listing_id": bool(listing.listing_id),
                    "source_site": bool(listing.source_site),
                    "city": bool(listing.city),
                    "province": bool(listing.province),
                    "agent_name": bool(listing.agent_name),
                },
                "calculated_confidence_signal": round(float(confidence), 4),
            },
            "roi_proxy_inputs": {
                "gross_yield_assumption": round(gross_yield, 6),
                "transaction_cost_pct": transaction_cost_pct,
                "vacancy_allowance_pct": vacancy_allowance_pct,
                "maintenance_pct": maintenance_pct,
                "management_pct": management_pct,
                "insurance_pct": insurance_pct,
                "monthly_fixed_costs": round(monthly_fixed_costs, 2),
                "annual_rent": round(annual_rent, 2),
                "annual_costs": round(annual_costs, 2),
                "net_yield": round(net_yield, 6) if net_yield is not None else None,
            },
        }
    return details


def _format_metric_input(value: dict[str, Any]) -> str:
    rows: list[str] = []
    for key, raw in value.items():
        if isinstance(raw, dict):
            nested = ", ".join(f"{k}={v}" for k, v in raw.items())
            rows.append(f"{key}: {nested}")
        else:
            rows.append(f"{key}: {raw}")
    return "<br>".join(html.escape(row) for row in rows)


def _build_details_table_html(records: list[dict[str, Any]]) -> str:
    header_cols = [
        "listing_id",
        "score",
        "price_vs_comp inputs",
        "size_vs_comp inputs",
        "time_on_market inputs",
        "feature_value inputs",
        "confidence inputs",
        "roi_proxy inputs",
    ]
    header_html = "".join(f"<th>{html.escape(col)}</th>" for col in header_cols)
    body_rows: list[str] = []

    for record in records:
        metric_inputs = record.get("metric_inputs", {})
        body_rows.append(
            "<tr>"
            f"<td>{record['listing_id']}</td>"
            f"<td>{record['score']:.2f}</td>"
            f"<td>{_format_metric_input(metric_inputs.get('price_vs_comp_inputs', {}))}</td>"
            f"<td>{_format_metric_input(metric_inputs.get('size_vs_comp_inputs', {}))}</td>"
            f"<td>{_format_metric_input(metric_inputs.get('time_on_market_inputs', {}))}</td>"
            f"<td>{_format_metric_input(metric_inputs.get('feature_value_inputs', {}))}</td>"
            f"<td>{_format_metric_input(metric_inputs.get('confidence_inputs', {}))}</td>"
            f"<td>{_format_metric_input(metric_inputs.get('roi_proxy_inputs', {}))}</td>"
            "</tr>"
        )

    return "".join(
        [
            "<h2>Metric Input Audit Table</h2>",
            (
                "<p>Inputs below are the listing datapoints and intermediate values "
                "used for metric calculations.</p>"
            ),
            "<div style='overflow-x:auto;'>",
            (
                "<table border='1' cellspacing='0' cellpadding='6' "
                "style='border-collapse:collapse;font-family:Arial,sans-serif;font-size:12px;'>"
            ),
            f"<thead><tr>{header_html}</tr></thead>",
            f"<tbody>{''.join(body_rows)}</tbody>",
            "</table>",
            "</div>",
        ]
    )


def _build_interactive_chart(
    records: list[dict[str, Any]],
    signal_names: list[str],
    matrix: list[dict[str, Any]],
    output_html: Path,
) -> None:
    fig = go.Figure()

    for row in matrix:
        listing_id = row["listing_id"]
        fig.add_trace(
            go.Bar(
                x=signal_names,
                y=row["signal_scores"],
                name=f"Listing {listing_id}",
                visible=True,
            )
        )

    prices = [record["price"] for record in records]
    scores = [record["score"] for record in records]
    sizes = [12 + (record["confidence"] * 26) for record in records]
    hover_text = [
        (
            f"listing_id={record['listing_id']}<br>"
            f"property_type={record['property_type']}<br>"
            f"location={record['suburb'] or '-'}, {record['city'] or '-'}<br>"
            f"score={record['score']:.2f}<br>"
            f"confidence={record['confidence']:.2f}<br>"
            f"model={record['model_version']}"
        )
        for record in records
    ]
    fig.add_trace(
        go.Scatter(
            x=prices,
            y=scores,
            mode="markers+text",
            text=[str(record["listing_id"]) for record in records],
            textposition="top center",
            marker={"size": sizes},
            hovertemplate="%{customdata}<extra></extra>",
            customdata=hover_text,
            name="Listings",
            xaxis="x2",
            yaxis="y2",
        )
    )

    fig.update_layout(
        title="PropSignal Human Audit: Top 5 Listings",
        barmode="group",
        template="plotly_white",
        height=650,
        width=1300,
        xaxis={"domain": [0.0, 0.58], "title": "Signals"},
        yaxis={"domain": [0.0, 1.0], "title": "Normalized score", "range": [0, 1]},
        xaxis2={"domain": [0.64, 1.0], "title": "Price"},
        yaxis2={"anchor": "x2", "title": "Final score"},
    )
    details_html = _build_details_table_html(records)
    chart_html = fig.to_html(include_plotlyjs="cdn", full_html=False)
    full_html = "".join(
        [
            (
                "<!DOCTYPE html><html><head><meta charset='utf-8'>"
                "<title>PropSignal Top 5 Audit</title></head>"
            ),
            "<body style='margin:18px;font-family:Arial,sans-serif;'>",
            "<h1>PropSignal Human Audit: Top 5 Listings</h1>",
            (
                "<p>Interactive chart + metric input audit table "
                "for explanation concordance checks.</p>"
            ),
            f"{chart_html}",
            f"{details_html}",
            "</body></html>",
        ]
    )
    output_html.write_text(full_html, encoding="utf-8")


def _build_static_image(
    signal_names: list[str],
    matrix: list[dict[str, Any]],
    output_png: Path,
) -> None:
    x = np.arange(len(signal_names))
    width = 0.8 / max(len(matrix), 1)
    _, ax = plt.subplots(figsize=(14, 7))

    for i, row in enumerate(matrix):
        ax.bar(
            x + i * width - 0.4 + width / 2,
            row["signal_scores"],
            width=width,
            label=f"Listing {row['listing_id']}",
        )

    ax.set_title("Top 5 Listings: Signal Comparison")
    ax.set_xticks(x)
    ax.set_xticklabels(signal_names, rotation=20, ha="right")
    ax.set_ylim(0, 1)
    ax.set_ylabel("Normalized score")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    plt.tight_layout()
    plt.savefig(output_png, dpi=180)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate top-listings audit visualization for a scoring job."
    )
    parser.add_argument("--job-id", type=int, default=5)
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    records = _load_top_listings(job_id=args.job_id, limit=args.limit)
    if not records:
        raise SystemExit(f"No score results found for job_id={args.job_id}.")

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_html = output_dir / f"job_{args.job_id}_top{args.limit}_audit_interactive.html"
    output_png = output_dir / f"job_{args.job_id}_top{args.limit}_signals.png"

    signal_names, matrix = _signal_matrix(records)
    if not signal_names:
        raise SystemExit("No signals found in explanation payload.")

    metric_inputs = _compute_audit_inputs(job_id=args.job_id, records=records)
    for record in records:
        record["metric_inputs"] = metric_inputs.get(int(record["listing_id"]), {})

    _build_interactive_chart(records, signal_names, matrix, output_html)
    _build_static_image(signal_names, matrix, output_png)

    print(f"Interactive chart: {output_html.resolve()}")
    print(f"Static image: {output_png.resolve()}")
    print("Top listings included:")
    for record in records:
        print(
            f"- listing_id={record['listing_id']}, "
            f"score={record['score']:.2f}, confidence={record['confidence']:.2f}"
        )


if __name__ == "__main__":
    main()
