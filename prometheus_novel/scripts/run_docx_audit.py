"""Audit quality of a standalone .docx manuscript.

Extracts text from the docx, runs pattern-based quality checks (AI tells,
filter words, overused phrases, preambles, grounding artifacts), and saves
a report. Works on any docx; does not require pipeline_state.json.

Usage:
    python -m prometheus_novel.scripts.run_docx_audit [path/to/manuscript.docx]
    python -m prometheus_novel.scripts.run_docx_audit  (defaults to burning-vows-30k output)
"""

import json
import re
import sys
from pathlib import Path

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT.parent))

DEFAULT_DOCX = PROJECT_ROOT / "data/projects/burning-vows-30k/output/Burning Vows Final.docx"

# Overused phrases (from phrase_replacement_banks / hot_phrases)
OVERUSED_PHRASES = [
    "against my ribs",
    "against my throat",
    "hammered against my",
    "pressed against my ribs",
]

FILTER_WORDS = [
    ("I could feel", r"\bI could feel\b"),
    ("I could see", r"\bI could see\b"),
    ("I could hear", r"\bI could hear\b"),
]

PREAMBLE_PATTERNS = [
    (r"^[A-Za-z]+\s+(?:[A-Za-z]+\s+)?found\s+(?:her|him)self\s+(?:in\s+|[\w]+ing\s+)", "X found herself/himself"),
    (r"^I\s+found\s+myself\s+(?:in\s+|[\w]+ing\s+)", "I found myself"),
]

GROUNDING_PHRASES = [
    "Glass clinked against the table.",
    "The floorboards creaked under shifting weight.",
    "Ice shifted in a glass no one was drinking.",
    "I grabbed the edge of the table.",
    "I gripped the edge of the table.",
]


def extract_text_from_docx(path: Path) -> str:
    """Extract paragraph text from a docx file."""
    try:
        from docx import Document
    except ImportError:
        print("[ERROR] python-docx required. Run: pip install python-docx")
        sys.exit(1)
    doc = Document(path)
    paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paras)


def count_words(text: str) -> int:
    """Rough word count."""
    if not text:
        return 0
    text = re.sub(r'[\*_\[\]`#]', '', text)
    return len([w for w in re.sub(r'\s+', ' ', text).strip().split() if w])


def run_ai_tells_audit(text: str, project_root: Path) -> dict:
    """Use pipeline's count_ai_tells if available."""
    try:
        from prometheus_novel.stages.pipeline import count_ai_tells
        return count_ai_tells(text)
    except Exception:
        # Fallback: simple pattern count
        patterns = [
            "i couldn't help but", "i found myself", "i noticed that",
            "i realized that", "suddenly", "in that moment", "before i knew it",
            "electricity coursed", "butterflies in my stomach", "seemed to",
            "appeared to", "managed to", "began to", "started to",
        ]
        text_lower = text.lower()
        counts = {p: text_lower.count(p) for p in patterns if text_lower.count(p) > 0}
        total = sum(counts.values())
        wc = count_words(text)
        ratio = total / (wc / 1000) if wc > 0 else 0
        return {
            "total_tells": total,
            "tells_per_1000_words": round(ratio, 2),
            "patterns_found": counts,
            "word_count": wc,
            "acceptable": ratio < 2.0,
        }


