# PatchBuddy

[![PyPI Version](https://img.shields.io/pypi/v/patchbuddy.svg)](https://pypi.org/project/patchbuddy/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Installation

```bash
pip install patchbuddy
```

## Quick Start Workflow

Maintain project integrity with this standard 11-step development cycle:

1. **Install PatchBuddy**: `pip install patchbuddy`
2. **Navigate to your project folder**: `cd your-project-path`
3. **Initialize the watcher**: `audit start` (Leave this terminal open)
4. **Set an operational mode before the agent runs**: `patchbuddy > mode safe`
5. **Generate agent context**: `patchbuddy > suggest`
6. **Paste context into agent prompt**: Copy the `suggest` output and paste it at the start of your AI prompt.
7. **Agent Execution**: Let the AI agent perform its work while PatchBuddy auto-snapshots changes.
8. **Verify Health**: Check the status after the agent finishes: `patchbuddy > status`
9. **Inspect Failures**: If regressions are found, use: `patchbuddy > report detail`
10. **Refine Instructions**: Run `patchbuddy > suggest` again to generate a fix-aware context block.
11. **Iterate**: Paste the new context into the agent and repeat until the health score is 10/10.

---

## Core Value Proposition

PatchBuddy addresses the critical risks of automated code generation by providing a deep audit layer that catches:
- Hallucination Detection: Identifies when an agent adds non-existent functions or references.
- Silent Regressions: Flags the removal of core methods, signature changes, or deleted error handling blocks.
- Tracker Consolidation Issues: Monitors Excel/CSV files for column renaming, row loss, or formula overwrites.
- Syntax and Schema Errors: Real-time alerts for broken code or data type drift.

---

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

---

## System Behavior

### Snapshot Trigger Logic
PatchBuddy utilizes a 2-second debounce timer. When a file change is detected, the utility waits for 2 seconds of inactivity before triggering a snapshot. This prevents excessive disk usage during rapid save operations.

### Automated Cleanup
To maintain a lean footprint, PatchBuddy implements the following default cleanup rules:
- Snapshot Retention: Maximum 50 files.
- Log Retention: 7 days.
- Report Retention: Last 20 generated reports.

---

## Command Reference

| Command | Subcommand | Description |
| :--- | :--- | :--- |
| status | - | Displays project health score and a summary of regressions. |
| report | - | Generates a standard regression report in the .audit directory. |
| report | detail | Provides a granular, per-function differential breakdown. |
| promptbuddy | - | Generates a high-fidelity audit prompt for fixes (strictly read-only). |
| suggest | <verbose> | Generates a clean instruction block for AI agent remediation. |
| suggest | holistic | Generates a final lifecycle audit prompt covering the entire project. |
| diff | - | Displays technical differences between the last two snapshots. |
| history | - | Shows a timeline table of all past snapshots and health scores. |
| mode | safe | The strictest mode; prevents any deletion or renaming of existing items. |
| mode | feature | Allows code additions but protects all existing definitions from change. |
| mode | fix <file> | Focuses audit on one file; ensures zero collateral damage elsewhere. |
| mode | status | Displays the currently active audit mode and scope. |
| mode | off | Disables strict audit enforcement. |
| protect | <file> | Marks a specific file for mandatory inclusion in all audit reports. |
| ignore | <file> | Excludes a file or directory from the monitoring scope. |
| baseline | mark | Pins the current project state as the 'Golden Goal'. |
| baseline | status | Compares current state against the pinned Golden Baseline. |
| baseline | diff | Shows detailed structural drift from the Golden Baseline. |
| storage | - | Shows disk usage statistics for the .audit directory. |
| clear | - | Clears the terminal screen and resets the interface to the top. |
| clear | snapshots | Prunes old snapshot files based on retention limits. |
| clear | history | Deletes all generated reports and the session command log. |
| clear | all | Wipes the entire .audit directory state. |
| log | session | Shows the timestamped command history of the current session. |
| help | - | Displays the interactive command menu. |
| exit | - | Shuts down the watcher and exits the CLI. |
| protect | <file> | Marks a specific file for mandatory inclusion in all audit reports. |
| ignore | <file> | Excludes a file or directory from the monitoring scope. |

---

## File Locations

- Audit Data: `.audit/`
- AI Agent Context: `.audit/context.md` (Self-updating file containing current health status for agent prompts)
- Session Command Log: `.audit/session.log`
- Configuration: `.audit/config.json`

---

## Troubleshooting

### Command Not Recognized (Windows)
If you receive an error stating that `patchbuddy` or `audit` is not recognized after installation, your Python Scripts folder may not be in your system PATH.

**The Universal Method**: You can bypass PATH issues on any system (Windows, Mac, Linux) by running the utility directly through Python:
```bash
python -m patchbuddy.cli start
```

### Installation Warnings
If you see a yellow warning during installation mentioning that scripts are installed in a directory not on PATH, you can either add that directory to your Environment Variables or use the **Universal Method** above.

## Upgrade

To update PatchBuddy to the latest version:
```bash
pip install --upgrade patchbuddy
```

## Links
- **PyPI**: [https://pypi.org/project/patchbuddy/](https://pypi.org/project/patchbuddy/)
- **GitHub**: [https://github.com/pred07/patchbuddy](https://github.com/pred07/patchbuddy)

---
By ./0xbrijith | github.com/pred07
