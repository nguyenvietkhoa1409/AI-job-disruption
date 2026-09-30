# BI Dashboard Specification

**Status:** design spec v2, not yet built. **Tool: Power BI Desktop** (decided;
see §0.1). v2 incorporates an external review of v1, checked against
`data/processed/*.csv`, `schema/*.sql` and `src/schema/dimension_maps.py`.
The decision log at the end records what was adopted, changed and rejected.
**Source of truth:** every field/table reference is verified against
`src/schema/star_schema.py` and `schema/*.sql` (4 fact tables, 8 dimension
tables). Anything that does not exist yet is listed under "New SQL objects."
**Scope:** 5 analytic dashboards — (1) Overview, (2) Layoffs, (3)
Role/Creation, (4) Sentiment, (5) Cross-source comparison — plus a
sixth "About the data" page. Visual styling (colors/typography) is a
BI-theme concern and is not covered here.

---

## 0. Cross-dashboard conventions

- **One filter row per dashboard, above everything it scopes.** Never a
  filter embedded in a single chart card.
- **No dual-axis charts.** Measures on different scales never share an axis;
  use small multiples or separate panels.
- **Every percentage or mean has a visible N.** Survey fields are missing on
  27–54% of rows (`AIThreat`, `AISent`, `AIAcc`, `AIOpen`,
  `ConvertedCompYearly`, `RemoteWork`, `Industry`, `Country`). Layoffs has
  its own gaps: `total_laid_off` is ~35% null and `percentage_laid_off` ~37%
  null. Show the non-null N in a tooltip or subtitle.
- **Suppress thin cells.** Any segment with N < 30 is greyed out and labelled
  "N < 30", never drawn with full-confidence styling.
- **Distinguish "no data" from zero.** Sector coverage differs by source
  (see §0.3). Missing combinations render as hatched/"no data", not 0.
- **Color scales:** ordered categories (`experience_level_canonical`,
  `company_size`, `stage`) get an ordinal ramp; unordered categories get fixed
  categorical color; magnitude grids get a single-hue sequential ramp.
  Ramps anchor at 0 (or show deviation from the overall rate), never
  min–max stretched: sector AIThreat rates span only ~10–18%, and a
  stretched ramp would make that look dramatic. Skewed magnitudes
  (US = 71% of layoff headcount) use a rank or log scale.
- **>7 unordered categories become a ranked bar + table, never a pie/donut.**
- **Chart titles state the finding**, written at build time from the frozen
  numbers (the spec uses descriptive names).
- **One source of N.** Every footnote figure is pulled from the warehouse,
  not from notes (the docs currently disagree: survey 49,191 raw / 49,123 in
  text mining / 49,078 in the warehouse; topic rows 15,675 vs 15,698).
- **Table-view twin** for every color-encoded chart.

### 0.1 Tool decision

Power BI Desktop (Windows) covers this spec: field parameters, drill-through
pages, custom Sankey-free visuals. Looker Studio has no multi-page
drill-through. Public sharing is the constraint: to our knowledge Power BI
"Publish to web" requires a work/school account — **verify with the account
actually used**. Plan the portfolio deliverable as a PDF/screenshots, a short
video walkthrough and the `.pbix` file in the repo's release assets (not
committed data).

### 0.2 Comparison window

Layoffs span 2020-03 → 2026-09, AI Jobs only **2025-01 → 2026-03**, and the
Survey is a single 2025 wave. Therefore:

- Dashboards 1 and 5 use a **fixed "2025-01 – 2026-03 comparison window"**
  with a visible label. No date slicer.
- Only Dashboard 2 exposes the full layoff date range.
- AI Jobs posting volume jumps ~5× from Jan 2026 (≈40–68 a month in 2025,
  ≈270–310 a month in 2026). This is a dataset artifact, so **no
  posting-volume time series** is shown anywhere.

### 0.3 Sector coverage (12 sectors, uneven by source)

| Sector | Layoffs | AI Jobs | Survey |
|---|---|---|---|
| Government & Public Sector | none | yes | yes |
| Real Estate | yes | none | none |
| Transportation & Logistics | yes | none | yes |
| the other 9 | yes | yes | yes |

Also: layoffs.fyi tracks tech companies, so its "Retail" means a
retail-*tech* company, whereas AI Jobs and the Survey record the employer's
actual industry. **Footnote this on the sector grid.** "Other" is the second
largest layoff sector by headcount (a catch-all); flag it, and exclude it
from ranked-sector callouts.

