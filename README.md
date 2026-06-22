# AgriScout AI — Automated Startup Discovery & Market Intelligence System

AgriScout AI is a production-ready, full-stack intelligence platform designed for venture capitalists, accelerators, agriculture investors, and researchers. It automatically scrapes, monitors, categorizes, and tracks emerging agricultural technology (AgTech) startups from news portals, funding logs, and startup blogs.

The system uses **FastAPI** for API routes, **Next.js + TypeScript + Tailwind + Recharts** for a visual dashboard, and **Google Gemini 2.5 Flash** for metadata extraction, text categorization, semantic description similarity, and natural language database querying.

---

## 1. System Architecture & Diagram

The platform splits operations into a background scheduled crawler, a FastAPI REST server, and a Next.js single-page application.

```mermaid
flowchart TD
    %% Define Styles
    classDef client fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#f8fafc;
    classDef server fill:#0f172a,stroke:#10b981,stroke-width:2px,color:#f8fafc;
    classDef storage fill:#0f172a,stroke:#f59e0b,stroke-width:2px,color:#f8fafc;
    classDef external fill:#0f172a,stroke:#64748b,stroke-width:2px,color:#f8fafc;

    subgraph FE ["💻 Frontend Client (Next.js & TypeScript)"]
        UI["🖥️ React Dashboard UI"]
        CH["📊 Recharts Analytics Panel"]
        QA["💬 AI Chat Widget"]
        SIM["🔍 Similarity Drawer"]
    end
    class FE,UI,CH,QA,SIM client;

    subgraph BE ["⚙️ Backend API Server (FastAPI & Uvicorn)"]
        API["🔌 REST API Endpoints"]
        SCH["⏱️ APScheduler (Cron Job)"]
        SCR["🕷️ Scraper & Collector"]
        FUZ["⚖️ RapidFuzz Deduplication"]
        EMB["🧠 Embedding similarity engine"]
        RPT["📄 ReportLab PDF Compiler"]
    end
    class BE,API,SCH,SCR,FUZ,EMB,RPT server;

    subgraph DB ["📁 Database Storage (Local Filesystem)"]
        EXCEL[("Excel DB: agtech_startups.xlsx")]
        EMB_CACHE[("JSON Cache: startup_embeddings.json")]
    end
    class DB,EXCEL,EMB_CACHE storage;

    subgraph EXT ["🌐 External Services"]
        GNEWS["📰 Google News RSS Feed"]
        GEMINI["♊ Google Gemini 2.5 Flash API"]
    end
    class EXT,GNEWS,GEMINI external;

    %% Flows
    SCH -->|Triggers Scrape Daily/6h| SCR
    SCR -->|Reads Feeds| GNEWS
    SCR -->|Deduplicates URL| EXCEL
    SCR -->|Structured extraction| GEMINI
    SCR -->|Fuzzy name duplicate check| FUZ
    SCR -->|Save rows progressively| EXCEL

    UI -->|GET /api/startups| API
    UI -->|GET /api/analytics| API
    UI -->|POST /api/chat| API
    UI -->|GET /api/startups/{id}/similar| API
    UI -->|GET /api/report/weekly| API

    API -->|Load & CRUD| EXCEL
    API -->|Embedding cosine distance| EMB
    EMB -->|Request embeddings| GEMINI
    EMB -->|Cache vectors| EMB_CACHE
    API -->|Inject data context Q&A| GEMINI
    API -->|Compile report flow| RPT
    RPT -->|Load rows| EXCEL
```

---

## 2. Use Case Diagram

The use case diagram illustrates user dashboard operations, background cron scheduler runs, and downstream dependencies on the Gemini AI service.

