"""BookOps Engine — generates launch/marketing assets and revision guidance.

Works in two modes:
  CONFIG-ONLY: produces docs 01-04 from config.yaml alone
  FULL: additionally produces docs 05-07 using scene data from pipeline_state.json
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from prometheus_novel.prometheus_lib.llm.clients import get_client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config field tiers
# ---------------------------------------------------------------------------

BOOKOPS_CRITICAL_FIELDS = ["title", "genre", "synopsis", "protagonist"]

BOOKOPS_RECOMMENDED_FIELDS = [
    "themes", "tone", "writing_style", "setting", "influences", "avoid",
    "central_conflict", "key_plot_points", "motifs", "antagonist",
    "strategic_guidance", "central_question", "subplots", "other_characters",
]

FIELD_QUESTIONS = {
    "title": "What is your book's title?",
    "genre": "What genre does this book belong to? (romance, thriller, sci-fi, literary, nonfiction, etc.)",
    "synopsis": "Write a 2-4 sentence synopsis of the story (or book's purpose for nonfiction).",
    "protagonist": "Describe your protagonist in 2-3 sentences (name, age, key traits, wound/desire).",
    "themes": "What are the 2-4 central themes?",
    "tone": "Describe the book's tone (e.g., 'Dark and atmospheric' or 'Light and witty').",
    "writing_style": "What POV and narrative style? (e.g., 'First person, past tense, lyrical')",
    "central_conflict": "What is the core conflict or central question driving the story?",
    "key_plot_points": "List the 5-8 major plot beats or chapter milestones.",
    "setting": "Where and when does the story take place?",
    "influences": "What books/authors is this comparable to?",
    "avoid": "What cliches, tropes, or patterns should be avoided?",
    "motifs": "What recurring images or symbols thread through the story?",
    "antagonist": "Who or what opposes the protagonist (can be internal)?",
    "strategic_guidance": "Any market positioning, target audience, or pacing notes?",
    "central_question": "What thematic question does the book explore?",
    "subplots": "What secondary storylines run alongside the main plot?",
    "other_characters": "Describe 2-3 key supporting characters.",
}


# ---------------------------------------------------------------------------
# BookOps Engine
# ---------------------------------------------------------------------------

@dataclass
class BookOpsEngine:
    """Generates launch/marketing assets and revision guidance for any book."""

    project_path: Path
    config: Dict[str, Any]
    scenes: Optional[List[Dict]] = None
    client: Any = None  # BaseLLMClient
    output_dir: Path = None

    _missing_fields: List[str] = field(default_factory=list)
    _generated_docs: List[str] = field(default_factory=list)
    _errors: List[str] = field(default_factory=list)

    @classmethod
    def from_config_path(cls, config_path: Path, model_override: str = None) -> "BookOpsEngine":
        """Factory: load config, optionally load scenes, init LLM client."""
        config_path = Path(config_path)
        project_path = config_path.parent

        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        # Try to load scenes from pipeline_state.json
        scenes = None
        state_file = project_path / "pipeline_state.json"
        if state_file.exists():
            try:
                with open(state_file, encoding="utf-8") as f:
                    state_data = json.load(f)
                raw_scenes = state_data.get("scenes", [])
                if raw_scenes and isinstance(raw_scenes, list):
                    scenes = [s for s in raw_scenes if isinstance(s, dict) and s.get("content")]
                    if not scenes:
                        scenes = None
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Could not load pipeline_state.json: {e}")

        # Determine LLM model
        if model_override:
            model_name = model_override
        else:
            defaults = config.get("model_defaults", {})
            model_name = defaults.get("api_model", defaults.get("local_model", "qwen2.5:7b"))

        llm_client = get_client(model_name)
        output_dir = project_path / "bookops"

        engine = cls(
            project_path=project_path,
            config=config,
            scenes=scenes,
            client=llm_client,
            output_dir=output_dir,
        )

        # Audit config for missing fields
        for f_name in BOOKOPS_CRITICAL_FIELDS:
            val = config.get(f_name)
            if not val or (isinstance(val, str) and val.strip().upper() == "TODO"):
                engine._missing_fields.append(f_name)

        mode = "FULL" if scenes else "CONFIG-ONLY"
        scene_count = len(scenes) if scenes else 0
        logger.info(f"BookOps initialized: mode={mode}, scenes={scene_count}, "
                     f"model={model_name}, missing={engine._missing_fields}")

        return engine

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _config_block(self) -> str:
        """Serialize config fields into a text block for prompts."""
        lines = []
        all_fields = BOOKOPS_CRITICAL_FIELDS + BOOKOPS_RECOMMENDED_FIELDS
        for f_name in all_fields:
            value = self.config.get(f_name)
            if f_name in BOOKOPS_CRITICAL_FIELDS and not value:
                lines.append(f"{f_name}: [TODO: not provided]")
            elif value:
                str_val = str(value).strip()
                if len(str_val) > 600:
                    str_val = str_val[:600] + "..."
                lines.append(f"{f_name}: {str_val}")
        return "\n".join(lines)

    def _scenes_text(self, max_scenes: int = None) -> str:
        """Concatenate scene content. Optionally limit to first N scenes."""
        if not self.scenes:
            return ""
        scenes = self.scenes[:max_scenes] if max_scenes else self.scenes
        parts = []
        for s in scenes:
            header = f"Chapter {s.get('chapter', '?')}, Scene {s.get('scene_number', '?')}"
            parts.append(f"--- {header} ---\n{s.get('content', '')}")
        return "\n\n".join(parts)

    def _scene_summary(self) -> str:
        """Build chapter/scene/location/word-count table (no prose)."""
        if not self.scenes:
            return ""
        lines = ["| Chapter | Scene | Location | Words | Purpose |",
                  "|---------|-------|----------|-------|---------|"]
        for s in self.scenes:
            ch = s.get("chapter", "?")
            sc = s.get("scene_number", "?")
            loc = s.get("location", "—")
            content = s.get("content", "")
            wc = len(content.split())
            purpose = s.get("purpose", "—")
            if len(purpose) > 60:
                purpose = purpose[:57] + "..."
            lines.append(f"| {ch} | {sc} | {loc} | {wc} | {purpose} |")
        return "\n".join(lines)

    def _sample_scenes(self, count: int = 3) -> str:
        """Pick representative scenes: first, middle, last."""
        if not self.scenes:
            return ""
        if len(self.scenes) <= count:
            return self._scenes_text()
        indices = [0, len(self.scenes) // 2, len(self.scenes) - 1]
        parts = []
        for i in indices[:count]:
            s = self.scenes[i]
            header = f"Chapter {s.get('chapter', '?')}, Scene {s.get('scene_number', '?')}"
            parts.append(f"--- {header} ---\n{s.get('content', '')}")
        return "\n\n".join(parts)

    def _write_doc(self, filename: str, content: str):
        """Write markdown doc to output dir."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        filepath = self.output_dir / filename
        filepath.write_text(content, encoding="utf-8")
        logger.info(f"  Written: {filepath}")

    async def _generate(self, system_prompt: str, user_prompt: str,
                        max_tokens: int = 2048, temperature: float = 0.4) -> str:
        """Call LLM and return content."""
        response = await self.client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.content

    # ------------------------------------------------------------------
    # Document generators
    # ------------------------------------------------------------------

    async def _generate_positioning(self):
        """01_positioning.md — hook, blurb, taglines, tropes, keywords, promise."""
        genre = self.config.get("genre", "fiction")
        tropes = self.config.get("strategic_guidance", {}).get("tropes", "")
        market = self.config.get("strategic_guidance", {}).get("market_positioning", "")

        content = await self._generate(
            system_prompt="You are a book marketing strategist. Generate positioning assets. "
                          "Be specific, avoid cliches, and match the genre conventions.",
            user_prompt=f"""Given this novel:
{self._config_block()}

{f"TROPES: {tropes}" if tropes else ""}
{f"MARKET POSITIONING: {market}" if market else ""}

Generate the following in clean Markdown format:

## Hook
One sentence, under 20 words. High clarity, no cliches.

## Blurb
150-200 word back-cover blurb. Match the tone of {genre} bestsellers.
End with a question or stakes statement that compels purchase.

## Taglines
5 options. Varied tone (witty, dramatic, mysterious, emotional, punchy).

## Tropes & Tags
8-12 reader-recognizable tropes/tags for discoverability.
Format as a bullet list.

## Keywords
10 Amazon/KDP search keyword phrases (2-4 words each).
Think like a reader searching, not like a marketer.

## Promise Statement
One paragraph: what emotional experience does this book guarantee?
What will the reader FEEL by the final page?""",
            max_tokens=2048,
            temperature=0.5,
        )
        self._write_doc("01_positioning.md", content)

    async def _generate_reader_problem_map(self):
        """02_reader_problem_map.md — 8 reader problems this book solves."""
        genre = self.config.get("genre", "fiction")

        content = await self._generate(
            system_prompt="You are a reader psychology expert specializing in book purchasing behavior.",
            user_prompt=f"""Given this novel:
{self._config_block()}

Identify exactly 8 reader "problems" (emotional needs, curiosities, desires)
that {genre} readers have which this specific book addresses.

For each problem, output a row in this Markdown table:

## Reader Problem Map

| # | Reader Need | How This Book Delivers | Marketing Hook |
|---|-------------|----------------------|----------------|
| 1 | ... | Which scenes/elements address this | One-line selling angle |

Examples of reader needs: justice fantasy, escapism, competence fantasy,
emotional catharsis, vicarious thrill, intellectual stimulation, comfort,
validation, wish fulfillment, self-discovery mirror.

Be specific to THIS book. Don't use generic filler.""",
            max_tokens=2048,
            temperature=0.4,
        )
        self._write_doc("02_reader_problem_map.md", content)

    async def _generate_first_10_checklist(self):
        """03_first_10_pages_checklist.md — conversion checklist for the opening."""
        genre = self.config.get("genre", "fiction")

        content = await self._generate(
            system_prompt="You are an acquisitions editor who has read 10,000 first chapters. "
                          "You know exactly what makes a reader buy vs. put the book back.",
            user_prompt=f"""Given this novel:
{self._config_block()}

Create a "First 10 Pages Checklist" for this specific {genre} novel.
What must the opening pages accomplish to convert a browsing reader into a buyer?

Format as checkboxes so the author can track completion:

## First 10 Pages Checklist

- [ ] **Item title** — Why it matters for this specific book. What "done" looks like.

Include 12-15 items covering:
- Voice establishment (does the narrator sound distinctive by page 2?)
- Protagonist intro (name, want, wound — within first 3 pages)
- Genre promise (what signals tell the reader this is {genre}?)
- Question raised (what makes them turn to page 11?)
- Momentum (does every paragraph earn its spot?)
- "Why now" urgency (why does this story start TODAY?)
- Sensory grounding (can the reader see/smell/hear the world?)
- Tone contract (does the opening match what the rest delivers?)
- Unique hook (what makes this different from other {genre} books?)

Be specific to THIS book, not generic writing advice.""",
            max_tokens=2048,
            temperature=0.3,
        )
        self._write_doc("03_first_10_pages_checklist.md", content)

    async def _generate_scene_revision_plan(self):
        """04_scene_revision_plan.md — 12 concrete revision actions."""
        avoid = self.config.get("avoid", "")

        content = await self._generate(
            system_prompt="You are a developmental editor. Every suggestion must be concrete, "
                          "testable, and tied to reader experience — not abstract writing advice.",
            user_prompt=f"""Given this novel's plan:
{self._config_block()}

Generate 12 concrete revision actions for the manuscript. For each:

## Action N: [Specific Title]
- **ADD**: What specific content to add (scene, beat, detail — not vague)
- **CUT**: What to remove or reduce (and why it's dead weight)
- **WHY**: The reader-experience reason (what changes for the reader)
- **VERIFY**: How to confirm the fix worked (a specific test or metric)

Focus areas:
- Emotional escalation (does tension ratchet up, not plateau?)
- Pacing (any sagging middle? too-fast resolution?)
- Character consistency (do actions match established personality?)
- Theme reinforcement (are themes felt, not just stated?)
- Genre expectations (does it deliver what {self.config.get('genre', 'fiction')} readers want?)
{f"- AVOID list: {avoid}" if avoid else ""}

Each action must be specific enough that the author can do it in one sitting.""",
            max_tokens=4096,
            temperature=0.4,
        )
        self._write_doc("04_scene_revision_plan.md", content)

    async def _generate_opening_diagnostic(self):
        """05_opening_diagnostic.md — rate and diagnose the first 10 pages."""
        first_scenes = self._scenes_text(max_scenes=2)

        content = await self._generate(
            system_prompt="You are a line editor specializing in novel openings. "
                          "Be specific. Quote exact lines. Don't soften criticism.",
            user_prompt=f"""Novel config:
{self._config_block()}

Here are the opening scenes (first ~10 pages):
---
{first_scenes}
---

Rate the opening on each dimension (1-10 scale):

## Opening Diagnostic

| Dimension | Score | Evidence (quote a specific line) |
|-----------|-------|----------------------------------|
| Clarity of premise | | |
| Voice distinctiveness | | |
| Momentum / pacing | | |
| Genre promise delivered | | |
| Character hook | | |
| Sensory grounding | | |
| Stakes / urgency | | |
| Tone consistency | | |

## 10 Line-Level Improvements

For each:
- **Original**: "exact quote from the text"
- **Revised**: "your improved version"
- **Why**: what this fixes

Target the biggest impact improvements first. Don't rewrite everything —
show the author the pattern so they can apply it throughout.""",
            max_tokens=4096,
            temperature=0.3,
        )
        self._write_doc("05_opening_diagnostic.md", content)

    async def _generate_structural_edit_plan(self):
        """06_structural_edit_plan.md — 10-15 structural edits."""
        summary = self._scene_summary()

        content = await self._generate(
            system_prompt="You are a structural editor analyzing a novel's architecture. "
                          "Focus on pacing, sequencing, and scene purpose — not prose quality.",
            user_prompt=f"""Novel config:
{self._config_block()}

Manuscript structure:
{summary}

Provide 10-15 structural edits. For each:

## Edit N: [Specific Title]
- **CHANGE**: What to restructure, move, combine, split, or cut
- **REASON**: Why this improves the reading experience
- **IMPACT**: Which specific chapters/scenes are affected
- **RISK**: What could go wrong (so the author can watch for it)

Focus on:
- Scene redundancy (two scenes doing the same job)
- Pacing valleys (where momentum dies)
- Reveal timing (is information delivered at maximum impact?)
- Subplot integration (do secondary threads serve the main arc?)
- Act structure (does the story escalate properly through acts?)""",
            max_tokens=4096,
            temperature=0.3,
        )
        self._write_doc("06_structural_edit_plan.md", content)

    async def _generate_prose_rules(self):
        """07_prose_rules_for_this_book.md — compact style constitution."""
        samples = self._sample_scenes(count=3)

        content = await self._generate(
            system_prompt="You are a style guide author. Create a compact, enforceable prose "
                          "constitution — not aspirational advice, but concrete rules.",
            user_prompt=f"""Novel config:
{self._config_block()}

Sample prose from the manuscript (3 representative scenes):
---
{samples}
---

Create a "Prose Rules for This Book" document. Each section: 3-5 bullet points.
Total document under 800 words.

## 1. Voice Signature
What makes this narrator's voice recognizable? (sentence patterns, attitude, vocabulary)

## 2. Sentence Rhythm Rules
Preferred patterns, lengths, cadence. What to never do (e.g., 3 long sentences in a row).

## 3. Sensory Hierarchy
Which senses dominate? In what order? What sensory details are off-limits for this voice?

## 4. Dialogue Rules
How characters speak. Formatting conventions. Tag rules.

## 5. Forbidden Patterns
From the "avoid" list + any AI tells or cliches detected in the sample prose.

## 6. Motif Vocabulary
Recurring images/words and what they mean. When to deploy them.

## 7. Emotional Range
How this narrator expresses vs. suppresses feeling. What emotions are shown directly
vs. through action/physical sensation.""",
            max_tokens=2048,
            temperature=0.4,
        )
        self._write_doc("07_prose_rules_for_this_book.md", content)

    async def _generate_questions_for_author(self):
        """08 — Only generated if critical config fields are missing."""
        critical_missing = [f for f in self._missing_fields if f in BOOKOPS_CRITICAL_FIELDS]
        if not critical_missing:
            return

        lines = ["# Questions for Author\n"]
        lines.append("The following fields are missing or empty in your `config.yaml`.")
        lines.append("BookOps documents marked with `[TODO]` need these filled in.\n")

        for f_name in critical_missing:
            question = FIELD_QUESTIONS.get(f_name, f"Please provide: {f_name}")
            lines.append(f"## `{f_name}`\n{question}\n")

        recommended_missing = [f for f in BOOKOPS_RECOMMENDED_FIELDS
                               if not self.config.get(f)]
        if recommended_missing:
            lines.append("\n---\n\n## Recommended (improves output quality)\n")
            for f_name in recommended_missing:
                question = FIELD_QUESTIONS.get(f_name, f"Please provide: {f_name}")
                lines.append(f"- **{f_name}**: {question}")

        self._write_doc("questions_for_author.md", "\n".join(lines))
        self._generated_docs.append("questions_for_author.md")

    # ------------------------------------------------------------------
    # Self-check guardrail
    # ------------------------------------------------------------------

    async def _self_check(self) -> Dict[str, Any]:
        """Post-generation guardrail. Validates all docs for completeness and consistency."""
        issues = []

        expected = ["01_positioning.md", "02_reader_problem_map.md",
                    "03_first_10_pages_checklist.md", "04_scene_revision_plan.md"]
        if self.scenes:
            expected += ["05_opening_diagnostic.md", "06_structural_edit_plan.md",
                         "07_prose_rules_for_this_book.md"]

        title = self.config.get("title", "")
        genre = self.config.get("genre", "")

        for doc_name in expected:
            doc_path = self.output_dir / doc_name
            if not doc_path.exists():
                issues.append(f"MISSING: {doc_name} was not generated")
                continue

            content = doc_path.read_text(encoding="utf-8")
            word_count = len(content.split())

            if word_count < 100:
                issues.append(f"STUB: {doc_name} has only {word_count} words")

            if title and title.lower() not in content.lower():
                issues.append(f"DRIFT: {doc_name} doesn't reference the book title '{title}'")

            if "[TODO" in content:
                todo_count = content.count("[TODO")
                issues.append(f"INCOMPLETE: {doc_name} has {todo_count} TODO placeholder(s)")

        # Write report
        lines = ["# BookOps Self-Check Report\n"]
        if not issues:
            lines.append("All checks passed. All documents are complete and consistent.\n")
        else:
            lines.append(f"Found {len(issues)} issue(s):\n")
            for issue in issues:
                lines.append(f"- {issue}")

        self._write_doc("_self_check_report.md", "\n".join(lines))
        return {"passed": len(issues) == 0, "issues": issues}

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------

    async def generate_all(self, doc_filter: Optional[List[str]] = None,
                           force: bool = False) -> Dict[str, Any]:
        """Generate all BookOps documents.

        Args:
            doc_filter: Only generate docs whose number matches (e.g., ["01", "05"]).
            force: Overwrite existing docs.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)

        doc_plan = [
            ("01", "01_positioning.md", self._generate_positioning, False),
            ("02", "02_reader_problem_map.md", self._generate_reader_problem_map, False),
            ("03", "03_first_10_pages_checklist.md", self._generate_first_10_checklist, False),
            ("04", "04_scene_revision_plan.md", self._generate_scene_revision_plan, False),
            ("05", "05_opening_diagnostic.md", self._generate_opening_diagnostic, True),
            ("06", "06_structural_edit_plan.md", self._generate_structural_edit_plan, True),
            ("07", "07_prose_rules_for_this_book.md", self._generate_prose_rules, True),
        ]

        for doc_num, filename, generator, needs_scenes in doc_plan:
            if doc_filter and doc_num not in doc_filter:
                continue

            if not force and (self.output_dir / filename).exists():
                logger.info(f"  Skipping {filename} (exists, use --force to overwrite)")
                self._generated_docs.append(f"{filename} (skipped)")
                continue

            if needs_scenes and not self.scenes:
                placeholder = (
                    f"# {filename.replace('.md', '').replace('_', ' ').title()}\n\n"
                    "> TODO: Run the pipeline first to generate scenes, then re-run "
                    "`writerai bookops` to populate this document.\n"
                )
                self._write_doc(filename, placeholder)
                self._generated_docs.append(f"{filename} (TODO)")
                continue

            try:
                logger.info(f"Generating {filename}...")
                await generator()
                self._generated_docs.append(filename)
            except Exception as e:
                logger.error(f"Failed to generate {filename}: {e}")
                self._errors.append(f"{filename}: {e}")

        # Questions for author (conditional, no LLM)
        if not doc_filter or "08" in (doc_filter or []):
            await self._generate_questions_for_author()

        # Self-check
        check = await self._self_check()
        return check

    def print_summary(self):
        """Print results to console."""
        print(f"\n{'=' * 50}")
        print(f"BookOps Complete: {self.config.get('title', 'Untitled')}")
        print(f"Output: {self.output_dir}")
        print(f"{'=' * 50}")

        if self._generated_docs:
            print("\nGenerated:")
            for doc in self._generated_docs:
                print(f"  + {doc}")

        if self._errors:
            print("\nErrors:")
            for err in self._errors:
                print(f"  ! {err}")

        if self._missing_fields:
            print(f"\nMissing config fields: {', '.join(self._missing_fields)}")
            print("  See: questions_for_author.md")

        print()
