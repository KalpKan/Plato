# Railway Deployment Fix

## Issue: "python: command not found"

Railway couldn't find the `python` command. Fixed by:

1. ✅ Updated `Procfile` to use `python3` instead of `python`
2. ✅ Added `runtime.txt` to specify Python version
3. ✅ Updated `railway.json` start command
4. ✅ Added `nixpacks.toml` for explicit build configuration

## Next Steps:

1. **Commit and push the fixes:**
   ```bash
   git add Procfile runtime.txt railway.json nixpacks.toml
   git commit -m "Fix Railway deployment - use python3"
   git push origin main
   ```

2. **Railway will auto-redeploy** when you push

3. **Check Railway logs** - should now see:
   - ✅ "Installing dependencies"
   - ✅ "Starting gunicorn"
   - ✅ "Listening at: http://0.0.0.0:5000"

## If it still fails:

Check Railway → Settings → Build:
- Build Command: (leave empty)
- Start Command: `python3 -m gunicorn src.app:app --bind 0.0.0.0:$PORT`

