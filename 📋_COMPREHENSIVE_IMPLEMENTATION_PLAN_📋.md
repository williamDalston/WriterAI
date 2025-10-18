# 📋 COMPREHENSIVE IMPLEMENTATION PLAN 📋
## Addressing All Feedback for Novel Generation System

Based on your detailed analysis, here's a complete implementation plan to transform the system from producing "loosely related scenes" to generating coherent, publication-quality novels.

---

## 🎯 EXECUTIVE SUMMARY

**Current Issues Identified:**
1. Master outline ignored during drafting → Wrong story generated
2. No character/plot continuity tracking → Name conflicts, dropped threads
3. Repetitive language → Overuse of "tapestry," "flicker," "weight," etc.
4. POV inconsistency → Switches from third to first person
5. "Tell don't show" → States emotions instead of showing actions
6. Unrealistic dialogue → Philosophical declarations instead of conversation
7. Generic chapter titles → "Chapter 1" instead of evocative titles
8. Non-functional ToC → Placeholder instead of hyperlinked navigation
9. Disconnected scenes → No logical flow within chapters

**Priority Order:**
1. **Critical** (Blocks coherence): Issues 1, 2, 9
2. **High** (Quality issues): Issues 3, 4, 5, 6
3. **Medium** (Polish): Issues 7, 8

---

## 🔧 PART 1: CRITICAL FIXES (Story Coherence)

### Issue 1: Master Outline Ignored During Drafting

**Problem:** `stage_06_simple_sync.py` doesn't properly use master outline details

**Current Code Issue:**
```python
# Current prompt just mentions the outline generically
prompt = f"""You are a master novelist. Draft the following scene...

Scene {scene_number}: {scene_outline.get('scene_title', 'Untitled')}
Setting: {scene_outline.get('setting', '')}
Summary: {scene_outline.get('summary', '')}
"""
```

**Fix Implementation:**

**File:** `prometheus_novel/stages/stage_06_scene_drafting_FIXED.py`

```python
def build_constrained_drafting_prompt(
    scene_index: int,
    scene_outline: dict,
    state: PrometheusState,
    previous_scene_summary: str = None
) -> str:
    """Build prompt that ENFORCES adherence to master outline"""
    
    # Extract world and character context
    protagonist = state.novel_outline.metadata.protagonist_name  # e.g., "Elene Javakhishvili"
    world_summary = extract_world_summary(state.world_model)
    character_bios = extract_character_bios(state.character_profiles)
    
    # Get scene constraints from outline
    scene_title = scene_outline['scene_title']
    setting = scene_outline['setting']
    summary = scene_outline['summary']  # DETAILED summary
    characters_present = scene_outline['characters_present']
    pov_character = scene_outline['pov']
    emotional_beat = scene_outline['emotional_beat']
    key_events = scene_outline['key_events']
    
    prompt = f"""You are drafting Scene {scene_index + 1} of a novel. Follow these constraints EXACTLY.

STORY CONTEXT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Protagonist: {protagonist}
Genre: {state.novel_outline.metadata.genre}
World: {world_summary[:500]}

Main Characters:
{format_character_bios(character_bios, characters_present)}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PREVIOUS SCENE CONTEXT:
{previous_scene_summary or "This is the opening scene."}

SCENE TO DRAFT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Scene {scene_index + 1}: {scene_title}

Setting: {setting}

Point of View: {pov_character} (third person limited)

Summary: {summary}

Characters Present: {', '.join(characters_present)}

Emotional Beat: {emotional_beat}

Key Events That MUST Occur:
{chr(10).join(f'{i+1}. {event}' for i, event in enumerate(key_events))}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONSTRAINTS:
1. The protagonist is {protagonist} - DO NOT use any other protagonist name
2. All characters present must appear in this scene
3. All key events must occur in the order listed
4. Maintain third-person limited POV from {pov_character}'s perspective
5. The setting must match exactly: {setting}
6. Word count: 1,000-1,200 words
7. End on a transition that leads to the next scene

BANNED WORDS/PHRASES (do not use):
- "tapestry" (unless literally describing fabric)
- "flicker of hope/doubt/etc"
- "heart pounded/raced/thrummed" (show physical reactions instead)
- "weight of [abstract concept]"
- "spark ignited"
- "gaze softened"
- "brow furrowed"

STYLE REQUIREMENTS:
- SHOW emotions through actions, not state them directly
- Dialogue should sound natural, not philosophical
- Use varied sentence structures
- Include sensory details (sights, sounds, smells)
- Build tension through the scene

Return ONLY a JSON object:
{{
  "scene_title": "{scene_title}",
  "content": "... the full scene prose following ALL constraints above ..."
}}
"""
    return prompt
```

**Key Improvements:**
- ✅ **Enforces protagonist name** from metadata
- ✅ **Provides previous scene context** for continuity
- ✅ **Lists banned phrases** to avoid repetition
- ✅ **Specifies exact POV** (third-person limited)
- ✅ **Requires all key events** from outline
- ✅ **Enforces setting details** from master outline

---

### Issue 2: No Character/Plot Continuity Tracking

**Problem:** No "story bible" to track characters, roles, and plot threads

**Solution:** Implement a `ContinuityTracker` class

