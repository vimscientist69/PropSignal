# 🏠 Real Estate Deal Intelligence Platform (Full System)

## 🎯 Goal

Build a **production-grade data intelligence system** that transforms large-scale real estate listing datasets into **high-quality investment opportunities** using advanced scoring, analytics, and a clean, interactive dashboard.

This project focuses on:
- processing **large datasets (10k–100k+ listings)** reliably  
- generating **actionable investment insights at scale**  
- demonstrating **real-world data engineering, backend systems, and UI quality**  
- enabling **high-value outreach after system maturity**

---

## 📚 How to Use This Document

- This file is the **master roadmap and execution reference**.
- Detailed companion docs:
  - Week 2 concept explanations: `docs/week2-advanced-scoring-explained.md`
  - Evaluation protocol and promote/revert gates: `docs/evaluation-review-protocol.md`
  - Principal audit findings and gaps: `docs/project-note-principal-audit.md`
  - MVP performance strategy: `docs/mvp-performance-plan.md`
  - Current status and kickoff checklist: `docs/current-project-status.md`
- If any guidance conflicts, use this precedence:
  1. implementation safety and data integrity
  2. investor decision usefulness
  3. delivery scope control (finish in <1 month)

---


# 🧩 Product Vision

## Core Idea

A system that outputs:

> “Top Investment Opportunities in [City] — Ranked, Explained, and Backed by Market Data”

Each deal is:
- underpriced vs comparable listings  
- showing seller pressure (time on market, price behavior)  
- evaluated using **multi-factor scoring across all metadata fields**  
- supported by **market analytics and visual insights**

---

# 📥 Input

## Supported Inputs

- PropFlux dataset (primary source)
- CSV / JSON uploads

## Large-Scale Dataset Requirement

- validated on:
  - 10,000+ listings (minimum target)
  - multiple locations / segments
- supports batch ingestion + processing

---

## Full Metadata Support

- price  
- location (city, suburb, region)  
- bedrooms, bathrooms  
- property type  
- listing date / age  
- price history (if available)  
- size (floor / erf)  
- features (garage, pool, etc.)  
- agent / agency (optional)  

---

# 📤 Output

## 1. Ranked Deal Feed (Dashboard)

- sorted by score  
- filterable and searchable  
- updated per dataset  

---

## 2. Exportable Reports

- CSV  
- JSON  
- structured PDF reports  

---

## Listing Output Fields

- `title / address`
- `price`
- `estimated_value`
- `price_per_sqm / room`
- `days_listed`
- `score (0–100)`
- `confidence`
- `deal_reason`

---

# 🧠 Core Features

## 1. Advanced Dynamic Scoring Engine

### Score = Multi-Factor Weighted Model

```text
Score = f(price_deviation, time_on_market, feature_value, liquidity, confidence)
````

---

### **Price Intelligence**

- clustering by:
    - location
    - property type
    - bedroom count
    
- compute:
    - average price
    - price deviation (%)
    - price per sqm / room

---

### **Time-Based Signals**

- days on market
- stale inventory detection
- listing age vs area baseline

---

### **Feature-Based Valuation**

- normalize:
    - bedrooms / bathrooms
    - size metrics
- compute:

```
relative value vs comparable listings
```

---

### **Liquidity / Demand Signals**

- listing duration vs market average
- inferred demand pressure

---

### **Confidence Score**

- based on:
    - data completeness
    - variance in comparables
    - signal consistency

---

## **2. Deal Explanation Engine**

Each deal includes clear reasoning:

```
Score: 84

