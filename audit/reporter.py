from .differ import AuditDiffer
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

_console = Console(highlight=False)

# Claude-inspired palette
C_PRIMARY = "#E07040"  # Original Orange
C_MUTED   = "#A0826D"
C_SUCCESS = "#7FB77E"
C_WARNING = "#D4A843"
C_DANGER  = "#C05050"
C_TEXT    = "#D4C4B4"
C_DIM     = "#7A6A5A"
C_BORDER  = "#A0826D"


class AuditReporter:
    def __init__(self, storage):
        self.storage = storage
        self.differ = AuditDiffer()

    # ── Basic report ─────────────────────────────────────────────────────────

    def generate_report(self, before_snap, after_snap):
        diff = self.differ.compare(before_snap, after_snap)

        timestamp = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
        score = diff['summary']['health_score']

        score_color = C_SUCCESS if score >= 9 else C_WARNING if score >= 5 else C_DANGER
        score_str = f"[bold {score_color}]{score}/10[/bold {score_color}]"

        lines = []
        lines.append(f"[{C_DIM}]generated[/{C_DIM}]  [{C_TEXT}]{timestamp}[/{C_TEXT}]")
        lines.append(f"[{C_DIM}]health   [/{C_DIM}]  {score_str}")
        lines.append("")

        if diff['regressions']:
            lines.append(f"[bold {C_DANGER}]  [REGRESSIONS][/bold {C_DANGER}]")
            for r in diff['regressions']:
                lines.append(f"  [{C_DANGER}]x[/{C_DANGER}]  [{C_TEXT}]{r}[/{C_TEXT}]")
            lines.append("")
        
        if diff.get('warnings'):
            lines.append(f"[bold {C_WARNING}]  [WARNINGS][/bold {C_WARNING}]")
            for w in diff['warnings']:
                lines.append(f"  [{C_WARNING}]![/{C_WARNING}]  [{C_TEXT}]{w}[/{C_TEXT}]")
            lines.append("")

        if not diff['regressions'] and not diff.get('warnings'):
            lines.append(f"[bold {C_SUCCESS}]  [OK] No major issues detected[/bold {C_SUCCESS}]")
            lines.append("")

        modified_shown = []
        if diff['modified']:
            # Filter out files already mentioned in regressions or warnings
            filtered = [f for f in diff['modified'] if not any(f in r for r in diff['regressions']) and not any(f in w for w in diff.get('warnings', []))]
            if filtered:
                lines.append(f"[bold {C_WARNING}]  [OTHER MODIFIED][/bold {C_WARNING}]")
                for f in filtered:
                    lines.append(f"  [{C_WARNING}]~[/{C_WARNING}]  [{C_TEXT}]{f}[/{C_TEXT}]")
                    modified_shown.append(f)
                lines.append("")

        if diff['added']:
            lines.append(f"[bold {C_PRIMARY}]  [ADDED][/bold {C_PRIMARY}]")
            for f in diff['added']:
                lines.append(f"  [{C_PRIMARY}]+[/{C_PRIMARY}]  [{C_TEXT}]{f}[/{C_TEXT}]")
            lines.append("")

        lines.append(f"[{C_DIM}]{'─' * 60}[/{C_DIM}]")
        if score < 5:
            lines.append(f"[bold {C_DANGER}]risk: HIGH[/bold {C_DANGER}]   significant regressions — review immediately")
        elif score < 9:
            lines.append(f"[bold {C_WARNING}]risk: MEDIUM[/bold {C_WARNING}] structural changes — verify functionality")
        else:
            lines.append(f"[bold {C_SUCCESS}]risk: LOW[/bold {C_SUCCESS}]    changes look safe")

        content = "\n".join(lines)
        panel = Panel(
            content,
            title=f"[bold {C_PRIMARY}] PATCHBUDDY REPORT [/bold {C_PRIMARY}]",
            border_style=C_BORDER,
            box=box.ROUNDED,
            padding=(0, 1),
            expand=False,
        )
        _console.print(panel)

        plain_lines = [
            f"PATCHBUDDY REPORT -- {timestamp}",
            f"Health Score: {score}/10", "",
        ]
        if diff['regressions']:
            plain_lines.append("REGRESSIONS FOUND:")
            for r in diff['regressions']:
                plain_lines.append(f"  - {r}")
        if diff.get('warnings'):
            plain_lines.append("\nWARNINGS:")
            for w in diff['warnings']:
                plain_lines.append(f"  - {w}")
        if modified_shown:
            plain_lines.append("\nOTHER MODIFIED FILES:")
            for f in modified_shown:
                plain_lines.append(f"  - {f}")
        plain_lines.append(f"\nRISK: {'HIGH' if score < 5 else 'MEDIUM' if score < 9 else 'LOW'}")

        return "\n".join(plain_lines), diff

    # ── Detail report ────────────────────────────────────────────────────────

    def generate_detail(self, before_snap, after_snap):
        """Full per-file, per-function breakdown."""
        diff = self.differ.compare(before_snap, after_snap)
        score = diff['summary']['health_score']
        score_color = C_SUCCESS if score >= 9 else C_WARNING if score >= 5 else C_DANGER

        lines = []
        lines.append(f"[{C_DIM}]health[/{C_DIM}]  [bold {score_color}]{score}/10[/bold {score_color}]")
        lines.append("")

        # --- Per-file breakdown ---
        all_files = set(list(before_snap['files'].keys()) + list(after_snap['files'].keys()))

        for fname in sorted(all_files):
            in_before = fname in before_snap['files']
            in_after  = fname in after_snap['files']

            if not in_before and in_after:
                lines.append(f"[{C_PRIMARY}]+ ADDED  [/{C_PRIMARY}] [{C_TEXT}]{fname}[/{C_TEXT}]")
                continue
            if in_before and not in_after:
                lines.append(f"[{C_DANGER}]x REMOVED[/{C_DANGER}] [{C_TEXT}]{fname}[/{C_TEXT}]")
                continue

            b = before_snap['files'][fname]
            a = after_snap['files'][fname]

            if b['hash'] == a.get('hash') and not a.get('has_syntax_error'):
                lines.append(f"[{C_DIM}]  ok      [{C_DIM}] [{C_DIM}]{fname}[/{C_DIM}]")
                continue

            if a.get('has_syntax_error'):
                lines.append(f"[{C_DANGER}]! SYNTAX [/{C_DANGER}] [{C_DANGER}]{fname}[/{C_DANGER}]")
                lines.append(f"    [{C_DANGER}]>> {a['error']}[/{C_DANGER}]")
                if b['hash'] == a['hash']: continue

            lines.append(f"[{C_WARNING}]~ MODIFIED[/{C_WARNING}] [{C_TEXT}]{fname}[/{C_TEXT}]")

            # Python diff
            if b.get('type') == 'python':
                # Functions
                b_funcs = {f['name']: f['args'] for f in b.get('functions', [])}
                a_funcs = {f['name']: f['args'] for f in a.get('functions', [])}

                for fn in sorted(b_funcs):
                    if fn not in a_funcs:
                        lines.append(f"    [{C_DANGER}]x removed[/{C_DANGER}]  fn {fn}()")
                    elif b_funcs[fn] != a_funcs.get(fn):
                        lines.append(f"    [{C_WARNING}]~ sig chg [/{C_WARNING}]  fn {fn}()")
                
                # Class methods
                b_classes = {c['name']: {m['name']: m['args'] for m in c.get('methods', [])} for c in b.get('classes', [])}
                a_classes = {c['name']: {m['name']: m['args'] for m in c.get('methods', [])} for c in a.get('classes', [])}
                
                for cn in sorted(b_classes):
                    if cn not in a_classes:
                        lines.append(f"    [{C_DANGER}]x removed[/{C_DANGER}]  class {cn}")
                    else:
                        for mn in sorted(b_classes[cn]):
                            if mn not in a_classes[cn]:
                                lines.append(f"    [{C_DANGER}]x removed[/{C_DANGER}]  method {cn}.{mn}()")
                
                # Imports
                b_imps = set(b.get('imports', []))
                a_imps = set(a.get('imports', []))
                for imp in sorted(b_imps - a_imps):
                    lines.append(f"    [{C_DANGER}]x removed[/{C_DANGER}]  import {imp}")

            # JS diff
            elif b.get('type') == 'javascript':
                b_funcs = set(b.get('functions', []))
                a_funcs = set(a.get('functions', []))
                for fn in sorted(b_funcs - a_funcs):
                    lines.append(f"    [{C_DANGER}]x removed[/{C_DANGER}]  fn {fn}")
                
                b_exps = set(b.get('exports', []))
                a_exps = set(a.get('exports', []))
                for ex in sorted(b_exps - a_exps):
                    lines.append(f"    [{C_DANGER}]x removed[/{C_DANGER}]  export {ex}")

            # Excel diff
            elif b.get('type') == 'excel':
                for sheet, b_sheet in b.get('sheets', {}).items():
                    a_sheet = a.get('sheets', {}).get(sheet, {})
                    if not a_sheet:
                        lines.append(f"    [{C_DANGER}]x removed[/{C_DANGER}]  sheet [{sheet}]")
                        continue
                    
                    if b_sheet.get('columns') != a_sheet.get('columns'):
                        lines.append(f"    [{C_WARNING}]~ reorder [/{C_WARNING}]  columns in [{sheet}]")
                    
                    b_rows = b_sheet.get('row_count', 0)
                    a_rows = a_sheet.get('row_count', 0)
                    if a_rows != b_rows:
                        col = C_DANGER if a_rows < b_rows * 0.95 else C_WARNING
                        lines.append(f"    [{col}]~ rows    [/{col}]  {b_rows} -> {a_rows} in [{sheet}]")

                    b_forms = b_sheet.get('formulas', {})
                    a_forms = a_sheet.get('formulas', {})
                    for addr in sorted(b_forms):
                        if addr not in a_forms:
                            lines.append(f"    [{C_DANGER}]x formula [/{C_DANGER}]  lost at {addr} in [{sheet}]")
                        elif b_forms[addr] != a_forms[addr]:
                            lines.append(f"    [{C_WARNING}]~ formula [/{C_WARNING}]  changed at {addr} in [{sheet}]")

            # CSV diff
            elif b.get('type') == 'csv':
                if b.get('columns') != a.get('columns'):
                    lines.append(f"    [{C_DANGER}]x columns [/{C_DANGER}]  schema changed")
                if b.get('dtypes') != a.get('dtypes'):
                    lines.append(f"    [{C_WARNING}]~ types   [/{C_WARNING}]  schema drift")
                b_rows = b.get('row_count', 0)
                a_rows = a.get('row_count', 0)
                if a_rows != b_rows:
                    lines.append(f"    [{C_WARNING}]~ rows    [/{C_WARNING}]  {b_rows} -> {a_rows}")

        content = "\n".join(lines)
        panel = Panel(
            content,
            title=f"[bold {C_PRIMARY}] DETAILED DIFF [/bold {C_PRIMARY}]",
            border_style=C_BORDER,
            box=box.ROUNDED,
            padding=(1, 2),
        )
        _console.print(panel)

    # ── History report ───────────────────────────────────────────────────────

    def generate_history(self, storage):
        """Table of all past snapshots with health score where available."""
        all_snaps = storage.get_all_snapshots()
        if not all_snaps:
            _console.print(f"[{C_WARNING}][!][/{C_WARNING}] No snapshots found.")
            return

        differ = AuditDiffer()

        table = Table(
            title=f"[bold {C_PRIMARY}] Snapshot History [/bold {C_PRIMARY}]",
            border_style=C_BORDER,
            box=box.ROUNDED,
            header_style=f"bold {C_MUTED}",
            padding=(0, 1),
        )
        table.add_column("#",           style=C_DIM,  width=4, justify="right")
        table.add_column("Timestamp",   style=C_TEXT, min_width=20)
        table.add_column("Trigger",     style=C_DIM,  width=8)
        table.add_column("Files",       style=C_DIM,  width=6, justify="right")
        table.add_column("Health",      width=10,     justify="right")
        table.add_column("Regressions", width=12,     justify="right")

        snap_list = list(all_snaps)
        for idx, snap_path in enumerate(snap_list):
            try:
                meta = storage.load_snapshot_meta(snap_path)
                ts       = meta['timestamp'][:19].replace("T", "  ")
                trigger  = meta['trigger']
                n_files  = str(meta['file_count'])

                # Compute health by comparing with next older snapshot
                if idx + 1 < len(snap_list):
                    before = storage.load_snapshot(snap_list[idx + 1])
                    after  = storage.load_snapshot(snap_path)
                    diff   = differ.compare(before, after)
                    score  = diff['summary']['health_score']
                    regs   = diff['summary']['regressions_found']
                    sc_col = C_SUCCESS if score >= 9 else C_WARNING if score >= 5 else C_DANGER
                    health_str = f"[bold {sc_col}]{score}/10[/bold {sc_col}]"
                    reg_col    = C_SUCCESS if regs == 0 else C_DANGER
                    reg_str    = f"[{reg_col}]{regs}[/{reg_col}]"
                else:
                    health_str = f"[{C_DIM}]baseline[/{C_DIM}]"
                    reg_str    = f"[{C_DIM}]--[/{C_DIM}]"

                num_str = f"[{C_DIM}]{idx + 1}[/{C_DIM}]"
                table.add_row(num_str, ts, trigger, n_files, health_str, reg_str)

            except Exception:
                table.add_row(str(idx + 1), str(snap_path.name), "?", "?", "?", "?")

        _console.print(table)