```mermaid
flowchart LR
    %% Define Styles
    classDef actorStyle fill:#1e293b,stroke:#64748b,stroke-width:2px,color:#f8fafc;
    classDef usecaseStyle fill:#0f172a,stroke:#10b981,stroke-width:2px,color:#f8fafc;
    classDef systemUsecase fill:#0f172a,stroke:#f59e0b,stroke-width:2px,color:#f8fafc;

    %% Actors
    User["👤 Venture Capitalist / Researcher"]:::actorStyle
    Cron["🤖 APScheduler Background Cron"]:::actorStyle
    Gemini["♊ Google Gemini AI Services"]:::actorStyle

    subgraph SystemBoundary ["AgriScout AI Boundary"]
        UC1(["📊 View Tracked Startups & Charts"]):::usecaseStyle
        UC2(["🔍 Search & Filter Startup Logs"]):::usecaseStyle
        UC3(["✨ Find Semantically Similar Startups"]):::usecaseStyle
        UC4(["💬 Consult AI Chat Assistant"]):::usecaseStyle
        UC5(["➕ Add Startup Entry Manually"]):::usecaseStyle
        UC6(["🗑️ Delete Startup Profile"]):::usecaseStyle
        UC7(["📥 Download PDF weekly report"]):::usecaseStyle
        UC8(["⚡ Trigger Manual News Crawl"]):::usecaseStyle
        UC9(["⏱️ Periodic Scraping Job (6h)"]):::systemUsecase
        UC10(["🧠 Extract & Categorize Metadata"]):::systemUsecase
        UC11(["⚖️ Verify Fuzzy duplicate check"]):::systemUsecase
    end

    %% User Interactions
    User --> UC1
    User --> UC2
    User --> UC3
    User --> UC4
    User --> UC5
    User --> UC6
    User --> UC7
    User --> UC8

    %% System Interactions
    Cron --> UC9
    UC9 --> UC10
    UC9 --> UC11

    %% AI dependencies
    UC10 --> Gemini
    UC3 --> Gemini
    UC4 --> Gemini
```

---

## 3. Class Diagram

The class diagram maps the modular object structures, models, and dependencies in the Python backend.

```mermaid
classDiagram
    class Startup {
        +int id
        +string startup_name
        +string startup_website
        +string country
        +string category
        +string brief_description
        +string funding_amount
        +string funding_stage
        +string news_type
        +string source_url
        +string news_summary
        +string date_tracked
    }

    class DatabaseManager {
        +ensure_db_initialized() void
        +read_startups() List~Startup~
        +add_startup(startup_data: dict) bool
        +delete_startup(row_index: int) bool
        +check_duplicate(name: string, website: string, list: List) bool
        -clean_domain(url: string) string
    }

    class ScraperEngine {
        +RSS_BASE_URL string
        +KEYWORDS List~string~
        +fetch_all_feeds() List~dict~
        +extract_startup_details(client: Client, title: string, summary: string) StartupDiscovery
        +run_discovery_pipeline() void
    }

    class SimilarityEngine {
        +EMBEDDINGS_FILE string
        +get_similarity_cache() dict
        +save_similarity_cache(cache: dict) void
        +get_embedding(client: Client, text: string) List~float~
        +get_similar_startups(client: Client, name: string, list: List) List~dict~
    }

    class ChatAssistant {
        +handle_chat_query(client: Client, query: string, list: List) string
    }

    class PDFGenerator {
        +generate_weekly_report_pdf(list: List) BytesIO
    }

    ScraperEngine ..> DatabaseManager : "Saves discovered rows"
    SimilarityEngine ..> DatabaseManager : "Reads description context"
    ChatAssistant ..> DatabaseManager : "Queries rows for context"
    PDFGenerator ..> DatabaseManager : "Tabulates report summaries"
```

---

## 4. Sequence Diagram (News Discovery & AI Extraction)

This diagram tracks the lifecycle of an article discovery run from scheduler execution to database insertion.

