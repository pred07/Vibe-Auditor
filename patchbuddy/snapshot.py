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
                while chunk := f.read(4096):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return None

    def capture(self):
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "files": {}
        }

        # Optimized traversal using os.walk to prune ignored directories early
        for root, dirs, files in os.walk(self.project_root):
            root_path = Path(root)
            
            # Prune directories in-place to prevent os.walk from entering them
            dirs_to_remove = []
            for d in dirs:
                if d in self.ignore_patterns:
                    dirs_to_remove.append(d)
                else:
                    # Check if the relative path of the directory is in ignored_files
                    rel_dir = str((root_path / d).relative_to(self.project_root))
                    if rel_dir in self.ignored_files:
                        dirs_to_remove.append(d)
            
            for d in dirs_to_remove:
                dirs.remove(d)

            for filename in files:
                path = root_path / filename
                rel_path = str(path.relative_to(self.project_root))
                
                # Double check ignored files (for files specifically)
                if rel_path in self.ignored_files:
                    continue
                    
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
