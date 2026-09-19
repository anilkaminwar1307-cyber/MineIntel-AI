"""
CSV Extractor — Extracts tabular data, headers, and text representation from CSV files.
Features:
- Robust encoding detection (utf-8, utf-8-sig, latin1, cp1252, iso-8859-1).
- Sniffing delimiter support (comma, semicolon, tab).
- Row and column provenance coordinates.
- Preserves source context for evidence linking.
"""
import os
import csv
import io
from typing import Dict, Any, List
import pandas as pd
from app.core.logging import logger


class CSVExtractor:
    @staticmethod
    def extract(file_path: str) -> Dict[str, Any]:
        """
        Reads a CSV file and extracts tabular structure, headers, rows, and raw preview.
        """
        filename = os.path.basename(file_path)
        encodings = ["utf-8", "utf-8-sig", "latin1", "cp1252", "iso-8859-1"]
        df = None
        used_encoding = "utf-8"

        for enc in encodings:
            try:
                # Use python engine to sniff delimiter (comma, tab, semicolon)
                df = pd.read_csv(file_path, encoding=enc, sep=None, engine="python")
                used_encoding = enc
                break
            except Exception:
                continue

        if df is None:
            # Fallback with standard comma read_csv latin1
            df = pd.read_csv(file_path, encoding="latin1")
            used_encoding = "latin1"

        # Sanitize columns
        df.columns = [str(col).strip() for col in df.columns]
        headers = list(df.columns)
        df_clean = df.fillna("")

        records: List[Dict[str, Any]] = []
        csv_text_lines = [", ".join(headers)]

        for r_idx, row in df_clean.iterrows():
            row_num = int(r_idx) + 2  # Row 1 is header
            row_dict: Dict[str, Any] = {}
            line_vals: List[str] = []

            for c_idx, col in enumerate(headers):
                val = row[col]
                row_dict[col] = {
                    "value": val,
                    "raw_value": val,
                    "row_number": row_num,
                    "column_number": c_idx + 1,
                    "column_name": col,
                    "sheet_name": "CSV_DATA",
                    "filename": filename
                }
                line_vals.append(str(val))

            records.append(row_dict)
            if len(csv_text_lines) < 200:
                csv_text_lines.append(", ".join(line_vals))

        raw_text = "\n".join(csv_text_lines)

        table_info = {
            "table_index": 0,
            "sheet_name": "CSV_DATA",
            "headers": headers,
            "row_count": len(df_clean),
            "column_count": len(headers),
            "source_range": f"R1C1:R{len(df_clean) + 1}C{len(headers)}",
            "data": records,
            "raw_text": raw_text,
            "confidence": 1.0,
            "structure_status": "CLEAN"
        }

        return {
            "tables": [table_info],
            "text": raw_text,
            "row_count": len(df_clean),
            "column_count": len(headers),
            "encoding": used_encoding
        }
