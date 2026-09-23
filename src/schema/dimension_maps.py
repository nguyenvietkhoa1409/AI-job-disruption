"""Controlled vocabulary maps shared across datasets for warehouse conformance.

Rationale for each map's design is documented in
reports/data_dictionary/dimension_maps.md. Short version: COUNTRY_MAP is
generated from the country_converter library (ISO 3166 has one unambiguous
standard, no need to hand-write it); INDUSTRY_MAP and ROLE_MAP are curated by
hand, because industry taxonomy has no reliable automated standard and role
classification here only needs to answer one narrow question (AI-native vs
traditional), not build a full occupation taxonomy.
"""

import country_converter as coco

# Every distinct raw country value observed across data/raw/{layoffs.csv,
# ai_jobs_market_2025_2026.csv, survey_results_public.csv} as of the three
# data source implementations (LayoffsSource, AIJobsSource, SurveySource).
# Hardcoded (not read from data/raw/ at import time) so this module works
# without the real datasets present, e.g. in CI. Regenerate by unioning
# LayoffsSource().load()["country"], AIJobsSource().load()["country"], and
# SurveySource().load()["Country"] if the raw files change.
_RAW_COUNTRIES = [
    'Afghanistan', 'Albania', 'Algeria', 'Andorra', 'Angola', 'Antigua and Barbuda', 'Argentina',
    'Armenia', 'Australia', 'Austria', 'Azerbaijan', 'Bahrain', 'Bangladesh', 'Barbados',
    'Belarus', 'Belgium', 'Belize', 'Benin', 'Bhutan', 'Bolivia', 'Bosnia and Herzegovina',
    'Botswana', 'Brazil', 'Brunei Darussalam', 'Bulgaria', 'Burundi', 'Cambodia', 'Cameroon',
    'Canada', 'Cape Verde', 'Cayman Islands', 'Chile', 'China', 'Colombia',
    'Congo, Republic of the...', 'Costa Rica', 'Croatia', 'Cuba', 'Cyprus', 'Czech Republic',
    "Côte d'Ivoire", "Democratic People's Republic of Korea", 'Democratic Republic of the Congo',
    'Denmark', 'Djibouti', 'Dominican Republic', 'Ecuador', 'Egypt', 'El Salvador', 'Estonia',
    'Ethiopia', 'Fiji', 'Finland', 'France', 'Gabon', 'Gambia', 'Georgia', 'Germany', 'Ghana',
    'Global', 'Greece', 'Guatemala', 'Guinea', 'Guinea-Bissau', 'Guyana', 'Haiti', 'Honduras',
    'Hong Kong', 'Hong Kong (S.A.R.)', 'Hungary', 'Iceland', 'India', 'Indonesia',
    'Iran, Islamic Republic of...', 'Iraq', 'Ireland', 'Isle of Man', 'Israel', 'Italy', 'Jamaica',
    'Japan', 'Jordan', 'Kazakhstan', 'Kenya', 'Kosovo', 'Kuwait', 'Kyrgyzstan',
    "Lao People's Democratic Republic", 'Latvia', 'Lebanon', 'Lesotho', 'Libyan Arab Jamahiriya',
    'Lithuania', 'Luxembourg', 'Madagascar', 'Malawi', 'Malaysia', 'Maldives', 'Mali', 'Malta',
    'Mauritania', 'Mauritius', 'Mexico', 'Micronesia, Federated States of...', 'Moldova',
    'Mongolia', 'Montenegro', 'Morocco', 'Mozambique', 'Myanmar', 'Namibia', 'Nepal',
    'Netherlands', 'New Zealand', 'Nicaragua', 'Niger', 'Nigeria', 'Nomadic', 'North Korea',
    'Norway', 'Oman', 'Pakistan', 'Palau', 'Palestine', 'Panama', 'Papua New Guinea', 'Paraguay',
    'Peru', 'Philippines', 'Poland', 'Portugal', 'Qatar', 'Republic of Korea',
    'Republic of Moldova', 'Republic of North Macedonia', 'Romania', 'Russia',
    'Russian Federation', 'Rwanda', 'Saint Lucia', 'San Marino', 'Saudi Arabia', 'Senegal',
    'Serbia', 'Seychelles', 'Sierra Leone', 'Singapore', 'Slovakia', 'Slovenia', 'Somalia',
    'South Africa', 'South Korea', 'Spain', 'Sri Lanka', 'Sudan', 'Suriname', 'Swaziland',
    'Sweden', 'Switzerland', 'Syrian Arab Republic', 'Taiwan', 'Tajikistan', 'Thailand',
    'Timor-Leste', 'Togo', 'Trinidad and Tobago', 'Tunisia', 'Turkey', 'Turkmenistan', 'UAE', 'UK',
    'USA', 'Uganda', 'Ukraine', 'United Arab Emirates', 'United Kingdom',
    'United Kingdom of Great Britain and Northern Ireland', 'United Republic of Tanzania',
    'United States', 'United States of America', 'Uruguay', 'Uzbekistan',
    'Venezuela, Bolivarian Republic of...', 'Viet Nam', 'Vietnam', 'Yemen', 'Zambia', 'Zimbabwe',
]

