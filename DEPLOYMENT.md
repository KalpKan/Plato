# Deployment Guide

Complete guide for deploying Plato to Railway with Supabase database.

## Prerequisites

- GitHub account with repository access
- Railway account (free tier available)
- Supabase account (free tier available)

## Part 1: Codebase Preparation

### Step 1: Verify Required Files

Ensure these files exist in your project root:

- `Procfile` - Railway startup command
- `requirements.txt` - Python dependencies
- `src/app.py` - Flask application entry point
- `templates/` - HTML templates directory
- `static/` - CSS/JS files directory

### Step 2: Update .gitignore

Ensure `.gitignore` includes:

```
.env
__pycache__/
*.pyc
uploads/
temp_calendars/
*.db
.DS_Store
```

### Step 3: Commit and Push to GitHub

```bash
# Check status
git status

# Add all changes
git add .

# Commit
git commit -m "Prepare for deployment"

# Push to GitHub
git push origin main
```

Important: All code must be pushed to GitHub before deploying to Railway.

## Part 2: Supabase Setup

### Step 1: Create Supabase Project

1. Go to https://supabase.com
2. Sign in or create an account
3. Click "New Project"
4. Fill in project details:
   - Name: `plato-course-converter` (or your choice)
   - Database Password: Create a strong password (save this securely)
   - Region: Choose closest to your users
5. Click "Create new project"
6. Wait 2-3 minutes for initialization

### Step 2: Get Database Connection String

1. In Supabase dashboard, go to Settings → Database
2. Scroll to "Connection string" section
3. Copy the "URI" connection string (Transaction mode recommended)
   - Format: `postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres`
4. Save this connection string securely

### Step 3: Create Database Tables

1. In Supabase dashboard, go to SQL Editor
2. Click "New query"
3. Paste and run this SQL:

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

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_user_choices_pdf_hash ON user_choices(pdf_hash);
CREATE INDEX IF NOT EXISTS idx_user_choices_session ON user_choices(session_id);
```

4. Click "Run" (or press Cmd/Ctrl + Enter)
5. Verify success message

### Step 4: Enable Row Level Security

1. In SQL Editor, run this SQL:

```sql
-- Enable Row Level Security on both tables
ALTER TABLE extraction_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_choices ENABLE ROW LEVEL SECURITY;

-- Create policies to allow all operations
-- Note: For a single-user app, allowing all is fine
-- For multi-user apps, you'd restrict based on user_id
CREATE POLICY "Allow all operations on extraction_cache" 
ON extraction_cache FOR ALL 
USING (true) 
WITH CHECK (true);

CREATE POLICY "Allow all operations on user_choices" 
ON user_choices FOR ALL 
USING (true) 
WITH CHECK (true);
```

2. Click "Run"
3. Go to Advisors → Security in Supabase dashboard
4. Verify no security warnings (should show 0 errors)

## Part 3: Railway Setup

### Step 1: Create Railway Account

1. Go to https://railway.app
2. Sign in with GitHub (recommended) or email
3. Authorize Railway to access your GitHub account

### Step 2: Create New Project

1. In Railway dashboard, click "New Project"
2. Select "Deploy from GitHub repo"
3. Authorize Railway to access your GitHub repositories
4. Select your `Plato` repository
5. Railway will automatically:
   - Detect it's a Python project
   - Start building
   - Create a service

### Step 3: Configure Environment Variables

1. In Railway dashboard, click on your service
2. Go to Variables tab
3. Click "New Variable" and add each of these:

**Required Variables:**

```
DATABASE_URL=postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
```

Replace with your actual Supabase connection string from Part 2, Step 2.

```
SECRET_KEY=97106b820b03615eae37e26059d1a62b2b9ae8980147e4171dd31a1ce67bea64
```

Generate a new one: `python3 -c "import secrets; print(secrets.token_hex(32))"`

```
PORT=5000
```

```
FLASK_ENV=production
```

**Optional Variables:**

```
FLASK_DEBUG=False
```

### Step 4: Verify Build Settings

1. In Railway dashboard, go to Settings → Build
2. Verify:
   - Build Command: (leave empty - Railway auto-detects)
   - Start Command: Should be `python -m gunicorn src.app:app --bind 0.0.0.0:$PORT`
   - If not set, configure it manually

### Step 5: Deploy

1. Railway automatically deploys when you:
   - Push to GitHub main branch, OR
   - Click "Deploy" button manually
2. Watch the Deployments tab for build progress
3. Once deployed, Railway will show your app URL:
   - Format: `https://your-app-name.up.railway.app`
   - Or set a custom domain in Settings → Domains

## Part 4: Post-Deployment Verification

### Step 1: Check Deployment Status

1. In Railway dashboard → Deployments
2. Look for:
   - Green checkmark = Success
   - Red X = Failed (check logs for errors)

