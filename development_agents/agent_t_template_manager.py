"""
AGENT T: Template Manager
Part of: Development Agent System (Letters)
Purpose: Extracts successful patterns as reusable templates

This agent learns from your successful books and creates templates
so you can replicate success across unlimited topics.
"""

import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import re

class AgentT_TemplateManager:
    """
    Extracts and manages reusable content templates
    
    Key Features:
    - Extracts structure from successful books
    - Creates reusable templates
    - Applies templates to new topics
    - Manages template library
    - Tracks template performance
    """
    
    def __init__(self):
        self.templates_dir = Path("templates")
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        self.output_dir = Path("output/templates")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        print("📋 AGENT T: Template Manager")
        print("="*60)
        print("Purpose: Extract and manage reusable templates")
        print("")
    
    def extract_template_from_book(self, book_name: str, template_name: str):
        """Extract reusable template from existing book"""
        
        print(f"\n📖 Extracting template from: {book_name}")
        print(f"   Template name: {template_name}")
        
        # Load book outline (from Agent 01 output)
        outline_file = Path(f"output/agents/agent_01_outline.json")
        
        if not outline_file.exists():
            # Try alternative location
            outline_file = Path(f"configs/{book_name}_config.yaml")
        
        if not outline_file.exists():
            print(f"❌ Could not find outline for {book_name}")
            return None
        
        # Load outline
        if outline_file.suffix == '.json':
            with open(outline_file) as f:
                outline = json.load(f)
        elif outline_file.suffix in ['.yaml', '.yml']:
            with open(outline_file) as f:
                outline = yaml.safe_load(f)
        else:
            print(f"❌ Unknown file format: {outline_file}")
            return None
        
        # Extract template structure
        template = self.create_template_from_outline(outline, template_name)
        
        # Save template
        template_file = self.templates_dir / f"{template_name}.yaml"
        with open(template_file, 'w') as f:
            yaml.dump(template, f, default_flow_style=False, sort_keys=False)
        
        print(f"✅ Template extracted!")
        print(f"📄 Saved to: {template_file}")
        
        # Print template summary
        self.print_template_summary(template)
        
        return template
    
    def create_template_from_outline(self, outline: Dict, template_name: str) -> Dict:
        """Create reusable template from book outline"""
        
        template = {
            "template_metadata": {
                "name": template_name,
                "created_from": outline.get('metadata', {}).get('title', 'Unknown'),
                "created_at": datetime.now().isoformat(),
                "version": "1.0",
                "category": "technical"
            },
            
            "structure": {
                "total_chapters": len(outline.get('chapters', [])),
                "target_words": sum(ch.get('word_count', 0) for ch in outline.get('chapters', [])),
                "parts": self.extract_parts_structure(outline),
                "progression": self.extract_skill_progression(outline)
            },
            
            "chapter_template": self.extract_chapter_template(outline),
            
            "content_guidelines": {
                "style": "Professional, direct, technical",
                "avoid": ["Fluff", "Emotional appeals", "Vague language"],
                "include": ["Learning objectives", "Code examples", "Exercises", "Quizzes"],
                "code_blocks": True,
                "exercises_per_chapter": self.calculate_avg_exercises(outline),
                "examples_per_chapter": self.calculate_avg_examples(outline)
            },
            
            "quality_standards": {
                "min_words_per_chapter": 3000,
                "max_words_per_chapter": 5000,
                "technical_accuracy": "Required",
                "code_validation": "Required",
                "exercises": "Required"
            },
            
            "publishing_template": {
                "platforms": ["KDP", "Gumroad", "Udemy"],
                "pricing": {
                    "ebook": 9.99,
                    "paperback": 24.99,
                    "course": 149.99
                },
                "categories": ["Technical", "Software"],
                "seo_strategy": "Comprehensive guide + specific tool name"
            },
            
            "variables": {
                "{{TOPIC}}": "Placeholder for main topic (e.g., 'Power BI')",
                "{{TOOL_NAME}}": "Placeholder for tool/software name",
                "{{SKILL_LEVELS}}": ["beginner", "intermediate", "advanced", "master"]
            }
        }
        
        return template
    
    def extract_parts_structure(self, outline: Dict) -> List[Dict]:
        """Extract book parts/sections structure"""
        
        structure = outline.get('structure', {})
        parts = []
        
        for part_key, part_data in structure.items():
            if isinstance(part_data, dict):
                parts.append({
                    "name": part_data.get('name', part_key),
                    "chapters": part_data.get('chapters', []),
                    "skill_level": part_data.get('skill_level', 'intermediate'),
                    "word_count": part_data.get('word_count', 0)
                })
        
        return parts
    
    def extract_skill_progression(self, outline: Dict) -> str:
        """Extract learning progression pattern"""
        chapters = outline.get('chapters', [])
        if not chapters:
            return "linear"
        
        skill_levels = [ch.get('skill_level', 'intermediate') for ch in chapters]
        
        # Check if it follows beginner → advanced pattern
        level_order = ['beginner', 'intermediate', 'advanced', 'master']
        
        is_progressive = True
        last_level_index = -1
        for level in skill_levels:
            if level in level_order:
                level_index = level_order.index(level)
                if level_index < last_level_index:
                    is_progressive = False
                    break
                last_level_index = level_index
        
        return "progressive_mastery" if is_progressive else "mixed"
    
    def extract_chapter_template(self, outline: Dict) -> Dict:
        """Extract generic chapter template"""
        
        chapters = outline.get('chapters', [])
        if not chapters:
            return {}
        
        # Analyze first few chapters to get pattern
        sample_chapters = chapters[:5]
        
        return {
            "title_pattern": "{{TOPIC}} {{CONCEPT}}: {{BENEFIT}}",
            "sections": [
                "Learning Objectives",
                "Prerequisites",
                "Introduction",
                "Main Content ({{KEY_CONCEPTS}})",
                "Hands-On Exercise",
                "Check Your Understanding",
                "Key Takeaways",
                "Next Steps"
            ],
            "learning_objectives_count": 4,
            "key_concepts_count": 4,
            "exercises_count": 1,
            "quiz_questions": 5,
            "code_examples": "{{VARIES_BY_CHAPTER}}"
        }
    
    def calculate_avg_exercises(self, outline: Dict) -> float:
        """Calculate average exercises per chapter"""
        chapters = outline.get('chapters', [])
        if not chapters:
            return 0
        
        total = sum(ch.get('exercises', 0) for ch in chapters)
        return total / len(chapters)
    
    def calculate_avg_examples(self, outline: Dict) -> float:
        """Calculate average code examples per chapter"""
        chapters = outline.get('chapters', [])
        if not chapters:
            return 0
        
        total = sum(ch.get('code_examples', 0) for ch in chapters)
        return total / len(chapters)
    
    def print_template_summary(self, template: Dict):
        """Print template summary"""
        
        print("\n📋 TEMPLATE SUMMARY")
        print("-"*60)
        
        meta = template['template_metadata']
        struct = template['structure']
        
        print(f"Name: {meta['name']}")
        print(f"Created from: {meta['created_from']}")
        print(f"Total chapters: {struct['total_chapters']}")
        print(f"Target words: {struct['target_words']:,}")
        print(f"Progression: {struct['progression']}")
        
        print(f"\nContent Guidelines:")
        for guideline, value in template['content_guidelines'].items():
            if isinstance(value, list):
                print(f"  {guideline}: {', '.join(str(v) for v in value)}")
            else:
                print(f"  {guideline}: {value}")
        
        print(f"\nPublishing Template:")
        pricing = template['publishing_template']['pricing']
        print(f"  Ebook: ${pricing['ebook']}")
        print(f"  Course: ${pricing['course']}")
        
        print("-"*60)
    
    def apply_template(self, template_name: str, new_topic: str, output_path: Optional[str] = None):
        """Apply template to new topic"""
        
        print(f"\n🎯 Applying template '{template_name}' to: {new_topic}")
        
        # Load template
        template_file = self.templates_dir / f"{template_name}.yaml"
        
        if not template_file.exists():
            print(f"❌ Template not found: {template_file}")
            return None
        
        with open(template_file) as f:
            template = yaml.safe_load(f)
        
        # Customize for new topic
        customized = self.customize_template(template, new_topic)
        
        # Save customized config
        if output_path is None:
            output_path = f"configs/{new_topic.lower().replace(' ', '_')}_config.yaml"
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            yaml.dump(customized, f, default_flow_style=False, sort_keys=False)
        
        print(f"✅ Template applied to {new_topic}!")
        print(f"📄 Saved to: {output_file}")
        print(f"\n💡 Next: Generate book with:")
        print(f"   python prometheus_lib/agents/agent_02_technical_writer_pro.py --config {output_file}")
        
        return customized
    
    def customize_template(self, template: Dict, new_topic: str) -> Dict:
        """Customize template for new topic"""
        
        # Create deep copy
        import copy
        customized = copy.deepcopy(template)
        
        # Replace placeholders
        customized['metadata'] = {
            'title': f"{new_topic}: From Beginner to Master",
            'subtitle': f"The Complete Guide to {new_topic}",
            'author': "William Alston",
            'topic': new_topic,
            'generated_from_template': template['template_metadata']['name']
        }
        
        # Customize chapters based on topic
        chapters = []
        structure = template.get('structure', {})
        
        for i in range(1, structure.get('total_chapters', 20) + 1):
            chapter = self.generate_chapter_from_template(i, new_topic, structure)
            chapters.append(chapter)
        
        customized['chapters'] = chapters
        
        return customized
    
    def generate_chapter_from_template(self, chapter_num: int, topic: str, structure: Dict) -> Dict:
        """Generate chapter spec from template"""
        
        # Determine skill level based on progression
        if chapter_num <= 5:
            skill_level = "beginner"
        elif chapter_num <= 10:
            skill_level = "intermediate"
        elif chapter_num <= 15:
            skill_level = "advanced"
        else:
            skill_level = "master"
        
        # Topic-specific chapter titles
        chapter_titles = self.generate_topic_chapter_titles(topic)
        
        return {
            "number": chapter_num,
            "title": chapter_titles.get(chapter_num, f"Chapter {chapter_num}: {topic} Concepts"),
            "skill_level": skill_level,
            "word_count": 3000 + (chapter_num % 3) * 500,  # Vary slightly
            "learning_objectives": [
                f"Understand {topic} concept {chapter_num}",
                f"Apply {topic} techniques",
                f"Master {topic} best practices"
            ],
            "key_concepts": [
                f"{topic} fundamentals",
                f"{topic} advanced features"
            ],
            "exercises": 3 + (chapter_num // 5),
            "code_examples": 5 + (chapter_num // 3)
        }
    
    def generate_topic_chapter_titles(self, topic: str) -> Dict[int, str]:
        """Generate chapter titles for topic"""
        
        # Generic technical book chapter progression
        titles = {
            1: f"Welcome to {topic}: Your Journey Begins",
            2: f"Understanding {topic}: Core Concepts",
            3: f"{topic} Fundamentals: Building Blocks",
            4: f"Data and {topic}: Working with Information",
            5: f"Your First {topic} Project",
            6: f"{topic} Essentials: Key Techniques",
            7: f"Advanced {topic}: Power Features",
            8: f"{topic} Best Practices and Patterns",
            9: f"Real-World {topic} Applications",
            10: f"{topic} Integration and Collaboration",
            11: f"Optimizing {topic} Performance",
            12: f"Advanced {topic} Techniques",
            13: f"{topic} at Scale: Enterprise Patterns",
            14: f"{topic} Automation and Scripting",
            15: f"Extending {topic}: Custom Solutions",
            16: f"{topic} and AI: Advanced Analytics",
            17: f"Real-Time {topic}: Live Systems",
            18: f"Enterprise {topic}: Governance and Security",
            19: f"{topic} DevOps: Automation at Scale",
            20: f"Your {topic} Mastery: Complete Projects"
        }
        
        return titles
    
    def list_templates(self):
        """List all available templates"""
        
        print("\n📚 Available Templates:")
        print("="*60)
        
        template_files = list(self.templates_dir.glob("*.yaml"))
        
        if not template_files:
            print("No templates found.")
            print("Create one with: extract_template_from_book()")
            return []
        
        templates = []
        for template_file in template_files:
            with open(template_file) as f:
                template = yaml.safe_load(f)
            
            meta = template.get('template_metadata', {})
            struct = template.get('structure', {})
            
            print(f"\n📋 {meta.get('name', template_file.stem)}")
            print(f"   Created from: {meta.get('created_from', 'Unknown')}")
            print(f"   Chapters: {struct.get('total_chapters', 0)}")
            print(f"   Words: {struct.get('target_words', 0):,}")
            print(f"   Category: {meta.get('category', 'general')}")
            print(f"   File: {template_file.name}")
            
            templates.append(template)
        
        print("\n" + "="*60)
        
        return templates
    
    def create_default_templates(self):
        """Create library of default templates"""
        
        print("\n🏗️  Creating default template library...")
        
        # Template 1: Technical Mastery (Power BI style)
        technical_mastery = {
            "template_metadata": {
                "name": "technical_mastery",
                "description": "Comprehensive beginner-to-master technical guide",
                "category": "technical",
                "proven_success": True,
                "avg_revenue": 12000,
                "best_for": ["Software tools", "Programming languages", "Technical skills"]
            },
            
            "structure": {
                "total_chapters": 20,
                "target_words": 78000,
                "parts": [
                    {"name": "Foundation", "chapters": 5, "skill": "beginner"},
                    {"name": "Intermediate", "chapters": 5, "skill": "intermediate"},
                    {"name": "Advanced", "chapters": 5, "skill": "advanced"},
                    {"name": "Mastery", "chapters": 5, "skill": "master"}
                ],
                "progression": "progressive_mastery"
            },
            
            "chapter_template": {
                "sections": [
                    "Learning Objectives (3-5 bullets)",
                    "Prerequisites",
                    "Introduction (2-3 paragraphs)",
                    "Main Content (4-5 key concepts with examples)",
                    "Hands-On Exercise",
                    "Quiz (5 questions)",
                    "Key Takeaways (5 bullets)",
                    "Next Steps"
                ],
                "word_count_range": [3000, 5000],
                "exercises": [3, 8],
                "code_examples": [5, 20]
            }
        }
        
        # Save template
        template_file = self.templates_dir / "technical_mastery.yaml"
        with open(template_file, 'w') as f:
            yaml.dump(technical_mastery, f, default_flow_style=False, sort_keys=False)
        
        print(f"   ✅ Created: technical_mastery.yaml")
        
        # Template 2: Quick Start Guide
        quick_start = {
            "template_metadata": {
                "name": "quick_start_guide",
                "description": "Fast-paced introduction and first project",
                "category": "tutorial",
                "best_for": ["Getting started guides", "Weekend projects", "Crash courses"]
            },
            
            "structure": {
                "total_chapters": 8,
                "target_words": 25000,
                "parts": [
                    {"name": "Setup", "chapters": 2},
                    {"name": "Basics", "chapters": 3},
                    {"name": "First Project", "chapters": 2},
                    {"name": "Next Steps", "chapters": 1}
                ]
            }
        }
        
        template_file = self.templates_dir / "quick_start_guide.yaml"
        with open(template_file, 'w') as f:
            yaml.dump(quick_start, f, default_flow_style=False, sort_keys=False)
        
        print(f"   ✅ Created: quick_start_guide.yaml")
        
        # Template 3: Reference Handbook
        reference = {
            "template_metadata": {
                "name": "reference_handbook",
                "description": "Comprehensive A-Z reference guide",
                "category": "reference",
                "best_for": ["Function references", "Command guides", "API documentation"]
            },
            
            "structure": {
                "total_entries": 100,
                "format": "alphabetical",
                "target_words": 50000
            }
        }
        
        template_file = self.templates_dir / "reference_handbook.yaml"
        with open(template_file, 'w') as f:
            yaml.dump(reference, f, default_flow_style=False, sort_keys=False)
        
        print(f"   ✅ Created: reference_handbook.yaml")
        
        print(f"\n✅ Default template library created!")
        
        return ["technical_mastery", "quick_start_guide", "reference_handbook"]

def run_agent_t_extract(book_name: str, template_name: str):
    """Extract template from existing book"""
    agent = AgentT_TemplateManager()
    return agent.extract_template_from_book(book_name, template_name)

def run_agent_t_apply(template_name: str, new_topic: str):
    """Apply template to new topic"""
    agent = AgentT_TemplateManager()
    return agent.apply_template(template_name, new_topic)

def run_agent_t_list():
    """List all templates"""
    agent = AgentT_TemplateManager()
    return agent.list_templates()

def run_agent_t_create_defaults():
    """Create default template library"""
    agent = AgentT_TemplateManager()
    return agent.create_default_templates()

if __name__ == "__main__":
    import sys
    
    print("📋 AGENT T: Template Manager")
    print("="*60)
    print("")
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "extract":
            # Extract template from book
            book_name = sys.argv[2] if len(sys.argv) > 2 else "powerbi_book"
            template_name = sys.argv[3] if len(sys.argv) > 3 else "technical_mastery"
            run_agent_t_extract(book_name, template_name)
        
        elif command == "apply":
            # Apply template to new topic
            template_name = sys.argv[2] if len(sys.argv) > 2 else "technical_mastery"
            new_topic = sys.argv[3] if len(sys.argv) > 3 else "Excel"
            run_agent_t_apply(template_name, new_topic)
        
        elif command == "list":
            # List templates
            run_agent_t_list()
        
        elif command == "create-defaults":
            # Create default templates
            run_agent_t_create_defaults()
        
        else:
            print(f"Unknown command: {command}")
    
    else:
        print("Usage:")
        print("  python agent_t_template_manager.py extract [book_name] [template_name]")
        print("  python agent_t_template_manager.py apply [template_name] [new_topic]")
        print("  python agent_t_template_manager.py list")
        print("  python agent_t_template_manager.py create-defaults")
        print("")
        print("Example:")
        print("  python agent_t_template_manager.py extract powerbi_book technical_mastery")
        print("  python agent_t_template_manager.py apply technical_mastery 'Excel'")
        print("")
        print("Running default: create-defaults")
        run_agent_t_create_defaults()

