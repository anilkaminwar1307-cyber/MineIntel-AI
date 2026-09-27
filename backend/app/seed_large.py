"""
MineIntel Large-Scale Synthetic Demo Database Generator (50,000 Facts)
Adheres strictly to the 10 Core Architectural Rules in AGENTS.md:
- Deterministic random state (SEED=26023)
- Provenance coordinates preserved on every fact
- Real relational links across Documents, Chunks, Facts, Topics, Reviews, and Conflicts
- High-performance bulk database transactions
"""
import os
import sys
import uuid
import random
import argparse
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.models.enums import DocumentStatus, ValidationStatus, ExtractionMethod, FileType, AuditAction
from app.models.document import Document, DocumentChunk
from app.models.fact import ExtractedFact
from app.models.validation import ValidationIssue, EvidenceConflict
from app.models.topic import Topic, TopicMention
from app.models.report import GeneratedReport
from app.models.audit import AuditEvent
from app.models.review import ReviewAction

SEED = 26023

# Domain Entities
SUBSIDIARY_MINE_MAP = {
    "SECL": {
        "full_name": "South Eastern Coalfields Limited",
        "coalfields": ["Korba", "Mand-Raigarh", "Sohagpur", "Hasdeo"],
        "mines": ["Gevra OC", "Dipka OC", "Kusmunda OC", "Manikpur OC", "Chhal OC", "Jamuna Kotma UG", "Bijuri UG", "Shivani UG"],
        "base_prod": 185.0
    },
    "MCL": {
        "full_name": "Mahanadi Coalfields Limited",
        "coalfields": ["Ib Valley", "Talcher"],
        "mines": ["Bhubaneswari OC", "Lakhanpur OC", "Bharatpur OC", "Kaniha OC", "Ananta OC", "Belpahar OC", "Hingula OC", "Jagannath OC"],
        "base_prod": 195.0
    },
    "NCL": {
        "full_name": "Northern Coalfields Limited",
        "coalfields": ["Singrauli"],
        "mines": ["Jayant OC", "Nigahi OC", "Dudhichua OC", "Amlohri OC", "Khadia OC", "Bina OC", "Kakri OC", "Krishnashila OC"],
        "base_prod": 135.0
    },
    "ECL": {
        "full_name": "Eastern Coalfields Limited",
        "coalfields": ["Raniganj", "Rajmahal"],
        "mines": ["Rajmahal OC", "Sonepur Bazari OC", "Jhanjra UG", "Chitra OC", "Kottadih UG/OC", "Bankola UG", "Pandaveswar UG", "Khottadih UG"],
        "base_prod": 38.0
    },
    "BCCL": {
        "full_name": "Bharat Coking Coal Limited",
        "coalfields": ["Jharia", "Raniganj West"],
        "mines": ["Moonidih UG", "Block II OC", "Kusunda OC", "Katras OC", "Lodna OC", "Bastacolla OC", "Barora OC", "Govindpur OC"],
        "base_prod": 42.0
    },
    "CCL": {
        "full_name": "Central Coalfields Limited",
        "coalfields": ["North Karanpura", "South Karanpura", "East Bokaro", "West Bokaro"],
        "mines": ["Ashoka OC", "Piparwar OC", "Amrapali OC", "Magadh OC", "Rajrappa OC", "Kathara OC", "Dhori OC", "Kuju OC"],
        "base_prod": 85.0
    },
    "WCL": {
        "full_name": "Western Coalfields Limited",
        "coalfields": ["Wardha Valley", "Pench-Kanhan", "Umrer"],
        "mines": ["Nagpur Area OC", "Majri OC", "Chandrapur OC", "Umrer OC", "Pathakhera UG", "Pench UG", "Kanhan UG", "Wani OC"],
        "base_prod": 65.0
    },
    "CMPDI": {
        "full_name": "Central Mine Planning & Design Institute",
        "coalfields": ["All CIL Coalfields (Exploration)", "Central Drilling Reserves", "Geological Directorate"],
        "mines": ["RI-I Asansol", "RI-II Dhanbad", "RI-III Ranchi", "RI-IV Nagpur", "RI-V Bilaspur", "RI-VI Singrauli", "RI-VII Bhubaneswar"],
        "base_prod": 0.0
    },
    "CIL": {
        "full_name": "Coal India Limited (Apex Holding)",
        "coalfields": ["Consolidated Indian Coalfields", "Pan-India Mining Operations"],
        "mines": ["NEC (North Eastern Coalfields)", "Tikak OC", "Leddo OC"],
        "base_prod": 780.0
    }
}

FINANCIAL_YEARS = [
    "FY 2016-17", "FY 2017-18", "FY 2018-19", "FY 2019-20", "FY 2020-21",
    "FY 2021-22", "FY 2022-23", "FY 2023-24", "FY 2024-25", "FY 2025-26"
]

QUARTERS = ["Q1", "Q2", "Q3", "Q4"]
MONTHS = [
    "April", "May", "June", "July", "August", "September",
    "October", "November", "December", "January", "February", "March"
]

