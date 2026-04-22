# PatchBuddy

PatchBuddy is a local static audit utility designed for real-time monitoring of project integrity. It tracks structural changes across Python, JavaScript, Excel, and CSV files to prevent silent regressions and unauthorized code modifications during development sessions, particularly when working with automated coding agents.

## Feature Overview

PatchBuddy provides deep structural analysis beyond simple file hashing. It categorizes changes into regressions, warnings, and modifications based on a predefined architectural taxonomy.

### Python Audit
- Detection of class method removal or renaming.
- Tracking of function signature changes (added or removed arguments).
- Monitoring of error handling integrity (deletion of try/except blocks).
- Identification of import statement removals.

### JavaScript and TypeScript Audit
- Extraction and monitoring of exported functions and classes.
- Detection of changes to API endpoint strings (tracking fetch and axios calls).

### Excel and CSV Data Integrity
- Formula tracking: Detects when spreadsheet formulas are replaced by hardcoded values.
- Column integrity: Monitors for renamed columns, changed column order, or count mismatches.
- Sheet integrity: Tracks sheet deletion, renaming, or unauthorized additions.
- Data type drift: Alerts when numeric columns transition to text or when date formats change.

### Agent Context Engine
Generates sanitized, high-density context blocks optimized for AI coding agents. This allows for immediate verification of current project state and provides explicit instructions for remediation of detected regressions.

## Installation

### Local Installation
To install dependencies within a specific project directory:
```bash
pip install -r requirements.txt
```

### Global Installation (Development Mode)
To install PatchBuddy as a system-wide command-line utility:
```bash
pip install -e .
```

## Command Reference

| Command | Subcommand | Description |
| :--- | :--- | :--- |
| status | - | Displays project health score and a summary of recent regressions. |
| report | - | Generates a standard regression report saved to the .audit directory. |
| report | detail | Provides a granular differential breakdown of specific structural changes. |
| report | history | Displays a table of all past snapshots and their corresponding health scores. |
| suggest | - | Outputs a sanitized context block for use in AI agent prompts. |
| diff | - | Compares the latest two snapshots and displays the technical differences. |
| history | - | Shows a timeline of project snapshots and health metrics. |
| mode | safe | Locks all existing functions, classes, and columns; no deletions allowed. |
| mode | feature | Allows code additions but prevents modification or removal of existing items. |
| mode | fix <file> | Locks the entire project state except for the specified target file. |
| mode | off | Disables strict enforcement and returns to normal monitoring. |
| storage | - | Displays a breakdown of disk space usage within the .audit directory. |
| clear | snapshots | Removes all but the last 50 snapshots to save disk space. |
| clear | history | Deletes all generated reports and clears the session command log. |
| clear | all | Wipes the entire .audit directory and resets the utility state. |
| log | session | Displays the timestamped command history of the current session. |
| protect | <file> | Marks a specific file as critical for inclusion in all audit reports. |
| ignore | <file> | Excludes a specific file or directory from the monitoring scope. |
| help | - | Displays the command assistance menu. |
| exit | - | Terminates the interactive session and stops the background watcher. |

## Operational Modes

PatchBuddy supports state-based enforcement to guide development workflows:

1. **Safe Mode**: Enforces strict structural parity. Any removal of established functions or class methods is flagged as a critical regression.
2. **Feature Mode**: Accommodates growth by allowing new definitions while maintaining protection for existing legacy code.
3. **Fix Mode**: Concentrates audit focus on a single file, allowing rapid iteration on a specific bug while ensuring zero collateral damage to the rest of the project.

## Storage Management

Data is persisted in the `.audit` directory. The utility includes automated rotation logic to ensure the directory size remains within manageable limits. Usage metrics can be queried at any time using the storage command.

---
By ./0xbrijith | github.com/pred07
