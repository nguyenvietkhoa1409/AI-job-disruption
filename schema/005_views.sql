-- Plain (non-materialised) views for the BI layer. They exist so Power BI
-- reads only marts/views and never re-derives business logic in DAX.
-- Views here are deliberately at row / observation grain: medians and rates
-- cannot be rolled up from pre-aggregates, and the dashboards' page filters
-- must still apply.

-- Grain: one layoff event, denormalised for Dashboard 2 (median % by stage,
-- repeat-offender and top-events tables). stage_order gives `stage` its
-- ordinal Seed -> Series J -> Private Equity -> Post-IPO sort.
CREATE OR REPLACE VIEW vw_layoff_event AS
SELECT f.layoff_event_key,
       comp.company_name,
       d.full_date                                       AS layoff_date,
       date_trunc('month', d.full_date)::date            AS month_start,
       COALESCE(c.country_canonical, '(Unknown)')        AS country_canonical,
       c.continent,
       COALESCE(i.industry_sector, '(Unknown)')          AS industry_sector,
       f.location,
       f.stage,
       CASE f.stage
            WHEN 'Seed'           THEN 1
            WHEN 'Series A'       THEN 2
            WHEN 'Series B'       THEN 3
            WHEN 'Series C'       THEN 4
            WHEN 'Series D'       THEN 5
            WHEN 'Series E'       THEN 6
            WHEN 'Series F'       THEN 7
            WHEN 'Series G'       THEN 8
            WHEN 'Series H'       THEN 9
            WHEN 'Series I'       THEN 10
            WHEN 'Series J'       THEN 11
            WHEN 'Private Equity' THEN 12
            WHEN 'Post-IPO'       THEN 13
            WHEN 'Acquired'       THEN 14
            WHEN 'Subsidiary'     THEN 15
            ELSE 16
       END                                               AS stage_order,
       f.total_laid_off,
       f.percentage_laid_off,
       (f.percentage_laid_off = 1)                       AS is_shutdown,
       f.funds_raised_usd_millions
FROM fact_layoff_event f
JOIN dim_date d         ON d.date_key = f.date_key
JOIN dim_company comp   ON comp.company_key = f.company_key
LEFT JOIN dim_country c ON c.country_key = f.country_key
LEFT JOIN dim_industry i ON i.industry_key = f.industry_key;

-- Grain: one salary observation. AI Jobs rows carry the posted (synthetic)
-- annual_salary_usd; Survey rows carry the winsorised self-reported
-- compensation (NULL-compensation respondents are omitted). `dataset` keeps
-- the two apart: role_category is confounded with dataset, so they must
-- never be pooled into one Emerging-vs-Traditional bar. AI Jobs-only columns
-- are NULL for Survey rows.
CREATE OR REPLACE VIEW vw_role_salary AS
SELECT 'AI Jobs'                          AS dataset,
       r.role_source,
       r.role_title,
       r.role_category,
       r.job_category,
       r.is_llm_role,
       p.experience_level_canonical,
       c.country_canonical,
       i.industry_sector,
       p.annual_salary_usd                AS salary_usd,
       p.company_size,
       p.education_required,
       p.remote_work,
       p.demand_score,
       p.demand_growth_yoy_pct,
       p.ai_salary_premium_pct,
       p.benefits_score_10
FROM fact_job_posting p
JOIN dim_role r     ON r.role_key = p.role_key
JOIN dim_country c  ON c.country_key = p.country_key
JOIN dim_industry i ON i.industry_key = p.industry_key
UNION ALL
SELECT 'Survey',
       r.role_source,
       r.role_title,
       r.role_category,
       r.job_category,
       r.is_llm_role,
       s.experience_level_canonical,
       c.country_canonical,
       i.industry_sector,
       s.converted_comp_yearly_winsorized,
       NULL, NULL, NULL, NULL, NULL, NULL, NULL
FROM fact_survey_response s
JOIN dim_role r          ON r.role_key = s.role_key
LEFT JOIN dim_country c  ON c.country_key = s.country_key
LEFT JOIN dim_industry i ON i.industry_key = s.industry_key
WHERE s.converted_comp_yearly_winsorized IS NOT NULL;

-- Grain: one skill. Averages are over the postings that require the skill.
CREATE OR REPLACE VIEW vw_skill_leaderboard AS
SELECT sk.skill_name,
       COUNT(*)                     AS postings,
       AVG(p.demand_score)          AS avg_demand_score,
       AVG(p.annual_salary_usd)     AS avg_annual_salary_usd
FROM fact_job_posting_skill b
JOIN dim_skill sk          ON sk.skill_key = b.skill_key
JOIN fact_job_posting p    ON p.job_posting_key = b.job_posting_key
GROUP BY sk.skill_name;

