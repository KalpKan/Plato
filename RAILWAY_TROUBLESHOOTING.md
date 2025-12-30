# Railway Troubleshooting Guide

## 1. Check Railway Service Settings - Expose Public URL

1. **Go to Railway Dashboard**
   - Visit https://railway.app
   - Log in to your account

2. **Select Your Project**
   - Click on your project (Plato) from the dashboard

3. **Select Your Service**
   - Click on the service that's running your Flask app

4. **Check Settings Tab**
   - Click on the **"Settings"** tab in the service view
   - Scroll down to the **"Networking"** section

5. **Enable Public Domain**
   - Look for **"Generate Domain"** or **"Public Domain"** option
   - If there's a toggle or button to generate a domain, click it
   - Railway will generate a public URL like: `your-app-name.up.railway.app`

6. **Verify Port Configuration**
   - In the Settings tab, check if there's a **"Port"** or **"Expose Port"** setting
   - Make sure it's configured correctly (Railway usually auto-detects this)

## 2. Verify Service Shows Public Domain/URL

1. **Check Service Overview**
   - In your service view, look at the top of the page
   - You should see a **"Domains"** or **"Public URL"** section
   - If you see a URL like `https://your-app-name.up.railway.app`, that's your public URL

2. **Check the Service Header**
   - At the top of the service page, Railway often displays:
     - Service name
     - Status (Running/Deployed)
     - A clickable public URL (if configured)

3. **If No Public URL is Shown**
   - Go to Settings → Networking
   - Click **"Generate Domain"** or **"Add Domain"**
   - Railway will create a public URL for you

4. **Test the URL**
   - Copy the public URL
   - Open it in a new browser tab
   - You should see your Flask app's homepage

## 3. Check Deploy Logs - Confirm Script Execution

1. **Open Deploy Logs**
   - In your service view, click on the **"Deployments"** tab
   - Or look for **"Logs"** or **"View Logs"** button

2. **Select Latest Deployment**
   - Click on the most recent deployment (usually at the top)
   - This will show the build and deploy logs

3. **Check Build Logs**
   - Look for messages like:
     - `COPY start.sh /app/start.sh`
     - `RUN chmod +x /app/start.sh`
     - `CMD ["/app/start.sh"]`

4. **Check Deploy/Runtime Logs**
   - Scroll to the bottom of the logs (most recent entries)
   - Look for:
     - `Starting gunicorn`
     - `Listening at: http://0.0.0.0:XXXX` (where XXXX is the PORT number)
     - The port number should match Railway's PORT environment variable

5. **Check for Errors**
   - Look for any error messages in red
   - Common issues:
     - `Permission denied` - script not executable (should be fixed by chmod +x)
     - `No such file or directory` - start.sh not found (check Dockerfile COPY)
     - `PORT not set` - Railway environment variable issue

6. **Verify Environment Variables**
   - Go to Settings → Variables
   - Check if `PORT` is listed (Railway usually sets this automatically)
   - You should also see your `DATABASE_URL` if configured

## Quick Checklist

- [ ] Service has a public domain/URL generated
- [ ] Public URL is accessible in browser
- [ ] Deploy logs show gunicorn starting successfully
- [ ] Deploy logs show gunicorn listening on a port (not just 5000)
- [ ] No errors in the deploy logs
- [ ] Environment variables are set correctly

## If Still Not Working

1. **Check Railway Status Page**
   - Visit https://status.railway.app to check for outages

2. **Try Redeploying**
   - In the service view, click **"Redeploy"** or **"Deploy"**
   - This will trigger a fresh build and deployment

3. **Check Application Logs**
   - In the service view, click **"Logs"** tab
   - Look for Flask/gunicorn error messages
   - Check for database connection errors if using Supabase

4. **Verify Dockerfile is Being Used**
   - In Settings → Build, verify that Railway is using the Dockerfile
   - Should show: `Builder: DOCKERFILE` or similar

