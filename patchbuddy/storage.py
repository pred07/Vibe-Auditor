import os
import json
import shutil
from datetime import datetime
from pathlib import Path


class AuditStorage:
    def __init__(self, project_root):
        self.project_root = Path(project_root).resolve()
        self.audit_dir = self.project_root / ".audit"
        self.snapshots_dir = self.audit_dir / "snapshots"
        self.diffs_dir = self.audit_dir / "diffs"
        self.reports_dir = self.audit_dir / "reports"
        self.baseline_file = self.audit_dir / "baseline.json"
        self.context_file = self.audit_dir / "context.md"
        self.session_log_file = self.audit_dir / "session.log"

        self._ensure_dirs()

    def _ensure_dirs(self):
        for d in [self.snapshots_dir, self.diffs_dir, self.reports_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def save_snapshot(self, data):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"snapshot_{timestamp}.json"
        filepath = self.snapshots_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        return filepath

    def log_session_command(self, command):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.session_log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {command}\n")

    def get_session_history(self):
        if not self.session_log_file.exists():
            return []
        with open(self.session_log_file, 'r', encoding='utf-8') as f:
            return f.readlines()

    def get_storage_usage(self):
        def get_dir_info(directory):
            files = list(directory.glob("*"))
            total_size = sum(f.stat().st_size for f in files if f.is_file())
            return {"count": len(files), "size": total_size}

        usage = {
            "snapshots": get_dir_info(self.snapshots_dir),
            "reports": get_dir_info(self.reports_dir),
            "diffs": get_dir_info(self.diffs_dir),
            "total_size": 0
        }
        usage["total_size"] = usage["snapshots"]["size"] + usage["reports"]["size"] + usage["diffs"]["size"]
        if self.session_log_file.exists():
            usage["total_size"] += self.session_log_file.stat().st_size
        return usage

    def clear_snapshots(self, keep_count=0):
        files = sorted(self.snapshots_dir.glob("snapshot_*.json"))
        to_delete = files[:-keep_count] if keep_count > 0 else files
        for f in to_delete:
            f.unlink()
        return len(to_delete)

    def clear_reports(self, keep_count=0):
        files = sorted(self.reports_dir.glob("report_*.txt"))
        to_delete = files[:-keep_count] if keep_count > 0 else files
        for f in to_delete:
            f.unlink()
        return len(to_delete)

    def clear_history(self):
        """Clears reports and session logs."""
        count = self.clear_reports(0)
        if self.session_log_file.exists():
            self.session_log_file.unlink()
        return count

    def clear_all(self):
        if self.audit_dir.exists():
            shutil.rmtree(self.audit_dir)
            self._ensure_dirs()
            return True
        return False

    def set_baseline(self, snapshot_path):
        """Copies a snapshot to be the permanent baseline."""
        if not snapshot_path.exists():
            return False
        shutil.copy2(snapshot_path, self.baseline_file)
        return True

    def get_baseline(self):
        """Returns the baseline snapshot data or None."""
        if not self.baseline_file.exists():
            return None
        return self.load_snapshot(self.baseline_file)

    def get_latest_snapshots(self, count=2):
        files = sorted(self.snapshots_dir.glob("snapshot_*.json"), reverse=True)
        return files[:count]

    def get_all_snapshots(self):
        """Return all snapshot files sorted newest first."""
        return sorted(self.snapshots_dir.glob("snapshot_*.json"), reverse=True)

    def load_snapshot(self, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_snapshot_meta(self, filepath):
        """Load only the top-level metadata without full file list (fast)."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {
            "timestamp": data.get("timestamp", ""),
            "trigger": data.get("trigger", "auto"),
            "file_count": len(data.get("files", {})),
        }

    def save_report(self, report_text):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{timestamp}.txt"
        filepath = self.reports_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_text)
        return filepath

    def update_context(self, context_text):
        with open(self.context_file, 'w', encoding='utf-8') as f:
            f.write(context_text)

    def _rotate_snapshots(self, limit=50):
        """Now handled externally or by clear_snapshots logic."""
        files = sorted(self.snapshots_dir.glob("snapshot_*.json"))
        if len(files) > limit:
            for f in files[:-limit]:
                f.unlink()

    def get_relative_path(self, absolute_path):
        try:
            return str(Path(absolute_path).relative_to(self.project_root))
        except ValueError:
            return absolute_path
