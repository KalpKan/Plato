# Railway Deployment Guide

## Quick Deploy Steps

### 1. Prepare Repository
- ✅ `Procfile` - Created
- ✅ `requirements.txt` - Includes gunicorn
- ✅ `railway.json` - Configuration file

### 2. Deploy to Railway

1. **Go to Railway**: https://railway.app
2. **Click "New Project"**
3. **Select "Deploy from GitHub repo"**
   - Connect your GitHub account if needed
   - Select the `Plato` repository
4. **Railway will auto-detect Python** and start building

### 3. Set Environment Variables

In Railway dashboard → Your Project → Variables:

```
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres
SECRET_KEY=[generate a random secret key]
PORT=5000
FLASK_ENV=production
```

**To generate SECRET_KEY:**
```python
import secrets
print(secrets.token_hex(32))
```

### 4. Verify Deployment

1. Railway will provide a URL like: `https://your-app.railway.app`
2. Visit the URL
3. Test PDF upload

### 5. Check Logs

In Railway dashboard → Deployments → View Logs

Look for:
- ✅ "Starting gunicorn"
- ✅ "Listening at: http://0.0.0.0:5000"
- ❌ Any errors (will help debug assessment issue)

## Why Deploy Now?

1. **Fresh Environment**: No stale cache/session data
2. **Better Logging**: Railway logs are clearer than local
3. **Real Testing**: Production-like environment
4. **Easier Debugging**: Can see exactly what's happening

## After Deployment

Once deployed, we can:
1. Test with fresh data
2. Check Railway logs for any issues
3. Make targeted fixes based on production behavior
4. The assessment issue should be clearer in logs

## Troubleshooting

If deployment fails:
- Check Railway logs
- Verify `requirements.txt` has all dependencies
- Check environment variables are set
- Ensure Supabase connection string is correct

