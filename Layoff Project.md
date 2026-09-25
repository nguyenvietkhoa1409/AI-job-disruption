# Project Scope

# **AI Job Market Disruption: An End to End Data Analytics and Data Engineering Project**

## **1\. Project Overview**

This project investigates how artificial intelligence is reshaping the global technology labor market. It combines three public data sources that represent three different angles of the same disruption: what is being cut (layoffs), what is being created (new AI related roles and salaries), and how practitioners feel about it (developer sentiment).

The project is designed to demonstrate both data engineering and data analytics competencies inside a single, coherent pipeline. The end to end flow follows five stages.

1. Data sources. Three public datasets are collected: a real world tech layoffs dataset, an AI job postings and salary dataset, and the Stack Overflow Developer Survey.  
2. Ingestion and raw storage. Batch files are loaded and, where possible, live data is pulled through public APIs into a raw storage layer with no transformation applied.  
3. Cleaning and exploratory data analysis. Each dataset is profiled, cleaned, and explored independently before any cross source work begins.  
4. Warehouse and transform. Cleaned data is modeled into a shared star schema and loaded into a data warehouse through a transformation layer.  
5. Analytics and delivery. SQL analysis, dashboards, and a written insight report are produced from the warehouse layer.

The remainder of this document details stage 3 (dataset analysis) and stage 4 (data schema). Later iterations of this report will cover transformation logic, orchestration design, data quality tests, and the dashboard specification.

## **2\. Project output**&nbsp;

**1\. A public GitHub repository** containing the full OOP Python codebase (data\_sources, quality, preprocessing, feature\_engineering, eda, schema, pipeline.py, config.py), a Docker Compose setup for Postgres, automated tests, and CI configuration.

**2\. A working PostgreSQL data warehouse** with the star schema populated (4 fact tables, 8 dimension tables) and a mart\_country\_month materialized view for fast dashboard queries.

**3\. A BI dashboard** (Looker Studio or Power BI) built on the warehouse, covering the layoff trend map, the emerging versus traditional role salary comparison, and the developer sentiment trend.

**4\. A topic model output** for the AIOpen free text field: labeled topics with example terms, feeding into the insight report as the "what skills survive AI" narrative thread.

**5\. A written insight report** in academic English, assembled from what has already been produced in this conversation (dataset analysis, data schema, data quality rules) plus the sections still pending (EDA findings, topic model results, cross source insight narrative, ad-hoc stakeholder Q\&A).

**6\. Documentation**: README, data dictionary, ERD and architecture diagrams, this PROJECT\_CONTEXT.md, and the tracking sheet below.

# Dataset descriptions

### **Dataset 1: Layoffs Dataset**

