# Dimension maps: rationale

Documents the design decisions behind `src/schema/dimension_maps.py`
(`COUNTRY_MAP`, `INDUSTRY_MAP`, `ROLE_MAP`) so a reviewer can see *why* each
mapping was made without re-deriving it. All coverage numbers below were
measured against the real files (`data/raw/layoffs.csv`,
`data/raw/ai_jobs_market_2025_2026.csv`, `data/raw/survey_results_public.csv`)
at the time this was written; they are not enforced by CI since those files
are gitignored.

## COUNTRY_MAP

**Approach:** generated at import time by the `country_converter` package
(ISO 3166 has one unambiguous international standard, and a library exists
specifically for this problem — no reason to hand-write a translation
table). `_RAW_COUNTRIES` in `dimension_maps.py` is the literal, hardcoded
union of every raw value seen across all three datasets' country columns
(188 distinct values), so the module works without the real data files
present (e.g. in CI).

**Coverage:** `country_converter.convert()` resolved 185/188 values
correctly on the first pass, including the genuinely ambiguous cases:

| Raw value | Canonical | Note |
|---|---|---|
| `Congo, Republic of the...` | Congo Republic | |
| `Democratic Republic of the Congo` | DR Congo | correctly kept distinct from the above |
| `Republic of Korea` | South Korea | |
| `Democratic People's Republic of Korea` | North Korea | correctly kept distinct from the above |
| `Russian Federation`, `Russia` | Russia | |
| `USA`, `United States`, `United States of America` | United States | |
| `UK`, `United Kingdom`, `United Kingdom of Great Britain and Northern Ireland` | United Kingdom | |

**3 manual overrides** (`_MANUAL_COUNTRY_OVERRIDES`), the values the library
could not resolve:

- `"UAE"` → `"United Arab Emirates"` — a plain alias gap in the library (the
  full ISO name resolves fine on its own). Not a domain decision, a data fix.
- `"Global"` (AI Jobs Market, **82/1500 rows = 5.5%**) and `"Nomadic"`
  (Survey, 29/49,123 rows = 0.06%) are not real countries — both mean "no
  single country applies." Domain decision: keep both as one explicit
  `"Multi-region / Remote"` bucket rather than silently dropping the rows or
  forcing them into a real country. 82 rows is too large a fraction of the
  AI Jobs dataset to discard quietly.

## INDUSTRY_MAP

**Approach:** manual curation, no library. There is no reliable automated
standard for industry taxonomy loose enough to fit three inconsistently
labeled datasets — the closest real standard (NAICS) has 1000+ codes, far
more granular than useful here. Fuzzy string matching was considered and
rejected: the two largest overlapping values by row count,
`"Software Development"` (Survey, 33.1% of rows) and `"Technology"` (AI
Jobs, 7.1% of rows), refer to the same concept but share almost no
substring — a matcher tuned to catch that pair would produce false
positives elsewhere.

**Taxonomy:** 12 sectors, loosely modeled on NAICS top-level groupings but
sized to what these three datasets actually contain: Finance, Healthcare,
Retail & Consumer, Technology & Software, Manufacturing & Industrial,
Government & Public Sector, Media & Marketing, Education, Real Estate,
Transportation & Logistics, Energy, Other.

**Coverage:** 46 distinct raw values across the three datasets, all mapped
by hand (~1-2 hours of manual review, not automated).

**Notable groupings:**
- `Fintech`, `Banking/Financial Services`, `Insurance` (Survey) + `Finance`
  (Layoffs, AI Jobs) → `Finance`.
- `Software Development`, `Computer Systems Design and Services`,
  `Internet, Telecomm or Information Services` (Survey) + `Technology`
  (AI Jobs) + `AI`, `Crypto`, `Data`, `Hardware`, `Infrastructure`,
  `Security` (Layoffs) → `Technology & Software`. Layoffs' `"AI"` industry
  is only 35/4600 rows (0.8%) — too small to justify its own sector, and
  it doesn't recur in the other two datasets' industry columns, so it is
  not treated as a cross-cutting category.
