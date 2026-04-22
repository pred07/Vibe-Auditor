import pandas as pd
import os

class CSVAnalyzer:
    def __init__(self):
        pass

    def analyze(self, filepath):
        try:
            # Read only first few rows for types
            df_head = pd.read_csv(filepath, nrows=100)
            
            # For row count and duplicates, we need more processing
            # But for large files we should be careful.
            # We'll use pandas to get duplicate count on the sample or 
            # if the file is small enough, read it all.
            file_size = os.path.getsize(filepath)
            
            row_count = 0
            duplicate_count = 0
            
            if file_size < 10 * 1024 * 1024: # < 10MB
                df_full = pd.read_csv(filepath)
                row_count = len(df_full)
                duplicate_count = int(df_full.duplicated().sum())
            else:
                # Large file - just get row count via line iteration
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    for _ in f:
                        row_count += 1
                row_count -= 1 # subtract header
            
            return {
                "columns": list(df_head.columns),
                "row_count": row_count,
                "dtypes": {col: str(dtype) for col, dtype in df_head.dtypes.items()},
                "duplicate_row_count": duplicate_count,
                "type": "csv"
            }
        except Exception as e:
            return {"error": str(e), "type": "csv"}