Link: [https://www.kaggle.com/datasets/swaptr/layoffs-2022](https://www.kaggle.com/datasets/swaptr/layoffs-2022)

The Layoffs Dataset is sourced from Layoffs.fyi, a technology sector layoff tracker founded by Roger Lee in 2020, mirrored on Kaggle under the Open Data Commons Open Database License. The version used in this project contains 4,600 records collected up to September 2026\. The dataset is event level, meaning each row represents a single reported layoff event, and a company may appear more than once if it reported layoffs on separate occasions. It covers 11 fields describing the company, the scale of the layoff, the company's industry and funding stage, and the geographic location of the event. In the context of this project, this dataset represents the loss side of the labor market disruption narrative.

&nbsp;

| No. | Field | Data Type | Description | Example Value |
| ----- | ----- | ----- | ----- | ----- |
| 1 | company | str | Name of the company that reported the layoff event | Neo Financial |
| 2 | location | str | City where the company is headquartered, tagged as US or Non-U.S. | Calgary, Non-U.S. |
| 3 | total\_laid\_off | float64 | Number of employees laid off, may be missing if only a percentage was disclosed | 102.0 |
| 4 | date | str | Date the layoff was reported, in M/D/YYYY format, requires parsing to a proper date type | 9/8/2026 |
| 5 | percentage\_laid\_off | float64 | Share of the workforce laid off, expressed on a 0 to 1 scale rather than 0 to 100 | 0.1 |
| 6 | industry | str | Industry the company operates in | Finance |
| 7 | source | str | URL of the news article confirming the layoff | linkedin.com/pulse/... |
| 8 | stage | str | Company funding stage at the time of the layoff | Series D |
| 9 | funds\_raised | float64 | Total funding raised by the company, in millions of USD | 544.0 |
| 10 | country | str | Country where the company is headquartered | Canada |
| 11 | date\_added | str | Date the record was added to the Layoffs.fyi tracker, distinct from the actual layoff date | 9/9/2026 |

### **Dataset 2: AI Jobs Market 2025-2026 Salaries**

Link: [https://www.kaggle.com/datasets/alitaqishah/ai-jobs-market-2025-2026-salaries](https://www.kaggle.com/datasets/alitaqishah/ai-jobs-market-2025-2026-salaries)

This dataset is sourced from Kaggle ("AI Jobs Market 2025-2026 | Salaries") and contains 1,500 job postings spanning 25 distinct roles across 14 countries. Each row represents a single posting. The dataset is a curated illustration of directional market trends rather than a live job board scrape, so findings drawn from it should be treated as illustrative rather than authoritative, a limitation already noted in the earlier project report. In this project, this dataset represents the creation side of the disruption narrative, capturing which AI related roles are emerging and how they are compensated.

| No. | Field | Data Type | Description | Example Value |
| ----- | ----- | ----- | ----- | ----- |
| 1 | job\_id | str | Unique identifier of the job posting | AIJOB0001 |
| 2 | job\_title | str | Job role title, one of 25 distinct roles | AI Agent Developer |
| 3 | job\_category | str | Functional grouping of the role, one of 12 categories | AI Engineering |
| 4 | experience\_level | str | Required experience bucket, one of 4 levels | Senior (6-9 yrs) |
| 5 | years\_of\_experience | int64 | Specific number of years of experience required | 7 |
| 6 | education\_required | str | Minimum education level required | Master's |
| 7 | annual\_salary\_usd | float64 | Annualized salary converted to USD | 239000.0 |
| 8 | salary\_min\_usd | int64 | Lower bound of the salary range | 155000 |
| 9 | salary\_max\_usd | int64 | Upper bound of the salary range | 290000 |
| 10 | city | str | City where the position is based | Boston |
| 11 | country | str | Country where the position is based, one of 14 countries | USA |
| 12 | remote\_work | str | Work arrangement offered | On-site |
| 13 | company\_size | str | Company size bucket, one of 5 categories | Startup (1-50) |
| 14 | industry | str | Industry of the hiring company, one of 12 industries | Finance |
| 15 | required\_skills | str | Pipe delimited list of required skills | APIs|Python|Cloud|SQL |
| 16 | ai\_salary\_premium\_pct | float64 | Percentage salary premium attributed to AI skills, observed range 3 to 18 | 13.1 |
| 17 | demand\_score | int64 | Market demand score for the role, observed range 68 to 98 | 96 |
| 18 | demand\_growth\_yoy\_pct | float64 | Year over year growth in demand for the role | 16.9 |
| 19 | benefits\_score\_10 | float64 | Benefits score on a 10 point scale, observed range 6.0 to 9.8 | 6.8 |
| 20 | posting\_year | int64 | Year the posting was listed | 2026 |
| 21 | posting\_month | int64 | Month the posting was listed | 3 |
| 22 | is\_senior | int64 (0/1) | Flag indicating a senior level or above position | 1 |
| 23 | is\_remote\_friendly | int64 (0/1) | Flag indicating remote work is supported | 0 |
| 24 | is\_llm\_role | int64 (0/1) | Flag indicating the role is directly tied to large language models | 1 |
| 25 | salary\_tier | str | Salary bracket, one of 5 tiers | Senior ($200-300k) |

### **Dataset 3: Stack Overflow Developer Survey 2025**

Sources:&nbsp;

- [https://survey.stackoverflow.co/](https://survey.stackoverflow.co/):  checkpoint dataset theo năm&nbsp;  
- [https://www.kaggle.com/datasets/edoardogalli/stack-overflow-annual-developer-survey-2025?select=survey\_results\_public.csv](https://www.kaggle.com/datasets/edoardogalli/stack-overflow-annual-developer-survey-2025?select=survey_results_public.csv): Bản CSV-ready&nbsp;

This dataset is the public release of the 2025 Stack Overflow Developer Survey, containing 49,191 valid responses across the full survey's 172 columns. Only a relevant subset of 17 fields is documented and used in this project, covering demographics, employment status, compensation, and attitudes toward AI tools, since the remaining columns fall outside the scope of this project's narrative. In this project, this dataset represents the human sentiment side of the narrative. A notable characteristic is a high missing rate on several optional fields, ranging from about 27 to 51 percent depending on the field, which must be preserved as an explicit "not answered" category rather than imputed.

| No. | Field | Data Type | Description | Example Value |
| ----- | ----- | ----- | ----- | ----- |
| 1 | ResponseId | int64 | Unique identifier of the survey respondent | 1 |
| 2 | MainBranch | str | Whether the respondent is a professional developer | I am a developer by profession |
| 3 | Age | str | Age bucket of the respondent | 25-34 years old |
| 4 | EdLevel | str | Highest level of education completed | Bachelor's degree |
| 5 | Employment | str | Current employment status | Employed |
| 6 | WorkExp | float64 | Years of professional work experience | 8.0 |
| 7 | YearsCode | float64 | Years the respondent has been writing code in any capacity | 14.0 |
| 8 | DevType | str | Primary job role or title | Developer, back-end |
| 9 | RemoteWork | str | Work arrangement, missing in about 31 percent of responses | Remote |
| 10 | Country | str | Country of residence, missing in about 28 percent of responses | Ukraine |
| 11 | Industry | str | Industry of the respondent's employer, missing in about 32 percent of responses | Fintech |
| 12 | ConvertedCompYearly | float64 | Total yearly compensation converted to USD, missing in about 51 percent of responses | 61256.0 |
| 13 | AIThreat | str | Whether the respondent believes AI threatens their job, missing in about 27 percent of responses | I'm not sure |
| 14 | AISelect | str | Reported frequency of AI tool usage at work, missing in about 32 percent of responses | Yes, I use AI tools daily |
| 15 | AISent | str | General sentiment toward AI tools, missing in about 32 percent of responses | Favorable |
| 16 | AIAcc | str | Level of trust in the accuracy of AI tool output, missing in about 32 percent of responses | Somewhat trust |
| 17 | JobSat | float64 | Job satisfaction score on a 10 point scale, missing in about 46 percent of responses | 10.0 |
| 18 | AIOpen&nbsp; | str | Open ended, free text response. Based on the observed answer pattern, respondents describe skills they believe remain valuable despite AI adoption. Missing in about 54.2 percent of responses since it is an optional write-in question. Sole free text field in scope, reserved for topic modeling&nbsp; | Troubleshooting, profiling, debugging&nbsp; |

&nbsp;

# EDA

&nbsp;

## **Overall EDA flow**

## &nbsp;![][image1]

&nbsp;

# Folder structure

## **Folder Structure**&nbsp;

ai\_job\_disruption/

├── src/

│   ├── data\_sources/

│   │   ├── base\_source.py        \# abstract BaseDataSource: load(), describe\_columns()

│   │   ├── layoffs\_source.py     \# class LayoffsSource(BaseDataSource)

│   │   ├── ai\_jobs\_source.py     \# class AIJobsSource(BaseDataSource)

│   │   └── survey\_source.py      \# class SurveySource(BaseDataSource)

│   │

│   ├── quality/

│   │   ├── base\_rule\_set.py      \# abstract BaseQualityRuleSet: apply(df) \-\> (clean, quarantine)

│   │   ├── layoffs\_rules.py      \# class LayoffsQualityRules(BaseQualityRuleSet)

│   │   ├── ai\_jobs\_rules.py      \# class AIJobsQualityRules(BaseQualityRuleSet)

│   │   └── survey\_rules.py       \# class SurveyQualityRules(BaseQualityRuleSet)

│   │

│   ├── preprocessing/

│   │   ├── base\_transformer.py   \# abstract BaseTransformer: transform(df) \-\> df

│   │   ├── layoffs\_transformer.py

│   │   ├── ai\_jobs\_transformer.py

│   │   └── survey\_transformer.py

│   │

│   ├── eda/

│   │   ├── profiler.py           \# class DatasetProfiler \-\> sinh bảng data dictionary tự động

│   │   └── visualizer.py         \# class EDAVisualizer

│   │

│   ├── schema/

│   │   ├── dimension\_maps.py     \# controlled list: COUNTRY\_MAP, ROLE\_MAP, INDUSTRY\_MAP

│   │   └── star\_schema.py        \# dataclass cho fact/dim table

│   │

│   ├── pipeline.py               \# class DatasetPipeline: nối 4 interface trên lại

│   └── config.py                 \# class ProjectPaths

│

├── data/{raw,processed,quarantine}/

├── reports/{data\_dictionary,figures}/

├── tests/

├── requirements.txt

└── [README.md](http://README.md)

&nbsp;

# Git working guideline

**GIT / GITHUB TEAM PLAYBOOK**

**AI Job Disruption — 2-Person Data Engineering \+ EDA Project**

Airflow • OOP source/quality/transform layers • EDA • Dashboard • Local development

| Item | Team convention |
| :---- | :---- |
| Repository | One shared GitHub repository: ai\_job\_disruption |
| Default branch | main \= stable integration branch; no routine direct pushes |
| Development | One feature/fix branch per task |
| Integration | Pull Request → review → tests → merge |
| Sync | Update local main, then merge main into the current feature branch |
| Data | Do not commit raw/processed/quarantine data, secrets, Airflow DB/logs |
| Default merge style | Prefer Squash and Merge for small team/task-based work |

&nbsp;

| Core idea  Git is the version-control system; GitHub is the shared remote \+ review/integration layer. The team should treat main as the project source of truth and feature branches as isolated workspaces. |
| :---- |

# **1\. Document Map**

| Section | Purpose |
| :---- | :---- |
| 2\. Project Git Model | Repository/branch/task model tailored to the project |
| 3\. Daily Workflow | Standard sequence from task assignment to merge |
| 4\. Case Groups | Common collaboration cases grouped by situation |
| 5\. Conflict Handling | Safe, repeatable conflict-resolution procedure |
| 6\. GitHub Rules | PR, review, protection, ownership and CI |
| 7\. Project-Specific Rules | Data, Airflow, config and shared-file policy |
| 8\. Command Cheat Sheet | Commands to keep beside the terminal |
| 9\. Checklists | Start-task, PR, merge and emergency checklists |
| 10\. Recommended Team Setup | Concrete setup for the two-person team |
| 11\. References | Current Git/GitHub documentation |

&nbsp;

# **2\. Project Git Model**

## **2.1 Repository structure**

ai\_job\_disruption/  
├── src/  
│   ├── data\_sources/  
│   ├── quality/  
│   ├── preprocessing/  
│   ├── eda/  
│   ├── schema/  
│   ├── pipeline.py  
│   └── config.py  
├── data/{raw,processed,quarantine}/  
├── reports/{data\_dictionary,figures}/  
├── tests/  
├── requirements.txt  
├── .gitignore  
├── README.md  
└── .github/  
&nbsp;&nbsp;&nbsp;&nbsp;├── pull\_request\_template.md  
&nbsp;&nbsp;&nbsp;&nbsp;└── workflows/tests.yml

**Recommended ownership pattern:**

* Module-specific files → primarily owned by the person assigned that task.  
* Shared integration points (pipeline.py, config.py, requirements.txt, schema/\*) → explicitly assigned owner or coordinated edits.  
* tests/ → each feature owner writes tests for their module; the other teammate reviews/executes the full suite.  
* README and GitHub workflow files → shared, but avoid simultaneous edits.

## **2.2 Branch model**

main  
├── feature/base-data-source  
├── feature/layoffs-source  
├── feature/ai-jobs-source  
├── feature/survey-source  
├── feature/layoffs-quality  
├── feature/eda-profiler  
├── feature/eda-visualizer  
├── feature/airflow-pipeline  
└── fix/\<short-description\>

| Rule  A branch should represent one coherent task or fix. Avoid branches such as final, test, version2, or one branch shared by both teammates. |
| :---- |

# **3\. Standard Daily Workflow**

## **3.1 Start a task**

git status  
git switch main  
git pull origin main  
git switch \-c feature/layoffs-source

*Why this order? You start from the latest main so your feature branch has the newest integration baseline. Git’s current documentation supports git switch \-c for creating and switching to a branch.*

## **3.2 Develop → test → inspect → commit**

\# edit files  
pytest  
git status  
git diff  
git add src/data\_sources/layoffs\_source.py tests/test\_layoffs\_source.py  
git diff \--staged  
git commit \-m "feat: implement LayoffsSource"

## **3.3 Push and open PR**

git push \-u origin feature/layoffs-source

| PR element | Recommended content |
| :---- | :---- |
| Title | feat: implement LayoffsSource |
| What | What was implemented? |
| Why | What issue/task does it solve? |
| Files | Main changed files |
| Testing | pytest result / relevant checks |
| Related issue | Closes \#N or Related to \#N |
| Known limitation | Anything reviewer should know |

&nbsp;

## **3.4 Review → merge → sync**

\# reviewer comments → author fixes → commit → push

\# after merge, each teammate updates local main  
git switch main  
git pull origin main

\# if you still have an active feature branch  
git switch feature/my-task  
git merge main

| Mental model  Updating main and updating your feature branch are two separate actions. git pull on main updates local main; git merge main while on the feature branch brings those changes into your feature branch. |
| :---- |

# **4\. Case Groups — Practical Scenarios**

## **Group A — Starting and ending normal work**

| Case | Situation | Action |
| :---- | :---- | :---- |
| A1 | Start new task | switch main → pull → create feature branch |
| A2 | Finished coding | pytest → diff → commit → push |
| A3 | PR review requested | respond to comments on same branch → commit → push |
| A4 | PR approved | merge to main; delete feature branch if no longer needed |

&nbsp;

### **Case A1 — New task**

git switch main  
git pull origin main  
git switch \-c feature/base-data-source

### **Case A2 — Commit**

git status  
git diff  
pytest  
git add .  
git commit \-m "feat: implement BaseDataSource interface"  
git push \-u origin feature/base-data-source

### **Case A3 — PR asks for changes**

\# fix requested code  
git add .  
git commit \-m "refactor: adjust data source interface"  
git push

**Do not create a second PR just because the first PR received review comments. The existing PR updates automatically when more commits are pushed to its source branch.**

## **Group B — Keeping up with the other teammate**

| Case | When | Preferred procedure |
| :---- | :---- | :---- |
| B1 | Teammate merged new work to main | Update local main |
| B2 | You still work on a feature branch | Merge updated main into your branch |
| B3 | You only want to inspect remote changes | git fetch origin |
| B4 | Your branch is behind main before PR merge | Sync main → merge into feature → test → push |

&nbsp;

### **Case B1 — Main changed**

git switch main  
git pull origin main

### **Case B2 — Bring main into current branch**

git switch main  
git pull origin main  
git switch feature/ai-jobs-source  
git merge main  
pytest  
git push

### **Case B3 — Inspect without integrating**

git fetch origin  
git log \--oneline origin/main \-n 10

*fetch updates your remote-tracking information without changing your current working tree. Use it when you want to inspect first and integrate later.*

## **Group C — Parallel development and dependencies**

| Case | Situation | Recommended approach |
| :---- | :---- | :---- |
| C1 | Two people edit different files | Continue independently; Git usually merges cleanly |
| C2 | Both need the same shared file | Name an owner / coordinate edit timing |
| C3 | Task B depends on task A | Prefer merge A to main, then branch/update B |
| C4 | Need to test teammate’s unmerged branch | fetch → switch to teammate branch → test → switch back |

&nbsp;

### **Case C2 — Shared file**

Shared-risk files:  
src/pipeline.py  
src/config.py  
requirements.txt  
src/schema/\*  
README.md

**Treat these as integration points. If both people change the same area at the same time, the probability of conflict increases and the reviewer needs more context.**

### **Case C3 — Dependency**

\# Preferred order  
PR \#10: BaseDataSource  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;↓ merge  
PR \#11: LayoffsSource  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;↓ merge

| Default for this team  Avoid stacked branches unless a dependency really needs parallel work. For a two-person student project, the simpler “merge dependency first” workflow is easier to understand and maintain. |
| :---- |

## **Group D — Merge conflicts**

| Case | Typical cause | Response |
| :---- | :---- | :---- |
| D1 | Same lines edited differently | Resolve manually on feature branch |
| D2 | Same file, different areas | Try normal merge; Git may resolve automatically |
| D3 | File edited vs deleted | Decide whether file should survive; resolve intentionally |
| D4 | Conflict appears in PR | Resolve locally for complex conflicts; push result |

&nbsp;

### **Case D1 — Conflict procedure**

git switch main  
git pull origin main  
git switch feature/layoffs-source  
git merge main

\# Git reports conflict  
git status  
\# open each conflicted file and remove conflict markers  
pytest  
git add \<resolved-files\>  
git commit \-m "resolve: integrate latest main"  
git push

Conflict markers:  
\<\<\<\<\<\<\< HEAD  
YOUR BRANCH  
\=======  
MAIN  
\>\>\>\>\>\>\> main

*Rule: never choose “ours” or “theirs” blindly. First decide what the correct behavior should be, then test the result. GitHub notes that conflicts commonly arise when competing edits touch the same lines or when one side edits while the other deletes a file.*

## **Group E — Uncommitted work / recovery**

| Case | Problem | Safe move |
| :---- | :---- | :---- |
| E1 | You need to switch branches but have changes | Commit a WIP change or stash |
| E2 | You committed but found a small mistake | Make a follow-up fix commit |
| E3 | You want to rewrite your own unmerged commit | amend \+ push \--force-with-lease |
| E4 | You accidentally changed main | stop; inspect status/history before pushing further |

&nbsp;

### **Case E1 — Work is not ready to commit**

git status  
git stash

\# update branches / do another task

git stash pop

*For this team, a small WIP commit on a private feature branch is often easier to recover and reason about than repeatedly using stash.*

### **Case E3 — Force push**

git commit \--amend  
git push \--force-with-lease

| Never  Do not force-push main. Do not use plain git push \--force on a shared branch. Force pushes can remove history that another collaborator based work on. |
| :---- |

## **Group F — CI, review and merge**

| Case | Condition | Action |
| :---- | :---- | :---- |
| F1 | PR needs review | Teammate reviews code \+ tests \+ interface compatibility |
| F2 | CI fails | Fix failure before merge; rerun automatically after push |
| F3 | PR is behind main | Sync main into feature branch; rerun tests |
| F4 | Merged code breaks project | Create fix branch \+ PR; do not patch main casually |

&nbsp;

## **Group G — GitHub administration**

| Control | Recommendation for this project |
| :---- | :---- |
| Protected main | Yes |
| Require PR before merge | Yes |
| Required approvals | 1 reviewer |
| Required status check | pytest / CI |
| Conversation resolution | Yes |
| Direct push to main | No for normal work |
| Force push to main | No |
| Code owners | Optional but useful for shared modules |

&nbsp;

# **5\. Conflict Handling — A Safe Mental Model**

**Think of three states:**

REMOTE MAIN  →  local main  →  your feature branch

1. Synchronize local main with GitHub.  
2. Move to your feature branch.  
3. Merge main into the feature branch.  
4. Resolve conflicts if Git cannot combine changes automatically.  
5. Run tests and inspect the final diff.  
6. Commit the resolution and push the feature branch.  
7. Let the PR continue through review and CI.

| Important  A conflict is not a Git error to “make disappear”; it is a semantic decision point. The correct resolution is the code that preserves the intended contract and passes tests. |
| :---- |

# **6\. GitHub Rules for the Team**

## **6.1 Pull Requests**

* One PR \= one coherent feature/fix.  
* PR title should state the change clearly: feat:, fix:, test:, refactor:, docs:, chore: etc.  
* Reviewer checks correctness, tests, interface compatibility, side effects, and unnecessary changes.  
* Keep PRs reasonably small. Large “everything” PRs are harder to review and merge.

## **6.2 Protect main**

*GitHub protected branches can require reviews, status checks, conversation resolution, and can block force pushes/deletion. These controls are appropriate for main as the stable integration branch.*

## **6.3 Merge method**

*Recommended team default: Squash and Merge for small task-based PRs. This turns multiple fix/review commits into one coherent main-branch commit. If your course/team later requires a detailed merge history, use Merge Commit instead. GitHub supports multiple merge strategies and repository-level configuration.*

## **6.4 Code ownership**

*GitHub CODEOWNERS can automatically request review from the people responsible for specific files/directories. For this project, it is most useful for shared integration points such as pipeline.py, schema/\*, and workflow/configuration files.*

# **7\. Project-Specific Rules**

## **7.1 Data should not be versioned like source code**

\# .gitignore examples  
data/raw/\*  
data/processed/\*  
data/quarantine/\*  
reports/figures/\*  
reports/data\_dictionary/\*  
airflow/logs/  
airflow/airflow.db  
.env  
.venv/  
\_\_pycache\_\_/  
\*.pyc

**Keep folder structure with .gitkeep files or documented setup instructions. Share reproducible data acquisition instructions, schemas, sample data, or small fixtures when needed rather than committing large datasets or credentials.**

## **7.2 Airflow**

* Version DAG/code/config templates; do not version local Airflow runtime DB or logs.  
* Do not commit connection passwords, API keys, .env files, or local credentials.  
* Keep DAG code deterministic and testable outside the Airflow scheduler when possible.  
* Use CI to catch import/syntax/test problems before merge.

## **7.3 Requirements and reproducibility**

python \-m venv .venv  
pip install \-r requirements.txt  
python \--version  
git \--version

**Agree on the Python major/minor version early (for example, Python 3.12.x) and keep the dependency file under version control.**

## **7.4 OOP interface discipline**

| Layer | Git implication |
| :---- | :---- |
| Base interfaces | High coordination value; changes can affect many modules |
| Concrete data sources | Good candidates for independent feature branches |
| Quality rule sets | Usually independent by dataset |
| Transformers | Independent by dataset; watch shared interfaces |
| EDA visualizer/profiler | Independent until integrated into pipeline |
| schema/\* | Shared contract; coordinate changes carefully |
| pipeline.py | Integration hotspot; prefer one owner at a time |

&nbsp;

# **8\. Command Cheat Sheet**

| Need | Command |
| :---- | :---- |
| See current state | git status |
| See branches | git branch |
| Create \+ switch branch | git switch \-c feature/name |
| Switch branch | git switch branch-name |
| Update current main | git switch main && git pull origin main |
| Fetch remote information | git fetch origin |
| Bring main into feature | git switch feature/x && git merge main |
| See unstaged changes | git diff |
| See staged changes | git diff \--staged |
| Commit | git add . && git commit \-m "feat: ..." |
| First push of branch | git push \-u origin feature/x |
| Later pushes | git push |
| Recent history | git log \--oneline \--graph \--all |

&nbsp;

## **8.1 The “safe sync” sequence**

git status  
git switch main  
git pull origin main  
git switch feature/my-task  
git merge main  
pytest  
git push

## **8.2 The “I have a conflict” sequence**

git status  
\# resolve files  
pytest  
git add \<resolved-files\>  
git commit \-m "resolve: ..."  
git push

# **9\. Checklists**

## **9.1 Before starting a task**

* \[ \] Read the issue/task scope  
* \[ \] Confirm target files  
* \[ \] Update main  
* \[ \] Create feature branch  
* \[ \] Know the test command

## **9.2 Before opening a PR**

* \[ \] Task is coherent and scoped  
* \[ \] Tests pass  
* \[ \] No secrets/data/runtime artifacts  
* \[ \] Diff reviewed locally  
* \[ \] Commit/PR title is clear  
* \[ \] README/config updated if needed

## **9.3 Before merge**

* \[ \] Reviewer approved  
* \[ \] CI passed  
* \[ \] PR is current with main or GitHub confirms mergeability  
* \[ \] All discussions resolved  
* \[ \] No unexplained debug code

## **9.4 After merge**

* \[ \] Update local main  
* \[ \] Update active feature branch if work continues  
* \[ \] Delete obsolete branch  
* \[ \] Continue from latest integrated state

# **10\. Recommended Team Setup**

## **10.1 Suggested ownership**

| Area | Primary owner | Secondary/reviewer |
| :---- | :---- | :---- |
| data\_sources/base\_source.py | Person A | Person B |
| data\_sources/layoffs\_source.py | Person A | Person B |
| data\_sources/ai\_jobs\_source.py | Person B | Person A |
| data\_sources/survey\_source.py | Person B | Person A |
| quality/\* | Split by dataset | Other teammate |
| preprocessing/\* | Split by dataset | Other teammate |
| eda/profiler.py | A or B | Other teammate |
| eda/visualizer.py | A or B | Other teammate |
| schema/\* | Named owner | Other teammate |
| pipeline.py | Named owner at a time | Other teammate |
| Airflow DAGs | Named owner | Other teammate |
| Dashboard | Named owner | Other teammate |

&nbsp;

## **10.2 Recommended weekly operating rhythm**

1\. Break work into small issues.  
2\. Assign each issue to one person.  
3\. Create one feature branch per issue.  
4\. Commit in logical chunks.  
5\. Open PR when testable.  
6\. Review and merge.  
7\. Everyone syncs main before starting the next task.  
8\. Before integration-heavy work, explicitly coordinate shared files.

| Team rule of thumb  Independent module work should be parallel. Interface/integration work should be coordinated. The goal is not “zero conflicts”; the goal is predictable integration with small reviewable changes. |
| :---- |

# **11\. References**

* **GitHub Docs — Branches:** https://docs.github.com/en/pull-requests/reference/branches  
* **GitHub Docs — About protected branches:** https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches  
* **GitHub Docs — Managing protected branches:** https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches  
* **GitHub Docs — Merge conflicts:** https://docs.github.com/en/pull-requests/reference/merge-conflicts  
* **GitHub Docs — Pull requests:** https://docs.github.com/en/pull-requests  
* **GitHub Docs — Managing and standardizing pull requests:** https://docs.github.com/en/pull-requests/reference/managing-and-standardizing-pull-requests  
* **Git Docs — git-switch:** https://git-scm.com/docs/git-switch  
* **GitHub Docs — Configuring commit merging:** https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/configuring-commit-merging-for-pull-requests

&nbsp;


MAJOR RULES: When the code is related to the action of update repo (push), i want you to ONLY GIVE ME THE CODE TO DO IT MYSELT, because i never want the Claude appear as contributor if you (Claude) do the push code your self.