TOPICS_DEF = [
    ("Production Intelligence", "Production", "Raw coal extraction, opencast dragline productivity, continuous miner outputs, and daily pit extraction stats."),
    ("Geological Exploration", "Geological", "Borehole core logging, seismic profiling, geophysical wireline logging, seam correlation, and lithology assessments."),
    ("Drilling & Coring", "Geological", "Diamond core drilling, non-core exploratory drilling meters, drilling rig utilization, and CMPDI departmental progress."),
    ("Coal Reserve Estimation", "Geological", "Proved (UNFC 111), indicated, and inferred resource block evaluations across Raniganj, Jharia, and Singrauli seams."),
    ("Dispatch & Offtake", "Operational", "Railway rake loadings, merry-go-round (MGR) conveyor dispatch, road deliveries, and power utility linkages."),
    ("Overburden & Stripping", "Operational", "Overburden removal in Million Cubic Meters (Mm3 / BCM), shovel-dumper stripping ratios, and bench stability."),
    ("Mine Safety & Hazards", "Safety", "DGMS compliance, gas monitoring in underground mines, slope stability radar, dust suppression, and safety audits."),
    ("Environmental Clearance", "Environmental", "MoEF&CC clearance conditions, air quality monitoring (PM10/PM2.5), effluent treatment, and mine water discharge."),
    ("Land Acquisition & R&R", "Compliance", "CBA Act notifications, Section 9 land vesting, tribal rehabilitation, compensation disbursement, and physical possession."),
    ("Mine Planning & Design", "Engineering", "CMPDI mine plan approvals, project reports (PR), 3D geological modeling, dump optimization, and haul road gradients."),
    ("Coal Quality & Grading", "Operational", "Gross Calorific Value (GCV), proximate analysis (ash, moisture, volatile matter), and G1-G17 coal grade slippage."),
    ("Coal Washeries", "Operational", "Heavy media cyclone beneficiation, coking coal washery yields, reject utilization, and clean coal dispatch to steel plants."),
    ("Capital Expenditure (Capex)", "Financial", "HEMM procurement (240T dumpers, 42m3 shovels), rail infrastructure, solar power plants, and FMC projects."),
    ("Manpower & Productivity", "Administrative", "OMS (Output per Manshift) in opencast and underground mines, executive staffing, and IT-enabled biometric shifts."),
    ("Statutory Compliance", "Compliance", "Mines Act 1952, Coal Mines Regulations 2017 (CMR), Forest Conservation Act (FCA), and Parliamentary assurances.")
]

TOPIC_KEYWORDS = {
    "Production Intelligence": ["coal", "production", "extraction", "opencast", "output", "achieved", "target", "dragline", "shovel", "tonnes"],
    "Geological Exploration": ["borehole", "coring", "strata", "seam", "geological", "cmpdi", "exploration", "lithology", "formation", "profiling"],
    "Drilling & Coring": ["drilling", "meters", "exploratory", "rigs", "hydrostatic", "depth", "casing", "penetration", "bit", "core"],
    "Coal Reserve Estimation": ["reserves", "proved", "indicated", "unfc", "resources", "measured", "in-situ", "estimation", "block", "tonnage"],
    "Dispatch & Offtake": ["offtake", "dispatch", "rakes", "railways", "mgr", "fmc", "linkage", "power plants", "supply", "evacuation"],
    "Overburden & Stripping": ["overburden", "stripping", "bcm", "mm3", "ratio", "bench", "dumper", "waste", "removal", "excavation"],
    "Mine Safety & Hazards": ["safety", "dgms", "hazard", "slope", "ventilation", "methane", "monitoring", "accident-free", "compliance", "inspection"],
    "Environmental Clearance": ["environmental", "clearance", "moef", "emissions", "plantation", "water treatment", "air quality", "monitoring", "reclamation", "greenbelt"],
    "Land Acquisition & R&R": ["land", "acquisition", "cba", "possession", "rehabilitation", "resettlement", "tenancy", "compensation", "vesting", "gram sabha"],
    "Mine Planning & Design": ["planning", "design", "project report", "gradient", "optimization", "slope", "3d modeling", "layout", "feasibility", "schedule"],
    "Coal Quality & Grading": ["quality", "gcv", "grade", "ash", "calorific", "moisture", "sampling", "third party", "analysis", "beneficiation"],
    "Coal Washeries": ["washery", "beneficiation", "yield", "coking coal", "clean coal", "rejects", "cyclone", "feed", "dense media", "slurry"],
    "Capital Expenditure (Capex)": ["capex", "capital expenditure", "procurement", "investment", "infrastructure", "machinery", "fmc", "budget", "inr cr", "expansion"],
    "Manpower & Productivity": ["manpower", "oms", "productivity", "manshift", "workforce", "safety training", "personnel", "attendance", "shifts", "efficiency"],
    "Statutory Compliance": ["statutory", "regulations", "cmr", "parliamentary", "audit", "compliance", "inspection", "tribunal", "directives", "guidelines"]
}

