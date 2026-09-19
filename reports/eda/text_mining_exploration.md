# Text Mining Exploration: `AIOpen` and `required_skills`

**Status:** exploratory / experimental, not part of the production pipeline.
**Source notebook:** `notebooks/text_mining_exploration.ipynb` (gitignored,
not committed — this document is the durable record of what was run and
found).
**Scope:** two free-form/tag fields that sit outside the core star schema
work: `AIOpen` (Stack Overflow Developer Survey — "what skills won't AI
replace") and `required_skills` (AI Jobs Market dataset). Investigated to
see whether short-text topic modeling and skill co-occurrence analysis
surface anything worth feeding into the BI dashboard or the written
insight report (Project output items 3–5 in `Layoff Project.md`).

---

## 1. Technical Implementation

### 1.1 Environment

Ad-hoc packages installed into `.venv` for this exploration only —
**deliberately not added to `requirements.txt`**, since that file is a
shared, coordinated-edit resource per the project's ownership convention
and none of this is wired into `pipeline.py`:

`scikit-learn`, `mlxtend`, `networkx`, `matplotlib`, `bertopic`,
`sentence-transformers`, `nbformat`, `nbconvert`, `ipykernel`.

### 1.2 `AIOpen` pipeline

Data: 49,123 survey rows, 22,520 non-null (45.9% response rate).

1. **Spam/troll filtering.** First attempt used a repeated-token ratio
   (`most_common_token_count / total_tokens > 0.8`). This flagged **1,621
   rows** — almost all false positives, because any genuine one-word
   answer (`"debugging"`, `"creativity"`) trivially has ratio 1.0. Fixed
   by requiring the ratio condition **and** `word_count > 15`, which
   correctly narrowed the flag to the single real troll response (a
   175,026-character answer repeating "no" thousands of times) and
   nothing else.
2. **Length-based split.** Answers with ≤ 4 words (6,844 rows) were routed
   to word/n-gram frequency counting (`CountVectorizer`, unigrams +
   bigrams) rather than topic modeling — a topic model cannot meaningfully
   place a one-word answer. Answers with > 4 words (15,675 rows) went to
   the topic-modeling stage.
3. **Topic modeling, two techniques compared:**
   - **NMF**: `TfidfVectorizer` (unigram+bigram, English stopwords,
     `min_df=5`, `max_df=0.6`) → 10-component NMF.
   - **BERTopic**: `sentence-transformers` embeddings (default MiniLM
     model) + HDBSCAN clustering, run on an 8,000-row sample for CPU time,
     `min_topic_size=40`. (First attempt crashed with `max_df corresponds
     to < documents than min_df` — BERTopic's internal per-topic c-TF-IDF
     vectorizer was given `min_df=5`, which exceeds the row count when the
     aggregated "documents" are one string per topic and topic count is
     small. Fixed by dropping `min_df` from that internal vectorizer.)

### 1.3 `required_skills` pipeline

Data: 1,500 AI Jobs Market rows, 1,500 non-null, pipe-delimited tags
(4–10 tags/row, 93 distinct raw tags).

1. **Synonym normalization — evidence-based, not assumed.** Before
   computing co-occurrence, every visually-similar tag pair was checked
   against two signals: (a) does it ever co-occur with its "twin" in the
   *same posting*, and (b) is it tied to one specific `job_title` or
   shared across many. Seven candidate groups were tested:
   `Risk Analysis`/`Risk Assessment`/`Risk Management`, `Prompt
   Design`/`Prompt Engineering`, `ML`/`ML Algorithms`, `LLM
   APIs`/`GenAI APIs`/`APIs`, `Deep Learning`/`Neural Networks`,
   `Cloud`/`Cloud (AWS/GCP/Azure)`, `Fine-tuning`/`LLM Fine-tuning`.
   Result: the first five groups are each **exclusive to one distinct
   `job_title`** and are lexically unrelated words — a deliberately
   role-specific skill pool by dataset design, kept separate. The last two
   pairs share the shorter tag's exact wording as a substring of the
   longer one (a formatting variant, not a different concept), so those
   were merged (93 → 91 distinct tags).
2. **Association rule mining** (`mlxtend`): each posting's tag set treated
   as a transaction; `apriori` + `association_rules` on support/confidence/
   lift. Run twice — `min_support=0.05, lift≥1.5` first, then
   `min_support=0.02, lift≥1.2` to loosen the filter once the first pass
   returned almost nothing.
3. **Co-occurrence network** (`networkx`): raw pairwise co-occurrence
   counts across all postings, edges kept at weight ≥ 30, for visual
   comparison against the lift-based rules.

---

## 2. Results

### 2.1 `AIOpen`

| Step | Before fix | After fix |
|---|---|---|
| Flagged as spam | 1,621 (mostly false positives) | 1 (the actual troll answer) |
| Short answers (≤4 words) | 5,224 | 6,844 |
| Sentence-level answers (>4 words) | 15,675 | 15,675 |

**Short-answer word frequency** (top terms): *problem*, *solving*,
*thinking*, *problem solving*, *architecture*, *debugging*, *skills*,
*design*, *code*, *understanding*, *critical thinking*, *communication*,
*creativity*, *soft skills*.

**NMF — 10 topics, all interpretable**, sized by dominant-topic assignment:

| Topic | Size | Label (from top terms) |
|---|---|---|
| 6 | 2,295 | Business/domain understanding |
| 7 | 2,253 | Code reading & writing |
| 0 | 2,095 | AI capability skepticism |
| 8 | 2,095 | Complex-problem-solving ability |
| 3 | 1,700 | Software architecture / system design |
| 1 | 1,551 | Problem solving |
| 5 | 1,132 | Soft skills / communication |
| 2 | 1,103 | Critical thinking |
| 9 | 731 | High-level vs. low-level design |
| 4 | 720 | "Skills will remain valuable" (generic) |

**BERTopic**, same corpus (8,000-row sample), found only **2 topics, 0
outliers**: Topic 0 (5,137 answers, "understanding/code/problem
solving/architecture") absorbs most of NMF's topics 1/2/3/6/7/8/9 into one
broad cluster; Topic 1 (2,863 answers, "AI/tools/skills/developers") ≈
NMF's topics 0/4/5. **NMF resolved this corpus more finely than
BERTopic** — a result worth noting precisely because it runs against the
usual expectation that embedding-based topic modeling outperforms TF-IDF
on short text. Likely explanation: these answers are semantically
homogeneous (all responding to the same "what survives AI" prompt), so
embedding distance discriminates less than literal word choice does.

### 2.2 `required_skills`

- Normalization: 93 → 91 distinct tags (2 merges; 5 other candidate
  merges rejected with evidence — see §1.3).
- Apriori at `min_support=0.05, lift≥1.5`: **1 rule** (`Docker ↔ Cloud`,
  lift 2.80). At `min_support=0.02, lift≥1.2`: **593 frequent itemsets,
  1,394 rules**. Top-lift rules (lift ≈ 29–33) cluster almost entirely
  around single-role skill pools discovered independently in §1.3, e.g.
  `Cybersecurity ↔ ML Security ↔ Red Teaming ↔ Risk Analysis` (AI Security
  Engineer's pool) and `AutoGen ↔ Tool Use ↔ APIs ↔ Python` (AI Agent
  Developer-adjacent pool) — i.e., **association rule mining reconstructs
  the dataset's underlying per-role skill templates without being told
  `job_title`.**
- Raw co-occurrence network: 80 nodes, 297 edges (weight ≥ 30). Top edges
  are all `Python –– X` (Python–SQL 288, Python–Cloud 278,
  Python–Leadership 240, Python–PyTorch 223, ...) because Python appears
  in 942/1,500 postings (62.8%) — a hub-frequency artifact, not a
  meaningful cluster. This is the concrete demonstration of why **lift
  (Apriori)**, which normalizes for base rate, is the trustworthy metric
  here and **raw co-occurrence count is not.**

---

## 3. What's Valuable / Worth Picking Up for BI or the Report

`Layoff Project.md` §2 fixes the BI dashboard to exactly three tiles
(layoff trend map, emerging-vs-traditional salary comparison, developer
sentiment trend) and lists "topic model output" as a **separate**
deliverable (item 4) feeding the **written insight report** (item 5), not
the dashboard. Recommendations below respect that split.

### A. Fits directly into the dashboard (sentiment-trend tile)

A single frequency chart of the 10 NMF topics (table in §2.1) — a
bar/donut chart answering "what developers believe will survive AI,"
quantified. Simple, on-brand for a BI tool, needs no further explanation
to land.

**Caveat before it can ship:** this requires productionizing the topic
assignment — persisting a stable `(response_id, topic_id, topic_label)`
table into the warehouse/mart, not re-running the notebook ad hoc. The
current NMF run has no versioning or reproducibility guarantee across
reruns (`random_state=42` fixes the seed, but topic *ordering/numbering*
is not guaranteed stable if the input row count or vocabulary changes).

### B. Belongs in the "topic model output" deliverable + written report (items 4–5), not a dashboard tile

- The 10 labeled topics with example terms and representative quotes
  (§2.1) — this is the "what skills survive AI" narrative thread the
  spec explicitly calls for. It's prose-and-quotes content, not a chart.
- The Apriori finding that skill co-occurrence reconstructs per-role
  skill pools (§2.2) — a genuinely strong analytical insight, but its
  value is in the *explanation*, not a standalone chart; best told as a
  short case-study paragraph plus one supporting static figure (e.g. one
  annotated subgraph for the AI Security Engineer cluster).

### C. Optional scope expansion — requires an explicit decision, not implied by current spec

A `required_skills` co-occurrence/association network as a 4th dashboard
panel. Visually strong and a genuine technical differentiator, but it
sits outside the three tiles already committed in the spec. Treat as a
deliberate scope-add, not a default inclusion.

### D. Not dashboard or report-narrative material — portfolio/methodology value only

The spam-filter debugging story (1,621 → 1 false positives) and the
NMF-vs-BERTopic comparison are process/rigor narratives. They're strong
material for a portfolio case study or an interview conversation about
technical judgment, but they don't belong in front of a BI dashboard
viewer or in the insight report's findings section — at most a footnote
in the report's methodology appendix.

---

## Open decisions

1. Confirm whether the dashboard should gain the item-A topic-frequency
   chart, and if so, scope the work to persist stable topic assignments
   into the warehouse.
2. Decide whether to pursue item C (skill co-occurrence panel) as a
   deliberate scope expansion or leave the dashboard at its original
   three tiles.
3. If pursued, item C also needs the same "reproducible, persisted output"
   treatment as item A before it can be dashboard-ready — the current
   network in the notebook is a one-off `networkx` render, not a queryable
   table.