- `"Other"` (Layoffs) is a deliberate catch-all covering low-frequency,
  ambiguous raw categories that don't fit the other 11 sectors cleanly:
  `HR`, `Legal`, `Product`, `Recruiting`, `Sales`, `Support` (Layoffs),
  `Consulting`, `Research` (AI Jobs), `"Other:"` (Survey, note the raw
  trailing colon — kept as a distinct dict key from Layoffs' `"Other"`
  since that's how it literally appears in the source data). Combined this
  covers roughly 10-16% of any one dataset's rows — a legitimate catch-all
  size, not the majority.

## ROLE_MAP

**Approach:** deliberately narrow in scope. The only analysis question in
scope (per the BI dashboard requirement) is "emerging vs traditional role
salary comparison," so `ROLE_MAP` is a binary `role_category`
(`"Emerging"` / `"Traditional"`), not a full occupation taxonomy like
O*NET-SOC — that would be over-engineering for a question this narrow.
Layoffs has no role-level column, so it is out of scope for this map.

**AI Jobs (`job_title`, 25 values): all "Emerging."** This dataset is
scoped to AI-market job postings by definition (per the project spec),
so every row is emerging regardless of what the title text says. This was
verified, not assumed: a keyword rule
(`AI|LLM|Prompt|Generative|Agent|ML Engineer`) was tested against all 25
titles first, and it only matched **15/25** — it misclassified obviously
AI-native roles as "Traditional" purely because the title text didn't
literally contain a keyword: `Computer Vision Engineer`, `Data Scientist`,
`Deep Learning Engineer`, `MLOps Engineer`, `NLP Engineer`, `RAG Engineer`,
`Senior Data Scientist`. Conclusion: title-text keyword matching is the
wrong signal for a dataset that is 100% AI roles by construction — the
dataset's own scope is the correct signal, so all 25 are hardcoded
`"Emerging"`.

**Survey (`DevType`, 32 values): keyword-matched, then reviewed by hand.**
Survey is a genuine mix of AI and non-AI roles, so keyword matching is the
right signal here. Only 2 of 32 matched: `"AI/ML engineer"` and
`"Developer, AI apps or physical AI"`. One borderline case was reviewed
manually: `"Applied scientist"` was initially assumed AI-adjacent, but on
review it's a general applied-research title (could be physics, chemistry,
ML, etc.), not AI-exclusive — kept as `"Traditional"`.

## EXPERIENCE_MAP

**Approach:** `experience_level` in `data/raw/ai_jobs_market_2025_2026.csv`
ships as `"<bucket> (<years> yrs)"`, not the bare bucket name:

| Raw value | Rows | Bucket |
|---|---|---|
| `Entry (0-2 yrs)` | 385 | Entry |
| `Lead (10+ yrs)` | 381 | Lead |
| `Mid (3-5 yrs)` | 370 | Mid |
| `Senior (6-9 yrs)` | 364 | Senior |

**Why this map exists:** a quality rule that checks the raw column against
a bare-label allow-list (`.isin(['Entry','Mid','Senior','Lead'])`) matches
**0/1500** rows, since none of the 4 raw strings equal a bare label —
that would quarantine the entire dataset. `EXPERIENCE_MAP`'s keys are the
raw strings actually observed in the file (same pattern as `COUNTRY_MAP`/
`INDUSTRY_MAP`/`ROLE_MAP`), so `ai_jobs_rules.py` checks
`.isin(EXPERIENCE_MAP)` against what the file really contains, and the
map's values are the normalized bucket used downstream.

**Coverage:** 4/4 distinct raw values mapped, verified against the real
file (100%).

## Fail-loud principle

`COUNTRY_MAP` raises `ValueError` at import time if `country_converter`
fails to resolve any value not covered by `_MANUAL_COUNTRY_OVERRIDES` — a
new unresolvable country name breaks the build immediately instead of
silently producing `NaN` downstream. `INDUSTRY_MAP` and `ROLE_MAP` are
closed dicts with no automatic fallback; a raw value not present as a key
will raise `KeyError` on a plain `dict[...]` lookup (or produce `NaN` via
`.map()`, which the quality-rule layer — `quarantine_writer.py`, not yet
built — is expected to catch and quarantine). Coverage against the real
files was manually verified at 100% for all three maps at the time this
was written (all raw values in `data/raw/` resolve to a mapped entry); see
`tests/test_dimension_maps.py` for the internal-consistency tests that do
run in CI.
