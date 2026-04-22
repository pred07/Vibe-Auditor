# audit-watch — Implementation Plan
## A Local Static Code Audit Utility for Vibe Coders

---

## 1. Objective

Modern AI-assisted (vibe) coding causes silent regressions — agents fix one thing and break three others. Developers have no visibility into what changed, what broke, and why. This is worse for data-heavy work like Excel trackers and automation scripts where column corruption and schema drift go unnoticed.

**audit-watch** is a local, always-on background utility that:
- Silently monitors your project while agents write code
- Snapshots working state before every change
- Detects regressions, overwrites, and corruption statically (no code execution needed)
- Generates plain-English reports for developers
- Produces ready-to-paste context summaries for the next agent prompt

No LLM API. No cloud. Fully local. Works for all developer types.

---

## 2. Problem It Solves

| Problem | How audit-watch solves it |
|---|---|
| Agent fixes thing 9, breaks things 1-3 | Snapshots before/after, flags regressions |
| No memory of what was working | Timestamped snapshots stored in `.audit/` |
| Excel column corruption | Schema snapshot compares headers, types, counts |
| Format overwriting | Detects style/format drift in files |
| Patch-on-patch mess | Change history timeline shows every agent action |
| Developer has no context for next prompt | Generates `context.md` ready to paste into agent |

---

## 3. Target Users

| User Type | What They Work With |
|---|---|
| Web Developers | HTML, CSS, JS, React components |
| App Developers | Python, Java, Node.js functions and classes |
| Automation Engineers | Python scripts, shell scripts, data pipelines |
| Tracker / Excel Creators | .xlsx, .csv, formulas, column schemas |

---

## 4. Core Concepts

### 4.1 Snapshot
A frozen copy of the project state at a point in time. Captures:
- All file contents (hashed)
- Function/class signatures extracted via AST
- Data file schemas (column names, types, row counts)
- Formula inventory for Excel files

### 4.2 Diff
A comparison between two snapshots. Identifies:
- Added / removed / modified files
- Added / removed / modified functions
- Signature changes (arguments changed)
- Schema drift (columns added, removed, renamed, reordered)

### 4.3 Static Analysis
No code is executed. Analysis is purely structural:
- AST parsing for Python and JavaScript
- Regex-based parsing for HTML/CSS
- openpyxl schema inspection for Excel
- pandas shape analysis for CSV

### 4.4 Health Score
A numeric score (e.g. 8/10) based on how many tracked units are still intact after an agent run. Units are functions, columns, classes, routes — whatever was working before.

### 4.5 Report
A human-readable breakdown of what changed, what broke, and what is safe. Saved to `.audit/reports/`.

### 4.6 Context Summary
A condensed text file (`context.md`) the developer pastes into the next agent prompt. It tells the agent: here is what was working, here is what broke, do not touch these.

---

## 5. Architecture

```
audit-watch/
│
├── audit/
│   ├── __init__.py
│   ├── cli.py              ← Entry point, all commands
│   ├── watcher.py          ← File system monitor (watchdog)
│   ├── snapshot.py         ← Capture project state
│   ├── differ.py           ← Compare two snapshots
│   ├── analyzer/
│   │   ├── __init__.py
│   │   ├── python_analyzer.py    ← AST parsing for .py files
│   │   ├── js_analyzer.py        ← Regex parsing for .js/.ts files
│   │   ├── web_analyzer.py       ← HTML/CSS structure parsing
│   │   ├── excel_analyzer.py     ← openpyxl schema analysis
│   │   └── csv_analyzer.py       ← pandas shape/type analysis
│   ├── reporter.py         ← Generate health score + readable report
│   ├── suggester.py        ← Generate context.md for next agent prompt
│   └── storage.py          ← Read/write .audit/ folder
│
├── .audit/                 ← Auto-created in user project root
│   ├── snapshots/          ← Timestamped JSON snapshots
│   ├── diffs/              ← Diff results per change event
│   ├── reports/            ← Human readable reports
│   └── context.md          ← Ready-to-paste agent context
│
├── setup.py
├── requirements.txt
└── README.md
```

---

## 6. Module Breakdown

### 6.1 cli.py
Entry point using `click`. Exposes all user-facing commands.

**Commands:**
```
audit-watch --project ./path      Start background watcher
audit status                      Quick health score in terminal
audit report                      Full report printed to terminal
audit suggest                     Print context.md to terminal
audit history                     Timeline of all changes
audit snapshot                    Manual snapshot (optional)
audit compare                     Manual compare last two snapshots
```

### 6.2 watcher.py
Uses `watchdog` to monitor file system events.

**Responsibilities:**
- Watch for file save/create/delete/rename events
- Ignore `.audit/`, `__pycache__/`, `node_modules/`, `.git/`
- On significant change: trigger auto-snapshot + auto-diff
- Debounce rapid saves (wait 2 seconds before triggering)
- Log every event to `.audit/watch.log`

