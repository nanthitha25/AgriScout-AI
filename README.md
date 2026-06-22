# AI-Powered Agriculture Startup Discovery Tracker

A complete, modular, and production-ready Python pipeline designed to monitor and track recent agriculture technology (AgTech) startup funding rounds, product launches, and company creations.

This tracker parses the Google News RSS feed, filters out already-tracked URLs to avoid redundancy, utilizes the **Google Gemini 2.5 Flash API** via the modern `google-genai` SDK with Structured Outputs to parse article contents, and persists discovered startup information to a local Excel database.

---

## Architecture & Data Flow

```
+--------------------+
|  Google News RSS   |
+---------+----------+
          |
          v
+--------------------+
| Deduplication      | <--- Compares article URL against agtech_startups.xlsx
+---------+----------+
          | (Only new URLs)
          v
+--------------------+
| Gemini 2.5 Flash   | <--- Extracts Startup Name, Website, Description, News Summary
+---------+----------+
          | (Filters out 'Unknown' entities)
          v
+--------------------+
| Excel Database     | <--- Appends new startup details with timestamp
+--------------------+
```

---

## Features

- **Robust Deduplication**: Keeps track of processed source URLs in `agtech_startups.xlsx` and skips duplicates instantly to optimize API quota usage.
- **Structured Output Verification**: Enforces Gemini model responses to strictly adhere to a Pydantic schema containing:
  - `startup_name`
  - `startup_website`
  - `brief_description`
  - `news_summary`
- **Error and Content Filtering**: Gracefully ignores general industry news, broad policy articles, or entries where a specific AgTech startup cannot be identified.
- **Free-Tier Protection**: Proactively manages API request rates (delaying calls to fit comfortably under the Gemini API 15 Requests Per Minute free-tier threshold) and handles `429 RESOURCE_EXHAUSTED` HTTP errors with an exponential backoff retry handler.

---

## Technical Specifications & Tech Stack

- **Language**: Python 3.10+
- **Feeds Engine**: `feedparser`
- **Database Engine**: `pandas` + `openpyxl` (Excel)
- **AI Processing**: Google Gemini 2.5 Flash (via the modern `google-genai` Python library)

---

## Setup & Installation

### 1. Clone the repository / Open workspace
Ensure you are inside the project directory:
```bash
cd /Users/nanthithavenkatachapathy/Desktop/agri_startup
```

### 2. Create and Activate Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## API Key Configuration

To connect with the Gemini API, you need to configure your `GEMINI_API_KEY` environment variable. 

#### On macOS / Linux (Terminal)
Run the following command to set your API Key for the current session:
```bash
export GEMINI_API_KEY="<YOUR_GEMINI_API_KEY_HERE>"
```

To make this variable permanent, add it to your shell configuration profile (e.g., `~/.zshrc` or `~/.bash_profile`):
```bash
echo 'export GEMINI_API_KEY="<YOUR_GEMINI_API_KEY_HERE>"' >> ~/.zshrc
source ~/.zshrc
```

#### On Windows (PowerShell)
```powershell
$env:GEMINI_API_KEY="<YOUR_GEMINI_API_KEY_HERE>"
```

---

## Running the Tracker

Simply run the tracker script using the Python interpreter in your virtual environment:
```bash
python3 tracker.py
```
Or directly without activating:
```bash
.venv/bin/python3 tracker.py
```

Upon execution:
- It checks for the existence of `agtech_startups.xlsx`. If missing, it will initialize the file with the columns: `['Startup Name', 'Startup Website', 'Source URL', 'Brief Description', 'News Summary', 'Date Tracked']`.
- Logs will trace each step of the pipeline.

---

## Automation & Scheduling

This script is designed to be self-contained and run on a schedule using a Cron job or GitHub Actions.

### Setting up a local Cron Job (macOS/Linux)
Open your crontab configuration file:
```bash
crontab -e
```

Add a line to execute the script daily at 9:00 AM (ensuring you supply the absolute paths to the python interpreter and the project folder):
```cron
0 9 * * * cd /Users/nanthithavenkatachapathy/Desktop/agri_startup && GEMINI_API_KEY="<YOUR_GEMINI_API_KEY_HERE>" .venv/bin/python3 tracker.py >> tracker.log 2>&1
```

### Setting up GitHub Actions
Create a folder structure `.github/workflows/` and define a workflow file `tracker_run.yml`:
```yaml
name: Run AgTech Discovery Tracker

on:
  schedule:
    - cron: '0 9 * * *' # Daily at 9:00 AM UTC
  workflow_dispatch: # Allows manual trigger

jobs:
  run-tracker:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install Dependencies
        run: |
          pip install -r requirements.txt

      - name: Run Tracker
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: |
          python tracker.py

      - name: Commit and Push Changes
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          git add agtech_startups.xlsx
          git commit -m "Auto-update tracked AgTech startups [skip ci]" || echo "No changes to commit"
          git push
```
*(Make sure to add your API Key to the repository secrets as `GEMINI_API_KEY`)*
