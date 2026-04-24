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
from rich.progress import Progress, TextColumn, BarColumn
from rich.rule import Rule
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

SEP = Rule(style=C_MUTED)
def get_banner_color(score):
    if score >= 9.0: return C_PRIMARY  # Original Orange
    if score >= 7.0: return C_WARNING  # Yellow
    return C_DANGER  # Red

def print_banner(score=10.0):
    color = get_banner_color(score)
    banner = [
        "    ____        __       __    __               __    __",
        "   / __ \\____ _/ /______/ /_  / /_  __  _______/ /___/ /_  __",
        "  / /_/ / __ `/ __/ ___/ __ \\/ __ \\/ / / / __  / __  / / / /",
        " / ____/ /_/ / /_/ /__/ / / / /_/ / /_/ / /_/ / /_/ / /_/ /",
        "/_/    \\__,_/\\__/\\___/_/ /_/_.___/\\__,_/\\__,_/\\__,_/\\__, /",
        "                                                     /____/",
    ]
    from rich.text import Text
    for line in banner:
        console.print(Text(line, style=color))
        time.sleep(0.02)
    console.print(rf"  [italic {C_TEXT}]your friendly patch companion[/]  [{C_DIM}]|[/]  [{C_MUTED}]v1.1.5[/]")
    console.print(rf"  [{C_DIM}]by ./0xbrijith  |  github.com/pred07[/]")
    console.print("")

def print_help():
    table = Table(box=None, show_header=False, padding=(0, 2))
    table.add_column("Command", style=C_WHITE, no_wrap=True)
    table.add_column("Description", style=C_TEXT)
    
    help_data = [
        ("status", "project health score"),
        ("report", "basic regression report"),
        ("report detail", "per-file, per-function diff"),
        ("suggest <verbose>", "agent context (paste into next prompt)"),
        ("promptbuddy", "audit context for fixes (strictly read-only)"),
        ("diff", "what changed between last two snapshots"),
        ("history", "snapshot timeline table"),
        ("mode <type>", "manage strict audit enforcement"),
        ("protect <filename>", "mark file as critical"),
        ("ignore <filename>", "stop tracking a file"),
        ("storage", "show .audit/ disk usage"),
        ("baseline <cmd>", "pin and track a 'Golden Goal'"),
        ("suggest holistic", "final lifecycle audit prompt"),
        ("clear", "clear screen and show banner"),
        ("clear logs|snaps", "cleanup old data"),
        ("help", "show this help"),
        ("exit", "quit")
    ]
    
    for cmd, desc in help_data:
        table.add_row(cmd, desc)
    
    console.print(f"\n[{C_MUTED}]commands:[/]")
    console.print(table)


# ── Helpers ──────────────────────────────────────────────────────────────────

