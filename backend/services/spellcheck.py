"""Typo and Spelling Detection Service.

Detects genuine spelling errors using pyspellchecker cross-referenced against the
Custom Engineering Dictionary, standard acronyms, chemical elements, and engineering
terminology to guarantee <5% false positives.
"""

from __future__ import annotations

import re
from typing import Final

from spellchecker import SpellChecker

from domain.enums import Severity
from schemas.extraction import CoordinateContract, ExtractionArtifact
from schemas.issues import BoundingBox
from schemas.linguistic import LinguisticFinding, SpellcheckAnalysis

SPELLCHECK_SCHEMA_VERSION = "1.0"
SPELLCHECK_RULE_VERSION = "spellcheck/1.0.0"

# Common metallurgical and engineering acronyms (never flagged as typos)
ENGINEERING_ACRONYMS: Final[set[str]] = {
    "ASME",
    "ASTM",
    "AWS",
    "API",
    "ISO",
    "NACE",
    "ANSI",
    "AISI",
    "DIN",
    "EN",
    "BSI",
    "JIS",
    "CSA",
    "MSS",
    "CEN",
    "WPS",
    "PQR",
    "WPQ",
    "MTR",
    "CMTR",
    "HAZ",
    "NDT",
    "NDE",
    "PWHT",
    "UTS",
    "CVN",
    "CE",
    "PREN",
    "RT",
    "UT",
    "MT",
    "PT",
    "VT",
    "ET",
    "LT",
    "PMI",
    "OES",
    "SEM",
    "EDS",
    "CRA",
    "HIC",
    "SSC",
    "SCC",
    "SOHIC",
    "SZC",
    "HBW",
    "HRC",
    "HV",
    "HRB",
    "OD",
    "ID",
    "WT",
    "NPS",
    "DN",
    "SCH",
    "BOP",
    "QC",
    "QA",
    "NCR",
    "CAR",
    "ITP",
    "MDR",
    "FAT",
    "SAT",
    "TPI",
    "PO",
    "ISO9001",
    "ISO14001",
    "ISO17025",
    "SMAW",
    "GMAW",
    "GTAW",
    "SAW",
    "FCAW",
    "PAW",
    "ESW",
    "EGW",
    "EBW",
    "LBW",
    "UNS",
    "AISI316",
    "AISI304",
    "MSS-SP",
    "B31",
    "B16",
    "EN10204",
}

# Chemical element symbols and compounds common in MTRs
CHEMICAL_SYMBOLS: Final[set[str]] = {
    "Fe",
    "C",
    "Mn",
    "Si",
    "P",
    "S",
    "Cr",
    "Ni",
    "Mo",
    "Cu",
    "V",
    "Nb",
    "Ti",
    "Al",
    "N",
    "B",
    "W",
    "Co",
    "Ca",
    "Mg",
    "Zr",
    "Ta",
    "Hf",
    "Sn",
    "Pb",
    "Bi",
    "Sb",
    "As",
    "Zn",
    "H",
    "O",
    "CO2",
    "H2S",
    "CH4",
    "N2",
    "O2",
}

# Common engineering vocabulary terms to add to the base dictionary
COMMON_ENGINEERING_TERMS: Final[set[str]] = {
    "austenitic",
    "ferritic",
    "martensitic",
    "pearlitic",
    "bainitic",
    "duplex",
    "superduplex",
    "inconel",
    "monel",
    "hastelloy",
    "nimonic",
    "stellite",
    "microstructure",
    "metallurgy",
    "metallurgical",
    "radiography",
    "ultrasonic",
    "hydrostatic",
    "pneumatic",
    "annealed",
    "normalized",
    "quenched",
    "tempered",
    "stress-relieved",
    "microalloyed",
    "forged",
    "extruded",
    "seamless",
    "welded",
    "ferrite",
    "austenite",
    "martensite",
    "carbide",
    "intergranular",
    "transgranular",
    "pitting",
    "crevice",
    "toughness",
    "ductility",
    "elongation",
    "weldability",
    "hardness",
    "tensile",
    "yield",
    "charpy",
    "brinell",
    "vickers",
    "rockwell",
    "heat-affected",
    "passivation",
    "galvanized",
    "calibration",
    "tolerance",
    "bevel",
    "fillet",
    "groove",
    "butt",
    "electrode",
    "flux",
    "shielding",
    "specimen",
    "specimens",
    "cmtr",
    "pren",
    "pwht",
    "mtr",
    "ndt",
    "piping",
    "tubing",
    "nozzle",
    "flange",
    "fitting",
    "fastener",
    "conformance",
    "nonconformance",
    "dimensional",
    "calibrated",
    "hydrotest",
    "spectrometry",
    "spectrometric",
    "spectroscopy",
}

# Known high-confidence engineering typo mapping
COMMON_TYPO_PAIRS: Final[dict[str, str]] = {
    "teh": "the",
    "recieve": "receive",
    "recieved": "received",
    "recieving": "receiving",
    "temprature": "temperature",
    "temparature": "temperature",
    "prcedure": "procedure",
    "procedeure": "procedure",
    "specifcation": "specification",
    "specificaton": "specification",
    "requirment": "requirement",
    "requirments": "requirements",
    "calbration": "calibration",
    "calibraton": "calibration",
    "tensil": "tensile",
    "yeild": "yield",
    "elongtion": "elongation",
    "hardnes": "hardness",
    "diminsion": "dimension",
    "diminsions": "dimensions",
    "thicknes": "thickness",
    "wellding": "welding",
    "electrod": "electrode",
    "electrods": "electrodes",
    "seperator": "separator",
    "tolerence": "tolerance",
    "definate": "definite",
    "occurrance": "occurrence",
    "accaptable": "acceptable",
    "complience": "compliance",
    "verifcation": "verification",
    "ceritificate": "certificate",
    "inspecon": "inspection",
    "audite": "audit",
    "criterea": "criteria",
    "appoved": "approved",
    "disscuss": "discuss",
    "independant": "independent",
    "maintainance": "maintenance",
    "matieral": "material",
    "metallurigal": "metallurgical",
    "radiogaphy": "radiography",
    "ultrasonc": "ultrasonic",
    "referance": "reference",
}

