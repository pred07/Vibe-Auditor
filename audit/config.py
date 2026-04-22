"""
audit/config.py
Manages .audit/config.json — persists mode, protect list, ignore list, locked snapshot.
"""
import json
from pathlib import Path


class AuditConfig:
    def __init__(self, audit_dir: Path):
        self.config_file = audit_dir / "config.json"
        self._data = self._load()

    def _load(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "mode": None,          # None | "safe" | "feature" | "fix"
            "mode_file": None,     # used when mode == "fix"
            "protected": [],       # manually protected filenames
            "ignored": [],         # filenames to exclude from snapshots
            "locked_snapshot": None,  # snapshot file path used when mode locked
            "max_snapshots": 50,
            "max_log_age_days": 7,
            "max_report_count": 20,
            "auto_cleanup": True
        }

    def save(self):
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, indent=2)

    # ── Mode ────────────────────────────────────────────────────────────────

    @property
    def mode(self):
        return self._data.get("mode")

    @property
    def mode_file(self):
        return self._data.get("mode_file")

    @property
    def locked_snapshot(self):
        return self._data.get("locked_snapshot")

    def set_mode(self, mode, mode_file=None, locked_snapshot_path=None):
        """Set active mode. Pass mode=None to clear."""
        self._data["mode"] = mode
        self._data["mode_file"] = mode_file
        if locked_snapshot_path is not None:
            self._data["locked_snapshot"] = str(locked_snapshot_path)
        self.save()

    def mode_description(self):
        m = self.mode
        if m is None:
            return "off (normal monitoring)"
        if m == "safe":
            return "SAFE — all functions, classes, and columns are locked"
        if m == "feature":
            return "FEATURE — new additions allowed, existing items locked"
        if m == "fix":
            f = self.mode_file or "<unknown>"
            return f"FIX — only '{f}' may change, everything else is locked"
        return m

    # ── Protected files ──────────────────────────────────────────────────────

    @property
    def protected(self):
        return list(self._data.get("protected", []))

    def protect(self, filename):
        if filename not in self._data["protected"]:
            self._data["protected"].append(filename)
            self.save()
            return True
        return False  # already protected

    def unprotect(self, filename):
        before = len(self._data["protected"])
        self._data["protected"] = [f for f in self._data["protected"] if f != filename]
        if len(self._data["protected"]) != before:
            self.save()
            return True
        return False

    # ── Ignored files ────────────────────────────────────────────────────────

    @property
    def ignored(self):
        return list(self._data.get("ignored", []))

    def ignore(self, filename):
        if filename not in self._data["ignored"]:
            self._data["ignored"].append(filename)
            self.save()
            return True
        return False

    def unignore(self, filename):
        before = len(self._data["ignored"])
        self._data["ignored"] = [f for f in self._data["ignored"] if f != filename]
        if len(self._data["ignored"]) != before:
            self.save()
            return True
        return False

    # ── Cleanup Settings ───────────────────────────────────────────────────

    @property
    def max_snapshots(self):
        return self._data.get("max_snapshots", 50)

    @max_snapshots.setter
    def max_snapshots(self, val):
        self._data["max_snapshots"] = int(val)
        self.save()

    @property
    def max_log_age_days(self):
        return self._data.get("max_log_age_days", 7)

    @max_log_age_days.setter
    def max_log_age_days(self, val):
        self._data["max_log_age_days"] = int(val)
        self.save()

    @property
    def max_report_count(self):
        return self._data.get("max_report_count", 20)

    @max_report_count.setter
    def max_report_count(self, val):
        self._data["max_report_count"] = int(val)
        self.save()

    @property
    def auto_cleanup(self):
        return self._data.get("auto_cleanup", True)

    @auto_cleanup.setter
    def auto_cleanup(self, val):
        self._data["auto_cleanup"] = bool(val)
        self.save()