---

## Dashboard 1 — Overview

**Purpose:** connective tissue. Shows the three datasets side by side on the
two dimensions they share, `industry_sector` and (restricted)
`country_canonical`. No cross-source analysis here; that is Dashboard 5.
Fixed window per §0.2.

### KPI row

| Tile | Source | Metric |
|---|---|---|
| Total layoffs | `fact_layoff_event` | `SUM(total_laid_off)`, subtitle: N events with headcount disclosed |
| Layoff events | `fact_layoff_event` | `COUNT(*)` |
| AI job postings | `fact_job_posting` | `COUNT(job_id)` |
| Survey responses | `fact_survey_response` | `COUNT(response_id)` |
| AI-threat rate | `fact_survey_response` + `dim_ai_sentiment` | `% AIThreat = 'Yes'` of answered, footnote N |

### Figure 1 — Sector grid (main figure)

Heatmap-style matrix, rows = 12 `industry_sector`, three column blocks
(Layoffs / Creation / Sentiment), each with its own single-hue ramp anchored
per §0. Missing combinations follow §0.3 (hatched "no data").

| Block | Metric | Source |
|---|---|---|
| Layoffs | `SUM(total_laid_off)` or event count | `fact_layoff_event` ⨝ `dim_industry` |
| Creation | `COUNT(job_id)` | `fact_job_posting` ⨝ `dim_industry` |
| Sentiment | `% AIThreat = 'Yes'` + N | `fact_survey_response` ⨝ `dim_ai_sentiment` ⨝ `dim_industry` |

Footnote: sector taxonomy differs by source (§0.3). Raw values visible on
hover and in the table twin.

### Figure 2 — Geography grid

Rows = the 14 AI-Jobs countries + "Multi-region / Remote". Same 3 blocks.
Layoff color uses a **rank or log scale** (US = 71% of headcount).
"Multi-region / Remote" sentiment is suppressed if N < 30 (Survey "Nomadic"
is a handful of respondents).

| Block | Metric | Source |
|---|---|---|
| Layoffs | `SUM(total_laid_off)` | `fact_layoff_event` ⨝ `dim_country` |
| Creation | `COUNT(job_id)`; median salary as a toggle | `fact_job_posting` ⨝ `dim_country` |
| Sentiment | `% AIThreat = 'Yes'` + N | `fact_survey_response` ⨝ `dim_ai_sentiment` ⨝ `dim_country` |

### Filters
Continent (`dim_country.continent`). No date filter (fixed window).

### Actions
Click a sector or country row → **drill-through to Dashboard 5**, pre-
filtered. A click on a no-data cell does nothing.

---

## Dashboard 2 — Layoffs ("what is being cut")

**Purpose:** full depth on `fact_layoff_event` alone. The only dashboard with
the full date range (2020-03 → 2026-09).

### KPI row
Total laid off (+ N with headcount), events, **shutdown events**
(`percentage_laid_off = 1`; 373 events, 8%), median `percentage_laid_off`
(+ N non-null).

### Figures

| Figure | Form | Fields | Notes |
|---|---|---|---|
| Layoff trend | Line by `month_start` | `mart_country_industry_month` rolled up | Responds to every page filter. Annotate **ChatGPT launch (Nov 2022)** worded as *context, not cause* (2022–23 cuts are commonly attributed to overhiring and interest rates). Small multiples by continent, not spaghetti. |
| Geographic distribution | Choropleth, rank or log scale | `country_canonical`, `SUM(total_laid_off)` | US is 71% of headcount |
| Sector breakdown | Ranked horizontal bar | `industry_sector`, `SUM(total_laid_off)` | Flag "Other" as a catch-all |
| Stage vs. severity | Bar, ordinal ramp, N per bar | `stage` (Seed → Series J → Post-IPO), **median `percentage_laid_off`** | Replaces "avg funds raised by stage" (near-tautological). Early stages cut a far larger share (Seed median 100%, Post-IPO 10%). `percentage_laid_off` is stored 0–1. |
| Largest events & repeat offenders | Table, sortable | `company_name`, event count, total laid off, top events | Natural key is `(company, date, location)`, so repeat companies are expected, not duplicates. Top 10 events ≈ 16% of headcount, so not dominant. |

Deferred (not in v2): absolute-vs-relative severity scatter; share of
layoffs by grouped stage per year.