-- Grain: skill x job_category, for the heatmap. pct_of_category = share of
-- that category's postings requiring the skill. Skill pools are role-specific
-- by dataset design, which is exactly the block structure this shows.
CREATE OR REPLACE VIEW vw_skill_category AS
WITH category_size AS (
    SELECT r.job_category, COUNT(*) AS category_postings
    FROM fact_job_posting p
    JOIN dim_role r ON r.role_key = p.role_key
    GROUP BY r.job_category
)
SELECT sk.skill_name,
       r.job_category,
       COUNT(*)                                          AS postings_with_skill,
       cs.category_postings,
       COUNT(*)::numeric / cs.category_postings          AS pct_of_category
FROM fact_job_posting_skill b
JOIN dim_skill sk       ON sk.skill_key = b.skill_key
JOIN fact_job_posting p ON p.job_posting_key = b.job_posting_key
JOIN dim_role r         ON r.role_key = p.role_key
JOIN category_size cs   ON cs.job_category = r.job_category
GROUP BY sk.skill_name, r.job_category, cs.category_postings;

-- Grain: one survey respondent, with the derived fields Dashboard 4 needs.
--   * ai_threat_yes is NULL when the question was not answered, so
--     AVG(ai_threat_yes::int) and COUNT(ai_threat_yes) give the rate and its N
--     without the 'Not answered' rows diluting the denominator.
--   * ai_sent_score / ai_acc_score are the 1-5 Likert encodings (see
--     dashboard_spec.md); 'Unsure' and 'Not answered' stay NULL so they are
--     excluded from the means. Kept as a CASE here, not a warehouse column.
--   * ai_adopter: uses AI tools daily, weekly or monthly. NULL if unanswered.
--   * topic_kind tags each AIOpen topic as 'skill' or 'stance'. "AI capability
--     skepticism" and the generic "Skills will remain valuable" are opinions,
--     not skills. Keyed on the label text: revisit it whenever MODEL_VERSION
--     in survey_feature_engineer.py changes.
CREATE OR REPLACE VIEW vw_sentiment_profile AS
SELECT r.response_key,
       r.survey_year,
       r.age_bucket,
       r.ed_level,
       r.main_branch,
       r.experience_level_canonical,
       ro.role_category,
       ro.role_title                                     AS dev_type,
       c.country_canonical,
       i.industry_sector,
       r.job_sat,
       s.ai_threat,
       s.ai_select,
       s.ai_sent,
       s.ai_acc,
       CASE WHEN s.ai_threat = 'Not answered' THEN NULL
            ELSE (s.ai_threat = 'Yes') END               AS ai_threat_yes,
       CASE s.ai_sent
            WHEN 'Very unfavorable' THEN 1
            WHEN 'Unfavorable'      THEN 2
            WHEN 'Indifferent'      THEN 3
            WHEN 'Favorable'        THEN 4
            WHEN 'Very favorable'   THEN 5
       END                                               AS ai_sent_score,
       CASE s.ai_acc
            WHEN 'Highly distrust'             THEN 1
            WHEN 'Somewhat distrust'           THEN 2
            WHEN 'Neither trust nor distrust'  THEN 3
            WHEN 'Somewhat trust'              THEN 4
            WHEN 'Highly trust'                THEN 5
       END                                               AS ai_acc_score,
       CASE WHEN s.ai_select = 'Not answered' THEN NULL
            ELSE s.ai_select LIKE 'Yes, %' END           AS ai_adopter,
       t.topic_label,
       CASE WHEN t.topic_label IS NULL THEN NULL
            WHEN t.topic_label IN ('AI capability skepticism',
                                   'Skills will remain valuable (generic)') THEN 'stance'
            ELSE 'skill' END                             AS topic_kind
FROM fact_survey_response r
JOIN dim_ai_sentiment s       ON s.ai_sentiment_key = r.ai_sentiment_key
LEFT JOIN dim_role ro         ON ro.role_key = r.role_key
LEFT JOIN dim_country c       ON c.country_key = r.country_key
LEFT JOIN dim_industry i      ON i.industry_key = r.industry_key
LEFT JOIN dim_ai_open_topic t ON t.ai_open_topic_key = r.ai_open_topic_key;

-- Grain: topic x role_category x AIThreat answer, with counts (additive, so
-- BI can filter and re-aggregate). Respondents without a topic (answers of
-- 4 words or fewer, or no answer) are not in this view.
CREATE OR REPLACE VIEW vw_topic_cross AS
SELECT topic_label,
       topic_kind,
       COALESCE(role_category, 'Unknown role') AS role_category,
       ai_threat,
       COUNT(*)                                AS responses
FROM vw_sentiment_profile
WHERE topic_label IS NOT NULL
GROUP BY topic_label, topic_kind, COALESCE(role_category, 'Unknown role'), ai_threat;