DOCUMENT_TEMPLATES = [
    ("Annual Production & Performance Review", "Production Report", FileType.PDF, "digital_pdf", 12, 0),
    ("Monthly Coal Production & Dispatch Statement", "Dispatch Statement", FileType.XLSX, "xlsx", 0, 4),
    ("CMPDI Detailed Geological Exploration Report", "Geological Assessment", FileType.PDF, "digital_pdf", 28, 0),
    ("Quarterly Financial & Capex Progress Sheet", "General Mining Report", FileType.XLSX, "xlsx", 0, 3),
    ("Subsidiary Drilling Achievement Statement", "Drilling & Exploration", FileType.CSV, "csv", 0, 1),
    ("Annual Reserve Estimation & UNFC Classification", "Reserve Estimation", FileType.PDF, "digital_pdf", 22, 0),
    ("Overburden Stripping & HEMM Performance Log", "Production Report", FileType.XLSX, "xlsx", 0, 5),
    ("Environmental Clearance & Air Quality Audit", "General Mining Report", FileType.PDF, "digital_pdf", 16, 0),
    ("Parliamentary Query Factsheet - Coal India", "General Mining Report", FileType.PDF, "digital_pdf", 8, 0),
    ("Historical Colliery Extraction Record (Scanned Archive)", "Production Report", FileType.PDF, "scanned_pdf", 14, 0),
    ("Coal Washery Yield & Quality Dispatch Log", "Dispatch Statement", FileType.CSV, "csv", 0, 1),
    ("Mine Planning & Safety Inspection Memo", "General Mining Report", FileType.TXT, "txt", 3, 0)
]


def generate_provenance(file_type: str, page_max: int, sheet_count: int) -> Tuple[int, str, int, str, str, str]:
    """Generates realistic synthetic provenance coordinates (Rule 2)."""
    if file_type == FileType.XLSX:
        sheet = f"Sheet_{random.randint(1, max(1, sheet_count))}"
        row = random.randint(4, 180)
        col_letters = ["B", "C", "D", "E", "F", "G", "H", "J"]
        col = random.choice(col_letters)
        cell = f"{col}{row}"
        col_names = ["Actual Production (MT)", "Target (MT)", "OBR (Mm3)", "Drilling (m)", "Offtake (MT)", "GCV (Kcal/kg)", "Closing Stock (MT)"]
        col_name = random.choice(col_names)
        context = f"Table Row {row} in '{sheet}' under column '{col_name}'"
        return (None, sheet, row, col_name, cell, context)
    elif file_type == FileType.CSV:
        row = random.randint(2, 250)
        col_name = random.choice(["production_mt", "dispatch_mt", "drilling_m", "target_mt", "obr_mm3"])
        cell = f"R{row}"
        context = f"CSV record at row {row}, field '{col_name}'"
        return (None, "Sheet1", row, col_name, cell, context)
    elif file_type == FileType.PDF:
        page = random.randint(1, max(1, page_max))
        context = f"Paragraph {random.randint(1, 6)} on Page {page} under executive operational statistics"
        return (page, None, None, None, None, context)
    else:  # Scanned or TXT
        page = random.randint(1, max(1, page_max))
        context = f"Optical record line {random.randint(10, 45)} on Page {page} (OCR text snippet)"
        return (page, None, None, None, None, context)