### 6.3 snapshot.py
Captures full project state into a structured JSON file.

**What it captures per file type:**

| File Type | What is Captured |
|---|---|
| .py | File hash, all function names + args, all class names, imports |
| .js / .ts | File hash, function names, exported names |
| .html | File hash, element count, form/button/link inventory |
| .css | File hash, rule count, class/id inventory |
| .xlsx | Sheet names, column headers per sheet, row count, formula cells |
| .csv | Column headers, row count, column data types |
| Any other | File hash, line count, last modified time |

**Snapshot file format:**
```json
{
  "timestamp": "2025-04-22T10:30:00",
  "trigger": "auto",
  "project_root": "/path/to/project",
  "files": {
    "src/main.py": {
      "hash": "abc123",
      "functions": ["process_data(df, cols)", "load_file(path)"],
      "classes": ["DataHandler"],
      "imports": ["pandas", "os"]
    },
    "data/tracker.xlsx": {
      "sheets": {
        "Sheet1": {
          "columns": ["Name", "Age", "Score"],
          "row_count": 150,
          "formulas": ["C2", "C3"]
        }
      }
    }
  }
}
```

### 6.4 differ.py
Compares two snapshot JSON files and produces a structured diff.

**What it detects:**

| Category | Detected Changes |
|---|---|
| Files | New file added, file deleted, file modified |
| Functions | Function added, function removed, function signature changed |
| Classes | Class added, class removed |
| Imports | New dependency added, dependency removed |
| Excel columns | Column added, column removed, column renamed, column reordered |
| Excel rows | Significant row count change (> 5%) |
| CSV schema | Same as Excel columns |
| Formulas | Formula cell added, removed, or overwritten |

**Diff output format:**
```json
{
  "snapshot_before": "2025-04-22T10:30:00",
  "snapshot_after": "2025-04-22T10:35:00",
  "summary": {
    "files_changed": 3,
    "functions_removed": 2,
    "functions_modified": 1,
    "columns_removed": 0,
    "health_score": 7
  },
  "regressions": [...],
  "additions": [...],
  "modifications": [...]
}
```

### 6.5 analyzer/ (Static Analysis Engine)

**python_analyzer.py**
- Uses Python built-in `ast` module
- Extracts: function names, argument lists, return annotations, class names, decorators
- Detects: renamed functions, removed functions, changed argument signatures
- No execution needed

**js_analyzer.py**
- Uses regex patterns to extract function declarations
- Handles: `function foo()`, `const foo = () =>`, `export function foo()`
- Detects: removed exports (breaking change), renamed functions

**web_analyzer.py**
- Parses HTML with `html.parser` (built-in)
- Tracks: form IDs, button names, API endpoint references in `fetch()`/`axios`
- Detects: removed form elements, changed API routes

**excel_analyzer.py**
- Uses `openpyxl` to read without executing macros
- Tracks: sheet names, column headers (row 1), data types per column, formula cells
- Detects: column header changes, sheet removal, formula overwriting

**csv_analyzer.py**
- Uses `pandas` for schema analysis
- Tracks: column names, column count, dtypes, row count
- Detects: column drift, type changes, unexpected row count drop

### 6.6 reporter.py
Reads the latest diff and generates a human-readable report.

**Health Score Calculation:**
```
tracked_units = all functions + all columns + all classes
intact_units = tracked_units still present and unchanged
health_score = (intact_units / tracked_units) * 10
```

**Report Sections:**
1. Health Score (X/10)
2. What Changed (files, functions, columns)
3. What Broke (regressions — things that existed and are now gone/changed)
4. What Was Added (new things — low risk)
5. Risk Assessment (high/medium/low per change)
6. Recommended Next Steps (plain English)

**Report saved to:** `.audit/reports/report_<timestamp>.txt`

### 6.7 suggester.py
Reads the latest report and generates `context.md`.

This file is designed to be pasted directly into the next agent prompt.

**context.md format:**
```
## Audit Context — paste this into your next agent prompt

### What is working (DO NOT MODIFY):
- process_data(df, cols) in src/main.py — verified working
- Sheet1 columns: Name, Age, Score in tracker.xlsx — verified intact

### What broke in last agent run:
- load_file(path) was REMOVED from src/main.py
- Column "Score" formula was overwritten in tracker.xlsx

### Instructions for agent:
- Restore load_file(path) function — do not remove it
- Fix formula in column C (Score) — do not overwrite other columns
- Do not rename or reorder any columns in tracker.xlsx
```

### 6.8 storage.py
Handles all `.audit/` folder operations.

**Responsibilities:**
- Create `.audit/` on first run
- Name and save snapshots with timestamps
- List available snapshots
- Load snapshot by timestamp or index
- Rotate old snapshots (keep last 50 by default)
- Write/read reports and context.md

---

## 7. Dependencies

