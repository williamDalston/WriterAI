# 💰 Power BI Book - Personal Learning Edition

**Profile:** `configs/powerbi_personal_learning.yaml`  
**Cost:** ~$3-5 (80% cheaper!)  
**Time:** 30-45 minutes (3x faster!)  
**Purpose:** Personal learning, no citations needed

---

## ✅ **What You Get (Still Valuable!)**

### **Keeps Everything Important:**
- ✅ **10 Chapters** on Power BI
- ✅ **50-60 Content Units** (concepts, tutorials, exercises)
- ✅ **Learning Objectives** per chapter
- ✅ **Dependency Graph** - Concepts in proper order (no forward references)
- ✅ **Step-by-Step Tutorials** - Learn by doing
- ✅ **Practice Exercises** - Reinforce learning
- ✅ **Case Studies** - Real-world examples
- ✅ **Tips & Warnings** - Practical advice
- ✅ **Glossary** - Power BI terminology
- ✅ **Clear Structure** - Easy to follow
- ✅ **Reading Level 9** - Accessible language
- ✅ **HTML Export** - Professional looking

### **Removes (For Cost Savings):**
- ❌ Citations (you don't need them for personal learning)
- ❌ Fact-checking stage (trust the LLM)
- ❌ Link validation (no links to check)
- ❌ Evidence attachment (skipped)
- ❌ EPUB/PDF export (HTML only)

---

## 💰 **Cost Breakdown**

**Personal Learning Edition:**

| Stage | Cost |
|-------|------|
| Outline Planning | ~$0.50 |
| Unit Generation (60 units) | ~$2.00 |
| Exercises (20 exercises) | ~$0.50 |
| Polish & Export | ~$0.50 |
| **TOTAL** | **~$3.50** |

**Compare to cited version:**
- With citations: ~$10-15
- Personal edition: **~$3-5**
- **Savings: $7-10** (70-80% cheaper!)

**Time savings:**
- With citations: 1-2 hours
- Personal edition: **30-45 minutes**
- **Saves: 45-75 minutes**

---

## 📚 **What Your Book Will Look Like**

### **Chapter Example**

```markdown
# Chapter 3: Data Modeling Fundamentals

## Learning Objectives
By the end of this chapter, you will be able to:
- Understand star schema and snowflake schema design
- Create relationships between tables
- Apply best practices for data modeling

## Introduction
Data modeling is the foundation of effective Power BI reports. In this 
chapter, you'll learn how to structure your data for optimal performance 
and usability. We'll cover schemas, relationships, and common patterns.

## Section 1: Understanding Schema Design

### Concept: Star Schema
A star schema is a dimensional model where a central fact table connects 
to dimension tables. Think of it like the hub of a wheel with spokes 
reaching out to each dimension.

**Why it matters:** Star schemas are the recommended approach for Power BI 
because they're simple, fast, and easy to understand.

**Example:**
- Fact Table: Sales (SalesAmount, Quantity, Date, ProductID, StoreID)
- Dimensions: Products, Stores, Calendar

💡 **Tip:** Keep your fact table focused on measurable events (sales, 
clicks, transactions) and your dimensions on descriptive attributes 
(product names, locations, dates).

### Step-by-Step: Create Your First Data Model

1. Load your data tables into Power BI Desktop
2. Go to Model view (left sidebar)
3. Drag relationships between tables
4. Set cardinality (one-to-many, many-to-one)
5. Verify relationship direction
6. Test with a simple visual

[SCREENSHOT: Model view showing tables and relationships]

**Common Mistakes:**
- Creating circular relationships (breaks the model)
- Wrong cardinality direction
- Missing primary keys

### Exercise: Design a Sales Data Model

**Prompt:** You have three tables: Sales, Products, and Stores. Design a 
star schema model with proper relationships.

**Hints:**
- Which table is the fact table?
- What should be the dimension tables?
- What columns create relationships?

**Solution:** [Included at end of chapter]

## Chapter Summary
In this chapter, you learned about data modeling in Power BI. Star schemas 
provide optimal performance and clarity. Relationships connect your data 
into a coherent model. Practice these concepts with the exercises to 
solidify your understanding.
```

**See? Still valuable without citations!** The learning structure, exercises, and clear explanations are what help you learn.

---

## ⚖️ **Personal Learning vs Professional**

### **For Personal Learning (You!):**
```yaml
# powerbi_personal_learning.yaml ← Use this!
citation_coverage: 0.0
budget_usd: 10.0
deliverables: [html]
```

**Cost: ~$3-5**  
**Perfect for:** Learning Power BI on your own

### **For Professional/Publishing (Later):**
```yaml
# textbook_powerbi.yaml ← Use this when ready
citation_coverage: 0.95
budget_usd: 150.0
deliverables: [html, epub, pdf]
```

**Cost: ~$10-15**  
**Perfect for:** Selling, corporate training, publishing

**You can always regenerate WITH citations later if needed!**

---

## 🚀 **Generate Your Personal Learning Book**

**Use the new cost-optimized profile:**

```bash
# Set API key
export OPENAI_API_KEY="your-key-here"

# Navigate
cd "/Users/williamalston/Desktop/WriterAI nonfiction/prometheus_novel"

# GENERATE! (Personal learning edition - fast & cheap)
python run_anbg.py --profile configs/powerbi_personal_learning.yaml
```

---

## ⏱️ **What to Expect**

### **Generation Time: 30-45 minutes**

```
STAGE 1: PREFLIGHT ✅ (1 min)
STAGE 3: OUTLINE PLANNER ✅ (5 min)
STAGE 4: UNIT GENERATOR ✅ (15-20 min)
STAGE 5-6: EVIDENCE (SKIPPED - no citations) ⏭️
STAGE 7: EXERCISES ✅ (5 min)
STAGE 8-11: POLISH ✅ (5 min)
STAGE 12: EXPORT ✅ (2 min)

✅ COMPLETE! Your book is ready!
```

### **Cost: $3-5**

Much cheaper because:
- No RAG queries for citations
- No fact-checking passes
- Faster generation = less LLM time
- Simpler export (HTML only)

---

## 📖 **Your Output**

```
data/powerbi_personal/exports/html/powerbi_personal.html
```

**Contains:**
- 10 chapters on Power BI
- Data modeling, DAX, visualizations
- Step-by-step tutorials
- Practice exercises with solutions
- Tips and warnings
- Clear explanations
- Proper learning progression (dependency graph still works!)
- Glossary of terms

**Missing (intentionally):**
- Citations/references
- Fact-checking validation
- EPUB/PDF (HTML only)

**Perfect for learning on your own!**

---

## 🎯 **COMMAND TO RUN**

```bash
export OPENAI_API_KEY="your-openai-key"
cd "/Users/williamalston/Desktop/WriterAI nonfiction/prometheus_novel"
python run_anbg.py --profile configs/powerbi_personal_learning.yaml
```

**Cost: ~$3-5**  
**Time: ~40 minutes**  
**Output: Complete Power BI learning guide (HTML)**

---

## 💡 **Pro Tip**

**Generate the personal edition now** (~$4) to learn from.

**Later, if you want to publish/share**, regenerate with full citations:
```bash
python run_anbg.py --profile configs/textbook_powerbi.yaml
```

**This way you can:**
1. Learn from the $4 version
2. Decide if you like the content
3. Only pay $10-15 for cited version if you want to publish

---

**Ready to generate your $3-5 personal learning edition?** 📚✨


