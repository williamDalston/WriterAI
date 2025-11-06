"""
AGENT B: Batch Content Factory
Part of: Development Agent System (Letters)
Purpose: Generates multiple books/products in parallel

The SCALING agent - turns 1 book/week into 10 books/week
"""

import asyncio
import json
import yaml
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict
import sys

# Add project to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "prometheus_novel"))

class AgentB_BatchFactory:
    """
    Batch content generation system
    
    Key Features:
    - Parallel book generation (10+ simultaneously)
    - Template-based rapid creation
    - Queue management
    - Progress tracking
    - Resource optimization
    """
    
    def __init__(self, max_parallel: int = 4):
        self.max_parallel = max_parallel
        self.output_dir = Path("output/batch_factory")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.queue = []
        self.in_progress = []
        self.completed = []
        self.failed = []
        
        print("🏭 AGENT B: Batch Content Factory")
        print("="*60)
        print(f"Max parallel generation: {max_parallel}")
        print("")
    
    async def generate_books_from_template(
        self,
        template_name: str,
        topics: List[str],
        parallel: int = None
    ):
        """Generate multiple books in parallel using template"""
        
        parallel = parallel or self.max_parallel
        
        print(f"\n🚀 Batch generating {len(topics)} books")
        print(f"   Template: {template_name}")
        print(f"   Parallel: {parallel}")
        print(f"   Topics: {', '.join(topics)}")
        print("")
        
        # Load template
        from development_agents.agent_t_template_manager import AgentT_TemplateManager
        template_mgr = AgentT_TemplateManager()
        
        # Apply template to each topic
        print("📋 Applying templates...")
        configs = []
        for topic in topics:
            print(f"   Configuring: {topic}")
            config_path = f"configs/{topic.lower().replace(' ', '_')}_batch.yaml"
            config = template_mgr.apply_template(template_name, topic, config_path)
            if config:
                configs.append({
                    "topic": topic,
                    "config_path": config_path,
                    "config": config
                })
        
        print(f"\n✅ Configured {len(configs)} books")
        
        # Generate books in parallel batches
        print(f"\n🏭 Starting batch generation...")
        
        results = []
        for i in range(0, len(configs), parallel):
            batch = configs[i:i+parallel]
            
            print(f"\n📦 Batch {i//parallel + 1}: Generating {len(batch)} books in parallel...")
            
            # Create tasks for parallel execution
            tasks = [
                self.generate_single_book(config['topic'], config['config_path'])
                for config in batch
            ]
            
            # Execute in parallel
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for config, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    print(f"   ❌ {config['topic']}: {result}")
                    self.failed.append(config['topic'])
                else:
                    print(f"   ✅ {config['topic']}: {result['total_words']} words")
                    self.completed.append(result)
                    results.append(result)
            
            # Brief pause between batches
            if i + parallel < len(configs):
                print(f"\n⏸️  Pausing 30 seconds before next batch...")
                await asyncio.sleep(30)
        
        # Generate batch report
        self.generate_batch_report(results)
        
        return results
    
    async def generate_single_book(self, topic: str, config_path: str):
        """Generate a single book"""
        
        print(f"\n   📖 Generating: {topic}")
        
        try:
            # Use Agent 02 to generate all chapters
            from prometheus_lib.agents.agent_02_technical_writer_pro import Agent02TechnicalWriterPro
            
            writer = Agent02TechnicalWriterPro(config_path)
            
            # Generate all chapters
            results = await writer.write_all_chapters()
            
            total_words = sum(r['word_count'] for r in results if r)
            
            return {
                "topic": topic,
                "status": "completed",
                "chapters": len(results),
                "total_words": total_words,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"   ❌ Error generating {topic}: {e}")
            raise
    
    def generate_batch_report(self, results: List[Dict]):
        """Generate comprehensive batch report"""
        
        print("\n" + "="*60)
        print("📊 BATCH GENERATION REPORT")
        print("="*60)
        
        total_books = len(results)
        total_chapters = sum(r.get('chapters', 0) for r in results)
        total_words = sum(r.get('total_words', 0) for r in results)
        
        print(f"\n✅ Completed: {total_books} books")
        print(f"📖 Total chapters: {total_chapters}")
        print(f"📝 Total words: {total_words:,}")
        print(f"❌ Failed: {len(self.failed)}")
        
        if self.failed:
            print(f"\n❌ Failed books:")
            for topic in self.failed:
                print(f"   • {topic}")
        
        print(f"\n📚 Generated books:")
        for result in results:
            print(f"   • {result['topic']}: {result['total_words']:,} words")
        
        # Estimate revenue
        estimated_revenue = self.estimate_batch_revenue(results)
        print(f"\n💰 Estimated Annual Revenue: ${estimated_revenue:,}")
        
        # Save report
        report_file = self.output_dir / f"batch_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                "generated_at": datetime.now().isoformat(),
                "total_books": total_books,
                "total_chapters": total_chapters,
                "total_words": total_words,
                "failed": self.failed,
                "results": results,
                "estimated_revenue": estimated_revenue
            }, f, indent=2)
        
        print(f"\n📄 Report saved: {report_file}")
        print("="*60)
    
    def estimate_batch_revenue(self, results: List[Dict]) -> int:
        """Estimate total revenue from batch"""
        
        # Conservative: $350/month per book
        monthly_per_book = 350
        books = len(results)
        
        return books * monthly_per_book * 12
    
    async def generate_content_series(
        self,
        main_topic: str,
        template: str = "technical_mastery"
    ):
        """Generate complete content series for a main topic"""
        
        print(f"\n📚 Generating content series for: {main_topic}")
        
        # Define series structure
        series = {
            "Power BI": [
                "Power BI: Beginner to Master",  # Main book
                "Advanced DAX Programming",        # Advanced spinoff
                "Power BI Performance Tuning",     # Specialist book
                "Power BI for Excel Users",        # Beginner bridge
                "Enterprise Power BI Architecture" # Enterprise focus
            ],
            "Excel": [
                "Excel: Beginner to Master",
                "Advanced Excel Formulas",
                "Power Query Mastery",
                "Excel VBA Programming",
                "Excel for Data Analysis"
            ],
            "Python": [
                "Python: Beginner to Master",
                "Python for Data Science",
                "Python Web Development",
                "Advanced Python Patterns",
                "Python DevOps Tools"
            ]
        }
        
        topics = series.get(main_topic, [main_topic])
        
        print(f"   Series includes {len(topics)} books")
        for i, topic in enumerate(topics, 1):
            print(f"   {i}. {topic}")
        
        # Generate all books in series
        results = await self.generate_books_from_template(template, topics, parallel=2)
        
        print(f"\n✅ Complete series generated!")
        print(f"📚 {len(results)} books ready")
        print(f"💰 Estimated series revenue: ${len(results) * 12000:,}/year")
        
        return results

