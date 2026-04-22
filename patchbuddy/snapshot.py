import os
import hashlib
from datetime import datetime
from pathlib import Path
from .analyzer.python_analyzer import PythonAnalyzer
from .analyzer.js_analyzer import JSAnalyzer
from .analyzer.excel_analyzer import ExcelAnalyzer
from .analyzer.csv_analyzer import CSVAnalyzer


class AuditSnapshot:
    def __init__(self, project_root, ignored_files=None):
        self.project_root = Path(project_root).resolve()
        self.ignore_patterns = [
            ".audit", "__pycache__", "node_modules", ".git", ".venv", "venv", ".idea", ".vscode"
        ]
        # Extra per-file ignores loaded from config
        self.ignored_files = set(ignored_files or [])

        self.py_analyzer = PythonAnalyzer()
        self.js_analyzer = JSAnalyzer()
        self.excel_analyzer = ExcelAnalyzer()
        self.csv_analyzer = CSVAnalyzer()

    def set_ignored_files(self, ignored_files):
        """Update ignore list at runtime (called when config changes)."""
        self.ignored_files = set(ignored_files or [])

    def _should_ignore(self, path):
        for pattern in self.ignore_patterns:
            if pattern in path.parts:
                return True
        rel = str(path.relative_to(self.project_root))
        if rel in self.ignored_files:
            return True
        return False

    def generate_hash(self, filepath):
        hasher = hashlib.md5()
        try:
            with open(filepath, 'rb') as f:
                buf = f.read()
                hasher.update(buf)
            return hasher.hexdigest()
        except Exception:
            return None

    def capture(self):
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "files": {}
        }

        for path in self.project_root.rglob("*"):
            if path.is_file() and not self._should_ignore(path):
                rel_path = str(path.relative_to(self.project_root))
                file_hash = self.generate_hash(path)

                snapshot["files"][rel_path] = {
                    "hash": file_hash,
                    "size": path.stat().st_size,
                    "last_modified": path.stat().st_mtime,
                    "ext": path.suffix.lower()
                }

                self._enrich_file_data(path, snapshot["files"][rel_path])

        return snapshot

    def _enrich_file_data(self, path, file_data):
        ext = path.suffix.lower()
        if ext == ".py":
            analysis = self.py_analyzer.analyze(path)
            file_data.update(analysis)
        elif ext in [".js", ".ts", ".jsx", ".tsx"]:
            analysis = self.js_analyzer.analyze(path)
            file_data.update(analysis)
        elif ext == ".xlsx":
            analysis = self.excel_analyzer.analyze(path)
            file_data.update(analysis)
        elif ext == ".csv":
            analysis = self.csv_analyzer.analyze(path)
            file_data.update(analysis)
