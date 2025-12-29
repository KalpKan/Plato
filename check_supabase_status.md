# Checking Supabase Project Status

## Current Issue: Connection Refused

The database connection is being refused. This is **most commonly** because:

### ⚠️ Supabase Free Tier Projects Auto-Pause

Free tier Supabase projects automatically pause after **1 week of inactivity** to save resources.

## Quick Fix Steps

1. **Go to Supabase Dashboard**
   - Visit: https://supabase.com/dashboard
   - Log in to your account

2. **Check Project Status**
   - Look for your project: `ftcqzuzpyebtwihizqfl`
   - If it shows "Paused" or is grayed out, it needs to be restored

3. **Restore/Resume Project**
   - Click on the project
   - Click "Restore" or "Resume" button
   - Wait 1-2 minutes for the database to fully start

4. **Verify Connection**
   - Once restored, the connection should work
   - Try querying again

## Alternative: Check via Supabase Dashboard

You can also check tables directly in the Supabase dashboard:

1. Go to **Table Editor** in your Supabase dashboard
2. This will show all tables in your database
3. If no tables exist, you'll see an empty state

## Once Project is Active

After restoring your project, I can:
- ✅ Query your database tables
- ✅ Create the `extraction_cache` table
- ✅ Create the `user_choices` table
- ✅ Set up the cache system

## MCP Integration Note

If the MCP integration is working properly, I should be able to query your database through that connection. However, if the project is paused, even MCP won't be able to connect.

**Next step:** Please check your Supabase dashboard and restore the project if it's paused, then we can try querying again!



