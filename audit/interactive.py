import sys
import time
import queue
import threading
from pathlib import Path
from datetime import datetime

# Fix Windows console encoding before importing rich (prevents charmap errors)
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn
from rich import box

from .watcher import AuditHandler
from .storage import AuditStorage
from .snapshot import AuditSnapshot
from .reporter import AuditReporter
from .suggester import AuditSuggester
from .differ import AuditDiffer
from .config import AuditConfig
from watchdog.observers import Observer

console = Console(highlight=False)

# Claude-inspired palette
C_PRIMARY = "#E07040"  # Original Orange
C_MUTED   = "#A0826D"
C_SUCCESS = "#7FB77E"
C_WARNING = "#D4A843"
C_DANGER  = "#C05050"
C_TEXT    = "#D4C4B4"
C_DIM     = "#7A6A5A"
C_BORDER  = "#A0826D"
C_WHITE   = "#F5F5F7"  # Clean White for commands

SEP = f"[{C_MUTED}]" + "─" * 80 + f"[/{C_MUTED}]"

# Original Large Banner
BANNER_LINES = [
    rf"[{C_PRIMARY}]    ____        __       __    __               __    __[/{C_PRIMARY}]",
    rf"[{C_PRIMARY}]   / __ \____ _/ /______/ /_  / /_  __  _______/ /___/ /_  __[/{C_PRIMARY}]",
    rf"[{C_PRIMARY}]  / /_/ / __ `/ __/ ___/ __ \/ __ \/ / / / __  / __  / / / /[/{C_PRIMARY}]",
    rf"[{C_PRIMARY}] / ____/ /_/ / /_/ /__/ / / / /_/ / /_/ / /_/ / /_/ / /_/ /[/{C_PRIMARY}]",
    rf"[{C_PRIMARY}]/_/    \__,_/\__/\___/_/ /_/_.___/\__,_/\__,_/\__,_/\__, /[/{C_PRIMARY}]",
    rf"[{C_PRIMARY}]                                                     /____/[/{C_PRIMARY}]",
    rf"  [italic {C_TEXT}]your friendly patch companion[/italic {C_TEXT}]  [{C_DIM}]|[/{C_DIM}]  [{C_MUTED}]v1.0[/{C_MUTED}]",
    rf"  [{C_DIM}]by ./0xbrijith  |  github.com/pred07[/{C_DIM}]",
    "",
]