Reason:
- 14% below comparable listings
- Listed 102 days (above area avg)
- High price-per-sqm advantage
- Strong feature-to-price ratio
```

---

## **3. Configurable Scoring System**

```
/config/scoring.yaml
```

Supports:

- adjustable weights
- toggling signals
- experimentation across datasets

---

## **3A. LLM-Assisted Listing Intelligence (Optional, Post-Baseline)**

Objective:
- extract additional high-signal variables from unstructured listing descriptions
- improve score representativeness for real purchasing decisions
- preserve explainability with structured, auditable feature outputs

Candidate LLM-derived variables:
- seller urgency language intensity
- hidden condition/renovation risk indicators
- amenity quality and property condition cues
- contextual location quality signals not present in structured fields
- risk flags (legal, disclosure, or unusual wording)

Integration model:
- run LLM enrichment as an optional pre-scoring feature extraction stage
- persist extracted outputs as structured features
- incorporate features as additional weighted scoring signals
- keep deterministic fallback scoring when LLM is unavailable

Validation gate (required before default enablement):
- compare baseline vs LLM-augmented scoring on labeled evaluation slices
- measure high-score precision uplift and false-positive rate impact
- enable by default only when improvements are consistent and material

---

## **4. Data Analytics & Visualization (HIGH PRIORITY)**

### **Dashboard Analytics**

Provide deep insights into the dataset:

#### **Market Overview**
- price distribution histograms
- listings per location
- property type distribution

#### **Pricing Intelligence**
- average price per area
- price vs bedrooms scatter plots
- price per sqm trends

#### **Time & Liquidity**
- days-on-market distribution
- stale listing heatmaps
- listing velocity indicators

#### **Deal Insights**
- score distribution
- top deals per location
- correlation between features and pricing

---

### **Visualization Requirements**
- interactive charts
- responsive filtering
- real-time updates per dataset
- clear, business-focused insights

---

## **5. Interactive Dashboard**

### **Requirements**
- consistent, high-quality UI design
- reusable component system
- fast rendering for large datasets

---

### **Features**

- deal ranking table
- filters:
    - price range
    - score threshold
    - location
- analytics views (charts & graphs)
- search functionality
- export actions

---

## **6. API Layer**

Endpoints:

```
GET /deals
GET /deals/{id}
POST /upload
POST /jobs
GET /analytics
```

Responsibilities:
- data ingestion
- scoring execution
- analytics computation
- results delivery

---

## **7. Data Pipeline**

- ingestion → normalization → grouping → scoring → analytics → output
- optimized for batch processing
- handles large datasets efficiently

---

# **⚙️ Architecture**

```
/backend
    api/
        routes.py
        jobs.py

    services/
        scoring.py
        grouping.py
        metrics.py
        reasoning.py
        analytics.py

    core/
        parser.py
        normalizer.py

/frontend
    dashboard/

config/
    scoring.yaml

/output
    deals.csv
    deals.json