### Technique notes
- `date` needs parsing to a true date type; use `month_start`.
- **Null headcount:** 35% of events have no `total_laid_off`, including 285 of
  the 373 shutdowns. Sums therefore undercount exactly the most severe events.
  Footnote on every headcount chart, and show "events with headcount".
- Roll-up of percentages uses `SUM(pct)/non-null count`, never an average of
  monthly averages.

### Filters
Date range, `country_canonical`, `industry_sector`, `stage`,
shutdown-only toggle.

### Actions
Click a country → cross-filters the sector bar and company table (same-page).
Optional drill-through from the sector bar to Dashboard 5.

---

## Dashboard 3 — Role & Creation ("what is being created")

**Purpose:** AI Jobs in full, plus the Survey fields that feed `dim_role`
(`DevType`, `Industry`). The "emerging vs traditional salary comparison" is
inherently cross-dataset.

### The confound (read first)
`role_category` is confounded with dataset: all 25 AI Jobs titles are
"Emerging" by dataset scope, so `(job_title, Traditional)` cannot exist.
Only **three** salary series are non-empty: AI Jobs (posted, synthetic),
Survey Emerging (2 DevTypes, self-reported) and Survey Traditional
(self-reported). The only like-for-like comparison is **Survey Emerging vs
Survey Traditional**.

### Figures

| Figure | Form | Fields | Notes |
|---|---|---|---|
| **Headline: Emerging vs Traditional salary** | Grouped bar, **median**, N per bar | Survey `converted_comp_yearly_winsorized` by `role_category` | Default **US-only** (Emerging N ≈ 103, Traditional ≈ 5,100), toggle to all countries (Emerging N ≈ 464). Mean salary across countries mostly measures country mix. **AI Jobs posted salary shown as a labeled reference band, "synthetic, illustrative."** |
| Salary by seniority | Small multiples by `experience_level_canonical` | + AI Jobs reference | Survey Emerging cells with N < 30 are suppressed (US-only cuts get thin fast) |
| LLM-role premium | Bar | `is_llm_role` within AI Jobs | AI Jobs-only; 327 LLM vs 1,173 other |
| Metric switcher (field parameter) | Bar by `job_category` | `demand_growth_yoy_pct` (e.g. ML Ops ≈ 53% vs ≈ 17% typical), `ai_salary_premium_pct`, `demand_score`, `benefits_score_10`, `annual_salary_usd` | Replaces the job-category *count* chart (counts reflect dataset construction, not the market) |
| Skill × job_category heatmap | Heatmap, ≈ 20 skills × 12 categories, % of postings with skill | `fact_job_posting_skill` ⨝ `dim_skill` ⨝ `dim_role` | Shows the per-role skill pools the Apriori run found. The network stays a static report figure. |
| Skill leaderboard | Ranked bar + table | `skill_name`, `AVG(demand_score)` | |
| Company size / education premium | Small multiples inside the switcher | `company_size` (ordinal, ≈ $168k → $238k), `education_required` | Remote-work premium is **cut**: flat (≈ $193–198k). |

### Technique notes
- **Persistent footnote on every AI Jobs salary figure:** `annual_salary_usd`
  exceeds `salary_max_usd` on 19.2% of rows (synthetic noise, directional
  only). AI Jobs is a curated illustration, not a live scrape.
- `converted_comp_yearly_winsorized` is already winsorized; do not re-clip.
- Skills come in role-specific pools, so there is no "salary with vs without
  a skill" view (it would measure the role, not the skill).

### Filters
`role_source`, `role_category`, `experience_level_canonical`,
`country_canonical` (default US), `industry_sector`, `company_size`,
`is_llm_role`.

### Actions
Click a skill → cross-filters the AI Jobs panels. The metric switcher counts
as an action.

---

## Dashboard 4 — Sentiment ("how practitioners feel")

**Purpose:** Survey AI-attitude fields, `JobSat` and the `AIOpen` topic
output. The survey is **one wave (2025)**, so this is a sentiment *profile by
cohort*, not a trend; `survey_year` gives no time axis. Attitudes are
largely uniform across cohorts (AIThreat "Yes" ≈ 14–15% across experience
levels and most age groups), so the page states findings honestly,
including "no cohort effect."

### KPI row
`% AIThreat = 'Yes'`, mean `AISent` (1–5, `Unsure` excluded), mean `AIAcc`
(1–5), `% AISelect` adoption, `AVG(job_sat)`; each with its non-null N.