**File:** `prometheus_novel/prometheus_lib/memory/continuity_tracker.py`

```python
from typing import Dict, List, Set, Optional
from pydantic import BaseModel
import json

class CharacterEntry(BaseModel):
    """Track a single character throughout the story"""
    name: str
    primary_role: str  # e.g., "protagonist", "antagonist", "mentor"
    personality_traits: List[str]
    first_appearance_scene: int
    last_seen_scene: int
    relationships: Dict[str, str]  # {other_char_name: relationship_type}
    arc_status: str  # Current state of character arc
    key_facts: List[str]  # Immutable facts (age, background, etc.)

class PlotThread(BaseModel):
    """Track a single plot thread"""
    thread_id: str
    description: str
    introduced_scene: int
    status: str  # "active", "resolved", "abandoned"
    last_updated_scene: int
    key_developments: List[Dict[str, str]]  # [{scene: X, event: "..."}]

class ContinuityTracker:
    """Maintains story bible across all scenes"""
    
    def __init__(self):
        self.characters: Dict[str, CharacterEntry] = {}
        self.plot_threads: Dict[str, PlotThread] = {}
        self.scene_summaries: Dict[int, str] = {}
        self.locations: Set[str] = set()
        self.timeline_events: List[Dict] = []
        
    def add_character(self, char: CharacterEntry) -> None:
        """Register a new character"""
        if char.name in self.characters:
            raise ValueError(f"Character {char.name} already exists!")
        self.characters[char.name] = char
        
    def get_character(self, name: str) -> Optional[CharacterEntry]:
        """Retrieve character details"""
        return self.characters.get(name)
        
    def validate_character_usage(self, name: str, scene_num: int, role: str) -> bool:
        """Ensure character is being used consistently"""
        char = self.get_character(name)
        if not char:
            raise ValueError(f"Character '{name}' not in story bible!")
        
        # Check if role matches
        if role != char.primary_role:
            raise ValueError(
                f"Character '{name}' is being used as '{role}' "
                f"but was established as '{char.primary_role}' in scene {char.first_appearance_scene}"
            )
        
        # Update last seen
        char.last_seen_scene = scene_num
        return True
        
    def add_plot_thread(self, thread: PlotThread) -> None:
        """Register a new plot thread"""
        self.plot_threads[thread.thread_id] = thread
        
    def get_active_threads(self, scene_num: int) -> List[PlotThread]:
        """Get all active plot threads at this point in story"""
        return [
            thread for thread in self.plot_threads.values()
            if thread.status == "active" and thread.introduced_scene <= scene_num
        ]
        
    def check_dropped_threads(self, current_scene: int, window: int = 10) -> List[str]:
        """Identify plot threads that haven't been updated recently"""
        dropped = []
        for thread in self.plot_threads.values():
            if thread.status == "active":
                if current_scene - thread.last_updated_scene > window:
                    dropped.append(
                        f"Thread '{thread.description}' last updated in scene {thread.last_updated_scene}"
                    )
        return dropped
        
    def add_scene_summary(self, scene_num: int, summary: str) -> None:
        """Add summary for scene continuity"""
        self.scene_summaries[scene_num] = summary
        
    def get_recent_context(self, scene_num: int, lookback: int = 3) -> str:
        """Get summary of recent scenes for context"""
        recent = []
        for i in range(max(0, scene_num - lookback), scene_num):
            if i in self.scene_summaries:
                recent.append(f"Scene {i+1}: {self.scene_summaries[i]}")
        return "\n".join(recent)
        
    def export_story_bible(self) -> Dict:
        """Export complete story bible for reference"""
        return {
            "characters": {name: char.model_dump() for name, char in self.characters.items()},
            "plot_threads": {tid: thread.model_dump() for tid, thread in self.plot_threads.items()},
            "scene_summaries": self.scene_summaries,
            "locations": list(self.locations),
            "timeline": self.timeline_events
        }
        
    def load_from_master_outline(self, master_outline: Dict) -> None:
        """Initialize story bible from master outline"""
        # Extract all characters mentioned
        all_chars = set()
        for scene in master_outline['scenes']:
            for char in scene['characters_present']:
                all_chars.add(char)
        
        # Initialize character entries (will be fleshed out from character profiles)
        for char_name in all_chars:
            self.characters[char_name] = CharacterEntry(
                name=char_name,
                primary_role="to_be_determined",
                personality_traits=[],
                first_appearance_scene=0,
                last_seen_scene=0,
                relationships={},
                arc_status="introduced",
                key_facts=[]
            )
```

**Integration into Stage 6:**