HELP_TEXT = (
    f"[{C_MUTED}]commands:[/{C_MUTED}]\n"
    f"  [{C_WHITE}]status[/{C_WHITE}]                   project health score\n"
    f"  [{C_WHITE}]report[/{C_WHITE}]                   basic regression report\n"
    f"  [{C_WHITE}]report detail[/{C_WHITE}]            per-file, per-function diff\n"
    f"  [{C_WHITE}]suggest[/{C_WHITE}]                  agent context (paste into next prompt)\n"
    f"  [{C_WHITE}]diff[/{C_WHITE}]                     what changed between last two snapshots\n"
    f"  [{C_WHITE}]history[/{C_WHITE}]                  snapshot timeline table\n"
    f"  [{C_WHITE}]mode safe|feature|fix <f>|off|status[/{C_WHITE}]\n"
    f"  [{C_WHITE}]protect <filename>[/{C_WHITE}]       mark file as critical\n"
    f"  [{C_WHITE}]ignore <filename>[/{C_WHITE}]        stop tracking a file\n"
    f"  [{C_WHITE}]storage[/{C_WHITE}]                  show .audit/ disk usage\n"
    f"  [{C_WHITE}]clear logs|snapshots|all[/{C_WHITE}]   cleanup old data\n"
    f"  [{C_WHITE}]log session[/{C_WHITE}]              show command history\n"
    f"  [{C_WHITE}]help[/{C_WHITE}]                     show this help\n"
    f"  [{C_WHITE}]exit[/{C_WHITE}]                     quit\n"
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def print_banner():
    for line in BANNER_LINES:
        console.print(line)
        time.sleep(0.05)


def run_initializer():
    with Progress(
        TextColumn(f"[{C_MUTED}]{{task.description}}[/{C_MUTED}]"),
        BarColumn(complete_style=C_PRIMARY, finished_style=C_SUCCESS),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Initializing PatchBuddy...", total=100)
        for _ in range(20):
            time.sleep(0.05)
            progress.update(task, advance=5)


def debounce_worker(event_handler, stop_event):
    while not stop_event.is_set():
        event_handler.check_debounce()
        time.sleep(0.5)


def flush_messages(msg_queue):
    """Drain buffered watcher notifications and print them on clean lines."""
    msgs = []
    while not msg_queue.empty():
        try:
            msgs.append(msg_queue.get_nowait())
        except Exception:
            break
    if msgs:
        console.print()
        for m in msgs:
            console.print(m)


def need_two_snaps(storage):
    snaps = storage.get_latest_snapshots(2)
    if len(snaps) < 2:
        console.print(
            f"[{C_WARNING}][!][/{C_WARNING}] Not enough snapshots yet — "
            "wait for a file change or run "
            f"[bold {C_PRIMARY}]python -m audit.cli snapshot[/bold {C_PRIMARY}]"
        )
        return None, None
    return snaps[1], snaps[0]


# ── Command handlers ─────────────────────────────────────────────────────────

def handle_status(storage):
    before_path, after_path = need_two_snaps(storage)
    if not before_path:
        return

    before = storage.load_snapshot(before_path)
    after  = storage.load_snapshot(after_path)

    differ = AuditDiffer()
    diff   = differ.compare(before, after)
    score  = diff['summary']['health_score']

    score_color = C_SUCCESS if score >= 7 else C_WARNING if score >= 5 else C_DANGER
    reg_val  = diff['summary']['regressions_found']
    reg_color = C_SUCCESS if reg_val == 0 else C_DANGER
    mod_val  = diff['summary']['files_modified']
    mod_color = C_WARNING if mod_val > 0 else C_SUCCESS
    added_val = diff['summary']['files_added']

    table = Table(
        title=f"[bold {C_PRIMARY}] Project Health [/bold {C_PRIMARY}]",
        border_style=C_BORDER,
        box=box.ROUNDED,
        header_style=f"bold {C_MUTED}",
        padding=(0, 1),
    )
    table.add_column("Metric",  style=C_TEXT, min_width=22)
    table.add_column("Value",   justify="right", min_width=8)

    table.add_row("Health Score",        f"[bold {score_color}]{score}/10[/bold {score_color}]")
    table.add_row("Regressions",         f"[bold {reg_color}]{reg_val}[/bold {reg_color}]")
    table.add_row("Warnings (Modified)", f"[{mod_color}]{mod_val}[/{mod_color}]")
    table.add_row("Files Added",         f"[{C_DIM}]{added_val}[/{C_DIM}]")

    console.print()
    console.print(table)

    if diff['regressions']:
        console.print(f"\n[bold {C_DANGER}]  [REGRESSIONS][/bold {C_DANGER}]")
        for r in diff['regressions']:
            console.print(f"  [{C_DANGER}]x[/{C_DANGER}]  [{C_TEXT}]{r}[/{C_TEXT}]")


def handle_report(storage, config, subcommand=None):
    reporter = AuditReporter(storage)

    before_path, after_path = need_two_snaps(storage)
    if not before_path:
        return

    before = storage.load_snapshot(before_path)
    after  = storage.load_snapshot(after_path)

    if subcommand == "detail":
        reporter.generate_detail(before, after)
        return

    # Basic report
    report_text, diff = reporter.generate_report(before, after)
    storage.save_report(report_text)

    # Auto-update context.md
    suggester = AuditSuggester(storage)
    context_text = suggester.generate_context(before, after, diff, config=config)
    storage.update_context(context_text)


def handle_suggest(storage, config):
    # Regenerate context first so it's always current
    before_path, after_path = need_two_snaps(storage)
    if before_path:
        before = storage.load_snapshot(before_path)
        after  = storage.load_snapshot(after_path)
        differ = AuditDiffer()
        diff   = differ.compare(before, after)
        suggester = AuditSuggester(storage)
        context_text = suggester.generate_context(before, after, diff, config=config)
        storage.update_context(context_text)

    suggester = AuditSuggester(storage)
    suggester.print_context(storage, config=config)


def handle_diff(storage):
    before_path, after_path = need_two_snaps(storage)
    if not before_path:
        return
    before   = storage.load_snapshot(before_path)
    after    = storage.load_snapshot(after_path)
    reporter = AuditReporter(storage)
    reporter.generate_detail(before, after)


def handle_history(storage):
    reporter = AuditReporter(storage)
    reporter.generate_history(storage)


def handle_mode(storage, config, args):
    """mode safe | feature | fix <filename> | off | status"""
    if not args:
        console.print(f"[{C_WARNING}]usage:[/{C_WARNING}] mode safe | feature | fix <filename> | off | status")
        return

    sub = args[0].lower()

    if sub == "status":
        mode_desc = config.mode_description()
        console.print(f"\n  [{C_PRIMARY}]active mode:[/{C_PRIMARY}]  [{C_TEXT}]{mode_desc}[/{C_TEXT}]")
        if config.protected:
            console.print(f"  [{C_PRIMARY}]protected  :[/{C_PRIMARY}]  [{C_TEXT}]{', '.join(config.protected)}[/{C_TEXT}]")
        if config.ignored:
            console.print(f"  [{C_PRIMARY}]ignored    :[/{C_PRIMARY}]  [{C_TEXT}]{', '.join(config.ignored)}[/{C_TEXT}]")
        return

    if sub == "off":
        config.set_mode(None, mode_file=None, locked_snapshot_path=None)
        console.print(f"[{C_SUCCESS}][ok][/{C_SUCCESS}] Mode cleared — back to normal monitoring.")
        return

    # For safe/feature/fix, lock against the latest snapshot
    snaps = storage.get_latest_snapshots(1)
    locked_path = str(snaps[0]) if snaps else None

    if sub == "safe":
        config.set_mode("safe", locked_snapshot_path=locked_path)
        console.print(
            f"[{C_SUCCESS}][ok][/{C_SUCCESS}] Mode set to "
            f"[bold {C_WARNING}]SAFE[/bold {C_WARNING}] — "
            "all functions, classes, and columns are now locked."
        )
    elif sub == "feature":
        config.set_mode("feature", locked_snapshot_path=locked_path)
        console.print(
            f"[{C_SUCCESS}][ok][/{C_SUCCESS}] Mode set to "
            f"[bold {C_WARNING}]FEATURE[/bold {C_WARNING}] — "
            "additions allowed, existing items locked."
        )
    elif sub == "fix":
        if len(args) < 2:
            console.print(f"[{C_WARNING}]usage:[/{C_WARNING}] mode fix <filename>")
            return
        target_file = args[1]
        config.set_mode("fix", mode_file=target_file, locked_snapshot_path=locked_path)
        console.print(
            f"[{C_SUCCESS}][ok][/{C_SUCCESS}] Mode set to "
            f"[bold {C_WARNING}]FIX[/bold {C_WARNING}] — "
            f"only [{C_TEXT}]{target_file}[/{C_TEXT}] may change."
        )
    else:
        console.print(f"[{C_WARNING}]unknown mode.[/{C_WARNING}] use: safe | feature | fix <filename> | off | status")


def handle_protect(storage, config, args):
    if not args:
        console.print(f"[{C_WARNING}]usage:[/{C_WARNING}] protect <filename>")
        return
    filename = args[0]
    if config.protect(filename):
        console.print(
            f"[{C_SUCCESS}][ok][/{C_SUCCESS}] [{C_TEXT}]{filename}[/{C_TEXT}] "
            f"marked as [{C_WARNING}]protected[/{C_WARNING}] — always included in suggest output."
        )
    else:
        console.print(f"[{C_DIM}]{filename} is already protected.[/{C_DIM}]")


def handle_ignore(storage, config, snap_engine, args):
    if not args:
        console.print(f"[{C_WARNING}]usage:[/{C_WARNING}] ignore <filename>")
        return
    filename = args[0]
    if config.ignore(filename):
        snap_engine.set_ignored_files(config.ignored)
        console.print(
            f"[{C_SUCCESS}][ok][/{C_SUCCESS}] [{C_TEXT}]{filename}[/{C_TEXT}] "
            "will be excluded from all future snapshots and reports."
        )
    else:
        console.print(f"[{C_DIM}]{filename} is already ignored.[/{C_DIM}]")


def handle_storage(storage):
    usage = storage.get_storage_usage()
    
    def format_size(size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    table = Table(
        title=f"[bold {C_PRIMARY}] .audit/ Usage Breakdown [/bold {C_PRIMARY}]",
        border_style=C_BORDER,
        box=box.ROUNDED,
        header_style=f"bold {C_MUTED}",
        expand=False,
    )
    table.add_column("Category", style=C_TEXT)
    table.add_column("Files",    justify="right", style=C_DIM)
    table.add_column("Size",     justify="right", style=C_WHITE)

    table.add_row("Snapshots", str(usage["snapshots"]["count"]), format_size(usage["snapshots"]["size"]))
    table.add_row("Reports",   str(usage["reports"]["count"]),   format_size(usage["reports"]["size"]))
    table.add_row("Diffs",     str(usage["diffs"]["count"]),     format_size(usage["diffs"]["size"]))
    table.add_section()
    table.add_row("[bold]Total[/bold]", "", f"[bold {C_WHITE}]{format_size(usage['total_size'])}[/bold {C_WHITE}]")

    console.print()
    console.print(table)


def handle_clear(storage, config, args):
    """clear logs | snapshots | all | history"""
    if not args:
        console.print(f"[{C_WARNING}]usage:[/{C_WARNING}] clear logs | snapshots | all | history")
        return

    sub = args[0].lower()
    if sub == "all":
        confirm = console.input(f"[{C_DANGER}]WARNING:[/{C_DANGER}] Wipe entire .audit folder? (y/n) ").lower()
        if confirm == 'y':
            storage.clear_all()
            config.save() # restore config
            console.print(f"[{C_SUCCESS}][ok][/{C_SUCCESS}] .audit folder wiped fresh.")
    elif sub == "snapshots":
        count = storage.clear_snapshots(config.max_snapshots)
        console.print(f"[{C_SUCCESS}][ok][/{C_SUCCESS}] Cleared {count} old snapshots. Kept {config.max_snapshots}.")
    elif sub == "history":
        count = storage.clear_history()
        console.print(f"[{C_SUCCESS}][ok][/{C_SUCCESS}] Cleared {count} reports and wiped session log.")
    elif sub == "logs":
        # logs for us are essentially reports + session
        count = storage.clear_history()
        console.print(f"[{C_SUCCESS}][ok][/{C_SUCCESS}] Logs and reports purged.")
    else:
        console.print(f"[{C_WARNING}]unknown subcommand.[/{C_WARNING}]")


def handle_log_session(storage):
    history = storage.get_session_history()
    if not history:
        console.print(f"[{C_DIM}]No session history recorded.[/{C_DIM}]")
        return
    
    console.print(f"\n[bold {C_PRIMARY}] Session Command Log [/bold {C_PRIMARY}]")
    console.print(SEP)
    for line in history[-20:]: # Show last 20
        console.print(f"  {line.strip()}", style=C_TEXT)
    console.print(SEP)


def trigger_auto_cleanup(storage, config):
    if not config.auto_cleanup:
        return
    storage.clear_snapshots(config.max_snapshots)
    storage.clear_reports(config.max_report_count)


# ── Main entry ───────────────────────────────────────────────────────────────

def start_interactive(project_root):
    print_banner()
    run_initializer()

    project_path = Path(project_root).resolve()
    storage    = AuditStorage(project_root)
    config     = AuditConfig(storage.audit_dir)
    snap_engine = AuditSnapshot(project_root, ignored_files=config.ignored)

    msg_queue   = queue.Queue()

    event_handler = AuditHandler(
        project_root, storage, snap_engine,
        message_queue=msg_queue,
        ignored_files=config.ignored,
    )
    observer = Observer()
    observer.schedule(event_handler, str(project_root), recursive=True)

    console.print()
    console.print(SEP)
    console.print(
        f"  [{C_DIM}]monitoring[/{C_DIM}]  [{C_TEXT}]{project_path}[/{C_TEXT}]"
    )
    if config.mode:
        console.print(
            f"  [{C_DIM}]mode      [/{C_DIM}]  [{C_WARNING}]{config.mode_description()}[/{C_WARNING}]"
        )
    console.print(
        f"  [{C_DIM}]commands  [/{C_DIM}]  "
        f"[bold {C_WHITE}]status[/bold {C_WHITE}]  "
        f"[bold {C_WHITE}]report[/bold {C_WHITE}]  "
        f"[bold {C_WHITE}]suggest[/bold {C_WHITE}]  "
        f"[bold {C_WHITE}]mode[/bold {C_WHITE}]  "
        f"[bold {C_WHITE}]storage[/bold {C_WHITE}]  "
        f"[bold {C_WHITE}]help[/bold {C_WHITE}]"
    )
    console.print(SEP)
    console.print()

    observer.start()

    stop_event = threading.Event()
    debounce_thread = threading.Thread(
        target=debounce_worker, args=(event_handler, stop_event)
    )
    debounce_thread.daemon = True
    debounce_thread.start()

    try:
        while True:
            try:
                raw_input = console.input(
                    f"[bold {C_PRIMARY}]patchbuddy[/bold {C_PRIMARY}] [{C_DIM}]>[/{C_DIM}] "
                ).strip()
            except EOFError:
                break

            # Flush any buffered watcher messages BEFORE processing command
            flush_messages(msg_queue)

            if not raw_input:
                continue

            # Log command to session history
            storage.log_session_command(raw_input)

            parts = raw_input.split()
            cmd   = parts[0].lower()
            args  = parts[1:]

            if cmd in ['exit', 'quit']:
                break

            elif cmd == 'help':
                console.print(HELP_TEXT)

            elif cmd == 'status':
                handle_status(storage)

            elif cmd == 'report':
                sub = args[0].lower() if args else None
                if sub and sub != 'detail':
                    console.print(
                        f"[{C_WARNING}]unknown subcommand.[/{C_WARNING}] "
                        f"try: [bold {C_PRIMARY}]report[/bold {C_PRIMARY}]  "
                        f"[bold {C_PRIMARY}]report detail[/bold {C_PRIMARY}]"
                    )
                else:
                    handle_report(storage, config, subcommand=sub)

            elif cmd == 'suggest':
                handle_suggest(storage, config)

            elif cmd == 'diff':
                handle_diff(storage)

            elif cmd == 'history':
                handle_history(storage)

            elif cmd == 'mode':
                handle_mode(storage, config, args)

            elif cmd == 'protect':
                handle_protect(storage, config, args)

            elif cmd == 'ignore':
                handle_ignore(storage, config, snap_engine, args)

            elif cmd == 'storage':
                handle_storage(storage)

            elif cmd == 'clear':
                handle_clear(storage, config, args)

            elif cmd == 'log':
                if args and args[0] == 'session':
                    handle_log_session(storage)
                else:
                    console.print(f"[{C_WARNING}]usage:[/{C_WARNING}] log session")

            else:
                console.print(
                    f"[{C_WARNING}]unknown command:[/{C_WARNING}] [{C_TEXT}]{cmd}[/{C_TEXT}]  "
                    f"— type [{C_PRIMARY}]help[/{C_PRIMARY}] for all commands"
                )

            # Auto-cleanup after each command
            trigger_auto_cleanup(storage, config)

            # Flush again after output so next prompt appears clean
            flush_messages(msg_queue)

    finally:
        console.print(f"\n[{C_DIM}]shutting down background watcher...[/{C_DIM}]")
        stop_event.set()
        observer.stop()
        observer.join()