### Figures

| Figure | Form | Fields | Notes |
|---|---|---|---|
| Sentiment shape | Diverging stacked bar centered on neutral | `AISent` full distribution | Shows bimodality a mean hides |
| Sentiment by cohort | Small multiples | `AIThreat`, `AISent` × `experience_level_canonical`, × `age_bucket` | Replaces the "trend"; expect it to be nearly flat |
| Emerging vs Traditional respondents | Bar + N | `AIThreat` × `role_category` | ≈ 19.8% (Emerging, N ≈ 738) vs ≈ 14.8% (Traditional) — only 2 DevTypes in Emerging, so label it |
| AIThreat by DevType | Ranked bar | `DevType`, `% Yes` | Only roles with N ≥ 30 |
| Use vs trust | Heatmap | `AISelect` × `AIAcc` | |
| JobSat vs AI threat | Bar, 3 categories | `AIThreat`, `AVG(job_sat)` | |
| Topic frequency | Ranked bar, colored by **topic kind** | `dim_ai_open_topic.topic_label`, count | Tag each of the 10 NMF topics as **skill** or **stance**. "AI capability skepticism" and "Skills will remain valuable (generic)" are opinions, not skills. Subtitle N: answers of ≤ 4 words have no topic. |
| Topic × role / threat | Grouped or stacked bar, ≤ 3 series | `topic_label` × `role_category` or `AIThreat` | Lives here only (not on Dashboard 5) |

**Cut:** sentiment by sector/country (duplicates Dashboard 1's sentiment
column).

### Technique notes
- `AISent`/`AIAcc` 1–5 encoding is a `CASE WHEN` in the SQL view, not a new
  warehouse column.
- Topic kind (skill/stance) lives in the view, keyed on topic label; revisit
  whenever `MODEL_VERSION` in `survey_feature_engineer.py` changes.
- Every tile shows N; any segment < 30 is suppressed (§0).

### Filters
`role_category`, `experience_level_canonical`, `country_canonical`,
`industry_sector`, `age_bucket`, `ed_level`, `main_branch`.

### Actions
Click a topic bar → filters the cohort panels to respondents in that topic
(same-page). Toggle switches the KPI/color metric between `AIThreat`,
`AISent` and `AIAcc`.

---

## Dashboard 5 — Cross-source comparison

**Purpose:** figures that need two or more fact tables, shown as
*juxtaposition*, never as a flow. Drill-through destination from
Dashboard 1. Fixed window per §0.2.

**Replaces the v1 "new opportunity" Sankey.** No individual-level join exists
between a layoff and a posting (`fact_layoff_event` has no `role_key`). A
Sankey would imply movement the data cannot support, and its right-hand side
collapsed to one node because every AI Jobs role is "Emerging". The
`is_llm_role`, `salary_tier` and `experience_level_canonical` alternatives
were each rejected (see decision log).

### Figures

| Figure | Form | Fields | Question |
|---|---|---|---|
| **Sector share gap** | Diverging bar | Sector's % of layoff headcount minus its % of AI postings | Which sectors lose more than they gain, relative to the others? Computed **only over the 9 sectors present in both sources**; shares renormalized over those 9. Footnote the exclusions (Government, Real Estate, Transportation). Title must not imply people moved between sectors. |
| Sector scatter (descriptive) | Scatter, ≤ 9 points | x = layoff headcount, y = sector `% AIThreat`, size = postings | Labeled **"descriptive, not correlational"**: too few points, and the AIThreat spread is ≈ 10–18%. Sectors with survey N < 30 suppressed. |

Topic × role/threat is on Dashboard 4 only. The geographic scatter is
dropped.

### Filters
Inherits the drill-through context from Dashboard 1; freestanding default =
all 9 shared sectors.

### Actions
Destination page; no onward navigation.

---

## Dashboard 6 — About the data & pipeline health

**Purpose:** consolidate the caveats and show the data-engineering side.

- **Limits panel:** layoffs.fyi is tech-company-only; AI Jobs is curated and
  illustrative (synthetic salaries, 2026 volume step); the Survey is a single
  self-selected wave (~38% tech) with 27–54% missingness; sector taxonomies
  differ by source (§0.3).
- **Pipeline-health strip:** rows ingested vs quarantined per source and last
  refresh time, from `pipeline_run_log`.
- **Row counts from the warehouse**, the single source of N (§0).

---

## Interactive-technique summary