```
watchdog        — file system monitoring
click           — CLI commands and arguments
rich            — pretty terminal output (tables, colors, progress)
openpyxl        — Excel file analysis
pandas          — CSV and data shape analysis
ast             — Python AST parsing (built-in, no install needed)
html.parser     — HTML parsing (built-in, no install needed)
re              — Regex for JS parsing (built-in, no install needed)
hashlib         — File hashing (built-in, no install needed)
json            — Snapshot storage (built-in, no install needed)
```

**requirements.txt:**
```
watchdog>=3.0.0
click>=8.0.0
rich>=13.0.0
openpyxl>=3.1.0
pandas>=2.0.0
```

---

## 8. Build Phases

### Phase 1 — Core Engine (Snapshot + Diff)
**Goal:** Get snapshot and differ working correctly. This is the foundation.

Deliverables:
- `snapshot.py` working for .py and .csv files
- `differ.py` producing structured diff JSON
- `storage.py` creating and reading `.audit/` folder
- Manual CLI test: `audit snapshot` and `audit compare`

---

### Phase 2 — Static Analyzers
**Goal:** Deep analysis per file type.

Deliverables:
- `python_analyzer.py` — AST function/class extraction
- `excel_analyzer.py` — column schema extraction
- `csv_analyzer.py` — shape and type analysis
- `js_analyzer.py` — function name extraction
- Unit tests for each analyzer

---

### Phase 3 — Background Watcher
**Goal:** Make it always-on.

Deliverables:
- `watcher.py` running silently with watchdog
- Auto-trigger snapshot on file save
- Debounce logic (2 second wait)
- Ignore patterns (.audit, node_modules, __pycache__)
- `audit-watch --project ./path` command working

---

### Phase 4 — Reporter
**Goal:** Health score and human-readable report.

Deliverables:
- `reporter.py` generating health score
- Report saved to `.audit/reports/`
- `audit status` showing quick score in terminal
- `audit report` showing full breakdown with `rich` formatting

---

### Phase 5 — Suggester + Context Generation
**Goal:** Help developer tell agent what NOT to break.

Deliverables:
- `suggester.py` reading report and generating `context.md`
- `audit suggest` printing context to terminal
- `context.md` updated after every agent run

---

### Phase 6 — History + CLI Polish
**Goal:** Full developer experience.

Deliverables:
- `audit history` showing timeline of all changes
- `rich` tables for all terminal output
- Color coding (green = safe, yellow = warning, red = regression)
- `audit-watch` startup banner showing what is being monitored

---

### Phase 7 — Packaging
**Goal:** pip installable tool.

Deliverables:
- `setup.py` with entry point for `audit` and `audit-watch`
- `README.md` with usage instructions
- `pip install audit-watch` works locally

---

## 9. Terminal Output Examples

### audit status
```
╔══════════════════════════════════╗
║  audit-watch  |  Health: 7/10   ║
╠══════════════════════════════════╣
║  Last change:  2 minutes ago    ║
║  Files tracked: 12              ║
║  Regressions:  2  ⚠             ║
║  New additions: 3               ║
╚══════════════════════════════════╝
```

### audit report
```
── AUDIT REPORT ─────────────────────────────
  Health Score: 7/10

  ✅ INTACT (8 units)
     process_data(df, cols)       src/main.py
     DataHandler class            src/main.py
     Sheet1 columns (3/3)         tracker.xlsx

  ❌ BROKEN (2 units)
     load_file(path)              REMOVED from src/main.py
     Column "Score" formula       OVERWRITTEN in tracker.xlsx

  ➕ ADDED (3 units)
     new_helper(x)                src/utils.py
     Column "Rank"                tracker.xlsx

  ⚠  RISK: HIGH
     load_file may be called by other functions — removing it likely breaks pipeline

  📋 NEXT STEPS
     1. Restore load_file(path) in src/main.py
     2. Recheck formula in tracker.xlsx column C
     3. Verify new_helper(x) does not conflict with existing logic
```

---

## 10. Key Design Decisions

| Decision | Reason |
|---|---|
| Fully local, no LLM API | Privacy, works offline, no cost |
| Static analysis only | No execution risk, works on broken/partial code |
| JSON snapshots | Human readable, easy to diff, version control friendly |
| Watchdog for monitoring | Cross platform, lightweight, battle tested |
| click for CLI | Clean API, auto help generation, easy to extend |
| rich for output | Developer friendly, readable without opening files |
| `.audit/` folder in project | Portable, dev can gitignore or commit it |

---

## 11. What audit-watch Does NOT Do

- Does not execute or run any code
- Does not send data anywhere (fully local)
- Does not fix code automatically
- Does not replace version control (complements git)
- Does not require tests to be written

---

## 12. Future Enhancements (Post MVP)

- VS Code extension wrapping the same Python engine
- Git integration (auto-snapshot on commit)
- Web UI for visual diff reports
- Support for Java, Go, Rust analyzers
- Team mode — shared `.audit/` across team members
- Pre-commit hook mode

---

*Plan version: 1.0 | Target: Local Python CLI | No external APIs*
