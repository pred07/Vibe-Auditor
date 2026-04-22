class AuditDiffer:
    def __init__(self):
        pass

    def compare(self, before, after):
        diff = {
            "timestamp_before": before["timestamp"],
            "timestamp_after": after["timestamp"],
            "added": [],
            "removed": [],
            "modified": [],
            "regressions": [],
            "warnings": [],
            "summary": {
                "files_added": 0,
                "files_removed": 0,
                "files_modified": 0,
                "regressions_found": 0,
                "warnings_found": 0,
                "health_score": 10
            }
        }

        before_files = set(before["files"].keys())
        after_files = set(after["files"].keys())

        # Added files
        diff["added"] = list(after_files - before_files)
        diff["summary"]["files_added"] = len(diff["added"])

        # Removed files
        diff["removed"] = list(before_files - after_files)
        diff["summary"]["files_removed"] = len(diff["removed"])
        for f in diff["removed"]:
            diff["regressions"].append(f"File removed: {f}")

        # Modified files
        common_files = before_files & after_files
        for f in common_files:
            b_data = before["files"][f]
            a_data = after["files"][f]
            
            if b_data.get("has_syntax_error") or a_data.get("has_syntax_error"):
                if a_data.get("has_syntax_error") and not b_data.get("has_syntax_error"):
                    diff["regressions"].append(f"Syntax error introduced: {f} ({a_data['error']})")
                elif a_data.get("has_syntax_error"):
                    diff["warnings"].append(f"Syntax error persists: {f}")
            
            if b_data["hash"] != a_data["hash"]:
                diff["modified"].append(f)
                self._analyze_content_diff(f, b_data, a_data, diff)
        
        diff["summary"]["files_modified"] = len(diff["modified"])
        diff["summary"]["regressions_found"] = len(diff["regressions"])
        diff["summary"]["warnings_found"] = len(diff["warnings"])

        # Health score calculation
        total_tracked = len(before_files)
        if total_tracked > 0:
            # Regressions cost 2 points each
            # Modifications/Warnings cost 0.5 points each
            penalty = (len(diff["regressions"]) * 2) + (len(diff["modified"]) * 0.2) + (len(diff["warnings"]) * 0.5)
            score = 10 - penalty
            diff["summary"]["health_score"] = max(0, round(score, 1))
        
        return diff

    def _analyze_content_diff(self, filename, b_data, a_data, diff):
        f_type = b_data.get("type")
        
        if f_type == "python":
            # Check for removed functions
            b_funcs = {f["name"]: f["args"] for f in b_data.get("functions", [])}
            a_funcs = {f["name"]: f["args"] for f in a_data.get("functions", [])}
            
            for fn in b_funcs:
                if fn not in a_funcs:
                    diff["regressions"].append(f"Function removed: {fn} in {filename}")
                elif b_funcs[fn] != a_funcs[fn]:
                    diff["regressions"].append(f"Function signature changed: {fn} in {filename}")

            # Class methods
            b_classes = {c["name"]: {m["name"]: m["args"] for m in c.get("methods", [])} for c in b_data.get("classes", [])}
            a_classes = {c["name"]: {m["name"]: m["args"] for m in c.get("methods", [])} for c in a_data.get("classes", [])}
            
            for c_name, b_methods in b_classes.items():
                if c_name not in a_classes:
                    diff["regressions"].append(f"Class removed: {c_name} in {filename}")
                else:
                    a_methods = a_classes[c_name]
                    for m_name in b_methods:
                        if m_name not in a_methods:
                            diff["regressions"].append(f"Method removed: {c_name}.{m_name} in {filename}")

            # Imports
            b_imports = set(b_data.get("imports", []))
            a_imports = set(a_data.get("imports", []))
            for imp in b_imports:
                if imp not in a_imports:
                    diff["regressions"].append(f"Import removed: {imp} in {filename}")

            # Try/Except
            b_try = b_data.get("try_except_count", 0)
            a_try = a_data.get("try_except_count", 0)
            if a_try < b_try:
                diff["warnings"].append(f"Error handling (try/except) count dropped from {b_try} to {a_try} in {filename}")

        elif f_type == "javascript":
            b_funcs = set(b_data.get("functions", []))
            a_funcs = set(a_data.get("functions", []))
            for func in b_funcs:
                if func not in a_funcs:
                    diff["regressions"].append(f"Function removed: {func} in {filename}")
            
            b_exports = set(b_data.get("exports", []))
            a_exports = set(a_data.get("exports", []))
            for exp in b_exports:
                if exp not in a_exports:
                    diff["regressions"].append(f"Export removed: {exp} from {filename}")

        elif f_type == "excel":
            b_sheets = b_data.get("sheets", {})
            a_sheets = a_data.get("sheets", {})
            
            # Sheet order
            if b_data.get("sheet_order") != a_data.get("sheet_order"):
                diff["warnings"].append(f"Sheet order changed in {filename}")

            for s_name in b_sheets:
                if s_name not in a_sheets:
                    diff["regressions"].append(f"Sheet removed: {s_name} in {filename}")
                else:
                    bs = b_sheets[s_name]
                    as_ = a_sheets[s_name]
                    
                    # Columns
                    if bs.get("columns") != as_.get("columns"):
                        diff["regressions"].append(f"Column order or names changed in sheet {s_name} of {filename}")
                    
                    # Row count anomaly
                    b_rows = bs.get("row_count", 0) or 0
                    a_rows = as_.get("row_count", 0) or 0
                    if b_rows > 0 and a_rows < b_rows * 0.95:
                        diff["regressions"].append(f"Significant row count drop in {s_name}: {b_rows} -> {a_rows} in {filename}")
                    elif a_rows > b_rows * 1.1:
                        diff["warnings"].append(f"Unexpected row count increase in {s_name}: {b_rows} -> {a_rows} in {filename}")

                    # Formulas
                    b_forms = bs.get("formulas", {})
                    a_forms = as_.get("formulas", {})
                    for addr, f_val in b_forms.items():
                        if addr not in a_forms:
                            diff["regressions"].append(f"Formula removed/overwritten at {addr} in {s_name} of {filename}")
                        elif f_val != a_forms[addr]:
                            diff["regressions"].append(f"Formula changed at {addr} in {s_name} of {filename}")

        elif f_type == "csv":
            if b_data.get("columns") != a_data.get("columns"):
                diff["regressions"].append(f"CSV Columns changed in {filename}")
            
            if b_data.get("dtypes") != a_data.get("dtypes"):
                diff["warnings"].append(f"CSV Data types changed in {filename}")
            
            b_dup = b_data.get("duplicate_row_count", 0)
            a_dup = a_data.get("duplicate_row_count", 0)
            if a_dup > b_dup:
                diff["warnings"].append(f"Duplicate rows increased from {b_dup} to {a_dup} in {filename}")