| Technique | Where used |
|---|---|
| Per-dashboard filter row | Every dashboard |
| Fixed comparison window (labelled) | Dashboards 1, 5 |
| Same-page cross-filtering | D2 (country → sector bar + table), D3 (skill → AI Jobs panels), D4 (topic → cohorts) |
| Drill-through (page → page, carries context) | D1 → D5 |
| Field-parameter metric switcher | D3 (job-category metrics), D4 (AIThreat/AISent/AIAcc) |
| Calculated field (Likert → numeric, topic kind) | D4 |
| Per-column anchored heatmap scales, rank/log scale | D1 grids, D2 choropleth |
| "No data" vs zero rendering; N < 30 suppression | D1, D3, D4, D5 |
| Annotation layer (context, not cause) | D2 trend |
| Table-view twin | Every color-encoded chart |

---

## New SQL objects needed (build checklist)

| Object | Grain | Feeds |
|---|---|---|
| `mart_country_industry_month` (**supersedes `mart_country_month`**) | `country × industry_sector × stage × month_start` | D2 trend and filters. Columns: `month_start DATE`, `layoff_events`, `total_laid_off_sum`, `events_with_headcount`, `pct_laid_off_sum`, `pct_laid_off_nonnull_count`, `shutdown_events`. Sums and counts, not averages, so roll-ups are correct. Keep the unique index for `REFRESH ... CONCURRENTLY`. |
| `mart_industry_overview` (includes sentiment) | `industry_sector` | D1 sector grid; D5 |
| `mart_country_overview` (14 countries + Multi-region) | `country_canonical` | D1 geography grid |
| `mart_sector_share_gap` | `industry_sector` (9 shared) | D5 share gap |
| `vw_role_salary` | `role_source × role_category × experience_level_canonical × country` with N | D3 headline |
| `vw_skill_leaderboard`, `vw_skill_category` | `skill`, `skill × job_category` | D3 |
| `vw_sentiment_profile` | `experience × age × role_category × DevType` with N | D4 |
| `vw_topic_cross` (with topic kind) | `topic × role_category / AIThreat` | D4 |
| `pipeline_run_log` | `run × source` (ingested, quarantined, timestamp) | D6 |

**Removed:** `mart_industry_role_flow` (was the Sankey's feed).

---

## Known caveats to carry through

- `role_category` is confounded with dataset source. Never show a pooled
  Emerging-vs-Traditional bar; the like-for-like comparison is within the Survey.
- AI Jobs salaries are synthetic and directional (19.2% of rows above
  `salary_max_usd`). Volume is ~5× higher from Jan 2026.
- AI Jobs covers 14 countries + Multi-region/Remote only.
- Survey fields are missing on 27–54% of rows; Emerging respondents are few
  (N ≈ 464 with compensation). Always show N; suppress N < 30.
- Layoff headcount is 35% null, concentrated in shutdowns; sums undercount.
- Sector taxonomies differ by source; 3 of 12 sectors lack a source.
- Single survey wave: profile by cohort, not a trend.
- No layoff-to-posting linkage exists; nothing on any page shows or implies
  individual transitions.

---

## Decision log (review of v1)

**Adopted:** drop the Sankey for a share-gap bar; Survey-only headline
salary with AI Jobs reference band and US default; sentiment reframed as a
profile; fixed comparison window (corrected to 2025-01 – 2026-03);
`mart_country_industry_month` with sums/counts and `month_start`; sector
taxonomy footnote; Power BI; cut duplicate sentiment, topic and geographic
figures; median % by stage; job-category count → growth/premium; shutdown
KPI, top events, ChatGPT annotation; skill × category heatmap; use vs trust;
DevType ranking; topic kind tags; About page; pipeline strip; single source
of N; rank/log color scales.

**Changed from the review:** window is 2025-01 – 2026-03, not "2025–26";
"job category counts are flat" was false (AI Engineering = 49%) but the chart
is still cut; the cohort view is expected to be flat, stated honestly.

**Rejected:** `is_llm_role` / `salary_tier` / `experience_level_canonical` as
the Sankey's right side (unit mismatch and implied flow persist; experience
is synthetically balanced); layoffs-vs-postings time series (2026 volume
step); remote share gap (5 vs 3 categories, 31% missing); salary with/without
a skill (measures role); belief-vs-demand mapping (manual, over-readable);
remote-work premium (flat); loading earlier survey waves (scope creep).
