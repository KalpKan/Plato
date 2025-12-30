# Railway + Supabase Setup Guide

This guide will help you deploy the application to Railway and set up Supabase for the database.

## Prerequisites

1. **Railway Account**: Sign up at https://railway.app
2. **Supabase Account**: Sign up at https://supabase.com
3. **GitHub Account**: (for GitHub integration)

---

## Part 1: Set Up Supabase

### Step 1: Create Supabase Project

1. Go to https://supabase.com and sign in
2. Click "New Project"
3. Fill in:
   - **Name**: `plato-course-converter` (or your choice)
   - **Database Password**: (save this securely!)
   - **Region**: Choose closest to you
4. Click "Create new project"
5. Wait 2-3 minutes for project to initialize

### Step 2: Get Connection Details

1. Go to **Settings** → **Database**
2. Find **Connection string** section
3. Copy the **URI** connection string (looks like: `postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres`)

<!-- Connection string removed for security - use environment variables instead -->

4. Also note:
   - **Host**: `db.[PROJECT].supabase.co`
   - **Database**: `postgres`
   - **Port**: `5432`
   - **User**: `postgres`
   - **Password**: (the one you set)

### Step 3: Create Database Tables

1. Go to **SQL Editor** in Supabase dashboard
2. Run this SQL to create the tables:

```sql
-- Extraction cache table (stores PDF extraction results)
CREATE TABLE IF NOT EXISTS extraction_cache (
    pdf_hash TEXT PRIMARY KEY,
    extracted_json JSONB NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- User choices table (stores user selections)
CREATE TABLE IF NOT EXISTS user_choices (
    id BIGSERIAL PRIMARY KEY,
    pdf_hash TEXT NOT NULL,
    session_id TEXT,
    selected_lecture_section_json JSONB,
    selected_lab_section_json JSONB,
    lead_time_overrides_json JSONB,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_user_choices_pdf_hash ON user_choices(pdf_hash);
CREATE INDEX IF NOT EXISTS idx_user_choices_session ON user_choices(session_id);
```

3. Click "Run" to execute

### Step 4: Enable Row Level Security (RLS)

**Important**: This is required for security. Supabase will warn you if RLS is disabled.

1. In SQL Editor, run this to enable RLS:

```sql
-- Enable Row Level Security on both tables
ALTER TABLE extraction_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_choices ENABLE ROW LEVEL SECURITY;

-- Create policies to allow all operations (since this is a single-user app)
-- For production, you may want to restrict access based on authentication
CREATE POLICY "Allow all operations on extraction_cache" 
ON extraction_cache FOR ALL 
USING (true) 
WITH CHECK (true);

CREATE POLICY "Allow all operations on user_choices" 
ON user_choices FOR ALL 
USING (true) 
WITH CHECK (true);
```

2. Click "Run" to execute
3. Verify in Supabase dashboard → **Advisors** → **Security** that warnings are gone

### Step 4: Set Up Row Level Security (Optional but Recommended)

```sql
-- Enable RLS
ALTER TABLE extraction_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_choices ENABLE ROW LEVEL SECURITY;

-- Allow all operations (adjust based on your needs)
CREATE POLICY "Allow all operations on extraction_cache" 
ON extraction_cache FOR ALL 
USING (true) 
WITH CHECK (true);

CREATE POLICY "Allow all operations on user_choices" 
ON user_choices FOR ALL 
USING (true) 
WITH CHECK (true);
```

---

## Part 2: Update Code for Supabase

### Step 1: Install Supabase Client

Add to `requirements.txt`:

```txt
supabase>=2.0.0
psycopg2-binary>=2.9.0
```

### Step 2: Create Supabase Cache Manager

We'll create a new file `src/supabase_cache.py` that uses Supabase instead of SQLite.

### Step 3: Environment Variables

