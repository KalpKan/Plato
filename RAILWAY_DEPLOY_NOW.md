# Railway Deployment - Next Steps

## Step 1: Create Railway Project

1. Go to **https://railway.app**
2. Sign in (use GitHub for easiest setup)
3. Click **"New Project"** button (top right)
4. Select **"Deploy from GitHub repo"**
5. If prompted, authorize Railway to access your GitHub
6. Select your **`Plato`** repository from the list
7. Railway will automatically:
   - Detect it's a Python project
   - Start building
   - Create a service

## Step 2: Get Your Supabase Connection String

1. Go to **Supabase Dashboard** → Your project
2. Go to **Settings** → **Database**
3. Scroll to **Connection string** section
4. Find **"URI"** or **"Connection pooling"** tab
5. Copy the connection string
   - Format: `postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres`
   - Or use the **Transaction** mode connection string
6. **SAVE THIS** - you'll need it in the next step

## Step 3: Set Environment Variables in Railway

1. In Railway dashboard, click on your **service** (the one that was just created)
2. Click on **"Variables"** tab
3. Click **"+ New Variable"** button
4. Add each variable one by one:

### Variable 1: DATABASE_URL
- **Name**: `DATABASE_URL`
- **Value**: (paste your Supabase connection string from Step 2)
- Click **"Add"**

### Variable 2: SECRET_KEY
- **Name**: `SECRET_KEY`
- **Value**: `97106b820b03615eae37e26059d1a62b2b9ae8980147e4171dd31a1ce67bea64`
- Click **"Add"**

### Variable 3: PORT
- **Name**: `PORT`
- **Value**: `5000`
- Click **"Add"**

### Variable 4: FLASK_ENV
- **Name**: `FLASK_ENV`
- **Value**: `production`
- Click **"Add"**

## Step 4: Verify Build Settings

1. In Railway dashboard, click **"Settings"** tab
2. Scroll to **"Build"** section
3. Verify:
   - **Build Command**: (should be empty - Railway auto-detects)
   - **Start Command**: Should be `python -m gunicorn src.app:app --bind 0.0.0.0:$PORT`
   - If Start Command is wrong, click **"Edit"** and set it manually

## Step 5: Wait for Deployment

1. Railway will automatically start building and deploying
2. Watch the **"Deployments"** tab
3. You'll see:
   - Building... (installing dependencies)
   - Deploying... (starting the app)
   - ✅ Success (green checkmark)

## Step 6: Get Your App URL

1. Once deployment succeeds, Railway will show your app URL
2. Click on your service → **"Settings"** → **"Domains"**
3. You'll see a URL like: `https://your-app-name.up.railway.app`
4. **Copy this URL** - this is your live app!

## Step 7: Test the Deployment

1. Open your Railway app URL in a browser
2. You should see the upload page
3. Test by uploading a PDF:
   - Upload `BMSUE Syllabus Phys3140A Fall 2025 Sept3.pdf`
   - Check if extraction works
   - Verify assessments appear
   - Test calendar generation

## Step 8: Check Logs (if issues)

1. In Railway dashboard → **"Deployments"**
2. Click on the latest deployment
3. Click **"View Logs"**
4. Look for:
   - ✅ "Starting gunicorn"
   - ✅ "Listening at: http://0.0.0.0:5000"
   - ❌ Any errors (will help debug)

## Troubleshooting

### If build fails:
- Check Railway logs for error messages
- Verify `requirements.txt` has all dependencies
- Check environment variables are set correctly

### If app crashes:
- Check Railway logs for errors
- Verify `DATABASE_URL` is correct
- Ensure Supabase project is active (not paused)

### If assessments don't show:
- Check Railway logs for extraction errors
- Try uploading with "Force refresh" checked
- Verify Supabase tables have data

---

## Quick Reference

**Railway Dashboard**: https://railway.app  
**Your App URL**: (will be shown after deployment)  
**Supabase Dashboard**: https://supabase.com/dashboard

---

**Once deployed, share your Railway app URL and we can test together!** 🚀

