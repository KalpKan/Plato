# Complete Deployment Guide: Railway + Supabase

This guide covers all steps needed to deploy the Course Outline Converter to Railway.

---

## Part 1: Codebase Preparation

### Step 1: Verify Required Files Exist

Check that these files exist in your project root:

- ✅ `Procfile` - Tells Railway how to run the app
- ✅ `requirements.txt` - All Python dependencies
- ✅ `railway.json` - Railway configuration (optional)
- ✅ `src/app.py` - Flask application
- ✅ `templates/` - HTML templates
- ✅ `static/` - CSS/JS files

### Step 2: Update .gitignore (if needed)

Ensure `.gitignore` includes:
```
.env
__pycache__/
*.pyc
uploads/
temp_calendars/
*.db
```

### Step 3: Commit All Changes

```bash
# Check what files have changed
git status

# Add all files
git add .

# Commit
git commit -m "Prepare for Railway deployment"

# Push to GitHub
git push origin main
```

**Important**: Make sure your code is pushed to GitHub before deploying!

---

## Part 2: Supabase Setup

### Step 1: Create Supabase Project

1. Go to https://supabase.com
2. Sign in (or create account)
3. Click **"New Project"**
4. Fill in:
   - **Name**: `plato-course-converter` (or your choice)
   - **Database Password**: Create a strong password (SAVE THIS!)
   - **Region**: Choose closest to you
5. Click **"Create new project"**
6. Wait 2-3 minutes for initialization

### Step 2: Get Connection Details

1. In Supabase dashboard, go to **Settings** → **Database**
2. Scroll to **Connection string** section
3. Copy the **URI** connection string
   - Format: `postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres`
   - Or use the **Transaction** mode connection string

**Save this connection string** - you'll need it for Railway!

### Step 3: Create Database Tables

1. In Supabase dashboard, go to **SQL Editor**
2. Click **"New query"**
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

4. Click **"Run"** (or press Cmd/Ctrl + Enter)
5. You should see "Success. No rows returned"

### Step 4: Get API Keys (Optional - for future use)

1. Go to **Settings** → **API**
2. Note your **Project URL** and **anon/public key** (for future features)

---

## Part 3: Railway Setup

### Step 1: Create Railway Account

1. Go to https://railway.app
2. Sign in with GitHub (recommended) or email
3. Railway will connect to your GitHub account

### Step 2: Create New Project

1. In Railway dashboard, click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. If prompted, authorize Railway to access your GitHub
4. Select your **`Plato`** repository
5. Railway will automatically:
   - Detect it's a Python project
   - Start building
   - Create a service

### Step 3: Configure Environment Variables

1. In Railway dashboard, click on your **service** (the one that was created)
2. Go to **Variables** tab
3. Click **"New Variable"** and add each of these:

**Required Variables:**

```
DATABASE_URL=postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
```

*(Replace with your actual Supabase connection string from Part 2, Step 2)*

```
SECRET_KEY=97106b820b03615eae37e26059d1a62b2b9ae8980147e4171dd31a1ce67bea64
```

*(Or generate a new one: `python3 -c "import secrets; print(secrets.token_hex(32))"`)*

```
PORT=5000
```

```
FLASK_ENV=production
```

**Optional Variables (for debugging):**

```
FLASK_DEBUG=False
```

### Step 4: Verify Build Settings

1. In Railway dashboard, go to **Settings** → **Build**
2. Verify:
   - **Build Command**: (leave empty - Railway auto-detects)
   - **Start Command**: Should be `python -m gunicorn src.app:app --bind 0.0.0.0:$PORT`
   - If not, set it manually

### Step 5: Deploy

1. Railway should automatically deploy when you:
   - Push to GitHub, OR
   - Click **"Deploy"** button
2. Watch the **Deployments** tab for build progress
3. Once deployed, Railway will show your app URL:
   - Format: `https://your-app-name.up.railway.app`
   - Or you can set a custom domain

---