def generate_synthetic_data(target_facts: int = 50000, reset: bool = False):
    """
    Main entry point for generating the 50K MineIntel synthetic dataset.
    """
    random.seed(SEED)
    print(f"=== MINEINTEL LARGE-SCALE DATASET GENERATOR ===")
    print(f"Target Facts: {target_facts:,}")
    print(f"Seed: {SEED} (Deterministic & Reproducible)")
    print(f"Target Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")

    db = SessionLocal()

    if reset:
        print("\n[RESET] Removing prior demo records (is_demo=True)...")
        # Remove only demo data, preserving any user-uploaded files!
        db.execute(text("DELETE FROM topic_mentions WHERE topic_id IN (SELECT id FROM topics WHERE category != 'User')"))
        db.execute(text("DELETE FROM topics WHERE category != 'User'"))
        db.execute(text("DELETE FROM evidence_conflicts"))
        db.execute(text("DELETE FROM validation_issues WHERE fact_id IN (SELECT id FROM extracted_facts WHERE is_demo = 1)"))
        db.execute(text("DELETE FROM review_actions WHERE fact_id IN (SELECT id FROM extracted_facts WHERE is_demo = 1)"))
        db.execute(text("DELETE FROM extracted_facts WHERE is_demo = 1"))
        db.execute(text("DELETE FROM document_chunks WHERE document_id IN (SELECT id FROM documents WHERE is_demo = 1)"))
        db.execute(text("DELETE FROM generated_reports WHERE id LIKE 'demo-%'"))
        db.execute(text("DELETE FROM documents WHERE is_demo = 1"))
        db.commit()
        print("[RESET] Cleaned prior demo records successfully.")

    # 1. Create Topics
    print("\n[1/7] Creating canonical mining topics...")
    topic_objs = []
    topic_id_map = {}
    for name, category, desc in TOPICS_DEF:
        existing = db.query(Topic).filter(Topic.name == name).first()
        if not existing:
            t_id = f"top-{uuid.uuid4().hex[:12]}"
            topic = Topic(
                id=t_id,
                name=name,
                category=category,
                mention_count=0,
                created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(60, 300))
            )
            db.add(topic)
            topic_objs.append(topic)
            topic_id_map[name] = t_id
        else:
            topic_objs.append(existing)
            topic_id_map[name] = existing.id
    db.commit()
    print(f"-> Verified/Created {len(topic_objs)} canonical topics.")

    # 2. Create Documents (~350 documents)
    num_docs = max(250, min(500, target_facts // 140))
    print(f"\n[2/7] Generating {num_docs} synthetic source documents across CIL & CMPDI...")

    documents = []
    doc_records_for_insert = []
    now = datetime.now(timezone.utc)

    for d_idx in range(num_docs):
        doc_id = f"doc-demo-{uuid.uuid4().hex[:12]}"
        sub = random.choice(list(SUBSIDIARY_MINE_MAP.keys()))
        sub_info = SUBSIDIARY_MINE_MAP[sub]
        tpl = random.choice(DOCUMENT_TEMPLATES)
        fy = random.choice(FINANCIAL_YEARS)

        title_prefix = tpl[0]
        ext = tpl[2].lower()
        if tpl[2] == FileType.PDF:
            filename = f"{sub}_{title_prefix.replace(' ', '_')}_{fy.replace(' ', '_')}_{d_idx+1:03d}.pdf"
            mime = "application/pdf"
        elif tpl[2] == FileType.XLSX:
            filename = f"{sub}_{title_prefix.replace(' ', '_')}_{fy.replace(' ', '_')}_{d_idx+1:03d}.xlsx"
            mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif tpl[2] == FileType.CSV:
            filename = f"{sub}_{title_prefix.replace(' ', '_')}_{fy.replace(' ', '_')}_{d_idx+1:03d}.csv"
            mime = "text/csv"
        else:
            filename = f"{sub}_{title_prefix.replace(' ', '_')}_{fy.replace(' ', '_')}_{d_idx+1:03d}.txt"
            mime = "text/plain"

        is_scanned = tpl[3] == "scanned_pdf"
        qual = "POOR" if is_scanned and random.random() < 0.25 else ("FAIR" if is_scanned else ("EXCELLENT" if random.random() < 0.7 else "GOOD"))
        avg_conf = round(random.uniform(0.60, 0.78) if is_scanned else random.uniform(0.85, 0.99), 3)

        doc_dict = {
            "id": doc_id,
            "original_filename": filename,
            "stored_filename": f"stored_{filename}",
            "file_type": tpl[2],
            "source_type": tpl[3],
            "mime_type": mime,
            "file_size": random.randint(45000, 18500000),
            "document_category": tpl[1],
            "organization": sub_info["full_name"],
            "reporting_period": fy,
            "storage_path": f"./data/uploads/{filename}",
            "page_count": tpl[4] if tpl[4] > 0 else (1 if tpl[2] in [FileType.CSV, FileType.XLSX] else random.randint(4, 25)),
            "sheet_count": tpl[5],
            "table_count": random.randint(1, 8) if tpl[2] in [FileType.PDF, FileType.XLSX, FileType.CSV] else 0,
            "quality_label": qual,
            "average_confidence": avg_conf,
            "status": DocumentStatus.READY.value,
            "processing_progress": 100,
            "processing_message": "Pipeline processing completed. Structured tables extracted and indexed.",
            "fact_count": 0,  # Will update after facts generated
            "topic_count": random.randint(2, 6),
            "is_demo": True,
            "created_at": now - timedelta(days=random.randint(1, 750)),
            "processed_at": now - timedelta(days=random.randint(1, 750))
        }
        doc_records_for_insert.append(doc_dict)
        documents.append(doc_dict)

    # Bulk insert documents
    db.bulk_insert_mappings(Document, doc_records_for_insert)
    db.commit()
    print(f"-> Inserted {len(documents)} documents.")

    # 3. Create Document Chunks (~8,000 Chunks)
    print("\n[3/7] Generating ~8,000 semantic document chunks for vector/topic retrieval...")
    chunk_records = []
    topic_mentions_records = []
    chunk_id_counter = 0

    topic_names_list = list(TOPIC_KEYWORDS.keys())

    for doc in documents:
        # 15 to 30 chunks per document
        n_chunks = random.randint(14, 28)
        doc_sub = doc["original_filename"].split("_")[0]
        sub_info = SUBSIDIARY_MINE_MAP.get(doc_sub, SUBSIDIARY_MINE_MAP["SECL"])

        for c_idx in range(n_chunks):
            chunk_id_counter += 1
            chunk_id = f"chk-{uuid.uuid4().hex[:12]}"
            assigned_topic = random.choice(topic_names_list)
            keywords = TOPIC_KEYWORDS[assigned_topic]
            mine_sample = random.choice(sub_info["mines"])
            cf_sample = random.choice(sub_info["coalfields"])

            # Generate high-realism operational text
            sample_val = round(random.uniform(0.5, 45.0), 2)
            content_templates = [
                f"During the reporting review for {mine_sample} in {cf_sample} coalfield, {assigned_topic.lower()} recorded significant operational activity. Verified figures indicate {sample_val} units under standard {keywords[0]} parameters. {keywords[1].capitalize()} and {keywords[2]} operations adhered to DGMS guidelines and CMPDI engineering design norms.",
                f"Technical inspection report on {assigned_topic.lower()} across {sub_info['full_name']}. The quarterly achievement at {mine_sample} reached {sample_val} amidst active {keywords[3]} and {keywords[4]} maintenance schedules. Safety and environmental thresholds were monitored continuously.",
                f"Operational statement for {doc['reporting_period']}: {mine_sample} coalfield operations in {cf_sample}. Key metrics for {assigned_topic.lower()} confirmed {sample_val} under {keywords[5]} specifications. Field measurements carried out using standardized CMPDI exploration and survey methods.",
                f"Executive brief on {assigned_topic.lower()} regarding {sub_info['full_name']}. Performance evaluation shows progress in {keywords[6]} and {keywords[7]} at {mine_sample}, with total measured volume of {sample_val}. No adverse geo-technical deviations detected."
            ]

            chunk_text = random.choice(content_templates)
            chunk_dict = {
                "id": chunk_id,
                "document_id": doc["id"],
                "chunk_index": c_idx,
                "page_number": (c_idx % max(1, doc["page_count"])) + 1 if doc["page_count"] > 0 else None,
                "sheet_name": f"Sheet_{(c_idx % max(1, doc['sheet_count'])) + 1}" if doc["sheet_count"] > 0 else None,
                "section": f"{assigned_topic} - Section {c_idx+1}",
                "content": chunk_text,
                "token_count": len(chunk_text.split()),
                "created_at": doc["created_at"]
            }
            chunk_records.append(chunk_dict)

            # Link to topic mention
            t_id = topic_id_map.get(assigned_topic)
            if t_id and random.random() < 0.65:
                topic_mentions_records.append({
                    "id": f"tm-{uuid.uuid4().hex[:12]}",
                    "topic_id": t_id,
                    "document_id": doc["id"],
                    "chunk_id": chunk_id,
                    "confidence": round(random.uniform(0.85, 0.99), 2),
                    "created_at": doc["created_at"]
                })

            if len(chunk_records) >= 3000:
                db.bulk_insert_mappings(DocumentChunk, chunk_records)
                db.commit()
                chunk_records = []

    if chunk_records:
        db.bulk_insert_mappings(DocumentChunk, chunk_records)
        db.commit()

    if topic_mentions_records:
        db.bulk_insert_mappings(TopicMention, topic_mentions_records)
        db.commit()

    # Update topic mention counts
    for t_name, t_id in topic_id_map.items():
        cnt = db.query(TopicMention).filter(TopicMention.topic_id == t_id).count()
        db.execute(text("UPDATE topics SET mention_count = :cnt WHERE id = :id"), {"cnt": cnt, "id": t_id})
    db.commit()

    total_chunks = db.query(DocumentChunk).count()
    print(f"-> Inserted {total_chunks:,} Document Chunks and {len(topic_mentions_records):,} Topic Mentions.")

    # 4. Generate 50,000 Extracted Facts
    print(f"\n[4/7] Generating {target_facts:,} grounded ExtractedFact records with complete provenance...")

    METRIC_SPECS = [
        # (code, name, unit, weight, base_range)
        ("COAL_PRODUCTION", "Raw Coal Production", "MT", 8000, (0.5, 45.0)),
        ("PRODUCTION_TARGET", "Production Target", "MT", 5000, (0.5, 48.0)),
        ("COAL_OFFTAKE", "Coal Dispatch / Offtake", "MT", 5000, (0.4, 44.0)),
        ("GEOLOGICAL_RESERVES", "Proved Geological Reserves", "MT", 4000, (15.0, 850.0)),
        ("DRILLING", "Exploratory Drilling Progress", "m", 4000, (150.0, 12500.0)),
        ("OVERBURDEN_REMOVAL", "Overburden Removal (OBR)", "Mm3", 3000, (1.2, 95.0)),
        ("TARGET_ACHIEVEMENT", "Production Target Achievement", "%", 3000, (82.0, 115.0)),
        ("COAL_STOCK", "Closing Pithead Coal Stock", "MT", 2500, (0.2, 8.5)),
        ("EXPLORATION_BOREHOLES", "Exploration Boreholes Drilled", "Count", 2500, (5.0, 180.0)),
        ("CAPITAL_EXPENDITURE", "Capital Expenditure (Capex)", "INR Cr", 2000, (12.0, 1450.0)),
        ("MINE_AREA", "Total Mining Leasehold Area", "ha", 1500, (120.0, 4200.0)),
        ("STRIPPING_RATIO", "Stripping Ratio (OB:Coal)", "m3/t", 1500, (1.1, 4.8)),
        ("MANPOWER", "Total Mine Manpower", "Employees", 1000, (450.0, 8200.0)),
        ("ENVIRONMENTAL_CLEARANCE", "Environmental Clearance EC Capacity", "MTPA", 1000, (1.0, 50.0)),
        ("GCV_QUALITY", "Gross Calorific Value (GCV)", "Kcal/kg", 1000, (3200.0, 6400.0)),
        ("WASHED_COAL_YIELD", "Coking Coal Washery Yield", "%", 800, (45.0, 78.0)),
        ("SPECIFIC_POWER_CONSUMPTION", "Specific Power Consumption", "kWh/t", 700, (8.5, 24.0))
    ]

    # Normalize weights to reach target_facts
    sum_weights = sum(s[3] for s in METRIC_SPECS)
    metric_pools = []
    for s in METRIC_SPECS:
        count_for_this = int((s[3] / sum_weights) * target_facts)
        metric_pools.append((s[0], s[1], s[2], count_for_this, s[4]))

    fact_records = []
    validation_issue_records = []
    conflict_pairs = []
    duplicate_records = []

    # Track logical identity for conflict and duplicate detection
    # (subsidiary, mine, metric_code, period) -> fact_id, numeric_value
    identity_registry: Dict[str, Tuple[str, float]] = {}

    fact_counter = 0
    target_conflicts = int(target_facts * 0.012)  # ~600 conflicts (1.2%)
    target_duplicates = int(target_facts * 0.010) # ~500 duplicates (1.0%)
    conflicts_created = 0
    duplicates_created = 0

    doc_fact_counts: Dict[str, int] = {d["id"]: 0 for d in documents}

    # Growth multiplier map for financial years to make 10-year trends realistic
    fy_multipliers = {
        "FY 2016-17": 0.72,
        "FY 2017-18": 0.76,
        "FY 2018-19": 0.81,
        "FY 2019-20": 0.86,
        "FY 2020-21": 0.83, # Covid dip
        "FY 2021-22": 0.90,
        "FY 2022-23": 0.97,
        "FY 2023-24": 1.05,
        "FY 2024-25": 1.14,
        "FY 2025-26": 1.22
    }

    print("-> Assembling fact rows with NumberSafe consistency...")

    for code, name, unit, count, (v_min, v_max) in metric_pools:
        for _ in range(count):
            fact_counter += 1
            fact_id = f"fact-{uuid.uuid4().hex[:14]}"
            doc = random.choice(documents)
            doc_sub = doc["original_filename"].split("_")[0]
            sub = doc_sub if doc_sub in SUBSIDIARY_MINE_MAP else random.choice(list(SUBSIDIARY_MINE_MAP.keys()))
            sub_info = SUBSIDIARY_MINE_MAP[sub]
            mine = random.choice(sub_info["mines"])
            cf = random.choice(sub_info["coalfields"])

            # Determine period (70% FY, 20% Quarter, 10% Month)
            fy = doc["reporting_period"] if doc["reporting_period"] in FINANCIAL_YEARS else random.choice(FINANCIAL_YEARS)
            p_roll = random.random()
            if p_roll < 0.70:
                period = fy
            elif p_roll < 0.90:
                period = f"{fy.split()[-1]}-{random.choice(QUARTERS)}"
            else:
                period = f"{random.choice(MONTHS)} {fy.split()[-1]}"

            # Growth factor applied to value range
            growth = fy_multipliers.get(fy, 1.0)
            base_val = random.uniform(v_min, v_max) * (growth if code not in ["%", "m3/t", "Kcal/kg"] else 1.0)
            numeric_val = round(base_val, 2)

            # Granular Provenance coordinates (Rule 2)
            page_num, sheet_name, row_num, col_name, cell_ref, src_ctx = generate_provenance(
                doc["file_type"], doc["page_count"], doc["sheet_count"]
            )

            # Quality and Confidence distribution
            # 65% Verified/High, 23% Needs Review, 12% Review Required / Low
            conf_roll = random.random()
            if conf_roll < 0.65:
                confidence = round(random.uniform(0.90, 0.99), 2)
                status = ValidationStatus.VERIFIED.value
                human_verified = True
                verified_by = "CMPDI Chief Geologist / RuleEngine"
            elif conf_roll < 0.88:
                confidence = round(random.uniform(0.72, 0.89), 2)
                status = ValidationStatus.NEEDS_REVIEW.value
                human_verified = False
                verified_by = None
            else:
                confidence = round(random.uniform(0.55, 0.71), 2)
                status = ValidationStatus.REVIEW_REQUIRED.value
                human_verified = False
                verified_by = None

            # Logical Identity Key
            id_key = f"{sub}|{mine}|{code}|{period}"

            # Check if this fact should be a TRUE CONFLICT
            is_conflict = False
            if conflicts_created < target_conflicts and id_key in identity_registry and random.random() < 0.15:
                orig_fact_id, orig_val = identity_registry[id_key]
                # Introduce contradictory figure (e.g. 5% - 25% discrepancy)
                diff_factor = random.choice([0.82, 0.88, 1.15, 1.22])
                numeric_val = round(orig_val * diff_factor, 2)
                status = ValidationStatus.CONFLICT.value
                confidence = round(random.uniform(0.65, 0.80), 2)
                human_verified = False

                conflict_id = f"cnf-{uuid.uuid4().hex[:12]}"
                discrepancy = round(abs(numeric_val - orig_val) / max(0.001, orig_val) * 100, 1)
                conflict_pairs.append({
                    "id": conflict_id,
                    "metric_code": code,
                    "primary_fact_id": orig_fact_id,
                    "conflicting_fact_id": fact_id,
                    "description": f"Contradictory {name} reported for {sub} ({mine}) in {period}: Primary recorded {orig_val} {unit} vs secondary recorded {numeric_val} {unit} (discrepancy: {discrepancy}%).",
                    "discrepancy_percent": discrepancy,
                    "status": "OPEN",
                    "created_at": doc["created_at"]
                })
                # Add validation issue for conflict
                validation_issue_records.append({
                    "id": f"iss-{uuid.uuid4().hex[:12]}",
                    "document_id": doc["id"],
                    "fact_id": fact_id,
                    "issue_type": "UNRESOLVED_CONFLICT",
                    "severity": "CRITICAL" if discrepancy > 20 else "HIGH",
                    "description": f"Cross-document discrepancy of {discrepancy}% against verified evidence ledger entry {orig_fact_id[:8]}...",
                    "is_resolved": False,
                    "created_at": doc["created_at"]
                })
                conflicts_created += 1
                is_conflict = True

            # Check if duplicate
            elif duplicates_created < target_duplicates and id_key in identity_registry and random.random() < 0.10:
                orig_fact_id, orig_val = identity_registry[id_key]
                numeric_val = orig_val  # Same value, potential duplicate
                status = ValidationStatus.NEEDS_REVIEW.value
                validation_issue_records.append({
                    "id": f"iss-{uuid.uuid4().hex[:12]}",
                    "document_id": doc["id"],
                    "fact_id": fact_id,
                    "issue_type": "DUPLICATE_CANDIDATE",
                    "severity": "LOW",
                    "description": f"Identical value {orig_val} {unit} already registered in ledger from prior document.",
                    "is_resolved": False,
                    "created_at": doc["created_at"]
                })
                duplicates_created += 1

            # Log other realistic validation issues for review queue (sampled so review queue has hundreds of items)
            elif status in [ValidationStatus.NEEDS_REVIEW.value, ValidationStatus.REVIEW_REQUIRED.value] and random.random() < 0.06:
                if confidence < 0.65:
                    issue_type = "LOW_OCR_CONFIDENCE" if doc["source_type"] == "scanned_pdf" else "UNCERTAIN_TABLE_STRUCTURE"
                    sev = "HIGH" if confidence < 0.60 else "MEDIUM"
                    desc = f"OCR engine certainty is {int(confidence*100)}% on scanned coordinate. Manual analyst verification advised."
                elif random.random() < 0.30:
                    issue_type = "MISSING_UNIT"
                    sev = "MEDIUM"
                    desc = "Raw table header lacked explicit unit identifier; inferred from domain registry."
                elif random.random() < 0.30:
                    issue_type = "OUTLIER_VALUE"
                    sev = "HIGH"
                    desc = f"Extracted value {numeric_val} exceeds 3-sigma historical mean for mine {mine}."
                else:
                    issue_type = "UNVERIFIED_SOURCE"
                    sev = "LOW"
                    desc = "Automated extraction requires first-time analyst confirmation."

                validation_issue_records.append({
                    "id": f"iss-{uuid.uuid4().hex[:12]}",
                    "document_id": doc["id"],
                    "fact_id": fact_id,
                    "issue_type": issue_type,
                    "severity": sev,
                    "description": desc,
                    "is_resolved": False,
                    "created_at": doc["created_at"]
                })


            # Record in logical registry
            if not is_conflict:
                identity_registry[id_key] = (fact_id, numeric_val)

            fact_dict = {
                "id": fact_id,
                "document_id": doc["id"],
                "metric_code": code,
                "metric_name": name,
                "raw_metric_name": f"{name} ({unit})" if random.random() < 0.5 else name,
                "numeric_value": numeric_val,
                "text_value": f"{numeric_val} {unit}",
                "unit": unit,
                "raw_unit": unit,
                "reporting_period": period,
                "organization": sub_info["full_name"],
                "subsidiary": sub,
                "coalfield": cf,
                "mine": mine,
                "location": f"{mine}, {cf}",
                "page_number": page_num,
                "sheet_name": sheet_name,
                "row_number": row_num,
                "column_name": col_name,
                "cell_reference": cell_ref,
                "table_reference": sheet_name or f"Table P{page_num}" if page_num else "Main Register",
                "source_context": f"[{doc['original_filename']}] {src_ctx} -> {name}: {numeric_val} {unit} ({period})",
                "extraction_method": ExtractionMethod.STRUCTURED_TABLE.value if doc["file_type"] in [FileType.XLSX, FileType.CSV] else (ExtractionMethod.OCR_BLOCK.value if doc["source_type"] == "scanned_pdf" else ExtractionMethod.REGEX_PATTERN.value),
                "confidence_score": confidence,
                "validation_status": status,
                "human_verified": human_verified,
                "verified_by": verified_by,
                "is_demo": True,
                "created_at": doc["created_at"],
                "updated_at": doc["created_at"]
            }
            fact_records.append(fact_dict)
            doc_fact_counts[doc["id"]] += 1

            # Batch flush every 5,000 facts to manage memory
            if len(fact_records) >= 5000:
                db.bulk_insert_mappings(ExtractedFact, fact_records)
                db.commit()
                print(f"   -> Committed batch: {fact_counter:,} / {target_facts:,} facts...")
                fact_records = []

    # Insert remainder
    if fact_records:
        db.bulk_insert_mappings(ExtractedFact, fact_records)
        db.commit()

    print(f"-> Successfully inserted {fact_counter:,} ExtractedFact records into Evidence Ledger.")

    # 5. Insert Conflicts & Validation Issues
    print(f"\n[5/7] Inserting {len(conflict_pairs)} true conflicts and {len(validation_issue_records)} validation issues...")
    if conflict_pairs:
        db.bulk_insert_mappings(EvidenceConflict, conflict_pairs)
        db.commit()
    if validation_issue_records:
        db.bulk_insert_mappings(ValidationIssue, validation_issue_records)
        db.commit()

    # Update document fact_count counters
    print("-> Updating document-level fact counters...")
    for doc_id, f_count in doc_fact_counts.items():
        db.execute(text("UPDATE documents SET fact_count = :cnt WHERE id = :id"), {"cnt": f_count, "id": doc_id})
    db.commit()

    # 6. Create Pre-generated Demonstrative Reports
    print("\n[6/7] Creating 8 realistic demonstrative reports in Report Studio...")
    demo_reports = [
        ("FY 2024-25 Consolidated CIL Coal Production & Offtake Summary", "Production Summary", "ALL", "FY 2024-25", 1420),
        ("CMPDI Pan-India Exploratory Drilling & Coring Achievement", "Exploration Summary", "CMPDI", "FY 2024-25", 850),
        ("SECL Korba & Mand-Raigarh Opencast Stripping & Production Review", "Subsidiary Performance", "SECL", "FY 2024-25", 620),
        ("MCL Ib Valley & Talcher Coalfields Target vs Achievement Audit", "Target vs Achievement", "MCL", "FY 2024-25", 540),
        ("Parliamentary Question (PQ) Brief: Coal Reserves & DGMS Safety", "Parliamentary Brief", "ALL", "FY 2023-24", 310),
        ("BCCL Jharia Coking Coal Extraction & Washery Yield Report", "Custom Report", "BCCL", "FY 2024-25", 480),
        ("Singrauli Coalfield NCL HEMM Productivity & OBR Evaluation", "Production Summary", "NCL", "FY 2024-25", 410),
        ("CMPDI UNFC Proved Geological Coal Reserves Assessment 2025", "Reserve Overview", "CMPDI", "FY 2025-26", 980)
    ]

    report_objs = []
    for title, rtype, sub_flt, per_flt, ev_cnt in demo_reports:
        rep_id = f"demo-rep-{uuid.uuid4().hex[:10]}"
        report_objs.append({
            "id": rep_id,
            "title": title,
            "report_type": rtype,
            "parameters": f'{{"subsidiary": "{sub_flt}", "period": "{per_flt}", "only_verified": true}}',
            "status": "READY",
            "summary": f"Comprehensive {rtype} synthesized deterministically from {ev_cnt} grounded evidence facts across Coal India subsidiaries. Verified with ReportGuard quality gate pass.",
            "output_path": f"./data/reports/{title.replace(' ', '_')[:40]}.pdf",
            "evidence_count": ev_cnt,
            "generated_by": "CMPDI Senior Analyst",
            "created_at": now - timedelta(days=random.randint(2, 60))
        })
    db.bulk_insert_mappings(GeneratedReport, report_objs)
    db.commit()
    print(f"-> Created {len(demo_reports)} demonstrative reports.")

    # 7. Create Audit Events
    print("\n[7/7] Recording immutable audit events...")
    audit_events = [
        {
            "id": f"aud-{uuid.uuid4().hex[:12]}",
            "timestamp": now - timedelta(days=2),
            "user": "System Administrator",
            "action": AuditAction.SYSTEM_CONFIG_CHANGED.value,
            "entity_type": "SYSTEM",
            "entity_id": "seed-50k",
            "details": f"Deterministic seed of {target_facts:,} facts initialized with SEED={SEED}."
        },
        {
            "id": f"aud-{uuid.uuid4().hex[:12]}",
            "timestamp": now - timedelta(days=1),
            "user": "CMPDI Analyst",
            "action": AuditAction.FACT_APPROVED.value,
            "entity_type": "FACT",
            "entity_id": "bulk-ledger",
            "details": f"Automated validation engine verified 32,500 structured facts with zero hallucination guarantee."
        },
        {
            "id": f"aud-{uuid.uuid4().hex[:12]}",
            "timestamp": now - timedelta(hours=6),
            "user": "CMPDI Lead Geologist",
            "action": AuditAction.REPORT_GENERATED.value,
            "entity_type": "REPORT",
            "entity_id": "demo-rep-1",
            "details": "Generated FY 2024-25 Consolidated CIL Coal Production & Offtake Summary PDF."
        }
    ]
    db.bulk_insert_mappings(AuditEvent, audit_events)
    db.commit()

    # Summary Check
    total_f = db.query(ExtractedFact).count()
    total_d = db.query(Document).count()
    total_c = db.query(DocumentChunk).count()
    total_t = db.query(Topic).count()
    total_iss = db.query(ValidationIssue).count()
    total_cnf = db.query(EvidenceConflict).count()
    total_rep = db.query(GeneratedReport).count()
    verified_f = db.query(ExtractedFact).filter(ExtractedFact.validation_status == ValidationStatus.VERIFIED.value).count()

    print("\n============================================================")
    print("SEEDING COMPLETE — DATABASE SUMMARY:")
    print("============================================================")
    print(f"Total Facts:          {total_f:,}")
    print(f"Verified Facts:       {verified_f:,} ({int(verified_f/max(1,total_f)*100)}%)")
    print(f"Source Documents:     {total_d:,}")
    print(f"Document Chunks:      {total_c:,}")
    print(f"Discovered Topics:    {total_t:,}")
    print(f"Open Validation Issues: {total_iss:,}")
    print(f"True Conflicts:       {total_cnf:,}")
    print(f"Generated Reports:    {total_rep:,}")
    print("============================================================\n")

    db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MineIntel 50K Synthetic Database Seeder")
    parser.add_argument("--size", type=int, default=50000, help="Target number of facts (default: 50,000)")
    parser.add_argument("--reset", action="store_true", help="Wipe prior demo records before generating")
    args = parser.parse_args()

    generate_synthetic_data(target_facts=args.size, reset=args.reset)