Create `.env` file (don't commit this!):

```env
SUPABASE_URL=https://[YOUR_PROJECT].supabase.co
SUPABASE_KEY=[YOUR_ANON_KEY]
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres
```

Add to `.gitignore`:
```
.env
```

---

## Part 3: Deploy to Railway

### Step 1: Prepare for Deployment

1. **Create `Procfile`** (for Railway):
```
web: python -m gunicorn src.app:app --bind 0.0.0.0:$PORT
```

2. **Update `requirements.txt`** to include:
```txt
gunicorn>=21.2.0
supabase>=2.0.0
psycopg2-binary>=2.9.0
```

3. **Create `runtime.txt`** (optional, specify Python version):
```
python-3.10.12
```

### Step 2: Deploy via Railway Dashboard

1. Go to https://railway.app
2. Click "New Project"
3. Select "Deploy from GitHub repo" (or "Empty Project")
4. If using GitHub:
   - Connect your GitHub account
   - Select the `Plato` repository
   - Railway will auto-detect it's a Python project
5. Railway will start building

### Step 3: Configure Environment Variables

In Railway dashboard:

1. Go to your project
2. Click on the service
3. Go to **Variables** tab
4. Add these environment variables:

```
SUPABASE_URL=https://[YOUR_PROJECT].supabase.co
SUPABASE_KEY=[YOUR_ANON_KEY]
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres
FLASK_ENV=production
PORT=5000
```

### Step 4: Configure Build Settings

Railway should auto-detect Python, but verify:

1. Go to **Settings** → **Build**
2. Build command: (leave empty, Railway auto-detects)
3. Start command: `python -m gunicorn src.app:app --bind 0.0.0.0:$PORT`

### Step 5: Deploy

1. Railway will automatically deploy on push to main branch
2. Or click "Deploy" button
3. Wait for build to complete
4. Get your app URL from Railway dashboard

---

## Part 4: Update Cache System

We need to update `src/cache.py` to support both SQLite (local) and Supabase (production).

### Option 1: Create Supabase Cache Manager

Create `src/supabase_cache.py`:

```python
"""
Supabase-based cache manager for production deployment.
"""

from supabase import create_client, Client
import os
import json
from typing import Optional
from datetime import datetime

from .models import ExtractedCourseData, UserSelections, CacheEntry
# ... (import serialization methods from cache.py)

class SupabaseCacheManager:
    """Cache manager using Supabase PostgreSQL."""
    
    def __init__(self):
        """Initialize Supabase client."""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
        
        self.client: Client = create_client(supabase_url, supabase_key)
    
    def lookup_extraction(self, pdf_hash: str) -> Optional[ExtractedCourseData]:
        """Look up extraction cache."""
        # Implementation here
        pass
    
    def store_extraction(self, pdf_hash: str, data: ExtractedCourseData):
        """Store extraction cache."""
        # Implementation here
        pass
    
    # ... (other methods)
```

### Option 2: Update Existing Cache Manager

Modify `src/cache.py` to support both:

```python
import os

# Use Supabase in production, SQLite locally
if os.getenv("DATABASE_URL"):
    # Use Supabase
    from .supabase_cache import SupabaseCacheManager as CacheManager
else:
    # Use SQLite (local development)
    from .cache import CacheManager
```

---

## Part 5: Testing Deployment

### Local Testing with Supabase

1. Set environment variables:
```bash
export SUPABASE_URL="https://[YOUR_PROJECT].supabase.co"
export SUPABASE_KEY="[YOUR_ANON_KEY]"
export DATABASE_URL="postgresql://..."
```

2. Test connection:
```python
from supabase import create_client
client = create_client(SUPABASE_URL, SUPABASE_KEY)
# Test query
result = client.table('extraction_cache').select('*').limit(1).execute()
print(result)
```

### Railway Deployment Testing

1. Check Railway logs for errors
2. Visit your Railway app URL
3. Test PDF upload
4. Verify database writes in Supabase dashboard

---

## Troubleshooting

### Common Issues

1. **Connection refused**
   - Check DATABASE_URL is correct
   - Verify Supabase project is active
   - Check firewall/network settings

2. **Authentication errors**
   - Verify SUPABASE_KEY is correct (use anon key, not service key)
   - Check RLS policies if enabled

3. **Build failures on Railway**
   - Check Python version compatibility
   - Verify all dependencies in requirements.txt
   - Check Railway build logs

4. **Module not found**
   - Ensure all dependencies in requirements.txt
   - Check Python path in Railway settings

---

## Next Steps

1. ✅ Set up Supabase project
2. ✅ Create database tables
3. ⏳ Update cache.py to use Supabase
4. ⏳ Create Flask web app
5. ⏳ Deploy to Railway
6. ⏳ Test end-to-end

---

## Resources

- **Railway Docs**: https://docs.railway.app
- **Supabase Docs**: https://supabase.com/docs
- **Supabase Python Client**: https://github.com/supabase/supabase-py