```mermaid
sequenceDiagram
    autonumber
    participant Scheduler as Background Scheduler
    participant Scraper as Scraper Engine
    participant GNews as Google News RSS
    participant DB as Database Manager
    participant Gemini as Gemini 2.5 Flash
    participant Excel as Excel Database (.xlsx)

    Scheduler->>Scraper: run_discovery_pipeline()
    activate Scraper
    Scraper->>DB: read_startups()
    DB-->>Scraper: list of existing startups & URLs
    Scraper->>GNews: Fetch feeds for keywords
    GNews-->>Scraper: list of unique news articles
    
    loop For each new article link
        alt Link already in existing URLs
            Scraper->>Scraper: Skip (Deduplicated by URL)
        else Link is unique
            Scraper->>Gemini: generate_content(title, summary, Pydantic schema)
            activate Gemini
            Gemini-->>Scraper: StartupDiscovery (Structured JSON)
            deactivate Gemini
            
            alt startup_name is 'Unknown'
                Scraper->>Scraper: Skip gracefully
            else Startup name identified
                Scraper->>DB: check_duplicate(extracted_name, extracted_website)
                DB-->>Scraper: True / False (Fuzzy & Domain check)
                
                alt Duplicate found
                    Scraper->>Scraper: Skip duplicate profile
                else Completely new startup
                    Scraper->>DB: add_startup(Startup data row)
                    DB->>Excel: Append row and save
                    Excel-->>DB: Success
                    DB-->>Scraper: Success
                end
            end
        end
    end
    deactivate Scraper
```

---

## 5. Activity Diagram (User UI Dashboard Interactions)

Describes state transitions and processing branches during dashboard interaction.

```mermaid
stateDiagram-v2
    [*] --> IdleDashboard
    
    state IdleDashboard {
        [*] --> ViewDashboard
        ViewDashboard --> SearchInput : User types search term
        SearchInput --> FilterCards : Client filters visible cards
        ViewDashboard --> SortSelect : User changes sorting option
        SortSelect --> RenderSortedCards : Re-order and render cards
    }

    state TriggerCrawl {
        [*] --> PostRunRequest
        PostRunRequest --> LockThread : Check tracker run lock
        LockThread --> ScraperRunning : Start background Scraper thread
        ScraperRunning --> UpdatePollStatus : Frontend polls GET /api/tracker/status
        UpdatePollStatus --> FinishedRun : Thread releases lock
    }

    state ModalInteraction {
        [*] --> OpenAddModal
        OpenAddModal --> FillFormInputs : Name, Desc, Funding, Category
        FillFormInputs --> SubmitForm : Click Save Discovery
        SubmitForm --> AddRowRequest : POST /api/startups
        AddRowRequest --> ExcelPersist : Update Excel sheet
        ExcelPersist --> RefreshGrid : Reload dashboard cards
    }

    state ChatInteraction {
        [*] --> OpenChatPanel
        OpenChatPanel --> UserQuery : Type and submit prompt
        UserQuery --> LoadRows : Backend reads Excel data
        LoadRows --> PromptGemini : Call Gemini with data context
        PromptGemini --> RenderReply : Markdown formatted AI response
    }
    
    IdleDashboard --> TriggerCrawl : Click "Scan Industry News"
    IdleDashboard --> ModalInteraction : Click "Add Startup Manually"
    IdleDashboard --> ChatInteraction : Open & chat with AI widget
```

---

## 6. Project Setup & Execution

### Prerequisites
- Python 3.10+
- Node.js v18+

### 1. Setup Backend
Activate the virtual environment, install dependencies, configure the environment variable, and boot the server:
```bash
# Navigate to root folder
cd /Users/nanthithavenkatachapathy/Desktop/agri_startup

# Activate virtual env
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure Gemini Key
export GEMINI_API_KEY="<YOUR_GEMINI_API_KEY_HERE>"

# Launch FastAPI web server on port 8001
uvicorn backend.main:app --host 127.0.0.1 --port 8001
```

### 2. Setup Frontend
Install NPM node modules and run the Next.js development server:
```bash
# Open a second terminal window
cd /Users/nanthithavenkatachapathy/Desktop/agri_startup/frontend

# Install dependencies
npm install

# Run dev server
npm run dev
```

Next.js will start the dashboard at **`http://localhost:3001`**. Open this address in your web browser to interact with the platform.
