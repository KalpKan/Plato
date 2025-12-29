# Deployment Guide: Supabase + Vercel

## Supabase + Vercel Compatibility

### ✅ Yes, They Work Together!

**Supabase + Vercel** is a popular and well-supported combination:

- **Supabase**: PostgreSQL database with built-in auth, storage, and real-time features
- **Vercel**: Excellent for deploying web applications (works with Flask, but better with Next.js/React)

### Current Stack Considerations

**Your current stack:**
- Flask (Python web framework)
- SQLite for caching (local)

**For Supabase + Vercel:**
- ✅ Supabase works great with Flask (via `supabase-py` client)
- ⚠️ Vercel can deploy Flask, but it's **not ideal** (better for Node.js/Next.js)
- ✅ You can migrate SQLite cache to Supabase PostgreSQL

---

## Recommended Approach

### Option 1: Supabase + Vercel (with Next.js) ⭐ **RECOMMENDED**

**Why:** Vercel is optimized for Next.js/React, and Supabase has excellent Next.js support.

**Migration Path:**
1. Keep Flask backend as API (or convert to Next.js API routes)
2. Build frontend in Next.js/React
3. Use Supabase for:
   - Database (replace SQLite cache)
   - File storage (for PDFs)
   - Authentication (if needed later)

**Pros:**
- Best performance on Vercel
- Excellent Supabase integration
- Modern stack
- Great developer experience

**Cons:**
- Need to learn Next.js/React (if not familiar)
- Some refactoring required

### Option 2: Supabase + Railway/Render (Keep Flask) ⭐ **EASIEST**

**Why:** Railway and Render are optimized for Flask/Python apps.

**Migration Path:**
1. Keep Flask backend as-is
2. Deploy to Railway or Render
3. Use Supabase for database
4. Keep current Python code mostly unchanged

**Pros:**
- Minimal changes to existing code
- Easy Flask deployment
- Supabase works great with Flask
- Fastest to deploy

**Cons:**
- Not using Vercel (but Railway/Render are also excellent)

### Option 3: Supabase + Vercel (with Flask) ⚠️ **POSSIBLE BUT NOT IDEAL**

**Why:** Vercel can deploy Flask, but it's not their specialty.

**Migration Path:**
1. Keep Flask backend
2. Use Vercel's Python runtime
3. Use Supabase for database

**Pros:**
- Use Vercel as planned
- Keep Flask code

**Cons:**
- Slower cold starts
- Less optimized than Next.js
- More configuration needed

---

## Easiest Alternative: Railway + Supabase

**Recommended for fastest deployment:**

1. **Railway** (https://railway.app)
   - One-click Flask deployment
   - Free tier available
   - Automatic HTTPS
   - Easy database setup

2. **Supabase** (https://supabase.com)
   - PostgreSQL database
   - Free tier: 500MB database
   - Built-in auth (if needed)
   - File storage (for PDFs)

**Why Railway:**
- Deploy Flask in minutes
- No configuration needed
- Better than Vercel for Python apps
- Free tier is generous

---

## Testing Current Functionality

Since the web interface isn't built yet, you can test using the **CLI interface** that already exists.

### Quick Test Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Test PDF extraction:**
   ```bash
   python -m src.main "BMSUE Syllabus Phys3140A Fall 2025 Sept3.pdf"
   ```

3. **Test with output directory:**
   ```bash
   python -m src.main "BMSUE Syllabus Phys3140A Fall 2025 Sept3.pdf" --output-dir ./output
   ```

4. **Test without cache:**
   ```bash
   python -m src.main "BMSUE Syllabus Phys3140A Fall 2025 Sept3.pdf" --no-cache
   ```

### What Gets Tested

- ✅ PDF text extraction
- ✅ Term detection
- ✅ Section extraction (lectures/labs)
- ✅ Assessment extraction
- ✅ Rule resolution
- ✅ Study plan generation
- ✅ iCalendar file generation
- ⚠️ Caching (has schema issues, may fail)

### Expected Output

The CLI will:
1. Extract data from PDF
2. Prompt you for section selection (if multiple found)
3. Review assessments (if ambiguous)
4. Generate `.ics` file
5. Save JSON extraction data

---

## Migration to Supabase

### Step 1: Set Up Supabase

1. Create account at https://supabase.com
2. Create new project
3. Get connection string from Settings → Database

### Step 2: Update Cache System

Replace SQLite with Supabase:

```python
# Install supabase client
pip install supabase

# Update src/cache.py to use Supabase instead of SQLite
```

### Step 3: Database Schema

Create tables in Supabase:

```sql
-- Extraction cache table
CREATE TABLE extraction_cache (
    pdf_hash TEXT PRIMARY KEY,
    extracted_json JSONB NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- User choices table
CREATE TABLE user_choices (
    id BIGSERIAL PRIMARY KEY,
    pdf_hash TEXT NOT NULL,
    session_id TEXT,
    selected_lecture_section_json JSONB,
    selected_lab_section_json JSONB,
    lead_time_overrides_json JSONB,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## Deployment Options Comparison

| Platform | Flask Support | Ease of Use | Free Tier | Best For |
|----------|--------------|-------------|-----------|----------|
| **Railway** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ Generous | Flask apps |
| **Render** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ Good | Flask apps |
| **Vercel** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ Good | Next.js apps |
| **Fly.io** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ✅ Good | Flask apps |
| **Heroku** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ❌ Paid | Flask apps |

---

## Recommended Next Steps

1. **Test current functionality** using CLI (see above)
2. **Choose deployment platform:**
   - If you want Vercel: Consider Next.js frontend
   - If you want easiest: Use Railway + Supabase
3. **Set up Supabase** for database
4. **Update cache.py** to use Supabase
5. **Build web interface
6. **Deploy**

---

## Quick Start: Test CLI Now

```bash
# Make sure you're in the project directory
cd /Users/kalp/Desktop/Plato

# Install dependencies
pip install -r requirements.txt

# Test with your PDF
python -m src.main "BMSUE Syllabus Phys3140A Fall 2025 Sept3.pdf"
```

This will test all the core functionality that's already built!