def run_initializer():
    with Progress(
        TextColumn(f"[{C_MUTED}]{{task.description}}[/]"),
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


def flush_messages(msg_queue, zen_callback=None):
    """Drain buffered watcher notifications and print them on clean lines."""
    msgs = []
    zen_update = False
    while not msg_queue.empty():
        try:
            m = msg_queue.get_nowait()
            if m == "__ZEN_UPDATE__":
                zen_update = True
            else:
                msgs.append(m)
        except Exception:
            break
    if msgs:
        # Don't print if we're just about to show a zen update anyway
        if not zen_update:
            console.print()
        for m in msgs:
            console.print(m)
    
    if zen_update and zen_callback:
        zen_callback()


def get_health_emoji(score):
    if score >= 9.5: return "( ^_^)ノ"
    if score >= 8.5: return "(^_^) "
    if score >= 7.5: return "(・_・)"
    if score >= 6.0: return "( -_ -)"
    if score >= 4.0: return "(⊙_⊙)"
    return "(╯°□°)╯"


def need_two_snaps(storage):
    snaps = storage.get_latest_snapshots(2)
    if len(snaps) < 2:
        console.print(
            f"[{C_WARNING}][!][/] Not enough snapshots yet - "
            "wait for a file change or run "
            f"[bold {C_PRIMARY}]python -m patchbuddy.cli snapshot[/]"
        )
        return None, None
    return snaps[1], snaps[0]


def simulate_processing(msg="analyzing project state..."):
    with console.status(f"[{C_DIM}]{msg}[/]", spinner="dots"):
        time.sleep(2.0)

def print_dashboard(project_path, config):
    console.print()
    console.print(SEP)
    console.print(
        f"  [{C_DIM}]monitoring[/]  [{C_TEXT}]{project_path}[/]"
    )
    if config.mode:
        console.print(
            f"  [{C_DIM}]mode      [/]  [{C_WARNING}]{config.mode_description()}[/]"
        )
    console.print(
        f"  [{C_DIM}]commands  [/]  "
        f"[bold {C_WHITE}]status[/]  "
        f"[bold {C_WHITE}]report[/]  "
        f"[bold {C_WHITE}]promptbuddy[/]  "
        f"[bold {C_WHITE}]mode[/]  "
        f"[bold {C_WHITE}]storage[/]  "
        f"[bold {C_WHITE}]help[/]"
    )
    console.print(SEP)
    console.print()


# ── Command handlers ─────────────────────────────────────────────────────────

def handle_zen_status(storage, silent=False):
    """Minimalistic health dashboard for Zen Mode."""
    snaps = storage.get_latest_snapshots(2)
    if len(snaps) < 2:
        if not silent:
            console.print(f"[{C_DIM}]  waiting for changes...[/]")
        return

    before = storage.load_snapshot(snaps[1])
    after  = storage.load_snapshot(snaps[0])
    differ = AuditDiffer()
    diff   = differ.compare(before, after)
    score  = diff['summary']['health_score']
    
    ts = datetime.now().strftime("%H:%M:%S")
    score_color = get_banner_color(score)
    emoji = get_health_emoji(score)
    
    # In Zen Mode or significant change, we want to make it feel "dynamic"
    if score < 8:
        # Show a "Mini Banner" in red/yellow
        console.print(f"\n[bold {score_color}]!! PROJECT DRIFT DETECTED !! {emoji}[/]")
        panel = Panel(
            f"[{C_TEXT}]Project health dropped to [bold {score_color}]{score}/10[/] {emoji}\n"
            f"Regressions found: [bold {C_DANGER}]{diff['summary']['regressions_found']}[/][/]",
            title=f"[{C_DANGER}]Health Alert {emoji}[/]",
            border_style=C_DANGER,
            box=box.ROUNDED,
            width=65
        )
        console.print(panel)
    else:
        # Silent success message with changing faces and dynamic banner-colored indicator
        console.print(f"[dim {C_MUTED}]  {ts}  [{score_color}][{emoji}][/] System Healthy ({score}/10) | context updated[/]")

    # Always update context.md in background for Zen mode
    suggester = AuditSuggester(storage, console=console)
    context_text = suggester.generate_context(before, after, diff)
    storage.update_context(context_text)


def handle_fix(storage, config):
    """Generates a high-fidelity audit prompt for AI agents."""
    before_path, after_path = need_two_snaps(storage)
    if not before_path:
        return

    simulate_processing("generating audit context...")
    before = storage.load_snapshot(before_path)
    after  = storage.load_snapshot(after_path)
    differ = AuditDiffer()
    diff   = differ.compare(before, after)
    
    suggester = AuditSuggester(storage, console=console)
    context_text = suggester.generate_context(before, after, diff, config=config)

    
    # Persona: Senior Auditor (Read-Only)
    audit_persona = (
        "# SYSTEM INTEGRITY AUDIT (STRICT READ-ONLY)\n"
        "CRITICAL: You are acting as a Senior Systems Architect and Code Auditor.\n"
        "Your primary mission is ARCHITECTURAL CONTINUITY.\n"
        "DO NOT modify any files. You are a pure verification layer.\n"
        "Your task is to analyze the regressions below, assess the structural impact,\n"
        "and provide a comprehensive parity report.\n"
        "The developer will review your findings and manually execute any necessary remediations.\n\n"
        "### IDENTIFIED REGRESSIONS:\n"
    )
    
    for reg in diff['regressions']:
        audit_persona += f"- {reg}\n"
    
    final_prompt = audit_persona + "\n" + context_text
    storage.update_context(final_prompt)
    
    suggester.print_context(storage, config=config)
    console.print(f"\n[{C_SUCCESS}][OK][/] Audit context generated in [bold]context.md[/].")
    console.print(f"[{C_DIM}]Paste this into your AI prompt to begin the verification cycle.[/]")
    console.print(f"[{C_DIM}]Use [bold {C_PRIMARY}]clear[/] to reset the screen and return to the top.[/]")


def handle_status(storage):
    simulate_processing("calculating health score...")
    before_path, after_path = need_two_snaps(storage)
    if not before_path:
        return

    before = storage.load_snapshot(before_path)
    after  = storage.load_snapshot(after_path)

    differ = AuditDiffer()
    diff   = differ.compare(before, after)
    score  = diff['summary']['health_score']

    score_color = C_SUCCESS if score >= 7 else C_WARNING if score >= 5 else C_DANGER
    emoji = get_health_emoji(score)
    reg_val  = diff['summary']['regressions_found']
    reg_color = C_SUCCESS if reg_val == 0 else C_DANGER
    mod_val  = diff['summary']['files_modified']
    mod_color = C_WARNING if mod_val > 0 else C_SUCCESS
    added_val = diff['summary']['files_added']

    table = Table(
        title=f"[bold {C_PRIMARY}] {emoji}  Project Health  {emoji} [/]",
        border_style=C_BORDER,
        box=box.ROUNDED,
        header_style=f"bold {C_MUTED}",
        padding=(0, 1),
    )
    table.add_column("Metric",  style=C_TEXT, min_width=22)
    table.add_column("Value",   justify="right", min_width=8)

    table.add_row("Health Score",        f"[bold {score_color}]{score}/10[/]")
    table.add_row("Regressions",         f"[bold {reg_color}]{reg_val}[/]")
    table.add_row("Warnings (Modified)", f"[{mod_color}]{mod_val}[/]")
    table.add_row("Files Added",         f"[{C_DIM}]{added_val}[/]")

    console.print()
    console.print(table)

    if diff['regressions']:
        console.print(f"\n[bold {C_DANGER}]  [REGRESSIONS][/]")
        for r in diff['regressions']:
            console.print(f"  [{C_DANGER}]x[/]  [{C_TEXT}]{r}[/]")


def handle_report(storage, config, subcommand=None, verbose=False):
    simulate_processing("generating regression report...")
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
    suggester = AuditSuggester(storage, console=console)
    context_text = suggester.generate_context(before, after, diff, config=config, verbose=verbose)
    storage.update_context(context_text)


def handle_suggest(storage, config, holistic=False, verbose=False):
    # Regenerate context first so it's always current
    before_path, after_path = need_two_snaps(storage)
    
    # Holistic override: compare latest against baseline
    if holistic:
        baseline = storage.baseline_file
        if not baseline.exists():
            console.print(f"[{C_WARNING}][!][/] No baseline marked. Run [bold {C_PRIMARY}]baseline mark[/] first.")
            return
        before_path = baseline

    if before_path:
        simulate_processing("generating suggestion context...")
        before = storage.load_snapshot(before_path)
        after  = storage.load_snapshot(after_path)
        differ = AuditDiffer()
        diff   = differ.compare(before, after)
        suggester = AuditSuggester(storage, console=console)
        context_text = suggester.generate_context(before, after, diff, config=config, verbose=verbose)
        
        if holistic:
            # Inject Holistic persona into the context
            context_text = (
                "# HOLISTIC LIFECYCLE AUDIT (GOAL ALIGNMENT REVIEW)\n"
                "CRITICAL: You are acting as a Senior Strategic Auditor.\n"
                "Your role is to assess PROJECT-GOAL ALIGNMENT.\n"
                "DO NOT execute code or modify files. Provide a comprehensive\n"
                "verification of the current delta against the baseline mission.\n"
                "Analyze the delta for:\n"
                "1. INTERFACE STABILITY: Ensure all public-facing structures maintain functional parity.\n"
                "2. LOGIC PRESERVATION: Verify the original intent and core algorithm logic remains intact.\n"
                "3. SCHEMA FIDELITY: Confirm that all data-serialization and output formats match the baseline.\n\n"
                + context_text
            )
        
        storage.update_context(context_text)

    suggester = AuditSuggester(storage, console=console)
    suggester.print_context(storage, config=config)
    console.print(f"\n[{C_SUCCESS}][OK][/] Audit context generated in [bold]context.md[/].")
    console.print(f"[{C_DIM}]Use [bold {C_PRIMARY}]clear[/] to reset the screen and return to the top.[/]")


def handle_baseline(storage, args):
    """baseline mark | status | diff"""
    if not args:
        console.print(f"[{C_WARNING}]usage:[/] baseline mark | status | diff")
        return

    simulate_processing("verifying baseline integrity...")

    sub = args[0].lower()
    
    if sub == "mark":
        snaps = storage.get_latest_snapshots(1)
        if not snaps:
            console.print(f"[{C_DANGER}][x][/] No snapshots available to mark as baseline.")
            return
        storage.set_baseline(snaps[0])
        console.print(f"[{C_SUCCESS}][ok][/] Current state pinned as your [bold]Golden Baseline[/].")
        console.print(f"[{C_DIM}]All future 'baseline' commands will compare against this moment.[/]")

    elif sub == "status":
        baseline_path = storage.baseline_file
        if not baseline_path.exists():
            console.print(f"[{C_WARNING}][!][/] No baseline found. Use [bold {C_PRIMARY}]baseline mark[/] first.")
            return
            
        snaps = storage.get_latest_snapshots(1)
        if not snaps: return
        
        before = storage.load_snapshot(baseline_path)
        after  = storage.load_snapshot(snaps[0])
        
        differ = AuditDiffer()
        diff = differ.compare(before, after)
        score = diff['summary']['health_score']
        
        score_color = C_SUCCESS if score >= 7 else C_WARNING if score >= 5 else C_DANGER
        
        console.print(f"\n  [bold {C_PRIMARY}]Objective Alignment Audit[/]")
        console.print(f"  [{C_DIM}]Comparing against your Golden Baseline[/]")
        console.print(SEP)
        console.print(f"  Alignment Score: [bold {score_color}]{score}/10[/]")
        console.print(f"  Total Deviations: [{C_DANGER}]{diff['summary']['regressions_found']}[/]")
        console.print(f"  Structural Drift: [{C_WARNING}]{diff['summary']['files_modified']}[/] files changed since baseline")
        console.print(SEP)

    elif sub == "diff":
        baseline_path = storage.baseline_file
        if not baseline_path.exists():
            console.print(f"[{C_WARNING}][!][/] No baseline found.")
            return
        snaps = storage.get_latest_snapshots(1)
        before = storage.load_snapshot(baseline_path)
        after  = storage.load_snapshot(snaps[0])
        
        reporter = AuditReporter(storage)
        console.print(f"\n[bold {C_PRIMARY}]Detailed Objective Drift Report[/]")
        reporter.generate_detail(before, after)
    else:
        console.print(f"[{C_WARNING}]unknown baseline subcommand.[/]")


def handle_diff(storage):
    simulate_processing("comparing snapshots...")
    before_path, after_path = need_two_snaps(storage)
    if not before_path:
        return
    before   = storage.load_snapshot(before_path)
    after    = storage.load_snapshot(after_path)
    reporter = AuditReporter(storage)
    reporter.generate_detail(before, after)


def handle_history(storage):
    simulate_processing("retrieving snapshot timeline...")
    reporter = AuditReporter(storage)
    reporter.generate_history(storage)


def handle_mode(storage, config, args):
    """mode safe | feature | fix <filename> | off | status"""
    if not args:
        console.print(f"[{C_WARNING}]usage:[/] mode safe | feature | fix <filename> | off | status")
        return

    sub = args[0].lower()

    if sub == "status":
        mode_desc = config.mode_description()
        console.print(f"\n  [{C_PRIMARY}]active mode:[/]  [{C_TEXT}]{mode_desc}[/]")
        if config.protected:
            console.print(f"  [{C_PRIMARY}]protected  :[/]  [{C_TEXT}]{', '.join(config.protected)}[/]")
        if config.ignored:
            console.print(f"  [{C_PRIMARY}]ignored    :[/]  [{C_TEXT}]{', '.join(config.ignored)}[/]")
        return

    if sub == "off":
        config.set_mode(None, mode_file=None, locked_snapshot_path=None)
        console.print(f"[{C_SUCCESS}][ok][/] Mode cleared — back to normal monitoring.")
        return

    # For safe/feature/fix, lock against the latest snapshot
    snaps = storage.get_latest_snapshots(1)
    locked_path = str(snaps[0]) if snaps else None

    if sub == "safe":
        config.set_mode("safe", locked_snapshot_path=locked_path)
        console.print(
            f"[{C_SUCCESS}][ok][/] Mode set to "
            f"[bold {C_WARNING}]SAFE[/] — "
            "all functions, classes, and columns are now locked."
        )
    elif sub == "feature":
        config.set_mode("feature", locked_snapshot_path=locked_path)
        console.print(
            f"[{C_SUCCESS}][ok][/] Mode set to "
            f"[bold {C_WARNING}]FEATURE[/] — "
            "additions allowed, existing items locked."
        )
    elif sub == "fix":
        if len(args) < 2:
            console.print(f"[{C_WARNING}]usage:[/] mode fix <filename>")
            return
        target_file = args[1]
        config.set_mode("fix", mode_file=target_file, locked_snapshot_path=locked_path)
        console.print(
            f"[{C_SUCCESS}][ok][/] Mode set to "
            f"[bold {C_WARNING}]FIX[/] — "
            f"only [{C_TEXT}]{target_file}[/] may change."
        )
    else:
        console.print(f"[{C_WARNING}]unknown mode.[/] use: safe | feature | fix <filename> | off | status")


def handle_protect(storage, config, args):
    """protect <filename>"""
    if not args:
        console.print(f"[{C_WARNING}]usage:[/] protect <filename>")
        return
    
    simulate_processing("updating protection layer...")
    filename = args[0]
    if config.protect(filename):
        console.print(
            f"[{C_SUCCESS}][ok][/] [{C_TEXT}]{filename}[/] "
            f"marked as [{C_WARNING}]protected[/] — always included in suggest output."
        )
    else:
        console.print(f"[{C_DIM}]{filename} is already protected.[/]")


def handle_ignore(storage, config, snap_engine, args):
    """ignore <filename>"""
    if not args:
        console.print(f"[{C_WARNING}]usage:[/] ignore <filename>")
        return

    simulate_processing("updating ignore scope...")
    filename = args[0]
    if config.ignore(filename):
        snap_engine.set_ignored_files(config.ignored)
        console.print(
            f"[{C_SUCCESS}][ok][/] [{C_TEXT}]{filename}[/] "
            "will be excluded from all future snapshots and reports."
        )
    else:
        console.print(f"[{C_DIM}]{filename} is already ignored.[/]")


def handle_storage(storage):
    simulate_processing("calculating disk usage...")
    usage = storage.get_storage_usage()
    
    def format_size(size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    table = Table(
        title=f"[bold {C_PRIMARY}] .audit/ Usage Breakdown [/]",
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
    table.add_row("[bold]Total[/]", "", f"[bold {C_WHITE}]{format_size(usage['total_size'])}[/]")

    console.print()
    console.print(table)


def handle_clear(storage, config, args):
    """clear logs | snapshots | all | history"""
    if not args:
        console.print(f"[{C_WARNING}]usage:[/] clear logs | snapshots | all | history")
        return

    simulate_processing("cleaning up audit data...")

    sub = args[0].lower()
    if sub == "all":
        confirm = console.input(f"[{C_DANGER}]WARNING:[/] Wipe entire .audit folder? (y/n) ").lower()
        if confirm == 'y':
            storage.clear_all()
            config.save() # restore config
            console.print(f"[{C_SUCCESS}][ok][/] .audit folder wiped fresh.")
    elif sub == "snapshots":
        count = storage.clear_snapshots(config.max_snapshots)
        console.print(f"[{C_SUCCESS}][ok][/] Cleared {count} old snapshots. Kept {config.max_snapshots}.")
    elif sub == "history":
        count = storage.clear_history()
        console.print(f"[{C_SUCCESS}][ok][/] Cleared {count} reports and wiped session log.")
    elif sub == "logs":
        # logs for us are essentially reports + session
        count = storage.clear_history()
        console.print(f"[{C_SUCCESS}][ok][/] Logs and reports purged.")
    else:
        console.print(f"[{C_WARNING}]unknown subcommand.[/]")


def handle_log_session(storage):
    history = storage.get_session_history()
    if not history:
        console.print(f"[{C_DIM}]No session history recorded.[/]")
        return
    
    console.print(f"\n[bold {C_PRIMARY}] Session Command Log [/]")
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

def start_interactive(project_root, zen_mode=False, fix_command=False):
    project_path = Path(project_root).resolve()
    storage    = AuditStorage(project_root)
    config     = AuditConfig(storage.audit_dir)
    snap_engine = AuditSnapshot(project_root, ignored_files=config.ignored)
    
    # Quick initial assessment for banner color
    initial_score = 10.0
    snaps = storage.get_latest_snapshots(1)
    if snaps:
        last = storage.load_snapshot(snaps[0])
        # If there's a baseline, compare against it; otherwise just use 10
        if storage.baseline_file.exists():
            base = storage.load_snapshot(storage.baseline_file)
            differ = AuditDiffer()
            diff = differ.compare(base, last)
            initial_score = diff['summary']['health_score']

    if not zen_mode and not fix_command:
        print_banner(score=initial_score)
        run_initializer()

    msg_queue   = queue.Queue()

    event_handler = AuditHandler(
        project_root, storage, snap_engine,
        message_queue=msg_queue,
        ignored_files=config.ignored,
    )
    
    # Handle direct promptbuddy command shortcut
    if fix_command:
        handle_fix(storage, config)
        return

    observer = Observer()
    observer.schedule(event_handler, str(project_root), recursive=True)

    if zen_mode:
        console.print(f"[bold {C_PRIMARY}] Patch Buddy | ZEN MODE [/]")
        console.print(f"[{C_DIM}]Monitoring:[/][{C_TEXT}]{project_path}[/]")
        console.print(f"[{C_DIM}]Status:[/][{C_SUCCESS}]Active Dashboard[/] | Press Ctrl+C to exit")
        console.print(SEP)
        handle_zen_status(storage, silent=True)
    else:
        handle_zen_status(storage, silent=True)
        console.print(f"  [{C_DIM}]Call [/][bold {C_PRIMARY}]buddy[/] [{C_DIM}]to show options or [/][bold {C_PRIMARY}]promptbuddy[/] [{C_DIM}]to get instant fix suggestions..[/]")
        console.print()
    observer.start()
    stop_event = threading.Event()
    debounce_thread = threading.Thread(target=debounce_worker, args=(event_handler, stop_event))
    debounce_thread.daemon = True
    debounce_thread.start()
    def zen_cb(): handle_zen_status(storage)
    try:
        while True:
            if zen_mode:
                time.sleep(1)
                flush_messages(msg_queue, zen_callback=zen_cb)
                continue
            try:
                raw_input = console.input(f"[bold {C_PRIMARY}]patchbuddy[/] [{C_DIM}]>[/] ").strip()
            except EOFError: break
            flush_messages(msg_queue, zen_callback=zen_cb)
            if not raw_input: continue
            storage.log_session_command(raw_input)
            parts = raw_input.split()
            cmd   = parts[0].lower()
            args  = parts[1:]
            if cmd in ['exit', 'quit']: break
            elif cmd == 'help' or cmd == 'buddy':
                print_dashboard(project_path, config)
                if cmd == 'help': print_help()
            elif cmd == 'cls' or (cmd == 'clear' and not args):
                console.clear()
                print_banner()
                handle_zen_status(storage, silent=False)
                console.print(f"  [{C_DIM}]Call [/][bold {C_PRIMARY}]buddy[/] [{C_DIM}]to show options or [/][bold {C_PRIMARY}]promptbuddy[/] [{C_DIM}]to get instant fix suggestions..[/]")
                console.print()
                continue
            elif cmd == 'status': handle_status(storage)
            elif cmd == 'report':
                sub = args[0].lower() if args else None
                if sub and sub != 'detail':
                    console.print(f"[{C_WARNING}]unknown subcommand.[/] try: [bold {C_PRIMARY}]report[/] [bold {C_PRIMARY}]report detail[/]")
                else:
                    verbose = True if (args and 'verbose' in [a.lower() for a in args]) else False
                    handle_report(storage, config, subcommand=sub, verbose=verbose)
            elif cmd == 'suggest':
                holistic = True if (args and 'holistic' in [a.lower() for a in args]) else False
                verbose = True if (args and 'verbose' in [a.lower() for a in args]) else False
                handle_suggest(storage, config, holistic=holistic, verbose=verbose)
            elif cmd == 'promptbuddy' or cmd == 'fix':
                handle_fix(storage, config)
            elif cmd == 'baseline': handle_baseline(storage, args)
            elif cmd == 'diff': handle_diff(storage)
            elif cmd == 'history': handle_history(storage)
            elif cmd == 'mode': handle_mode(storage, config, args)
            elif cmd == 'protect': handle_protect(storage, config, args)
            elif cmd == 'ignore': handle_ignore(storage, config, snap_engine, args)
            elif cmd == 'storage': handle_storage(storage)
            elif cmd == 'clear': handle_clear(storage, config, args)
            elif cmd == 'log':
                if args and args[0] == 'session': handle_log_session(storage)
                else: console.print(f"[{C_WARNING}]usage:[/] log session")
            else:
                console.print(f"[{C_WARNING}]unknown command:[/][{C_TEXT}]{cmd}[/] - type [{C_PRIMARY}]help[/] for all commands")
            trigger_auto_cleanup(storage, config)
            flush_messages(msg_queue, zen_callback=zen_cb)
    except KeyboardInterrupt: pass
    finally:
        console.print(f"\n[{C_DIM}]shutting down background watcher...[/]")
        stop_event.set()
        observer.stop()
        observer.join()