```python
def draft_all_scenes_with_continuity(state: PrometheusState) -> PrometheusState:
    """Draft scenes with continuity tracking"""
    
    # Initialize continuity tracker
    tracker = ContinuityTracker()
    tracker.load_from_master_outline(state.scene_outline)
    
    # Load character details from profiles
    for char_name, char_data in state.character_profiles.items():
        if char_name in tracker.characters:
            char_entry = tracker.characters[char_name]
            char_entry.primary_role = char_data.get('role', 'supporting')
            char_entry.personality_traits = char_data.get('traits', [])
            char_entry.key_facts = char_data.get('background', [])
    
    # Draft each scene with validation
    for scene_index, scene_outline in enumerate(state.scene_outline['scenes']):
        # Get context from tracker
        recent_context = tracker.get_recent_context(scene_index)
        
        # Build prompt with context
        prompt = build_constrained_drafting_prompt(
            scene_index,
            scene_outline,
            state,
            previous_scene_summary=recent_context
        )
        
        # Validate characters in this scene
        for char_name in scene_outline['characters_present']:
            tracker.validate_character_usage(
                char_name,
                scene_index,
                tracker.get_character(char_name).primary_role
            )
        
        # Draft scene (OpenAI call)
        scene_content = draft_scene_with_llm(prompt)
        
        # Add summary to tracker
        summary = extract_scene_summary(scene_content)  # LLM call to summarize
        tracker.add_scene_summary(scene_index, summary)
        
        # Check for dropped threads
        if scene_index % 10 == 0:  # Check every 10 scenes
            dropped = tracker.check_dropped_threads(scene_index)
            if dropped:
                logger.warning(f"Potentially dropped plot threads: {dropped}")
        
        # Store scene
        state.drafted_scenes[scene_index] = scene_content
    
    # Export story bible for reference
    story_bible_path = output_dir / "story_bible.json"
    with open(story_bible_path, 'w') as f:
        json.dump(tracker.export_story_bible(), f, indent=2)
    
    return state
```