# Values country_converter's regex matching does not resolve on its own.
# "UAE" is a plain alias gap in the library (the ISO name resolves fine).
# "Global" (AI Jobs Market, 82/1500 rows = 5.5%) and "Nomadic" (Survey,
# 29/49123 rows) are not real countries - both mean "no single country
# applies" and are kept as one explicit non-country bucket rather than
# silently dropped or forced into a real country.
_MANUAL_COUNTRY_OVERRIDES = {
    "UAE": "United Arab Emirates",
    "Global": "Multi-region / Remote",
    "Nomadic": "Multi-region / Remote",
}


def _build_country_map() -> dict[str, str]:
    to_convert = [c for c in _RAW_COUNTRIES if c not in _MANUAL_COUNTRY_OVERRIDES]
    converted = coco.convert(names=to_convert, to="name_short", not_found=None)
    result = dict(zip(to_convert, converted))
    unresolved = [raw for raw, canonical in result.items() if canonical is None]
    if unresolved:
        raise ValueError(
            f"COUNTRY_MAP: country_converter could not resolve {unresolved}; "
            "add explicit entries to _MANUAL_COUNTRY_OVERRIDES for these."
        )
    result.update(_MANUAL_COUNTRY_OVERRIDES)
    return result


COUNTRY_MAP: dict[str, str] = _build_country_map()

# 12-sector taxonomy loosely inspired by NAICS top-level groupings, sized to
# what these three datasets actually need (not NAICS's full 1000+ codes).
# "Other" is a deliberate catch-all for small/ambiguous raw categories
# (HR, Legal, Recruiting, Sales, Support, Consulting, Research, Product) -
# each individually low-frequency and not worth a dedicated sector.
INDUSTRY_MAP: dict[str, str] = {
    # --- Layoffs (raw column: industry) ---
    "AI": "Technology & Software",
    "Aerospace": "Manufacturing & Industrial",
    "Construction": "Manufacturing & Industrial",
    "Consumer": "Retail & Consumer",
    "Crypto": "Technology & Software",
    "Data": "Technology & Software",
    "Education": "Education",
    "Energy": "Energy",
    "Finance": "Finance",
    "Fitness": "Retail & Consumer",
    "Food": "Retail & Consumer",
    "HR": "Other",
    "Hardware": "Technology & Software",
    "Healthcare": "Healthcare",
    "Infrastructure": "Technology & Software",
    "Legal": "Other",
    "Logistics": "Transportation & Logistics",
    "Manufacturing": "Manufacturing & Industrial",
    "Marketing": "Media & Marketing",
    "Media": "Media & Marketing",
    "Other": "Other",
    "Product": "Other",
    "Real Estate": "Real Estate",
    "Recruiting": "Other",
    "Retail": "Retail & Consumer",
    "Sales": "Other",
    "Security": "Technology & Software",
    "Support": "Other",
    "Transportation": "Transportation & Logistics",
    "Travel": "Retail & Consumer",
    # --- AI Jobs (raw column: industry) ---
    "Automotive": "Manufacturing & Industrial",
    "Consulting": "Other",
    "Government": "Government & Public Sector",
    "Research": "Other",
    "Technology": "Technology & Software",
    # --- Survey (raw column: Industry) ---
    "Banking/Financial Services": "Finance",
    "Computer Systems Design and Services": "Technology & Software",
    "Fintech": "Finance",
    "Higher Education": "Education",
    "Insurance": "Finance",
    "Internet, Telecomm or Information Services": "Technology & Software",
    "Media & Advertising Services": "Media & Marketing",
    "Other:": "Other",
    "Retail and Consumer Services": "Retail & Consumer",
    "Software Development": "Technology & Software",
    "Transportation, or Supply Chain": "Transportation & Logistics",
}

INDUSTRY_SECTORS = sorted(set(INDUSTRY_MAP.values()))

