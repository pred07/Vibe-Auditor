# PatchBuddy 🛡️

**PatchBuddy** is a real-time, always-on static audit utility designed to protect your codebase from silent regressions, code corruption, and accidental deletions while working with AI coding agents.

It monitors your files in the background and provides deep structural analysis for Python, JavaScript, Excel, and CSV files, ensuring that your core functions, data schemas, and formulas stay intact.

---

## ✨ Features

- 🕵️ **Deep Structural Audit**: Goes beyond file hashes to track removed methods, class signatures, import changes, and even dropped `try/except` blocks.
- 📊 **Excel & CSV Integrity**: Monitors column ordering, formula overwrites, sheet deletions, and data type schema drift.
- 🔒 **Locking Modes**: Lock your project into `SAFE`, `FEATURE`, or `FIX` modes to prevent AI agents from making unwanted destructive changes.
- 🤖 **Agent Context**: Generate one-click, high-density context blocks to paste into your next AI prompt, instructing the agent on exactly what is working and what needs fixing.
- 📈 **Health Scoring**: Get an instant `0-10` health score for your project after every change.
- 🧹 **Storage Management**: Auto-cleanup rules to keep the `.audit/` folder lean, with detailed usage breakdowns.

---

## 🚀 Getting Started

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start Monitoring
Run PatchBuddy in your project root:
```bash
python -m audit.cli start
```

---

## 🛠️ Commands

| Command | Description |
| :--- | :--- |
| `status` | Show project health score and summary of recent changes. |
| `report` | Generate a detailed regression report. |
| `report detail` | View a granular, per-function/per-column differential breakdown. |
| `suggest` | Generate a context-aware prompt block for your AI agent. |
| `mode <type>` | Set a project lock mode (see below). |
| `storage` | Show `.audit/` folder disk usage. |
| `clear <type>` | Prune snapshots, logs, or wipe history. |
| `history` | View a timeline of all past snapshots and health scores. |
| `protect <file>` | Mark a file as critical so its functions are always verified. |
| `ignore <file>` | Exclude a file from monitoring. |

---

## 🔐 Project Modes

PatchBuddy allows you to "lock" your code's behavior:

- **`mode safe`**: The strictest mode. No existing functions, classes, or columns can be removed or renamed.
- **`mode feature`**: Allows adding new functions or code, but prevents modification or deletion of existing "working" components.
- **`mode fix <file>`**: Locks the entire project *except* for one specific file you are currently debugging.
- **`mode off`**: Normal real-time monitoring without strict enforcement.

---

## 📁 Storage & Cleanup

PatchBuddy keeps snapshots in the `.audit/` folder. To prevent bloat, you can configure limits or manually purge data:

- `clear snapshots`: Keeps only the last N snapshots (default 50).
- `clear history`: Purges all report text files and session logs.
- `clear all`: Resets the audit state entirely.

*Auto-cleanup is enabled by default and will keep your folder size in check.*

---

## 📝 Session Audit Trail

Every command you type in the PatchBuddy shell is logged with a timestamp in `.audit/session.log`. Use `log session` to review your activity or debug a complex patch session.

---

> *"Built for developers who want to move fast without breaking things."*  
> **By ./0xbrijith | [GitHub](https://github.com/pred07)**