runner.py
README.md
```

---

# **🛠 Tech Stack**

- Python 3.11+
- FastAPI
- pandas / numpy
- PostgreSQL (recommended for scale)
- Next.js + React
- charting (Recharts / similar)
- Docker
- Fly.io (backend deployment)

---

# **🧪 Engineering Improvements**

## **1. High-Quality UI System**

- consistent design system
- reusable components
- strong UX focus

---

## **2. Testing Strategy**

- unit tests (scoring + analytics)
- integration tests (pipeline)
- UI tests (core flows)

---

## **3. Deployment**

- backend on Fly.io
- frontend on Vercel
- environment config + secrets management

---

## **4. Software Engineering Best Practices**

- modular architecture
- type-safe code
- clear separation of concerns
- logging + monitoring
- performance optimization for large datasets

---

# **🚀 Execution Plan (2–4 Weeks)**

## **Scope Control (Finish in < 1 Month)**

Must-have before release:
- accurate ingestion + normalization
- baseline + advanced scoring that is explainable
- analytics + API + usable dashboard
- deployment + validation on 10k+ listings
- MVP performance standards for 10k+ datasets and multi-dataset ranking selection

High-ROI additions (time-boxed, no indefinite expansion):
- local comparables refinement (location/type/bedroom segmented medians)
- rental-yield and transaction-cost adjustments
- LLM feature extraction prototype (optional, gated)
- configurable investor strategy modes (rental/resale/refurbishment/balanced) in dashboard + API
- rich per-listing explanation payload for auditability and investor decision support

Deferred unless core goals are already complete:
- multi-provider external data integrations beyond one high-impact source
- broad geospatial or macroeconomic modeling
- extensive experimentation not tied to measurable precision uplift

---

## **Week 1**

- data ingestion + normalization
- baseline scoring
- dataset validation

---

## **Week 2**

### **Goal**

Ship an **ROI-first, explainable advanced scoring system** that improves ranking quality over the Week 1 baseline by:
- using **micro-comparables** (location/type/bed/bath segment medians, not a single dataset median),
- adding **rental yield + transaction-cost adjustments** (net-ish ROI proxy),
- producing a **reasoning/explanations payload** for every score (so results are inspectable),
- adding an **analytics engine** that can quantify scoring quality and data health,
- integrating **LLM enrichment** in a controlled, measurable way (only if it improves outcomes).

### **Deliverables (Week 2)**

#### **2.1 Advanced scoring system (v2)**

- **Micro-comps pricing signals**
  - Compute segmented medians / distributions for:
    - `province/city/suburb` (use the deepest level with enough samples)
    - `property_type`
    - `bedrooms`, `bathrooms` (bucketed)
  - Add fallbacks when segment sample size is too small (e.g., suburb → city → province → global).
  - Replace baseline “single median” price deviation with:
    - **price_vs_comp_median** (price deviation within the best-available segment)
    - **price_per_sqm_vs_comp_median** (if floor_size available)

- **ROI proxy signals**
  - **Transaction-cost adjustment**
    - Upfront costs modeled as configurable % or fixed schedule (kept in config).
    - Optional LLM-assisted extraction path:
      - infer additional upfront-cost signals from listing fields + description text
      - emit `upfront_cost_estimate`, `cost_drivers`, and `confidence`
      - use only when confidence is above threshold, otherwise fallback to deterministic config assumptions
  - **Net yield proxy**
    - Use available fields (`rates_and_taxes`, `levies`) + configurable assumptions:
      - vacancy allowance %, maintenance %, management %, insurance (optional)
    - Rent estimation approach for Week 2:
      - **Phase 1 (required):** heuristic rent estimate (config-driven by `property_type`, `bedrooms`, `city/province` buckets)
      - **Phase 2 (optional):** upgrade rent estimate via LLM/external data only if Phase 1 is weak
  - Add a yield-derived score component such as:
    - **net_yield_signal** and **payback_signal** (optional, time-boxed)

- **Liquidity & risk adjustments**
  - Keep time-on-market but improve it:
    - use `date_posted` where available
    - add a **stale inventory non-linear curve** (e.g., diminishing returns after N days)
  - Penalize low-confidence or missing-critical-fields in a consistent way:
    - separate **data_confidence** (completeness) from **investment_risk** (flags like auction/private seller if used)

- **Scoring versioning**
  - Output `model_version="advanced_v2"` (keep baseline runnable side-by-side).
  - Ensure scoring is **idempotent** per job (overwrite results like Week 1).

#### **2.2 Reasoning engine (explainability)**

- Persist a structured explanation per listing score:
  - top contributing signals with raw values and normalized scores
  - “why this was ranked high/low”
  - confidence and missing-field notes
- Output target:
  - a single `deal_reason` string (short)
  - plus a structured `explanation` JSON blob (machine-readable) for later UI.

#### **2.3 Analytics engine (quality + insight)**

- Implement job-level analytics for:
  - score distribution (histogram bins, min/max/median, percentiles)
  - top-N listing summaries (score + key drivers)
  - missingness report for key fields that affect scoring
  - comps coverage report: what % of listings got suburb-level comps vs city/province/global
- Add “ranking quality checks” (offline):
  - sanity checks for pathological outcomes (e.g., missing price scored too high)
  - stability checks when changing weights (top-N overlap)

#### **2.4 LLM enrichment prototype (Week 2)**

- **Purpose:** extract high-value structured variables from `description` to improve scoring.
- **Candidate variables (minimal set):**
  - condition/renovation level (e.g., “newly renovated”, “needs TLC”)
  - security/amenities not reliably structured (pool, inverter/solar, etc.)
  - rental hints (furnished, “investment”, “tenant in place”) as weak signals
  - upfront-cost hints (legal/levy/special conditions) for ROI proxy refinement
- **Integration approach (controlled):**
  - store derived fields in a separate enrichment payload (do not overwrite canonical listing fields)
  - feed enrichment into scoring only behind an **experiment flag**
- **Week 2 validation gate (must pass to enable by default):**
  - improves top-N deal quality on offline evaluation metrics (see 2.5)
  - does not significantly increase invalid/low-confidence scores

#### **2.5 Evaluation + gates (scope control)**

- Add a lightweight offline evaluation process:
  - compare baseline_v1 vs advanced_v2 on:
    - top-N stability and reason diversity
    - fewer “unknown / missing data” in top ranks
    - comps coverage improvements
    - yield proxy sanity (high yield not correlated with missing price)
- **Decision gates:**
  - only ship LLM-influenced scoring as default if it improves metrics and is stable
  - otherwise keep LLM enrichment stored but not used in ranking

### **Suggested implementation order**

- Build micro-comps computation + comp-based pricing signals
- Add ROI proxy (transaction costs + net yield)
- Add reasoning payload format
- Add analytics summaries + evaluation scripts
- Add LLM enrichment prototype + validation gate

---

## **Week 3**

### **Goal**

Turn PropSignal into a **configurable investor decision tool** where users can:
- upload/select a dataset,
- apply location + quality filters,
- choose an investment strategy mode,
- and receive ranked listings with detailed per-listing diagnostics.

### **Deliverables (Week 3)**

#### **3.1 Dashboard product functionality (strategy-driven ranking)**

- Dataset handling:
  - upload/select dataset source/s
  - view job status and validation summary
- Filter controls:
  - change selected data source/s (allow more than one data source selected at once for merging, useful select all, unselect all data sources)
  - province/city/suburb
  - budget range
  - property type / bed / bath
  - confidence threshold
- Strategy presets:
  - rental income focus
  - resale/arbitrage focus
  - refurbishment/value-add focus
  - balanced long-term hold
- Preset behavior:
  - each preset maps to weight profiles and signal toggles
  - users can optionally fine-tune weights within safe bounds

#### **3.2 Backend revamp to support strategy tool behavior**

- API additions:
  - endpoint(s) for ranking requests with filter + strategy payload
  - endpoint(s) for listing detail diagnostics
  - endpoint(s) for scoring profile definitions and defaults
- Service-layer additions:
  - query/filter pipeline for selected dataset segments
  - scoring profile resolver (preset -> config)
  - optional re-score on demand for filtered subset
- Persistence additions:
  - save ranking run metadata (dataset, filters, strategy, score version)
  - save per-listing explanation payload for UI retrieval
- Performance requirements:
  - indexed query paths for core filters
  - pagination and top-N optimized retrieval
  - asynchronous processing for heavy jobs (ingestion/scoring/validation)
  - freshness metadata (`last_ingested_at`, `last_scored_at`, `model/profile version`)

#### **3.3 CLI revamp to mirror backend/dashboard capability**

- Add CLI command(s) for strategy-based ranking runs, for example:
  - run ranking with dataset + filters + strategy preset
  - export top-N detailed diagnostics
- Add CLI support for profile inspection:
  - list strategy profiles
  - show resolved weights/signals for a selected profile
- Keep CLI and API behavior aligned (same validation rules and scoring profile resolution).

#### **3.4 Rich per-listing detail output (beyond reason strings)**

- Keep concise `deal_reason` string for quick scan.
- Add structured detail payload for each ranked listing:
  - full signal breakdown (raw + normalized + weighted contribution)
  - comps segment used and fallback path
  - ROI assumptions used (rent estimate, costs, yield proxy components)
  - risk/confidence flags
  - model/profile/version metadata
- Ensure this payload is available in:
  - API listing detail response
  - dashboard detail panel
  - CLI detailed export

#### **3.5 Decision gates and rollout**

- decision gate: enable LLM-derived scoring signals by default only if Week 2 validation improves deal-quality metrics
- optional: integrate one high-impact external data source only if it improves precision on top-ranked deals
- keep deterministic fallback path as default if LLM enrichment confidence or quality is insufficient

---

## **Week 4**

### **Goal**

Harden the system for real-world use by running structured validation on real datasets, tuning core engines based on evidence, and documenting repeatable feedback loops.

### **Deliverables (Week 4)**

#### **4.1 Real-dataset validation testing**

- Run end-to-end validation on representative real datasets (including larger 10k+ samples when available).
- Produce a validation report for each run with:
  - ingestion quality (`valid/invalid`, rejection reasons, schema drift)
  - scoring quality (distribution, top-N sanity, outlier behavior)
  - explanation quality (reason clarity + signal consistency)
  - analytics usefulness (can users understand and act on results)
- Include manual audit slices:
  - review top 20, middle 20, bottom 20 ranked listings
  - verify that score drivers align with investor intuition and data reality.

#### **4.2 Tuning and enhancement cycles**

- Use validation findings to tune:
  - scoring weights and signal formulas
  - reasoning output format and detail quality
  - analytics summaries and diagnostics
- Define a controlled iteration protocol:
  - change one tuning bundle at a time
  - compare against previous baseline
  - keep only changes with measurable uplift.

#### **4.3 Business-problem fitness checks**

- Verify that system output is genuinely useful for investor decisions:
  - ranking quality by strategy mode (rental/resale/refurbishment/balanced)
  - reduced false-positive “good deals” in top-N
  - improved explainability and trust for end users.
- Add acceptance gates for release:
  - minimum quality thresholds per strategy profile
  - no major regression in stability/consistency across reruns.

#### **4.4 Performance tuning + deployment readiness**

- Profile high-cost stages (ingestion, scoring, ranking APIs, dashboard queries).
- Optimize bottlenecks (indexes, pagination paths, batch operations).
- Complete deployment checklist (env config, observability, rollback path, smoke tests).
- Use `docs/mvp-performance-plan.md` as the implementation checklist and SLO reference.

#### **4.5 Documentation pack (operator + analyst guidance)**

- Create practical docs for:
  - how to run validation on a new real dataset
  - how to interpret outputs and detect weak signals
  - how to tune scoring/reasoning/analytics safely
  - how to run iteration loops and record decisions
  - how to decide go/no-go for enabling LLM-derived signals by default
- Ensure docs include concrete command examples and expected artifacts.

---

# **💰 Outreach Phase (Post-Build)**

## **🎯 Target**

- property investors
- developers
- deal analysts

---

## **📣 Strategy**

- share analytics + deal insights
- provide sample reports
- demo dashboard

---

## **💬 Message**

```
Hi, I built a system that analyzes large-scale property data and identifies high-value investment opportunities using market-based scoring and analytics.