# Binary role_category: "Emerging" (AI-native) vs "Traditional". Deliberately
# NOT a fine-grained occupation taxonomy (e.g. O*NET-SOC) - the only analysis
# question in scope is the dashboard's "emerging vs traditional role salary
# comparison", which only needs this one split.
#
# AI Jobs job_title: all 25 values are "Emerging" by dataset definition (the
# dataset is scoped to AI-market postings), not by keyword match on the
# title. A plain keyword rule (AI|LLM|Prompt|Generative|Agent|ML Engineer)
# was tested against these 25 titles and only matched 15/25, misclassifying
# obviously AI-native roles ("Computer Vision Engineer", "Data Scientist",
# "Deep Learning Engineer", "MLOps Engineer", "NLP Engineer", "RAG Engineer",
# "Senior Data Scientist") as "Traditional" - the title text is the wrong
# signal for a dataset that is 100% AI roles by construction.
#
# Survey DevType: the dataset is a genuine mix, so keyword-based tagging is
# the right signal here. Only "AI/ML engineer" and "Developer, AI apps or
# physical AI" matched; "Applied scientist" was reviewed manually and kept
# as "Traditional" - it is a general research title (not AI-exclusive), not
# an AI-specific role like the two above.
ROLE_MAP: dict[str, str] = {
    # --- AI Jobs (raw column: job_title) - all Emerging by dataset scope ---
    "AI Agent Developer": "Emerging",
    "AI Business Analyst": "Emerging",
    "AI Compliance Manager": "Emerging",
    "AI Engineer": "Emerging",
    "AI Ethics Officer": "Emerging",
    "AI Infrastructure Eng": "Emerging",
    "AI Product Manager": "Emerging",
    "AI Research Scientist": "Emerging",
    "AI Security Engineer": "Emerging",
    "AI Solutions Architect": "Emerging",
    "Computer Vision Engineer": "Emerging",
    "Data Engineer (AI)": "Emerging",
    "Data Scientist": "Emerging",
    "Deep Learning Engineer": "Emerging",
    "Generative AI Engineer": "Emerging",
    "LLM Engineer": "Emerging",
    "ML Engineer": "Emerging",
    "MLOps Engineer": "Emerging",
    "Multimodal AI Engineer": "Emerging",
    "NLP Engineer": "Emerging",
    "Prompt Engineer": "Emerging",
    "RAG Engineer": "Emerging",
    "Robotics Engineer (AI)": "Emerging",
    "Senior Data Scientist": "Emerging",
    "Senior ML Engineer": "Emerging",
    # --- Survey (raw column: DevType) ---
    "AI/ML engineer": "Emerging",
    "Developer, AI apps or physical AI": "Emerging",
    "Academic researcher": "Traditional",
    "Applied scientist": "Traditional",
    "Architect, software or solutions": "Traditional",
    "Cloud infrastructure engineer": "Traditional",
    "Cybersecurity or InfoSec professional": "Traditional",
    "Data engineer": "Traditional",
    "Data or business analyst": "Traditional",
    "Data scientist": "Traditional",
    "Database administrator or engineer": "Traditional",
    "DevOps engineer or professional": "Traditional",
    "Developer, QA or test": "Traditional",
    "Developer, back-end": "Traditional",
    "Developer, desktop or enterprise applications": "Traditional",
    "Developer, embedded applications or devices": "Traditional",
    "Developer, front-end": "Traditional",
    "Developer, full-stack": "Traditional",
    "Developer, game or graphics": "Traditional",
    "Developer, mobile": "Traditional",
    "Engineering manager": "Traditional",
    "Financial analyst or engineer": "Traditional",
    "Founder, technology or otherwise": "Traditional",
    "Other (please specify):": "Traditional",
    "Product manager": "Traditional",
    "Project manager": "Traditional",
    "Retired": "Traditional",
    "Senior executive (C-suite, VP, etc.)": "Traditional",
    "Student": "Traditional",
    "Support engineer or analyst": "Traditional",
    "System administrator": "Traditional",
    "UX, Research Ops or UI design professional": "Traditional",
}

ROLE_CATEGORIES = ("Emerging", "Traditional")

# AI Jobs experience_level ships as "<bucket> (<years> yrs)" (e.g.
# "Senior (6-9 yrs)"), not the bare bucket name. A rule that checks
# raw values against a bare-label allow-list (['Entry','Mid','Senior','Lead'])
# would match 0/1500 rows and quarantine the entire dataset - none of the
# real file's 4 raw strings equal a bare label. This map's keys are the
# raw strings actually observed in data/raw/ai_jobs_market_2025_2026.csv,
# so quality rules can check .isin(EXPERIENCE_MAP) against what the file
# really contains, same pattern as COUNTRY_MAP/INDUSTRY_MAP/ROLE_MAP.
EXPERIENCE_MAP: dict[str, str] = {
    "Entry (0-2 yrs)": "Entry",
    "Mid (3-5 yrs)": "Mid",
    "Senior (6-9 yrs)": "Senior",
    "Lead (10+ yrs)": "Lead",
}

EXPERIENCE_LEVELS = ("Entry", "Mid", "Senior", "Lead")

# Numeric cutoffs backing the same Entry/Mid/Senior/Lead buckets, for
# datasets that report years of experience as a number instead of AI Jobs'
# pre-labeled string (e.g. Survey's WorkExp). right=True bin edges give
# Entry=[0,2], Mid=[3,5], Senior=[6,9], Lead=[10,+inf) - see
# SurveyTransformer and fact_survey_response's docstring in star_schema.py.
EXPERIENCE_BUCKET_BINS: list[float] = [-float("inf"), 2, 5, 9, float("inf")]