## Part 4: Post-Deployment Verification

### Step 1: Check Deployment Status

1. In Railway dashboard → **Deployments**
2. Look for:
   - ✅ Green checkmark = Success
   - ❌ Red X = Failed (check logs)

### Step 2: View Logs

1. Click on the latest deployment
2. Click **"View Logs"**
3. Look for:
   - ✅ "Starting gunicorn"
   - ✅ "Listening at: http://0.0.0.0:5000"
   - ❌ Any errors (will help debug)

### Step 3: Test the Application

1. Visit your Railway app URL
2. Test PDF upload:
   - Upload a test PDF
   - Check if extraction works
   - Verify assessments appear
   - Test calendar generation

### Step 4: Verify Database Connection

1. In Supabase dashboard → **Table Editor**
2. Check `extraction_cache` table:
   - Should see entries after PDF uploads
3. Check `user_choices` table:
   - Should see entries after user selections

---

## Part 5: Troubleshooting

### Issue: Build Fails

**Check:**
- Railway logs for error messages
- `requirements.txt` has all dependencies
- Python version compatibility
- File paths are correct

**Common fixes:**
```bash
# Make sure gunicorn is in requirements.txt
grep gunicorn requirements.txt

# Check Procfile exists
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
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
print("Connected!")
```

### Issue: Assessments Not Showing

**This is the issue we're debugging!**

**Steps to debug:**
1. Check Railway logs for extraction errors
2. Verify cache is working (check Supabase tables)
3. Test with "Force refresh" option
4. Check session data in logs

**Quick test:**
- Upload PDF with "Force refresh" checked
- Check Railway logs for assessment count
- Verify Supabase `extraction_cache` table has data

---

## Part 6: Custom Domain (Optional)

### Step 1: Add Custom Domain in Railway

1. In Railway dashboard → **Settings** → **Domains**
2. Click **"Custom Domain"**
3. Enter your domain (e.g., `plato.yourdomain.com`)
4. Follow Railway's DNS instructions

### Step 2: Update DNS

1. Add CNAME record in your DNS provider:
   - **Name**: `plato` (or subdomain of choice)
   - **Value**: Railway-provided domain
2. Wait for DNS propagation (5-60 minutes)

---

## Part 7: Monitoring & Maintenance

### View Logs

- Railway dashboard → **Deployments** → **View Logs**
- Real-time logs available
- Search/filter logs for errors

### Monitor Database

- Supabase dashboard → **Database** → **Table Editor**
- Check table sizes
- Monitor query performance

### Update Deployment

1. Make code changes locally
2. Commit and push to GitHub:
   ```bash
   git add .
   git commit -m "Your changes"
   git push origin main
   ```
3. Railway automatically redeploys

---

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

---

## Next Steps After Deployment

1. **Test thoroughly** with both reference PDFs
2. **Monitor logs** for any errors
3. **Fix assessment issue** based on production logs
4. **Optimize** based on real usage
5. **Add features** as needed

---

## Support Resources

- **Railway Docs**: https://docs.railway.app
- **Supabase Docs**: https://supabase.com/docs
- **Flask Docs**: https://flask.palletsprojects.com
- **Railway Discord**: https://discord.gg/railway

---

## Environment Variables Summary

```bash
# Required
DATABASE_URL=postgresql://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
SECRET_KEY=97106b820b03615eae37e26059d1a62b2b9ae8980147e4171dd31a1ce67bea64
PORT=5000
FLASK_ENV=production

# Optional
FLASK_DEBUG=False
```

---

## Important Notes

1. **Never commit `.env` files** - use Railway's environment variables
2. **Keep `SECRET_KEY` secret** - generate a new one for production
3. **Database password** - save it securely, you'll need it for `DATABASE_URL`
4. **Free tier limits**:
   - Railway: 500 hours/month free
   - Supabase: 500MB database free
5. **Auto-deploy**: Railway redeploys on every push to main branch

---

Good luck with deployment! 🚀

