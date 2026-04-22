# PatchBuddy

PatchBuddy is a professional static audit utility designed to monitor project integrity in real-time. It specializes in detecting silent regressions, code hallucinations, and data corruption during development sessions, particularly when utilizing automated AI coding agents.

## Core Value Proposition

PatchBuddy addresses the critical risks of automated code generation by providing a deep audit layer that catches:
- Hallucination Detection: Identifies when an agent adds non-existent functions or references.
- Silent Regressions: Flags the removal of core methods, signature changes, or deleted error handling blocks.
- Tracker Consolidation Issues: Monitors Excel/CSV files for column renaming, row loss, or formula overwrites.
- Syntax and Schema Errors: Real-time alerts for broken code or data type drift.

## Technical Monitoring

### Supported File Types
- Programming: .py, .js, .ts
- Web: .html, .css
- Data: .xlsx, .csv

### Audit Checklist Categories

#### Hallucination Detection
- Unrequested Additions: Identification of functions or logic blocks that were never part of the original project scope.
- Assumption Fill: Detection of "fake" column data or assumed cell values in spreadsheets.
- Redundant Variation: Alerts for duplicate functions added with slight naming or signature variations.
- Dead Code Insertion: Tracking of orphaned or unreachable code blocks inserted without request.

#### Python Analysis
- Removal or renaming of class methods.
- Modification of function signatures (argument mismatch).
- Deletion of try/except blocks (loss of error handling).
- Removal of required import statements.

#### JavaScript and TypeScript Analysis
- Tracking of exported functions and class definitions.
- Monitoring of API endpoint strings in fetch or axios calls.

#### Web Interface Integrity (HTML/CSS)
- Structural Shifts: Monitoring for unauthorized changes to semantic HTML5 hierarchies.
- Identity Tracking: Alerts for renaming or deletion of critical element IDs used in scripts.
- Styling Regressions: Tracking of CSS rule deletions or global variable overrides.

#### Spreadsheet and Data Integrity
- Formula Protection: Detects when spreadsheet formulas are replaced by hardcoded values.
- Column Integrity: Tracks renaming, reordering, or count mismatches.
- Data Type Drift: Alerts when numeric columns transition to text or when date formats change.
- Sheet Integrity: Monitors for deleted, renamed, or unauthorized sheet additions.

## Workflow Example

1. Start PatchBuddy in your project root:
   `python -m audit.cli start`
2. Allow your AI Agent to perform modifications.
3. Check the project health:
   `patchbuddy > status`
4. If regressions are found, generate instructions for the agent:
   `patchbuddy > suggest`
5. Paste the output back into the agent prompt to trigger fixes.

## System Behavior

### Snapshot Trigger Logic
PatchBuddy utilizes a 2-second debounce timer. When a file change is detected, the utility waits for 2 seconds of inactivity before triggering a snapshot. This prevents excessive disk usage during rapid save operations.

### Automated Cleanup
To maintain a lean footprint, PatchBuddy implements the following default cleanup rules:
- Snapshot Retention: Maximum 50 files.
- Log Retention: 7 days.
- Report Retention: Last 20 generated reports.

## Installation

### Local Usage
Install dependencies within your project:
```bash
pip install -r requirements.txt
```

### Global Utility
Install PatchBuddy system-wide in development mode:
```bash
pip install -e .
```

## Command Reference

| Command | Subcommand | Description |
| :--- | :--- | :--- |
| status | - | Displays project health score and a summary of regressions. |
| report | - | Generates a standard regression report in the .audit directory. |
| report | detail | Provides a granular, per-function differential breakdown. |
| suggest | - | Generates a clean instruction block for AI agent remediation. |
| diff | - | Displays technical differences between the last two snapshots. |
| history | - | Shows a timeline table of all past snapshots and health scores. |
| mode | safe | The strictest mode; prevents any deletion or renaming of existing items. |
| mode | feature | Allows code additions but protects all existing definitions from change. |
| mode | fix <file> | Focuses audit on one file; ensures zero collateral damage elsewhere. |
| mode | off | Disables strict audit enforcement. |
| storage | - | Shows disk usage statistics for the .audit directory. |
| clear | snapshots | Prunes old snapshot files based on retention limits. |
| clear | history | Deletes all generated reports and the session command log. |
| clear | all | Wipes the entire .audit directory state. |
| log | session | Shows the timestamped command history of the current session. |
| protect | <file> | Marks a specific file for mandatory inclusion in all audit reports. |
| ignore | <file> | Excludes a file or directory from the monitoring scope. |

## File Locations

- Audit Data: `.audit/`
- AI Agent Context: `.audit/context.md` (Self-updating file containing current health status for agent prompts)
- Session Command Log: `.audit/session.log`
- Configuration: `.audit/config.json`

---
By ./0xbrijith | github.com/pred07