async def run_agent_b_batch(template: str, topics: List[str], parallel: int = 4):
    """Run batch generation"""
    agent = AgentB_BatchFactory(max_parallel=parallel)
    return await agent.generate_books_from_template(template, topics, parallel)

async def run_agent_b_series(main_topic: str):
    """Generate complete series"""
    agent = AgentB_BatchFactory()
    return await agent.generate_content_series(main_topic)

if __name__ == "__main__":
    import sys
    
    print("🏭 AGENT B: Batch Content Factory")
    print("="*60)
    print("")
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "batch":
            # Batch generate from topics
            template = sys.argv[2] if len(sys.argv) > 2 else "technical_mastery"
            topics = sys.argv[3:] if len(sys.argv) > 3 else ["Excel", "SQL"]
            
            print(f"Generating {len(topics)} books with template: {template}")
            asyncio.run(run_agent_b_batch(template, topics))
        
        elif command == "series":
            # Generate complete series
            main_topic = sys.argv[2] if len(sys.argv) > 2 else "Power BI"
            asyncio.run(run_agent_b_series(main_topic))
        
        else:
            print(f"Unknown command: {command}")
    
    else:
        print("Usage:")
        print("  python agent_b_batch_factory.py batch [template] [topic1] [topic2] ...")
        print("  python agent_b_batch_factory.py series [main_topic]")
        print("")
        print("Examples:")
        print("  python agent_b_batch_factory.py batch technical_mastery 'Excel' 'SQL' 'Python'")
        print("  python agent_b_batch_factory.py series 'Power BI'")
        print("")
        print("⚠️  Note: Requires Agent T templates and Agent 02 writer to be set up")
        print("")
        print("First, create templates with:")
        print("  python agent_t_template_manager.py create-defaults")

