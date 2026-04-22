import time
import queue
import sys
from datetime import datetime
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .storage import AuditStorage
from .snapshot import AuditSnapshot
from .differ import AuditDiffer
from rich.console import Console

console = Console(highlight=False)


class AuditHandler(FileSystemEventHandler):
    def __init__(self, project_root, storage, snapshot_engine,
                 debounce_seconds=2, message_queue=None, ignored_files=None):
        self.project_root = Path(project_root).resolve()
        self.storage = storage
        self.snap_engine = snapshot_engine
        self.debounce_seconds = debounce_seconds
        self.last_trigger = 0
        self.pending_change = False
        # Thread-safe queue for buffered notifications (avoids mid-prompt prints)
        self.message_queue = message_queue if message_queue is not None else queue.Queue()
        self.ignored_files = set(ignored_files or [])

        # Take initial snapshot — print directly (no prompt yet)
        ts = datetime.now().strftime("%H:%M:%S")
        console.print(f"[dim #A0826D]  {ts}  [init] scanning project...[/dim #A0826D]")
        self.take_snapshot("initial", direct_print=True)

    def on_modified(self, event):
        if event.is_directory:
            return
        self._trigger_snapshot(event.src_path)

    def on_created(self, event):
        if event.is_directory:
            return
        self._trigger_snapshot(event.src_path)

    def on_deleted(self, event):
        if event.is_directory:
            return
        self._trigger_snapshot(event.src_path)

    def _trigger_snapshot(self, path):
        path_obj = Path(path)
        if any(p in path_obj.parts for p in [".audit", "__pycache__", "node_modules", ".git"]):
            return
        rel = ""
        try:
            rel = str(path_obj.relative_to(self.project_root))
        except ValueError:
            pass
        if rel in self.ignored_files:
            return
        self.last_trigger = time.time()
        self.pending_change = True

    def take_snapshot(self, trigger_type="auto", direct_print=False):
        data = self.snap_engine.capture()
        data["trigger"] = trigger_type
        self.storage.save_snapshot(data)
        ts = datetime.now().strftime("%H:%M:%S")
        msg = f"[dim #A0826D]  {ts}  [~] snapshot updated[/dim #A0826D]"
        if trigger_type == "initial":
            msg = f"[dim #A0826D]  {ts}  [ok] snapshot ready[/dim #A0826D]"
        if direct_print:
            console.print(msg)
        else:
            self.message_queue.put(msg)

    def check_debounce(self):
        if self.pending_change and (time.time() - self.last_trigger) > self.debounce_seconds:
            self.take_snapshot("auto", direct_print=False)
            self.pending_change = False


def start_watcher(project_root):
    storage = AuditStorage(project_root)
    snap_engine = AuditSnapshot(project_root)
    abs_path = Path(project_root).resolve()

    event_handler = AuditHandler(project_root, storage, snap_engine)
    observer = Observer()
    observer.schedule(event_handler, str(project_root), recursive=True)

    console.print(f"[bold #E07040][OK][/bold #E07040] audit-watch monitoring: [#D4C4B4]{abs_path}[/#D4C4B4]")
    console.print("[dim #A0826D]Press Ctrl+C to stop.[/dim #A0826D]")

    observer.start()
    try:
        while True:
            event_handler.check_debounce()
            time.sleep(0.5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