### Step 2: View Logs

1. Click on the latest deployment
2. Click "View Logs"
3. Look for:
   - "Starting gunicorn"
   - "Listening at: http://0.0.0.0:5000"
   - Any error messages (will help debug)

### Step 3: Test the Application

1. Visit your Railway app URL
2. Test PDF upload:
   - Upload a test PDF
   - Verify extraction works
   - Check if assessments appear
   - Test calendar generation
   - Verify .ics file downloads correctly

### Step 4: Verify Database Connection

1. In Supabase dashboard → Table Editor
2. Check `extraction_cache` table:
   - Should see entries after PDF uploads
3. Check `user_choices` table:
   - Should see entries after user selections

## Part 5: Troubleshooting

### Issue: Build Fails

**Check:**
- Railway logs for error messages
- `requirements.txt` has all dependencies (especially `gunicorn`)
- Python version compatibility
- File paths are correct

**Common fixes:**
```bash
# Verify gunicorn is in requirements.txt
grep gunicorn requirements.txt

# Check Procfile exists and is correct
cat Procfile
```

### Issue: App Crashes on Startup

**Check Railway logs for:**
- Missing environment variables
- Database connection errors
- Import errors

**Common fixes:**
- Verify `DATABASE_URL` is set correctly
- Check `SECRET_KEY` is set
- Ensure all dependencies in `requirements.txt`
- Verify `Procfile` has correct command

### Issue: Database Connection Fails

**Check:**
- `DATABASE_URL` format is correct
- Supabase project is active (not paused)
- Password in connection string is correct
- Network/firewall settings

**Test connection:**
```python
# In Railway console or locally
import psycopg2
import os
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
print("Connected!")
```

### Issue: Assessments Not Showing

**Steps to debug:**
1. Check Railway logs for extraction errors
2. Verify cache is working (check Supabase tables)
3. Test with "Force refresh" option
4. Check session data in logs

**Quick test:**
- Upload PDF with "Force refresh" checked
- Check Railway logs for assessment count
- Verify Supabase `extraction_cache` table has data

### Issue: Static Files Not Loading

**Check:**
- `static/` directory exists in repository
- Files are committed to git
- Railway build includes static files

## Part 6: Custom Domain (Optional)

### Step 1: Add Custom Domain in Railway

1. In Railway dashboard → Settings → Domains
2. Click "Custom Domain"
3. Enter your domain (e.g., `plato.yourdomain.com`)
4. Follow Railway's DNS instructions

### Step 2: Update DNS

1. Add CNAME record in your DNS provider:
   - Name: `plato` (or subdomain of choice)
   - Value: Railway-provided domain
2. Wait for DNS propagation (5-60 minutes)

## Part 7: Monitoring and Maintenance

### View Logs

- Railway dashboard → Deployments → View Logs
- Real-time logs available
- Search/filter logs for errors

### Monitor Database

- Supabase dashboard → Database → Table Editor
- Check table sizes
- Monitor query performance
- Check for connection issues

### Update Deployment

1. Make code changes locally
2. Commit and push to GitHub:
   ```bash
   git add .
   git commit -m "Your changes"
   git push origin main
   ```
3. Railway automatically redeploys on push to main branch

## Environment Variables Summary

```bash
# Required
DATABASE_URL=postgresql://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
SECRET_KEY=your-secret-key-here
PORT=5000
FLASK_ENV=production

# Optional
FLASK_DEBUG=False
```

## Important Notes

1. Never commit `.env` files - use Railway's environment variables
2. Keep `SECRET_KEY` secret - generate a new one for production
3. Database password - save it securely, you'll need it for `DATABASE_URL`
4. Free tier limits:
   - Railway: 500 hours/month free
   - Supabase: 500MB database free
5. Auto-deploy: Railway redeploys on every push to main branch

## Quick Reference Checklist

### Before Deployment
- [ ] Code pushed to GitHub
- [ ] `Procfile` exists
- [ ] `requirements.txt` includes `gunicorn`
- [ ] Supabase project created
- [ ] Database tables created
- [ ] Connection string ready

### During Deployment
- [ ] Railway project created
- [ ] GitHub repo connected
- [ ] Environment variables set:
  - [ ] `DATABASE_URL`
  - [ ] `SECRET_KEY`
  - [ ] `PORT=5000`
  - [ ] `FLASK_ENV=production`
- [ ] Build successful
- [ ] App URL obtained

### After Deployment
- [ ] App loads in browser
- [ ] PDF upload works
- [ ] Extraction works
- [ ] Assessments appear
- [ ] Calendar generation works
- [ ] Database writes verified

## Support Resources

- Railway Documentation: https://docs.railway.app
- Supabase Documentation: https://supabase.com/docs
- Flask Documentation: https://flask.palletsprojects.com
- Railway Discord: https://discord.gg/railway

