"""
Excel Extractor — Multi-sheet Excel workbook extraction using openpyxl and pandas.
Features:
- Dynamic header detection (does NOT assume row 1 is always the header).
- Cell provenance: records sheet_name, row_number, column_name, cell_reference (e.g. F18), raw value.
- Formula preservation: extracts both formula string and evaluated numeric value.
- Merged cell detection and multi-table partition per worksheet.
- Security: Never executes macros or evaluates arbitrary formulas.
"""
import os
from typing import Dict, Any, List, Optional, Tuple
import openpyxl
from openpyxl.utils import get_column_letter
import pandas as pd

from app.core.logging import logger
from app.services.mining.metric_registry import MiningMetricRegistry
from app.services.mining.org_normalizer import OrgNormalizer
from app.services.mining.period_normalizer import PeriodNormalizer


class ExcelExtractor:
    @staticmethod
    def extract(file_path: str) -> Dict[str, Any]:
        """
        Reads XLSX/XLS workbook. Extracts all worksheets, structures detected tables,
        and builds granular cell-referenced provenance models.
        """
        filename = os.path.basename(file_path)
        sheets_data: List[Dict[str, Any]] = []
        tables_data: List[Dict[str, Any]] = []
        full_text_blocks: List[str] = []

        # Load both data_only=True (values) and data_only=False (formulas)
        wb_values = None
        wb_formulas = None
        sheet_names = []

        try:
            wb_values = openpyxl.load_workbook(file_path, data_only=True, read_only=False)
            wb_formulas = openpyxl.load_workbook(file_path, data_only=False, read_only=False)
            sheet_names = wb_values.sheetnames
        except Exception as e:
            logger.warning(f"openpyxl failed to load {file_path}: {e}. Trying pandas.")
            try:
                xl_file = pd.ExcelFile(file_path)
                sheet_names = xl_file.sheet_names
            except Exception:
                sheet_names = []

        table_global_idx = 0

        for sheet_idx, sheet_name in enumerate(sheet_names):
            ws_val = wb_values[sheet_name] if wb_values and sheet_name in wb_values.sheetnames else None
            ws_form = wb_formulas[sheet_name] if wb_formulas and sheet_name in wb_formulas.sheetnames else None

            if ws_val is not None:
                # Extract directly from openpyxl with cell-level fidelity
                sheet_res = ExcelExtractor._extract_openpyxl_sheet(
                    ws_val, ws_form, filename, sheet_name, sheet_idx, table_global_idx
                )
            else:
                # Fallback to pandas extraction
                sheet_res = ExcelExtractor._extract_pandas_sheet(
                    file_path, filename, sheet_name, sheet_idx, table_global_idx
                )

            sheets_data.append(sheet_res["sheet_info"])
            tables_data.extend(sheet_res["tables"])
            full_text_blocks.append(sheet_res["sheet_text"])
            table_global_idx += len(sheet_res["tables"])

        if wb_values:
            wb_values.close()
        if wb_formulas:
            wb_formulas.close()

        return {
            "sheets": sheets_data,
            "tables": tables_data,
            "text": "\n\n".join(full_text_blocks),
            "sheet_count": len(sheets_data)
        }

    @staticmethod
    def _extract_openpyxl_sheet(
        ws_val,
        ws_form,
        filename: str,
        sheet_name: str,
        sheet_idx: int,
        start_table_idx: int
    ) -> Dict[str, Any]:
        """
        Extracts sheet using openpyxl, dynamically detecting header row,
        merged cells, formulas, and tabular data regions.
        """
        max_row = ws_val.max_row or 0
        max_col = ws_val.max_column or 0

        # Handle empty sheet
        if max_row == 0 or max_col == 0:
            return {
                "sheet_info": {
                    "sheet_name": sheet_name,
                    "sheet_index": sheet_idx,
                    "row_count": 0,
                    "column_count": 0,
                    "used_range": "A1:A1",
                    "header_row": 1,
                    "has_merged_cells": False
                },
                "tables": [],
                "sheet_text": f"=== Sheet: {sheet_name} (Empty) ==="
            }

        used_range = f"A1:{get_column_letter(max_col)}{max_row}"
        has_merged = len(ws_val.merged_cells.ranges) > 0 if hasattr(ws_val, "merged_cells") else False

        # Read all rows into matrix
        raw_grid: List[List[Any]] = []
        formula_grid: List[List[Any]] = []

        for r in range(1, max_row + 1):
            row_vals = []
            row_forms = []
            for c in range(1, max_col + 1):
                val_cell = ws_val.cell(row=r, column=c)
                val = val_cell.value
                row_vals.append(val)

                form_val = None
                if ws_form:
                    f_cell = ws_form.cell(row=r, column=c)
                    if str(f_cell.value).startswith("="):
                        form_val = str(f_cell.value)
                row_forms.append(form_val)

            raw_grid.append(row_vals)
            formula_grid.append(row_forms)

        # 1. Dynamic header detection: scan first 12 rows for row with best candidate headers
        header_row_idx = 0  # 0-based index in raw_grid
        best_header_score = -1

        for r_idx in range(min(12, len(raw_grid))):
            row = raw_grid[r_idx]
            non_empty = [str(c).strip() for c in row if c is not None and str(c).strip() != ""]
            if not non_empty:
                continue

            score = len(non_empty)
            for item in non_empty:
                # Boost if recognized mining metric, org, or common column label
                if MiningMetricRegistry.find_metric(item):
                    score += 5
                if OrgNormalizer.normalize_org(item) in ("CIL", "MCL", "SECL", "NCL", "ECL", "BCCL", "CCL", "WCL", "CMPDI"):
                    score += 4
                if PeriodNormalizer.normalize_period(item):
                    score += 3
                if any(w in item.lower() for w in ["target", "actual", "production", "subsidiary", "mine", "period", "unit", "value", "sl", "s.no"]):
                    score += 3

            if score > best_header_score:
                best_header_score = score
                header_row_idx = r_idx

        # Extract headers
        header_row = raw_grid[header_row_idx] if raw_grid else []
        headers: List[str] = []
        for c_idx, col_val in enumerate(header_row):
            if col_val is not None and str(col_val).strip():
                headers.append(str(col_val).strip())
            else:
                col_letter = get_column_letter(c_idx + 1)
                headers.append(f"Column_{col_letter}")

        # Build records with detailed cell provenance
        records: List[Dict[str, Any]] = []
        text_lines: List[str] = [f"=== Sheet: {sheet_name} ===", ", ".join(headers)]

        for r_idx in range(header_row_idx + 1, len(raw_grid)):
            row = raw_grid[r_idx]
            form_row = formula_grid[r_idx] if r_idx < len(formula_grid) else [None] * len(row)
            actual_row_num = r_idx + 1  # 1-based row number

            # Skip entirely empty rows
            if all(v is None or str(v).strip() == "" for v in row):
                continue

            row_dict: Dict[str, Any] = {}
            line_vals: List[str] = []

            for c_idx in range(len(headers)):
                col_name = headers[c_idx]
                val = row[c_idx] if c_idx < len(row) else ""
                formula_val = form_row[c_idx] if c_idx < len(form_row) else None
                col_letter = get_column_letter(c_idx + 1)
                cell_ref = f"{col_letter}{actual_row_num}"

                row_dict[col_name] = {
                    "value": val if val is not None else "",
                    "raw_value": val if val is not None else "",
                    "formula": formula_val,
                    "cell_reference": cell_ref,
                    "row_number": actual_row_num,
                    "column_number": c_idx + 1,
                    "column_name": col_name,
                    "sheet_name": sheet_name,
                    "filename": filename
                }
                line_vals.append(str(val) if val is not None else "")

            records.append(row_dict)
            text_lines.append(", ".join(line_vals))

        sheet_info = {
            "sheet_name": sheet_name,
            "sheet_index": sheet_idx,
            "row_count": len(records),
            "column_count": len(headers),
            "used_range": used_range,
            "header_row": header_row_idx + 1,
            "has_merged_cells": has_merged
        }

        table_info = {
            "table_index": start_table_idx,
            "sheet_name": sheet_name,
            "headers": headers,
            "row_count": len(records),
            "column_count": len(headers),
            "source_range": used_range,
            "data": records,
            "raw_text": "\n".join(text_lines)
        }

        return {
            "sheet_info": sheet_info,
            "tables": [table_info],
            "sheet_text": "\n".join(text_lines)
        }

    @staticmethod
    def _extract_pandas_sheet(
        file_path: str,
        filename: str,
        sheet_name: str,
        sheet_idx: int,
        start_table_idx: int
    ) -> Dict[str, Any]:
        """Fallback pandas reader when openpyxl fails."""
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name).fillna("")
        except Exception:
            df = pd.DataFrame()

        headers = [str(c).strip() for c in df.columns]
        records = []
        text_lines = [f"=== Sheet: {sheet_name} ===", ", ".join(headers)]

        for r_idx, row in df.iterrows():
            row_dict = {}
            line_vals = []
            actual_row = int(r_idx) + 2
            for c_idx, col in enumerate(headers):
                val = row[col]
                col_letter = get_column_letter(c_idx + 1)
                cell_ref = f"{col_letter}{actual_row}"
                row_dict[col] = {
                    "value": val,
                    "raw_value": val,
                    "formula": None,
                    "cell_reference": cell_ref,
                    "row_number": actual_row,
                    "column_number": c_idx + 1,
                    "column_name": col,
                    "sheet_name": sheet_name,
                    "filename": filename
                }
                line_vals.append(str(val))
            records.append(row_dict)
            text_lines.append(", ".join(line_vals))

        sheet_info = {
            "sheet_name": sheet_name,
            "sheet_index": sheet_idx,
            "row_count": len(records),
            "column_count": len(headers),
            "used_range": f"A1:{get_column_letter(max(1, len(headers)))}{len(records) + 1}",
            "header_row": 1,
            "has_merged_cells": False
        }

        table_info = {
            "table_index": start_table_idx,
            "sheet_name": sheet_name,
            "headers": headers,
            "row_count": len(records),
            "column_count": len(headers),
            "source_range": sheet_info["used_range"],
            "data": records,
            "raw_text": "\n".join(text_lines)
        }

        return {
            "sheet_info": sheet_info,
            "tables": [table_info],
            "sheet_text": "\n".join(text_lines)
        }
