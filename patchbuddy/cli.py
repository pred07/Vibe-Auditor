import os
import click
from rich.console import Console
from rich.table import Table
from pathlib import Path
from .storage import AuditStorage
from .snapshot import AuditSnapshot
from .differ import AuditDiffer

console = Console()

@click.group()
def main():
    """audit-watch — Local static code audit utility."""
    pass

@main.command()
@click.option('--project', default='.', help='Project root directory')
def snapshot(project):
    """Manually take a snapshot of the project."""
    storage = AuditStorage(project)
    snap = AuditSnapshot(project)
    
    with console.status("[bold green]Taking snapshot..."):
        data = snap.capture()
        filepath = storage.save_snapshot(data)
    
    console.print(f"[bold green][OK][/bold green] Snapshot saved: [cyan]{filepath.name}[/cyan]")
    console.print(f"Tracked [bold]{len(data['files'])}[/bold] files.")

@main.command()
@click.option('--project', default='.', help='Project root directory')
def status(project):
    """Compare the last two snapshots and show health status."""
    storage = AuditStorage(project)
    snaps = storage.get_latest_snapshots(2)
    
    if len(snaps) < 2:
        console.print("[yellow][!][/yellow] Need at least two snapshots to compare. Run 'audit snapshot' first.")
        return

    before = storage.load_snapshot(snaps[1])
    after = storage.load_snapshot(snaps[0])
    
    differ = AuditDiffer()
    diff = differ.compare(before, after)
    
    score = diff['summary']['health_score']
    color = "green" if score > 8 else "yellow" if score > 5 else "red"
    
    table = Table(title="audit-watch | Project Health", border_style="blue")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style=color, justify="right")
    
    table.add_row("Health Score", f"{score}/10")
    table.add_row("Regressions", str(diff['summary']['regressions_found']))
    table.add_row("Files Modified", str(diff['summary']['files_modified']))
    table.add_row("Files Added", str(diff['summary']['files_added']))
    
    console.print(table)
    
    if diff['regressions']:
        console.print("\n[bold red][X] Regressions Found:[/bold red]")
        for r in diff['regressions']:
            console.print(f"  - {r}")
            
    if diff['modified'] and not any(r in diff['regressions'] for r in diff['modified']):
        console.print("\n[bold yellow][!] Other Modifications:[/bold yellow]")
        for f in diff['modified']:
            # Only show if not already covered by a regression
            if not any(f in r for r in diff['regressions']):
                console.print(f"  - {f}")

from .reporter import AuditReporter
from .suggester import AuditSuggester

@main.command()
@click.option('--project', default='.', help='Project root directory')
def report(project):
    """Generate report and update context.md."""
    storage = AuditStorage(project)
    snaps = storage.get_latest_snapshots(2)
    
    if len(snaps) < 2:
        console.print("[yellow][!][/yellow] Need at least two snapshots.")
        return

    before = storage.load_snapshot(snaps[1])
    after = storage.load_snapshot(snaps[0])
    
    reporter = AuditReporter(storage)
    report_text, diff = reporter.generate_report(before, after)
    storage.save_report(report_text)
    
    suggester = AuditSuggester(storage)
    context_text = suggester.generate_context(before, after, diff)
    storage.update_context(context_text)
    
    console.print(report_text)
    console.print(f"\n[bold green][OK][/bold green] context.md updated.")

@main.command()
@click.option('--project', default='.', help='Project root directory')
def suggest(project):
    """Print the ready-to-paste agent context."""
    storage = AuditStorage(project)
    if not storage.context_file.exists():
        console.print("[yellow][!][/yellow] No context.md found. Run 'audit report' first.")
        return
        
    with open(storage.context_file, 'r') as f:
        console.print(f.read())

@main.command()
@click.option('--project', default='.', help='Project root directory')
def watch(project):
    """Start the background watcher."""
    try:
        start_watcher(project)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")

from .interactive import start_interactive

@main.command()
@click.option('--project', default='.', help='Project root directory')
def start(project):
    """Start interactive mode (watcher + command line)."""
    try:
        start_interactive(project)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")

if __name__ == "__main__":
    main()