Happy to share a few insights if you're interested.
```

---

# **🔁 Feedback Loop**

Collect:
- insight usefulness
- accuracy perception
- analytics clarity

Iterate:
- scoring formulas + weights (based on validation evidence, not intuition only)
- reasoning payload clarity and usefulness
- analytics report utility for investor workflows
- strategy profile defaults and filter presets
- LLM enrichment usage policy (enable/disable thresholds)

### **Iteration cadence**

- Run weekly validation cycle:
  1. ingest and validate latest dataset
  2. score with current profile versions
  3. audit ranked outputs + explanations
  4. tune one controlled change set
  5. compare metrics and decide keep/revert
- Log each cycle’s outcomes and decisions to prevent regressions and drift.

---

# **💼 Portfolio Positioning**

> “A large-scale real estate data intelligence platform that processes and analyzes thousands of listings to identify high-value investment opportunities using advanced scoring and analytics.”

---

# **🎯 Upwork Relevance**

Demonstrates:
- data analysis systems
- large-scale data processing
- scoring / ranking models
- backend APIs
- dashboards + analytics
- ETL pipelines

---

# **✅ Definition of Done**

- validated on large dataset (10k+ listings)
- scoring system stable and accurate
- analytics dashboards fully functional
- system deployed and accessible
- end-to-end pipeline working

---

# **🎯 End Result**

A **production-grade analytics and decision system** that:
- processes large datasets reliably
- generates actionable investment insights
- showcases strong engineering and data skills
- strengthens portfolio and client acquisition

---

# **🧭 Guiding Principles**

- build for scale
- prioritize clarity and usefulness
- design for real-world application
- focus on actionable insights

---

# **🚀 Final Outcome**

A system that proves:

```
You can take large-scale data and turn it into meaningful, decision-ready intelligence.
```