def run_quality_audit(docx_path: Path) -> dict:
    """Run all quality checks on extracted docx text."""
    text = extract_text_from_docx(docx_path)
    if not text:
        return {"error": "No text extracted", "path": str(docx_path)}

    wc = count_words(text)
    report = {
        "source": str(docx_path),
        "word_count": wc,
        "char_count": len(text),
        "issues": [],
        "details": {},
    }

    # AI tells
    ai = run_ai_tells_audit(text, PROJECT_ROOT)
    report["details"]["ai_tells"] = ai
    if not ai.get("acceptable", True):
        report["issues"].append({
            "type": "ai_tells",
            "severity": "medium",
            "message": f"AI tell ratio {ai.get('tells_per_1000_words', 0)}/1000 words (target <2)",
        })
    if ai.get("patterns_found"):
        report["details"]["ai_tells_patterns"] = ai["patterns_found"]

    # Filter words
    filter_hits = []
    for label, pat in FILTER_WORDS:
        matches = len(re.findall(pat, text, re.IGNORECASE))
        if matches:
            filter_hits.append({"phrase": label, "count": matches})
    report["details"]["filter_words"] = filter_hits
    if filter_hits:
        report["issues"].append({
            "type": "filter_words",
            "severity": "low",
            "message": "Filter hedges: " + ", ".join(f"{h['phrase']} ({h['count']})" for h in filter_hits),
        })

    # Preambles
    preamble_hits = []
    for pat, name in PREAMBLE_PATTERNS:
        for m in re.finditer(pat, text, re.IGNORECASE | re.MULTILINE):
            snippet = text[m.start() : m.end() + 60].replace("\n", " ")
            preamble_hits.append({"type": name, "snippet": snippet[:80] + "..."})
    report["details"]["preambles"] = preamble_hits
    if preamble_hits:
        report["issues"].append({
            "type": "preambles",
            "severity": "high",
            "message": f"Found {len(preamble_hits)} preamble(s): '{preamble_hits[0]['type']}'",
        })

    # Overused phrases
    phrase_hits = []
    text_lower = text.lower()
    for phrase in OVERUSED_PHRASES:
        c = text_lower.count(phrase.lower())
        if c:
            phrase_hits.append({"phrase": phrase, "count": c})
    report["details"]["overused_phrases"] = phrase_hits
    total_overused = sum(h["count"] for h in phrase_hits)
    if total_overused > 5:
        report["issues"].append({
            "type": "overused_phrases",
            "severity": "medium",
            "message": f"Physical reaction clichés: {total_overused} total ({phrase_hits})",
        })

    # Double periods
    double_periods = len(re.findall(r"\.\.", text))
    report["details"]["double_periods"] = double_periods
    if double_periods:
        report["issues"].append({
            "type": "double_periods",
            "severity": "low",
            "message": f"{double_periods} double period(s) ('..')",
        })

    # Grounding artifacts
    grounding_hits = []
    for phrase in GROUNDING_PHRASES:
        c = text.count(phrase)
        if c:
            grounding_hits.append({"phrase": phrase, "count": c})
    report["details"]["grounding_artifacts"] = grounding_hits
    if grounding_hits:
        report["issues"].append({
            "type": "grounding_artifacts",
            "severity": "low",
            "message": f"Generic grounding sentences: {grounding_hits}",
        })

    report["pass"] = len([i for i in report["issues"] if i.get("severity") == "high"]) == 0
    return report


def main():
    docx_arg = sys.argv[1] if len(sys.argv) > 1 else None
    if docx_arg:
        docx_path = Path(docx_arg)
        if not docx_path.is_absolute():
            # Resolve relative to workspace (parent of prometheus_novel)
            docx_path = (PROJECT_ROOT.parent / docx_arg).resolve()
    else:
        docx_path = DEFAULT_DOCX

    if not docx_path.exists():
        print(f"[ERROR] File not found: {docx_path}")
        return 1

    print(f"Auditing: {docx_path.name}")
    print("-" * 50)
    report = run_quality_audit(docx_path)

    if report.get("error"):
        print(f"[ERROR] {report['error']}")
        return 1

    # Summary
    print(f"Word count: {report['word_count']:,}")
    print(f"Characters: {report['char_count']:,}")
    print()

    ai = report.get("details", {}).get("ai_tells", {})
    if ai:
        print("AI Tells:")
        print(f"  Total: {ai.get('total_tells', 0)} | Per 1000 words: {ai.get('tells_per_1000_words', 0)} | OK: {ai.get('acceptable', True)}")
        for p, c in list((ai.get("patterns_found") or {}).items())[:10]:
            print(f"    - \"{p}\": {c}")
        print()

    if report.get("details", {}).get("overused_phrases"):
        print("Overused phrases (physical reaction clichés):")
        for h in report["details"]["overused_phrases"]:
            print(f"  - \"{h['phrase']}\": {h['count']}")
        print()

    if report.get("details", {}).get("filter_words"):
        print("Filter words:")
        for h in report["details"]["filter_words"]:
            print(f"  - {h['phrase']}: {h['count']}")
        print()

    if report.get("issues"):
        print("Issues:")
        for i in report["issues"]:
            print(f"  [{i.get('severity', '?')}] {i.get('message', '')}")
    else:
        print("No issues found.")

    print()
    print(f"Overall: {'PASS' if report.get('pass', True) else 'NEEDS REVIEW'}")

    # Save report
    out_dir = docx_path.parent
    out_path = out_dir / "docx_quality_audit.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nReport saved: {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
