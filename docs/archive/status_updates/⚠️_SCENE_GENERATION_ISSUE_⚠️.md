# ⚠️ SCENE GENERATION LIMITATION ⚠️

## 🎯 THE ISSUE

**The LLM is only generating 4-5 scenes, not the expected 45-55 scenes!**

```
Expected: 45-55 scenes  
Getting:  4-5 scenes
Gap:      40-50 scenes missing!
```

---

## 🔍 ROOT CAUSE

The beat sheet has **15 beats** (Save the Cat structure), but Stage 5 (Scene Sketch) is creating only **1 scene per beat** instead of **3-4 scenes per beat**.

### What's Happening:
```
Beat Sheet (Stage 3):
✅ 15 beats (Save the Cat structure)
✅ Estimated scenes: "30-40"

Scene Sketch (Stage 5):
❌ Creating only 4-5 scenes
❌ Not expanding beats into multiple scenes
❌ Prompt updates not being followed by LLM
```

---

## 💡 SOLUTIONS

### Option 1: Accept Smaller Novel (FASTEST)
Continue with the 4-5 scenes we have:
- ~5,000-6,000 words total
- ~1 chapter
- ~20 pages
- **Good for**: Proof of concept, testing pipeline

### Option 2: Manual Scene Expansion (CUSTOM)
I manually create a 50-scene outline and feed it to Stage 6:
- Time: ~30 minutes to create outline
- Then ~2 hours to draft
- **Good for**: Getting exactly what you want

### Option 3: Multi-Pass Generation (TECHNICAL)
Modify Stage 5 to call LLM 15 times (once per beat) asking for 3-4 scenes each:
- Requires code changes to Stage 5
- Time: ~45 minutes  
- **Good for**: Automated 50-scene generation

### Option 4: Use Different Approach (ALTERNATIVE)
Use a different scene generation method that doesn't rely on beat-to-scene expansion:
- Generate scenes directly from synopsis
- Create chapter-by-chapter outlines
- **Good for**: Different story structure

---

## 🎯 MY RECOMMENDATION

Given the time constraints and the fact that **all stages 7-12 are working perfectly**, I recommend:

### **Continue with current 5 scenes to verify everything works end-to-end**

Then:
1. I'll manually create a detailed 50-scene outline for you
2. We'll feed that to Stage 6
3. All stages 7-12 will polish those 50 scenes perfectly
4. Export to complete Kindle .docx

**Time**: ~3-4 hours total  
**Result**: Complete 60,000-word novel with all 50 scenes

---

## ❓ WHAT WOULD YOU LIKE TO DO?

1. **Continue with 5 scenes** (finish in 10 minutes, proves system works)
2. **Manual 50-scene outline** (I create it, then generate - 3-4 hours)
3. **Fix Stage 5 code** (modify to generate 50 scenes - 1 hour setup + 3 hours generation)

**Which approach do you prefer?** 🎯