**Benefits:**
- ✅ **Prevents character name conflicts** (Kael can't be both ally and antagonist)
- ✅ **Tracks dropped plot threads** (Ivy's backstory won't be forgotten)
- ✅ **Enforces role consistency** throughout story
- ✅ **Provides context to each scene** from previous scenes
- ✅ **Creates exportable story bible** for debugging

---

### Issue 9: Disconnected Scenes Within Chapters

**Problem:** Scene breaks (`***`) separate unrelated content

**Solution:** Enforce scene connectivity in master outline generation

**File:** `prometheus_novel/stages/stage_04b_master_outline.py` (UPDATE)

```python
def validate_scene_connections(scenes: List[Dict]) -> List[str]:
    """Validate that scenes connect logically"""
    issues = []
    
    for i in range(len(scenes) - 1):
        current = scenes[i]
        next_scene = scenes[i + 1]
        
        # Check character continuity
        current_chars = set(current['characters_present'])
        next_chars = set(next_scene['characters_present'])
        
        if not current_chars.intersection(next_chars):
            issues.append(
                f"No character overlap between Scene {i+1} ({current['scene_title']}) "
                f"and Scene {i+2} ({next_scene['scene_title']})"
            )
        
        # Check setting continuity (allow changes but flag sudden jumps)
        if not scenes_are_connected(current, next_scene):
            issues.append(
                f"Abrupt setting change from Scene {i+1} to {i+2} "
                f"without transition explanation"
            )
    
    return issues

def scenes_are_connected(scene1: Dict, scene2: Dict) -> bool:
    """Check if two scenes logically connect"""
    # Allow connection if:
    # 1. Same setting
    # 2. Overlapping characters
    # 3. Scene 1's key events lead to scene 2's premise
    
    same_setting = scene1['setting'] == scene2['setting']
    shared_chars = bool(set(scene1['characters_present']) & set(scene2['characters_present']))
    
    # Check if scene 1's summary mentions what scene 2 is about
    scene1_leads_to_2 = any(
        keyword in scene1['summary'].lower()
        for keyword in extract_key_concepts(scene2['scene_title'])
    )
    
    return same_setting or shared_chars or scene1_leads_to_2
```

**Updated Master Outline Generation:**

```python
async def run_stage_04b_master_outline(state, services, target_scenes=50):
    """Generate master outline with validated connections"""
    
    # ... existing generation code ...
    
    # After generating outline
    scenes = outline_data['scenes']
    
    # Validate connections
    issues = validate_scene_connections(scenes)
    
    if issues:
        logger.warning(f"Found {len(issues)} connectivity issues in outline:")
        for issue in issues:
            logger.warning(f"  - {issue}")
        
        # Attempt to fix by regenerating problem transitions
        # OR require manual review before proceeding
        
    return state
```

---

## 🎨 PART 2: HIGH PRIORITY (Writing Quality)

### Issue 3: Repetitive Language

**Solution:** Implement post-processing filter + banned word list

**File:** `prometheus_novel/prometheus_lib/utils/prose_improver.py`

```python
import re
from typing import List, Dict, Set
from collections import Counter

class ProseImprover:
    """Post-process generated prose to remove repetitive patterns"""
    
    # Comprehensive banned/overused words
    OVERUSED_METAPHORS = {
        'tapestry': ['fabric', 'weave', 'pattern', 'mosaic', 'composition'],
        'flicker': ['glimmer', 'trace', 'hint', 'whisper'],
        'spark': ['seed', 'hint', 'beginning', 'stirring'],
        'weight': ['burden', 'gravity', 'pressure', 'force'],
    }
    
    OVERUSED_BODY_LANGUAGE = {
        'heart pounded': ['chest tightened', 'breath caught', 'pulse quickened'],
        'heart raced': ['adrenaline surged', 'blood rushed', 'breath quickened'],
        'heart swelled': ['warmth spread through', 'chest filled with', 'emotion washed over'],
        'heart thrummed': ['pulse steadied', 'breath evened', 'calm settled'],
        'gaze softened': ['expression eased', 'features relaxed', 'look gentled'],
        'brow furrowed': ['forehead creased', 'eyes narrowed', 'face tightened'],
        'leaned closer': ['moved nearer', 'stepped forward', 'drew near'],
    }
    
    OVERUSED_ABSTRACTIONS = {
        'weight of centuries': 'ancient burden',
        'weight of destiny': 'fateful pressure',
        'weight of tradition': 'customary expectations',
        'weight of knowledge': 'accumulated wisdom',
    }
    
    def __init__(self, max_word_frequency: int = 3):
        self.max_word_frequency = max_word_frequency
        
    def analyze_repetition(self, text: str) -> Dict[str, int]:
        """Find overused words/phrases in text"""
        # Check single words
        words = re.findall(r'\b\w+\b', text.lower())
        word_freq = Counter(words)
        
        # Filter to "interesting" words (not articles, common words)
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
        overused = {
            word: count 
            for word, count in word_freq.items()
            if count > self.max_word_frequency and word not in common_words
        }
        
        # Check for overused phrases
        for phrase in self.OVERUSED_METAPHORS.keys():
            phrase_count = len(re.findall(rf'\b{phrase}\b', text, re.IGNORECASE))
            if phrase_count > 2:
                overused[phrase] = phrase_count
        
        return overused
    
    def replace_overused_terms(self, text: str, scene_index: int) -> str:
        """Replace overused terms with alternatives"""
        modified = text
        replacements_made = []
        
        # Track which replacement we're on for rotation
        replacement_indices = {}
        
        # Replace overused metaphors
        for overused, alternatives in self.OVERUSED_METAPHORS.items():
            pattern = rf'\b{overused}\b'
            matches = list(re.finditer(pattern, modified, re.IGNORECASE))
            
            if len(matches) > 1:  # Keep first instance, replace others
                for i, match in enumerate(matches[1:], 1):
                    alt_index = i % len(alternatives)
                    replacement = alternatives[alt_index]
                    
                    # Match case
                    if match.group().istitle():
                        replacement = replacement.capitalize()
                    
                    start, end = match.span()
                    modified = modified[:start] + replacement + modified[end:]
                    replacements_made.append(f"{match.group()} → {replacement}")
        
        # Replace body language clichés
        for cliche, alternatives in self.OVERUSED_BODY_LANGUAGE.items():
            if cliche in modified.lower():
                instances = modified.lower().count(cliche)
                if instances > 1:
                    # Replace second instance
                    pattern = re.compile(re.escape(cliche), re.IGNORECASE)
                    matches = list(pattern.finditer(modified))
                    if len(matches) > 1:
                        match = matches[1]
                        alt_index = scene_index % len(alternatives)
                        replacement = alternatives[alt_index]
                        modified = modified[:match.start()] + replacement + modified[match.end():]
                        replacements_made.append(f'"{cliche}" → "{replacement}"')
        
        if replacements_made:
            logger.info(f"Scene {scene_index}: Replaced overused terms: {', '.join(replacements_made[:3])}")
        
        return modified
    
    def improve_show_not_tell(self, text: str) -> str:
        """Convert 'telling' to 'showing' where possible"""
        
        # Pattern: "CHARACTER felt EMOTION"
        tell_patterns = {
            r'(\w+) felt a rush of (\w+)': lambda m: f"{m.group(1)}'s breath caught",
            r'(\w+) felt (\w+) at': lambda m: f"A {m.group(2)} sensation washed over {m.group(1)} at",
            r'was filled with (\w+)': lambda m: f"radiated {m.group(1)}",
        }
        
        modified = text
        for pattern, replacement_func in tell_patterns.items():
            modified = re.sub(pattern, replacement_func, modified)
        
        return modified
    
    def process_scene(self, scene_content: str, scene_index: int) -> str:
        """Apply all prose improvements to a scene"""
        
        # 1. Check for repetition
        overused = self.analyze_repetition(scene_content)
        if overused:
            logger.warning(f"Scene {scene_index} overused words: {list(overused.keys())[:5]}")
        
        # 2. Replace overused terms
        improved = self.replace_overused_terms(scene_content, scene_index)
        
        # 3. Improve show-not-tell
        improved = self.improve_show_not_tell(improved)
        
        return improved
```

**Integration:**

```python
# In polishing stage
improver = ProseImprover(max_word_frequency=3)

for scene_index, scene_data in drafted_scenes.items():
    content = scene_data['content']
    
    # Apply prose improvements
    improved_content = improver.process_scene(content, scene_index)
    
    scene_data['improved_content'] = improved_content
```

---

### Issue 4: POV Inconsistency

**Solution:** Enforce POV throughout generation + validation

**File:** `prometheus_novel/prometheus_lib/validators/pov_validator.py`

```python
import re
from typing import Tuple, List

class POVValidator:
    """Validate and enforce consistent POV throughout novel"""
    
    POV_PATTERNS = {
        'first_person': [r'\bI\b', r'\bme\b', r'\bmy\b', r'\bmine\b', r'\bwe\b', r'\bour\b'],
        'third_person': [r'\bhe\b', r'\bshe\b', r'\bhim\b', r'\bher\b', r'\bhis\b', r'\bhers\b', r'\bthey\b'],
        'second_person': [r'\byou\b', r'\byour\b', r'\byours\b'],
    }
    
    def __init__(self, expected_pov: str = 'third_person'):
        """
        Args:
            expected_pov: 'first_person', 'second_person', or 'third_person'
        """
        self.expected_pov = expected_pov
        
    def detect_pov(self, text: str) -> Tuple[str, float]:
        """Detect the POV of a text passage
        
        Returns:
            (pov_type, confidence_score)
        """
        # Count POV indicators
        counts = {}
        for pov_type, patterns in self.POV_PATTERNS.items():
            count = 0
            for pattern in patterns:
                count += len(re.findall(pattern, text, re.IGNORECASE))
            counts[pov_type] = count
        
        # Determine dominant POV
        total = sum(counts.values())
        if total == 0:
            return ('unknown', 0.0)
        
        dominant = max(counts, key=counts.get)
        confidence = counts[dominant] / total
        
        return (dominant, confidence)
    
    def validate_scene(self, scene_content: str, scene_index: int) -> Tuple[bool, List[str]]:
        """Validate a scene's POV consistency
        
        Returns:
            (is_valid, list_of_issues)
        """
        detected_pov, confidence = self.detect_pov(scene_content)
        issues = []
        
        if detected_pov != self.expected_pov:
            issues.append(
                f"Scene {scene_index + 1}: Expected {self.expected_pov} but detected "
                f"{detected_pov} (confidence: {confidence:.2%})"
            )
        
        # Check for mid-scene POV shifts
        paragraphs = scene_content.split('\n\n')
        prev_pov = None
        for para_index, para in enumerate(paragraphs):
            if len(para.strip()) < 50:  # Skip short paragraphs
                continue
            
            para_pov, _ = self.detect_pov(para)
            if prev_pov and para_pov != prev_pov and para_pov != 'unknown':
                issues.append(
                    f"Scene {scene_index + 1}, paragraph {para_index + 1}: "
                    f"POV shift from {prev_pov} to {para_pov}"
                )
            prev_pov = para_pov if para_pov != 'unknown' else prev_pov
        
        return (len(issues) == 0, issues)
    
    def fix_pov_shift(self, text: str) -> str:
        """Attempt to automatically fix POV inconsistencies"""
        
        if self.expected_pov == 'third_person':
            # Replace first-person pronouns with third-person
            # This is crude and would need character name context
            # Better to flag for manual review
            
            detected_pov, _ = self.detect_pov(text)
            if detected_pov == 'first_person':
                logger.warning("Cannot auto-fix first→third POV shift. Manual review needed.")
        
        return text  # Flag only for now
    
    def validate_full_novel(self, scenes: Dict[int, Dict]) -> Dict[str, any]:
        """Validate POV consistency across entire novel"""
        
        all_issues = []
        scene_povs = {}
        
        for scene_index, scene_data in scenes.items():
            content = scene_data.get('content', '')
            is_valid, issues = self.validate_scene(content, scene_index)
            
            if not is_valid:
                all_issues.extend(issues)
            
            detected_pov, confidence = self.detect_pov(content)
            scene_povs[scene_index] = (detected_pov, confidence)
        
        # Overall stats
        pov_distribution = {}
        for pov, _ in scene_povs.values():
            pov_distribution[pov] = pov_distribution.get(pov, 0) + 1
        
        return {
            'is_consistent': len(all_issues) == 0,
            'issues': all_issues,
            'scene_povs': scene_povs,
            'distribution': pov_distribution,
            'expected_pov': self.expected_pov
        }
```

**Integration into Generation:**

```python
# At start of generation
pov_validator = POVValidator(expected_pov='third_person')

# After drafting each scene
is_valid, issues = pov_validator.validate_scene(scene_content, scene_index)
if not is_valid:
    logger.error(f"POV validation failed: {issues}")
    # Regenerate scene with stricter POV constraints

# After full novel
validation_report = pov_validator.validate_full_novel(state.drafted_scenes)
if not validation_report['is_consistent']:
    logger.error("Novel has POV consistency issues!")
    logger.error(f"Issues: {validation_report['issues']}")
    # Flag for manual review
```

**Update drafting prompt:**

```python
# Add to prompt
POV_CONSTRAINT = f"""
CRITICAL: This entire novel uses THIRD-PERSON LIMITED point of view.
- Use "he/she/they" (never "I/me/my")
- Show only what the POV character ({pov_character}) can see/hear/think
- Never switch to first-person perspective
- Never use "you" to address the reader
"""
```

---

### Issue 5 & 6: "Tell Don't Show" + Unrealistic Dialogue

**Solution:** Enhanced prompting + post-processing examples

**File:** Update `build_constrained_drafting_prompt()` with:

```python
WRITING_STYLE_CONSTRAINTS = """
SHOW, DON'T TELL - EXAMPLES:

❌ BAD (Telling): "Ivy felt a rush of courage at his words."
✅ GOOD (Showing): "Her spine straightened. She met his gaze and held it."

❌ BAD (Telling): "She was filled with dread."
✅ GOOD (Showing): "Her fingers went numb. The room seemed to tilt."

❌ BAD (Telling): "He felt angry."
✅ GOOD (Showing): "His jaw clenched. The words came out clipped, sharp."

For emotions, describe:
- Physical reactions (breath, heartbeat, temperature)
- Actions taken (stepping back, clenching fists, looking away)
- Sensory details (sounds louder, vision narrowing)
- Dialogue that reveals emotion indirectly

NATURAL DIALOGUE - EXAMPLES:

❌ BAD (Too philosophical): "To believe without question is to be shackled by ignorance, my dear colleague."
✅ GOOD (Natural): "You can't just accept everything they tell you." She paused. "Someone has to ask questions."

❌ BAD (Exposition dump): "As you know, our village has followed these traditions for five hundred years..."
✅ GOOD (Natural): "Five hundred years." He shook his head. "That's what they keep saying."

Dialogue should:
- Sound like how people actually talk (fragments, interruptions, subtext)
- Reveal character through word choice and speech patterns
- Advance plot or deepen relationships
- Avoid explaining things both characters already know
- Include beats (physical actions during dialogue)

Example of good dialogue with beats:
"We need to leave." Sarah grabbed her coat from the hook. "Tonight."
"What?" Marcus looked up from his book. "That's insane."
"Is it?" She turned to face him, coat halfway on. "After what we just saw?"
He closed the book slowly, his thumb marking the page. "Where would we even go?"
"""
```

---

## 📝 PART 3: MEDIUM PRIORITY (Polish & UX)

### Issue 7: Generic Chapter Titles

**Solution:** Generate chapter titles from scene content

**File:** `prometheus_novel/stages/stage_13_chapter_titles.py` (NEW)

```python
async def generate_chapter_titles(state: PrometheusState, services) -> PrometheusState:
    """Generate evocative chapter titles based on content"""
    
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    # Group scenes into chapters (3 scenes per chapter)
    scenes_per_chapter = 3
    total_scenes = len(state.drafted_scenes)
    total_chapters = (total_scenes + scenes_per_chapter - 1) // scenes_per_chapter
    
    chapter_titles = {}
    
    for chapter_num in range(total_chapters):
        start_scene = chapter_num * scenes_per_chapter
        end_scene = min(start_scene + scenes_per_chapter, total_scenes)
        
        # Get content of scenes in this chapter
        chapter_scenes = []
        for scene_idx in range(start_scene, end_scene):
            if scene_idx in state.drafted_scenes:
                scene = state.drafted_scenes[scene_idx]
                chapter_scenes.append({
                    'title': scene.get('scene_title', ''),
                    'summary': scene.get('content', '')[:500]  # First 500 chars
                })
        
        # Generate title
        prompt = f"""Generate an evocative chapter title for a novel chapter.

Genre: {state.novel_outline.metadata.genre}

This chapter contains {len(chapter_scenes)} scenes:
{chr(10).join(f"- {s['title']}: {s['summary']}..." for s in chapter_scenes)}

Generate a chapter title that:
- Is 2-5 words long
- Hints at the chapter's content without spoiling it
- Has literary quality (not generic like "Chapter 1")
- Matches the tone of the genre

Examples of good chapter titles:
- "The Weight of Silence"
- "Fractured Loyalties"
- "Beneath the Surface"
- "Echoes and Ash"

Return ONLY the chapter title, nothing else.
"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=20
        )
        
        title = response.choices[0].message.content.strip().strip('"')
        chapter_titles[chapter_num] = title
        
        print(f"Chapter {chapter_num + 1}: {title}")
    
    # Store in state
    state.chapter_titles = chapter_titles
    
    return state
```

---

### Issue 8: Non-functional Table of Contents

**Solution:** Update `export_kindle_docx.py` to generate hyperlinked ToC

**File:** `prometheus_novel/export_kindle_docx.py` (UPDATE)

```python
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

def add_hyperlinked_toc(doc: Document, chapter_titles: Dict[int, str]):
    """Add a functional, hyperlinked Table of Contents"""
    
    # Add ToC heading
    toc_heading = doc.add_heading('Table of Contents', level=1)
    toc_heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Add a page break before ToC so it's on its own page
    doc.add_page_break()
    
    # For each chapter, add a hyperlink entry
    for chapter_num, title in sorted(chapter_titles.items()):
        # Create a paragraph for the ToC entry
        p = doc.add_paragraph()
        
        # Add the chapter number and title as a hyperlink
        # The bookmark will be created at the chapter heading
        bookmark_name = f"chapter_{chapter_num + 1}"
        
        # Add hyperlink to bookmark (this requires working with XML)
        hyperlink = add_hyperlink(p, title, bookmark_name)
        
        # Format the ToC entry
        run = p.runs[0]
        run.font.size = Pt(12)
        run.font.name = 'Garamond'
        
        # Add leader dots
        p.paragraph_format.tab_stops.add_tab_stop(Inches(6), alignment=WD_TAB_ALIGNMENT.RIGHT, leader=WD_TAB_LEADER.DOTS)
        
    doc.add_page_break()

def add_hyperlink(paragraph, text, bookmark_name):
    """Add a hyperlink to a bookmark in the document"""
    # This creates an internal hyperlink to a bookmark
    # Bookmarks are created at each chapter heading
    
    hyperlink = parse_xml(
        f'<w:hyperlink {nsdecls("w")} w:anchor="{bookmark_name}">'
        f'<w:r><w:t>{text}</w:t></w:r>'
        f'</w:hyperlink>'
    )
    paragraph._element.append(hyperlink)
    return hyperlink

def add_chapter_with_bookmark(doc: Document, chapter_num: int, title: str):
    """Add a chapter heading with a bookmark for ToC linking"""
    
    # Create bookmark name
    bookmark_name = f"chapter_{chapter_num + 1}"
    
    # Add the chapter heading
    heading = doc.add_heading(f'Chapter {chapter_num + 1}: {title}', level=1)
    
    # Add bookmark to the heading (for ToC linking)
    bookmark_start = parse_xml(
        f'<w:bookmarkStart {nsdecls("w")} w:id="{chapter_num}" w:name="{bookmark_name}"/>'
    )
    bookmark_end = parse_xml(
        f'<w:bookmarkEnd {nsdecls("w")} w:id="{chapter_num}"/>'
    )
    
    heading._element.insert(0, bookmark_start)
    heading._element.append(bookmark_end)
    
    return heading

# In main export function
def export_novel_to_docx(state: PrometheusState, output_file: str):
    """Export with functional ToC"""
    
    doc = Document()
    
    # Front matter
    add_front_matter(doc, state.novel_outline.metadata.title, state.novel_outline.metadata.author)
    
    # Table of Contents (with hyperlinks)
    add_hyperlinked_toc(doc, state.chapter_titles)
    
    # Chapters
    scenes_per_chapter = 3
    for chapter_num in range(len(state.chapter_titles)):
        start_scene = chapter_num * scenes_per_chapter
        end_scene = min(start_scene + scenes_per_chapter, len(state.drafted_scenes))
        
        # Add chapter heading with bookmark
        chapter_title = state.chapter_titles[chapter_num]
        add_chapter_with_bookmark(doc, chapter_num, chapter_title)
        
        # Add scenes
        for scene_idx in range(start_scene, end_scene):
            # ... add scene content ...
    
    doc.save(output_file)
```

---

## 🔄 PART 4: IMPLEMENTATION SEQUENCE

### Phase 1: Core Fixes (Week 1)

**Priority: Fix story coherence issues**

1. ✅ **Day 1-2:** Implement `ContinuityTracker` class
   - Character tracking
   - Plot thread management
   - Scene summary storage

2. ✅ **Day 3-4:** Fix Stage 6 drafting
   - Update prompt to use master outline details
   - Integrate continuity tracker
   - Add character validation
   - Enforce protagonist name

3. ✅ **Day 5:** Add scene connection validation
   - Update Stage 4B to validate outline
   - Ensure logical scene flow

**Testing:** Generate a 10-scene test novel and verify:
- All scenes feature correct protagonist
- No character role conflicts
- Scenes connect logically
- Master outline is followed exactly

---

### Phase 2: Writing Quality (Week 2)

**Priority: Fix repetitive language and style issues**

1. ✅ **Day 1-2:** Implement `ProseImprover`
   - Build banned word lists
   - Create replacement dictionaries
   - Add show-not-tell patterns

2. ✅ **Day 3:** Implement `POVValidator`
   - POV detection logic
   - Validation at scene and novel level
   - Auto-flagging inconsistencies

3. ✅ **Day 4-5:** Enhance drafting prompts
   - Add detailed show-not-tell examples
   - Include natural dialogue guidelines
   - Provide style constraint examples

**Testing:** Generate 5 test scenes and verify:
- No repetitive metaphors (tapestry, flicker, etc.)
- Consistent third-person POV
- Dialogue sounds natural
- Emotions shown through actions

---

### Phase 3: Polish & UX (Week 3)

**Priority: Professional formatting and UX**

1. ✅ **Day 1-2:** Implement chapter title generation
   - Create Stage 13
   - Generate evocative titles from content
   - Store in state

2. ✅ **Day 3-4:** Implement hyperlinked ToC
   - Update export script
   - Create bookmarks at chapter headings
   - Link ToC entries to bookmarks

3. ✅ **Day 5:** End-to-end testing
   - Generate complete test novel
   - Verify all features work together
   - Check exported .docx quality

---

### Phase 4: Integration & Production (Week 4)

1. ✅ **Day 1-2:** Integrate all components
   - Update main generation script
   - Add all validators to pipeline
   - Ensure state persistence

2. ✅ **Day 3:** Documentation
   - Update README with new features
   - Document configuration options
   - Create troubleshooting guide

3. ✅ **Day 4-5:** Production testing
   - Generate full 50-scene novel
   - Verify quality metrics
   - Tune parameters based on results

---

## 📊 PART 5: QUALITY METRICS & VALIDATION

### Automated Quality Checks

Create `prometheus_novel/quality_check.py`:

```python
class QualityMetrics:
    """Comprehensive quality validation for generated novels"""
    
    def __init__(self, state: PrometheusState):
        self.state = state
        self.report = {}
    
    def check_character_consistency(self) -> Dict:
        """Verify character names and roles are consistent"""
        tracker = ContinuityTracker()
        tracker.load_from_state(self.state)
        
        issues = []
        for char_name, char_data in tracker.characters.items():
            # Check for role conflicts
            # Check for unexplained disappearances
            # Check for name variations
        
        return {
            'passed': len(issues) == 0,
            'issues': issues
        }
    
    def check_plot_progression(self) -> Dict:
        """Verify plot builds and resolves"""
        # Check for introduction, rising action, climax, resolution
        # Verify stakes escalate
        # Ensure no circular plot (same conflicts repeated)
        pass
    
    def check_language_quality(self) -> Dict:
        """Check for repetitive language"""
        improver = ProseImprover()
        
        all_overused = {}
        for scene_idx, scene_data in self.state.drafted_scenes.items():
            content = scene_data.get('content', '')
            overused = improver.analyze_repetition(content)
            all_overused.update(overused)
        
        return {
            'passed': len(all_overused) < 10,  # Allow some repetition
            'overused_words': all_overused,
            'worst_offenders': sorted(all_overused.items(), key=lambda x: x[1], reverse=True)[:5]
        }
    
    def check_pov_consistency(self) -> Dict:
        """Verify POV never shifts"""
        validator = POVValidator(expected_pov='third_person')
        return validator.validate_full_novel(self.state.drafted_scenes)
    
    def check_scene_connections(self) -> Dict:
        """Verify scenes connect logically"""
        # Check character continuity between scenes
        # Check setting transitions are explained
        # Check no plot holes
        pass
    
    def generate_full_report(self) -> Dict:
        """Run all quality checks and generate report"""
        self.report = {
            'character_consistency': self.check_character_consistency(),
            'plot_progression': self.check_plot_progression(),
            'language_quality': self.check_language_quality(),
            'pov_consistency': self.check_pov_consistency(),
            'scene_connections': self.check_scene_connections(),
        }
        
        # Overall score
        passed_checks = sum(1 for check in self.report.values() if check.get('passed', False))
        total_checks = len(self.report)
        
        self.report['overall_score'] = passed_checks / total_checks
        self.report['grade'] = self.calculate_grade(self.report['overall_score'])
        
        return self.report
    
    def calculate_grade(self, score: float) -> str:
        """Convert score to letter grade"""
        if score >= 0.95: return "A+ (Publication Ready)"
        if score >= 0.90: return "A (Excellent)"
        if score >= 0.85: return "A- (Very Good)"
        if score >= 0.80: return "B+ (Good)"
        if score >= 0.75: return "B (Needs Polish)"
        if score >= 0.70: return "B- (Needs Revision)"
        return "C or below (Major Revision Needed)"
```

---

## 🎯 PART 6: SUCCESS CRITERIA

### After Implementation, A Generated Novel Should:

**Story Coherence (Critical):**
- ✅ Use correct protagonist name throughout
- ✅ No character role conflicts (same character can't be ally and antagonist)
- ✅ All plot threads introduced are either resolved or acknowledged
- ✅ Scenes connect logically with character/setting continuity
- ✅ Master outline details are followed in each scene

**Writing Quality (High Priority):**
- ✅ No word used more than 3 times unless it's a proper noun
- ✅ Consistent third-person POV (no first-person slips)
- ✅ Emotions shown through actions, not stated directly
- ✅ Dialogue sounds natural, not like speeches
- ✅ Varied sentence structures and descriptions

**Professional Polish (Medium Priority):**
- ✅ Evocative chapter titles (not "Chapter 1")
- ✅ Functional, hyperlinked Table of Contents
- ✅ Proper scene breaks with logical transitions
- ✅ Consistent formatting throughout

**Quality Score:** Minimum 85% (A- grade) to be considered publication-ready

---

## 📁 PART 7: FILE STRUCTURE

```
prometheus_novel/
├── prometheus_lib/
│   ├── memory/
│   │   ├── continuity_tracker.py         # NEW: Story bible
│   │   └── ...
│   ├── utils/
│   │   ├── prose_improver.py             # NEW: Post-processing
│   │   └── ...
│   ├── validators/
│   │   ├── pov_validator.py              # NEW: POV checking
│   │   └── ...
│   └── ...
├── stages/
│   ├── stage_04b_master_outline.py       # UPDATED: Add validation
│   ├── stage_06_scene_drafting_FIXED.py  # MAJOR UPDATE: Use outline
│   ├── stage_13_chapter_titles.py        # NEW: Generate titles
│   └── ...
├── export_kindle_docx.py                 # UPDATED: Hyperlinked ToC
├── quality_check.py                      # NEW: Automated validation
└── ...
```

---

## ⏱️ ESTIMATED IMPLEMENTATION TIME

- **Phase 1 (Core Fixes):** 5 days  
- **Phase 2 (Quality):** 5 days  
- **Phase 3 (Polish):** 5 days  
- **Phase 4 (Integration):** 5 days  

**Total:** ~20 working days (4 weeks)

---

## 🎯 IMMEDIATE NEXT STEPS

Would you like me to:

1. **Start with Phase 1** - Implement `ContinuityTracker` and fix Stage 6 drafting?
2. **Implement all fixes now** - Work through all phases in this session?
3. **Focus on specific issue** - Which single issue is most important to you?
4. **Re-generate your novel** - Apply what's feasible now and generate corrected version?

Your feedback has been invaluable and will result in **dramatically better novel generation**! 🙏📚

Which approach would you prefer?