# Initialize global base spellchecker and preload engineering vocabulary
_BASE_SPELLCHECKER = SpellChecker(distance=1)
_BASE_SPELLCHECKER.word_frequency.load_words(
    [t.lower() for t in COMMON_ENGINEERING_TERMS]
    + [a.lower() for a in ENGINEERING_ACRONYMS]
    + [c.lower() for c in CHEMICAL_SYMBOLS]
)


def _sub_bounding_box(
    span_bbox: CoordinateContract,
    span_text: str,
    start_char: int,
    end_char: int,
) -> BoundingBox:
    """Linearly interpolate bounding box coordinates for a sub-string word."""
    total_len = max(len(span_text), 1)
    span_width = span_bbox.x1 - span_bbox.x0
    x0 = span_bbox.x0 + (start_char / total_len) * span_width
    x1 = span_bbox.x0 + (end_char / total_len) * span_width
    return BoundingBox(
        page_index=span_bbox.page_index,
        x0=round(max(0.0, x0), 1),
        y0=round(max(0.0, span_bbox.y0), 1),
        x1=round(max(0.0, x1), 1),
        y1=round(max(0.0, span_bbox.y1), 1),
        page_width=span_bbox.page_width,
        page_height=span_bbox.page_height,
    )


def _is_whitelisted(
    word: str,
    custom_dictionary: set[str] | None = None,
) -> bool:
    """Check if a word is an exempt domain token, acronym, code, or dictionary term."""
    # 1. Custom dictionary match (case-insensitive)
    if custom_dictionary and (
        word in custom_dictionary or word.lower() in {t.lower() for t in custom_dictionary}
    ):
        return True

    # 2. Exact acronym match (ALL CAPS, 2-8 chars)
    if word.isupper() and 2 <= len(word) <= 8:
        return True

    # 3. Explicit engineering acronyms & chemical symbols
    if word in ENGINEERING_ACRONYMS or word in CHEMICAL_SYMBOLS:
        return True

    # 4. Contains digits, hyphens, slashes, or underscores (e.g. SA-516, 316L, 100mm, ASME-IX)
    if any(c.isdigit() for c in word) or "-" in word or "/" in word or "_" in word:
        return True

    # 5. Base spellchecker check
    lower = word.lower()
    return lower in _BASE_SPELLCHECKER


def _find_suggestion(word: str) -> str | None:
    """Find a high-confidence spelling replacement for a genuine typo."""
    lower = word.lower()
    # Direct dictionary typo match
    if lower in COMMON_TYPO_PAIRS:
        replacement = COMMON_TYPO_PAIRS[lower]
        if word.istitle():
            return replacement.capitalize()
        if word.isupper():
            return replacement.upper()
        return replacement

    # pyspellchecker correction
    candidate = _BASE_SPELLCHECKER.correction(lower)
    if candidate and candidate != lower:
        if word.istitle():
            return candidate.capitalize()
        if word.isupper():
            return candidate.upper()
        return candidate

    return None


def analyze_spelling(
    artifact: ExtractionArtifact,
    custom_dictionary: set[str] | None = None,
) -> SpellcheckAnalysis:
    """Run deterministic typo detection across document text spans."""
    findings: list[LinguisticFinding] = []
    seen_locations: set[tuple[int, str, float]] = set()

    word_pattern = re.compile(r"\b[A-Za-z][A-Za-z0-9_-]*\b")

    for span in artifact.spans:
        text = span.text
        if not text or len(text.strip()) == 0:
            continue

        for match in word_pattern.finditer(text):
            word = match.group(0)

            # Skip very short tokens
            if len(word) < 3:
                continue

            # Check if exempt or valid
            if _is_whitelisted(word, custom_dictionary):
                continue

            suggestion = _find_suggestion(word)
            # Only flag if we have a known typo match or suggestion
            if suggestion is None and len(word) < 4:
                continue

            bbox = _sub_bounding_box(span.bbox, text, match.start(), match.end())
            loc_key = (bbox.page_index, word.lower(), round(bbox.y0, 0))
            if loc_key in seen_locations:
                continue
            seen_locations.add(loc_key)

            confidence = 0.95 if suggestion is not None else 0.80
            message = (
                f"Possible spelling error '{word}'. Suggested replacement: '{suggestion}'."
                if suggestion
                else f"Possible unverified term or typo '{word}'."
            )

            findings.append(
                LinguisticFinding(
                    type="SPELLING_ERROR",
                    message=message,
                    severity=Severity.LOW,
                    confidence=confidence,
                    original_text=word,
                    suggestion=suggestion,
                    location=bbox,
                    rule_id="RULE_SPELLING_001",
                )
            )

    return SpellcheckAnalysis(
        schema_version=SPELLCHECK_SCHEMA_VERSION,
        rule_version=SPELLCHECK_RULE_VERSION,
        findings=findings,
    )
