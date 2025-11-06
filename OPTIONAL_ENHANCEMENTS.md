# Optional Enhancements for ANBG

**Status:** Core system complete and operational  
**These enhancements are OPTIONAL** - the system works without them

---

## 1. Export Library Integration (Low Priority)

### Current Status
- ✅ HTML export: FULLY WORKING
- ⚠️  EPUB export: Placeholder (needs `ebooklib`)
- ⚠️  PDF export: Placeholder (needs `weasyprint`)

### To Complete

**Install libraries:**
```bash
pip install ebooklib weasyprint
```

**Update `stages/stage_12_formatting_export.py`:**

```python
# For EPUB (replace _export_epub function)
from ebooklib import epub

async def _export_epub(html_content: str, export_path: Path, state: ANBGState) -> Path:
    book = epub.EpubBook()
    
    # Set metadata
    book.set_title(state.manuscript.title)
    book.set_language('en')
    book.add_author(state.manuscript.author)
    
    # Add chapters
    for chapter in state.manuscript.chapters:
        c = epub.EpubHtml(
            title=chapter.title,
            file_name=f'chap_{chapter.chapter_number}.xhtml',
            content=f'<h1>{chapter.title}</h1>{chapter.introduction}...'
        )
        book.add_item(c)
    
    # Write file
    output_file = export_path / "epub" / f"{state.profile.project_name}.epub"
    epub.write_epub(str(output_file), book, {})
    
    return output_file

# For PDF (replace _export_pdf function)
from weasyprint import HTML

async def _export_pdf(html_content: str, export_path: Path, state: ANBGState) -> Path:
    output_file = export_path / "pdf" / f"{state.profile.project_name}.pdf"
    HTML(string=html_content).write_pdf(str(output_file))
    return output_file
```

**Effort:** 1-2 hours  
**Value:** Medium (many readers prefer EPUB/PDF)

---

## 2. Performance Caching (Low Priority)

### Current Status
- ✅ Basic caching in vector store (LRU cache)
- ✅ Link check caching
- ⚠️  No LLM response memoization
- ⚠️  No context diet optimization

### To Add

**Redis caching for LLM responses:**

```python
# prometheus_lib/llm/cache.py
import redis
import hashlib
import json

class LLMCache:
    def __init__(self):
        self.redis = redis.Redis(host='localhost', port=6379, db=0)
    
    def get_cache_key(self, profile, prompt, seed):
        # Create hash from inputs
        content = f"{profile.project_name}:{prompt}:{seed}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    async def get(self, profile, prompt, seed):
        key = self.get_cache_key(profile, prompt, seed)
        cached = self.redis.get(key)
        if cached:
            return json.loads(cached)
        return None
    
    async def set(self, profile, prompt, seed, response):
        key = self.get_cache_key(profile, prompt, seed)
        self.redis.setex(key, 86400, json.dumps(response))  # 24hr TTL
```

**Effort:** 2-3 hours  
**Value:** Medium (speeds up reruns significantly)

---

## 3. Automated Test Suite (Medium Priority)

### Current Status
- ✅ Testing guide with manual procedures
- ✅ Test data templates
- ⚠️  No pytest suite

### To Add

Create `tests/test_anbg_complete.py`:

```python
import pytest
from pathlib import Path

@pytest.mark.asyncio
class TestANBGPipeline:
    async def test_full_pipeline_small_book(self):
        """Test generating a small 3-chapter book."""
        profile = load_test_profile()
        orchestrator = ANBGOrchestrator(profile)
        await orchestrator.initialize()
        
        state = await orchestrator.run_full_pipeline()
        
        # Assertions
        assert len(state.manuscript.chapters) >= 3
        assert state.quality_metrics.all_blocking_gates_pass
        assert state.quality_metrics.citation_coverage >= 0.95
        assert state.exports_generated.get("html")
    
    async def test_evidence_system(self):
        """Test citation attachment and validation."""
        # Test evidence attacher
        # Test fact checker
        # Test source validator
        pass
    
    async def test_learning_system(self):
        """Test dependency graphs and learning order."""
        # Test DAG validation
        # Test forward reference detection
        # Test Bloom classification
        pass
```

**Run:**
```bash
pytest tests/ -v --cov=prometheus_lib
```

**Effort:** 4-6 hours  
**Value:** High (ensures reliability)

---

## 4. Interactive HTML Features (Low Priority)

### Current Status
- ✅ Semantic HTML structure
- ✅ Navigation working
- ⚠️  No JavaScript interactivity

### To Add

**Interactive quizzes:**

```javascript
// Add to HTML export
<script>
function checkQuiz(quizId) {
    // Get user answers
    // Compare to correct answers
    // Show results
    // Track progress
}
</script>
```

**Code syntax highlighting:**

```bash
pip install Pygments
# Use for code blocks in HTML export
```

**Diagram rendering:**

```bash
pip install cairosvg
# Render Mermaid diagrams to SVG
```

**Effort:** 3-4 hours  
**Value:** Medium (enhances user experience)

---

## 5. CLI Enhancements (Low Priority)

### Current Status
- ✅ Basic CLI (`run_anbg.py`)
- ⚠️  No rich UI

### To Add

**Rich progress bars:**

```python
from rich.progress import Progress

with Progress() as progress:
    task = progress.add_task("Generating...", total=13)
    for stage in stages:
        await run_stage(stage)
        progress.advance(task)
```

**Interactive profile creation:**

```python
from rich.prompt import Prompt

def create_profile_interactive():
    title = Prompt.ask("Book title")
    author = Prompt.ask("Author name")
    book_type = Prompt.ask("Book type", choices=["textbook", "business", "memoir"])
    # ... etc
```

**Effort:** 2-3 hours  
**Value:** Low (nice to have)

---

## 6. Additional Style Packs (Low Priority)

### To Add

- **Journalistic:** News/magazine style
- **Technical:** API documentation style
- **Conversational:** Podcast/blog style
- **Scientific:** Research paper style

**Each style pack needs:**
- Style guidelines file
- Example prompts
- Metric adjustments

**Effort:** 1 hour per style pack  
**Value:** Low (4 existing packs cover most needs)

---

## 7. Advanced Features (Future)

### Web Interface
- Browser-based profile editor
- Real-time generation dashboard
- Visual dependency graph editor

### Collaboration
- Multi-author support
- Review and comment system
- Version control integration

### Publishing
- Direct upload to KDP
- EPUB validation
- ISBN generation support

**These are v2.0+ features**

---

## 🎯 PRIORITY RECOMMENDATIONS

### Do First (High Value, Low Effort)
1. **Use the system!** - Generate a real book
2. **Add test suite** - 4-6 hours for confidence

### Do If Needed (Medium Value)
3. **EPUB/PDF libs** - If you need those formats (1-2 hours)
4. **Performance caching** - If generating many books (3-4 hours)

### Do Eventually (Low Priority)
5. **CLI polish** - Nice to have (2-3 hours)
6. **Migration cleanup** - Organizational (30 mins)

### Don't Bother (Yet)
7. **Interactive features** - Wait for user demand
8. **Additional style packs** - 4 is enough
9. **Web interface** - Future version

---

## ✨ BOTTOM LINE

**The system is PRODUCTION-READY without any of these enhancements.**

The core functionality works:
- ✅ Generate books
- ✅ Enforce quality
- ✅ Export HTML
- ✅ Validate evidence
- ✅ Ensure accessibility

Everything else is polish, not prerequisites.

**START GENERATING BOOKS TODAY!** 🎉


