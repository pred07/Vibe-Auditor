from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box
import re

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


class AuditSuggester:
    def __init__(self, storage):
        self.storage = storage

    @staticmethod
    def _to_clean_text(raw):
        """
        Convert the markdown-style context.md into clean plain text
        for the raw copy block — no ## or ### symbols.
        """
        lines = raw.splitlines()
        out = []
        for line in lines:
            if line.startswith("## "):
                out.append(line[3:])
            elif line.startswith("### "):
                section = line[4:]
                out.append("")
                out.append(section)
                out.append("-" * len(section))
            else:
                out.append(line)
        return "\n".join(out)

    def generate_context(self, before_snap, after_snap, diff, config=None, verbose=False):
        """
        Generate plain-text context.md for storage.
        Enhanced: lists protected functions by name, column names, active mode.
        """
        context = []
        context.append("## PatchBuddy Context -- paste this into your next agent prompt")
        context.append("")

        # Active mode
        if config and config.mode:
            context.append(f"### Active Mode: {config.mode_description()}")
            context.append("")

        # What is working — list protected functions + columns per file
        context.append("### What is working (DO NOT MODIFY):")
        common_files = set(before_snap["files"].keys()) & set(after_snap["files"].keys())
        # A file is "intact" if not in modified AND not in regressions/warnings
        intact = [f for f in common_files if f not in diff["modified"] and not any(f in r for r in diff["regressions"]) and not any(f in w for w in diff.get("warnings", []))]

        # Add config-protected files first
        protected_set = set(config.protected if config else [])

        shown = set()
        for f in intact:
            fdata = after_snap["files"].get(f, {})
            ftype = fdata.get("type", "")
            is_protected = f in protected_set

            prefix = "[PROTECTED] " if is_protected else ""

            if not verbose and not is_protected:
                context.append(f"- {prefix}{f} -- verified working")
                shown.add(f)
                continue

            if ftype == "python":
                funcs = fdata.get("functions", [])
                classes = fdata.get("classes", [])
                if funcs or classes:
                    context.append(f"- {prefix}{f}")
                    for fn in funcs:
                        name = fn['name'] if isinstance(fn, dict) else fn
                        args = fn.get('args', '') if isinstance(fn, dict) else ''
                        context.append(f"    fn  {name}({args}) -- verified working")
                    for cls in classes:
                        c_name = cls['name'] if isinstance(cls, dict) else cls
                        context.append(f"    cls {c_name} -- verified working")
                else:
                    context.append(f"- {prefix}{f} -- verified working")

            elif ftype == "javascript":
                funcs = fdata.get("functions", [])
                if funcs:
                    context.append(f"- {prefix}{f}")
                    for fn in funcs:
                        context.append(f"    fn  {fn} -- verified working")
                else:
                    context.append(f"- {prefix}{f} -- verified working")

            elif ftype == "excel":
                context.append(f"- {prefix}{f}")
                for sheet, sdata in fdata.get("sheets", {}).items():
                    cols = sdata.get("columns", [])
                    if cols:
                        context.append(f"    sheet [{sheet}] columns: {', '.join(cols)}")

            elif ftype == "csv":
                cols = fdata.get("columns", [])
                context.append(f"- {prefix}{f}")
                if cols:
                    context.append(f"    columns: {', '.join(cols)}")

            else:
                context.append(f"- {prefix}{f} -- verified working")

            shown.add(f)

        # Any config-protected files not already shown
        for f in protected_set:
            if f not in shown:
                context.append(f"- [PROTECTED] {f} -- manually marked critical")

        context.append("")

        # What broke
        if diff["regressions"]:
            context.append("### What broke in the last change (FIX THESE):")
            for r in diff["regressions"]:
                context.append(f"- {r}")
            context.append("")
        
        if diff.get("warnings"):
            context.append("### Warnings / Suspicious changes (VERIFY THESE):")
            for w in diff["warnings"]:
                context.append(f"- {w}")
            context.append("")

        context.append("### Instructions for agent:")
        context.append("- Your role is to VERIFY and REPORT. The developer will make all final decisions on implementation.")
        if config and config.mode == "safe":
            context.append("- MODE SAFE: Do not remove or rename any existing function, class, or column.")
        elif config and config.mode == "feature":
            context.append("- MODE FEATURE: New additions are allowed. Do not remove or modify any existing item.")
        elif config and config.mode == "fix":
            mf = config.mode_file or "<unknown>"
            context.append(f"- MODE FIX: Only '{mf}' may be changed. All other files are locked.")
        
        if diff["regressions"] or diff.get("warnings"):
            context.append("- Audit the regressions/warnings above. You may suggest fixes in your reply, but DO NOT modify files unless the developer approves.")
        
        context.append("- Report any removed functions, methods, or imports.")
        context.append("- Verify if Excel formulas and CSV schemas remain identical to previous versions.")

        return "\n".join(context)

    def print_context(self, storage, config=None):
        """Render context.md as a styled rich Panel in the terminal."""
        if not storage.context_file.exists():
            _console.print(
                f"[{C_WARNING}][!][/{C_WARNING}] No context yet. Type "
                f"[bold {C_PRIMARY}]report[/bold {C_PRIMARY}] first."
            )
            return

        with open(storage.context_file, 'r', encoding='utf-8') as f:
            raw = f.read()

        lines = raw.splitlines()
        text = Text()

        for line in lines:
            if line.startswith("## "):
                text.append(line[3:] + "\n", style=f"bold {C_TEXT}")
            elif line.startswith("### "):
                heading = line[4:]
                if "DO NOT MODIFY" in heading or "working" in heading.lower():
                    text.append("\n[ok]  " + heading + "\n", style=f"bold {C_SUCCESS}")
                elif "broke" in heading.lower() or "fix" in heading.lower():
                    text.append("\n[!!] " + heading + "\n", style=f"bold {C_DANGER}")
                elif "Instructions" in heading:
                    text.append("\n[>>] " + heading + "\n", style=f"bold {C_PRIMARY}")
                elif "Mode" in heading or "mode" in heading:
                    text.append("\n[**] " + heading + "\n", style=f"bold {C_WARNING}")
                else:
                    text.append("\n" + heading + "\n", style=f"bold {C_TEXT}")
            elif line.startswith("    fn  ") or line.startswith("    cls "):
                text.append("      ", style="")
                text.append(line.strip() + "\n", style=C_DIM)
            elif line.startswith("    sheet") or line.startswith("    col"):
                text.append("      ", style="")
                text.append(line.strip() + "\n", style=C_DIM)
            elif line.startswith("- [PROTECTED]"):
                text.append("  [P] ", style=f"bold {C_WARNING}")
                text.append(line[2 + len("[PROTECTED] "):] + "\n", style=C_TEXT)
            elif line.startswith("- "):
                content = line[2:]
                if "verified working" in content or "verified intact" in content:
                    text.append("  +  ", style=C_SUCCESS)
                    text.append(content + "\n", style=C_TEXT)
                elif any(k in content.lower() for k in ["prioritize", "restore", "fix"]):
                    text.append("  x  ", style=C_DANGER)
                    text.append(content + "\n", style=C_TEXT)
                else:
                    text.append("  -  ", style=C_MUTED)
                    text.append(content + "\n", style=f"dim {C_TEXT}")
            elif line == "":
                text.append("\n")
            else:
                text.append(line + "\n", style=f"dim {C_TEXT}")

        panel = Panel(
            text,
            title=f"[bold {C_PRIMARY}] AGENT CONTEXT [/bold {C_PRIMARY}]",
            subtitle=f"[{C_DIM}]copy and paste into your next prompt[/{C_DIM}]",
            border_style=C_BORDER,
            box=box.ROUNDED,
            padding=(0, 1),
            expand=False,
        )
        _console.print(panel)

        # Raw copyable block — clean, no markdown symbols
        clean = self._to_clean_text(raw)
        _console.print()
        _console.print(f"[{C_DIM}]  raw copy block  [/{C_DIM}]", justify="center")
        _console.print(f"[{C_DIM}]" + "-" * 44 + f"[/{C_DIM}]")
        _console.print(f"[{C_DIM}]{clean}[/{C_DIM}]")
        _console.print(f"[{C_DIM}]" + "-" * 44 + f"[/{C_DIM}]")
