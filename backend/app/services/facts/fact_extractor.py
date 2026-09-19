"""
Fact Extractor — Deterministic mining metric extractor.
Extracts quantitative facts from tabular rows and text snippets.
Adheres strictly to Rule 1: Zero LLM hallucination for numerical metrics.
All values are parsed as floats/ints and associated with full provenance coordinates.
"""
import re
from typing import List, Dict, Any, Optional
from app.models.enums import ExtractionMethod
from app.services.mining.metric_registry import MiningMetricRegistry
from app.services.mining.unit_normalizer import UnitNormalizer
from app.services.mining.period_normalizer import PeriodNormalizer
from app.services.mining.org_normalizer import OrgNormalizer, VALID_SUBSIDIARIES
from app.services.mining.entity_extractor import MiningEntityExtractor
from app.services.facts.confidence_engine import ConfidenceEngine


class FactExtractor:
    @classmethod
    def extract_from_tables(
        cls,
        tables: List[Dict[str, Any]],
        document_id: str,
        doc_category: Optional[str] = None,
        doc_quality_score: float = 1.0,
        global_context_entities: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Scans extracted tables (CSV, Excel, or PDF) for metric rows/columns and numbers.
        Handles:
        1. Multi-metric column tables (e.g. Subsidiary | Production | Target | Period)
        2. Metric-value-unit tables (e.g. Mine | Metric | Value | Unit | Period)
        3. Row-metric tables (e.g. Row label is metric, columns are periods/types)
        """
        facts: List[Dict[str, Any]] = []
        global_entities = global_context_entities or {}

        for tbl in tables:
            page_num = tbl.get("page_number")
            sheet_name = tbl.get("sheet_name", "Sheet1")
            headers = tbl.get("headers", [])
            data_rows = tbl.get("data", [])
            is_spreadsheet = "sheet" in sheet_name.lower() or tbl.get("sheet_name") is not None

            # Detect if this table has explicit "Metric" and "Value" columns (Format 2)
            metric_col_name = None
            value_col_name = None
            unit_col_name = None
            period_col_name = None
            org_col_name = None
            mine_col_name = None

            for col in headers:
                c_low = col.strip().lower()
                if c_low in ("metric", "parameter", "indicator", "activity", "item", "particulars"):
                    metric_col_name = col
                elif c_low in ("value", "actual", "figure", "qty", "quantity", "amount", "total"):
                    value_col_name = col
                elif c_low in ("unit", "uom"):
                    unit_col_name = col
                elif any(p in c_low for p in ("period", "year", "fy", "financial year", "quarter", "month")):
                    period_col_name = col
                elif any(o in c_low for o in ("subsidiary", "company", "organization", "org", "co")):
                    org_col_name = col
                elif any(m in c_low for m in ("mine", "colliery", "project", "block", "area", "field")):
                    mine_col_name = col

            # Map column headers to metrics if columns are metric names (Format 1)
            col_metric_map = {}
            for col in headers:
                matched = MiningMetricRegistry.find_metric(col)
                if matched:
                    col_metric_map[col] = matched

            # Check if headers contain global period or subsidiary
            header_text = " ".join(headers)
            table_period = PeriodNormalizer.extract_period(header_text) or global_entities.get("period")
            table_subsidiary = None
            for token in headers:
                norm_sub = OrgNormalizer.normalize_org(token)
                if norm_sub in ["CIL", "ECL", "BCCL", "CCL", "WCL", "SECL", "NCL", "MCL", "CMPDI"]:
                    table_subsidiary = norm_sub
                    break

            for r_idx, row in enumerate(data_rows):
                if not isinstance(row, dict):
                    continue

                # Context extraction from row
                row_period = None
                row_subsidiary = None
                row_mine = None
                row_unit = None

                # 1. Extract period from row cells
                if period_col_name and period_col_name in row:
                    p_cell = cls._cell_val(row[period_col_name])
                    row_period = PeriodNormalizer.normalize_period(p_cell) or PeriodNormalizer.extract_period(p_cell)

                if not row_period:
                    for k, v in row.items():
                        if any(pw in k.lower() for pw in ["period", "year", "quarter", "month", "fy"]):
                            v_clean = cls._cell_val(v)
                            p_match = PeriodNormalizer.normalize_period(v_clean) or PeriodNormalizer.extract_period(v_clean)
                            if p_match:
                                row_period = p_match
                                break

                # 2. Extract subsidiary from row cells
                if org_col_name and org_col_name in row:
                    o_cell = cls._cell_val(row[org_col_name])
                    cand_sub = OrgNormalizer.normalize_org(o_cell)
                    if cand_sub in ["CIL", "ECL", "BCCL", "CCL", "WCL", "SECL", "NCL", "MCL", "CMPDI"]:
                        row_subsidiary = cand_sub

                if not row_subsidiary:
                    for k, v in row.items():
                        v_clean = cls._cell_val(v)
                        cand_sub = OrgNormalizer.normalize_org(v_clean)
                        if cand_sub in ["CIL", "ECL", "BCCL", "CCL", "WCL", "SECL", "NCL", "MCL", "CMPDI"]:
                            row_subsidiary = cand_sub
                            break

                # 3. Extract mine/location from row cells
                if mine_col_name and mine_col_name in row:
                    m_cell = cls._cell_val(row[mine_col_name])
                    if m_cell and len(m_cell) > 2:
                        row_mine = m_cell

                # 4. Extract unit from row cells
                if unit_col_name and unit_col_name in row:
                    u_cell = cls._cell_val(row[unit_col_name])
                    c_unit, _ = UnitNormalizer.normalize(u_cell)
                    if c_unit:
                        row_unit = c_unit

                # Check first column for row-based metric or subsidiary
                first_col = headers[0] if headers else ""
                first_col_val = cls._cell_val(row.get(first_col, ""))
                row_metric = MiningMetricRegistry.find_metric(first_col_val)

                # CASE 1: Format with explicit Metric and Value columns (e.g. CSV with Mine, Metric, Value, Unit, Period)
                if metric_col_name and value_col_name and metric_col_name in row and value_col_name in row:
                    metric_str = cls._cell_val(row[metric_col_name])
                    metric_info = MiningMetricRegistry.find_metric(metric_str)
                    val_cell = row[value_col_name]
                    val_str = cls._cell_val(val_cell)
                    num_val = cls._parse_number(val_str)

                    if metric_info and num_val is not None:
                        canonical_unit = row_unit
                        if not canonical_unit:
                            canonical_unit, _ = UnitNormalizer.normalize(val_str)
                        if not canonical_unit:
                            canonical_unit = metric_info.get("default_unit")

                        subsidiary = row_subsidiary or table_subsidiary or global_entities.get("subsidiary")
                        period = row_period or table_period or global_entities.get("period")
                        cell_ref = cls._cell_prop(val_cell, "cell_reference")
                        row_num = cls._cell_prop(val_cell, "row_number", r_idx + 2)

                        source_context = f"{sheet_name} | Row {row_num}: " + " | ".join(
                            f"{k}: {cls._cell_val(v)}" for k, v in row.items()
                        )

                        method = ExtractionMethod.STRUCTURED_TABLE.value
                        conf, rationale = ConfidenceEngine.calculate_confidence(
                            extraction_method=method,
                            has_metric=True,
                            has_unit=bool(canonical_unit),
                            has_period=bool(period),
                            has_subsidiary=bool(subsidiary),
                            document_quality_score=doc_quality_score,
                            is_structured_spreadsheet=is_spreadsheet
                        )

                        facts.append({
                            "document_id": document_id,
                            "metric_name": metric_info["name"],
                            "metric_code": metric_info["code"],
                            "raw_metric_name": metric_str,
                            "numeric_value": num_val,
                            "unit": canonical_unit,
                            "raw_unit": canonical_unit,
                            "reporting_period": period,
                            "subsidiary": subsidiary,
                            "mine": row_mine or global_entities.get("mine"),
                            "location": global_entities.get("project"),
                            "confidence_score": conf,
                            "confidence_rationale": rationale,
                            "validation_status": ConfidenceEngine.get_initial_validation_status(conf),
                            "extraction_method": method,
                            "page_number": page_num,
                            "sheet_name": sheet_name,
                            "row_number": row_num,
                            "column_name": value_col_name,
                            "cell_reference": cell_ref,
                            "table_reference": sheet_name,
                            "source_context": source_context
                        })
                        continue

                # CASE 2: Column-metric or Row-metric extraction
                for col in headers:
                    cell_raw = row.get(col, "")
                    val_str = cls._cell_val(cell_raw)
                    if not val_str:
                        continue

                    # Don't parse the column that acts as label/organization/period
                    if col in (org_col_name, period_col_name, mine_col_name, unit_col_name, first_col):
                        # But if first_col is not row_metric, it could be a metric value if col_metric_map has it
                        if col == first_col and not col_metric_map.get(col):
                            continue
                        elif col != first_col and not col_metric_map.get(col):
                            continue

                    metric_info = col_metric_map.get(col) or row_metric
                    if not metric_info:
                        continue

                    num_val = cls._parse_number(val_str)
                    if num_val is None:
                        continue

                    # Avoid confusing four-digit year (e.g. 2025) with metric value if not recognized capex/drilling
                    if 1950 <= num_val <= 2050 and "." not in val_str and metric_info["code"] not in ("DRILLING", "BOREHOLE_COUNT"):
                        continue

                    canonical_unit = row_unit
                    if not canonical_unit:
                        canonical_unit, _ = UnitNormalizer.normalize(val_str)
                    if not canonical_unit:
                        canonical_unit, _ = UnitNormalizer.normalize(col)
                    if not canonical_unit:
                        canonical_unit = metric_info.get("default_unit")

                    subsidiary = row_subsidiary or table_subsidiary or global_entities.get("subsidiary")
                    # If column name has a period (e.g. "Q1 FY25"), that takes precedence
                    col_period = PeriodNormalizer.extract_period(col) or PeriodNormalizer.normalize_period(col)
                    period = col_period or row_period or table_period or global_entities.get("period")

                    cell_ref = cls._cell_prop(cell_raw, "cell_reference")
                    row_num = cls._cell_prop(cell_raw, "row_number", r_idx + 2)
                    col_name = cls._cell_prop(cell_raw, "column_name", col)

                    source_context = f"{sheet_name} | Cell: {cell_ref or f'R{row_num}C{col}'} | Row context: {first_col_val or ''} | Col: '{col}' -> Value: {val_str}"

                    method = ExtractionMethod.STRUCTURED_TABLE.value
                    conf, rationale = ConfidenceEngine.calculate_confidence(
                        extraction_method=method,
                        has_metric=True,
                        has_unit=bool(canonical_unit),
                        has_period=bool(period),
                        has_subsidiary=bool(subsidiary),
                        document_quality_score=doc_quality_score,
                        is_structured_spreadsheet=is_spreadsheet
                    )

                    facts.append({
                        "document_id": document_id,
                        "metric_name": metric_info["name"],
                        "metric_code": metric_info["code"],
                        "raw_metric_name": col if col in col_metric_map else first_col_val,
                        "numeric_value": num_val,
                        "unit": canonical_unit,
                        "raw_unit": canonical_unit,
                        "reporting_period": period,
                        "subsidiary": subsidiary,
                        "mine": row_mine or global_entities.get("mine"),
                        "location": global_entities.get("project"),
                        "confidence_score": conf,
                        "confidence_rationale": rationale,
                        "validation_status": ConfidenceEngine.get_initial_validation_status(conf),
                        "extraction_method": method,
                        "page_number": page_num,
                        "sheet_name": sheet_name,
                        "row_number": row_num,
                        "column_name": col_name,
                        "cell_reference": cell_ref,
                        "table_reference": sheet_name,
                        "source_context": source_context
                    })

        return facts

    @classmethod
    def extract_from_text(
        cls,
        text: str,
        document_id: str,
        page_number: Optional[int] = None,
        doc_quality_score: float = 1.0,
        global_context_entities: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Extracts facts from free text and paragraphs using strict deterministic regex patterns.
        """
        facts: List[Dict[str, Any]] = []
        if not text:
            return facts

        global_entities = global_context_entities or {}

        pattern = re.compile(
            r'\b([A-Z]{3,5})?\s*(?:achieved|recorded|reported|produced|mined|drilled)?\s*'
            r'([a-zA-Z\s]{3,35}?)\s*(?:of|is|was|reached|totalling|stands at)?\s*'
            r'[:=]?\s*([0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)\s*'
            r'(MT|BCM|Lakh Tonnes|Million Tonnes|Tonnes|Mte|M\.T\.|m|Mm3|ha|Cr|INR Cr)?\b'
            r'(?:[^\n\.\;]*?(?:during|in|for)?\s*(FY\s*\d{4}[-–]\d{2,4}|\d{4}[-–]\d{2,4}|Q[1-4]\s*FY\d{2}))?',
            re.IGNORECASE
        )

        for match in pattern.finditer(text):
            sub_raw, metric_raw, num_raw, unit_raw, period_raw = match.groups()

            norm_sub = OrgNormalizer.normalize_org(sub_raw)
            if not norm_sub or norm_sub not in VALID_SUBSIDIARIES:
                norm_sub = None
                words = metric_raw.strip().split()
                if words:
                    cand = OrgNormalizer.normalize_org(words[0])
                    if cand in VALID_SUBSIDIARIES:
                        norm_sub = cand
                        rest = words[1:]
                        if rest and rest[0].lower() in ("achieved", "recorded", "reported", "produced", "mined", "drilled"):
                            rest = rest[1:]
                        metric_raw = " ".join(rest)

            metric_info = MiningMetricRegistry.find_metric(metric_raw)
            if not metric_info:
                continue

            num_val = cls._parse_number(num_raw)
            if num_val is None or num_val == 0.0:
                continue

            # Check year confusion
            if 1950 <= num_val <= 2050 and "." not in num_raw and metric_info["code"] not in ("DRILLING", "BOREHOLE_COUNT"):
                continue

            canonical_unit, _ = UnitNormalizer.normalize(unit_raw) if unit_raw else (metric_info.get("default_unit"), None)
            subsidiary = norm_sub or global_entities.get("subsidiary")
            period = PeriodNormalizer.normalize_period(period_raw) if period_raw else global_entities.get("period")

            snippet_start = max(0, match.start() - 40)
            snippet_end = min(len(text), match.end() + 40)
            source_context = f"...{text[snippet_start:snippet_end].strip()}..."

            method = ExtractionMethod.REGEX_PATTERN.value
            conf, rationale = ConfidenceEngine.calculate_confidence(
                extraction_method=method,
                has_metric=True,
                has_unit=bool(canonical_unit),
                has_period=bool(period),
                has_subsidiary=bool(subsidiary),
                document_quality_score=doc_quality_score
            )

            facts.append({
                "document_id": document_id,
                "metric_name": metric_info["name"],
                "metric_code": metric_info["code"],
                "raw_metric_name": metric_raw.strip(),
                "numeric_value": num_val,
                "unit": canonical_unit,
                "raw_unit": canonical_unit,
                "reporting_period": period,
                "subsidiary": subsidiary,
                "mine": global_entities.get("mine"),
                "location": global_entities.get("project"),
                "confidence_score": conf,
                "confidence_rationale": rationale,
                "validation_status": ConfidenceEngine.get_initial_validation_status(conf),
                "extraction_method": method,
                "page_number": page_number,
                "source_context": source_context
            })

        return facts

    @staticmethod
    def _cell_val(cell: Any) -> str:
        if isinstance(cell, dict):
            return str(cell.get("value", "")).strip()
        return str(cell).strip() if cell is not None else ""

    @staticmethod
    def _cell_prop(cell: Any, prop: str, default: Any = None) -> Any:
        if isinstance(cell, dict):
            return cell.get(prop, default)
        return default

    @staticmethod
    def _parse_number(val_str: str) -> Optional[float]:
        """
        Parses numeric mining figures:
        12.4, 12,400, 12.4 MT, ₹ 125 Cr, 95%, 1,250 m, 1.2 million tonnes
        """
        if not val_str:
            return None
        clean = str(val_str).strip()

        # Handle currency symbol prefix
        clean = re.sub(r'^[₹$\€\£\s]+', '', clean)

        # Remove commas inside numbers (e.g. 12,400 -> 12400)
        clean = re.sub(r'(?<=\d),(?=\d)', '', clean)

        # Extract leading numeric float or int
        m = re.search(r'[-+]?[0-9]*\.?[0-9]+', clean)
        if not m:
            return None

        try:
            val = float(m.group(0))
            if abs(val) > 1e12:
                return None
            return round(val, 4)
        except (ValueError, TypeError):
            return None
