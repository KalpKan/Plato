# Supabase Connection Troubleshooting

## Current Issue: Connection Refused

The database connection is being refused. Here are the most common causes and solutions:

## 1. Check Supabase Project Status

**Most Common Issue:** Free tier Supabase projects pause after 1 week of inactivity.

### Solution:
1. Go to https://supabase.com/dashboard
2. Log in to your account
3. Check if your project shows as "Paused" or "Inactive"
4. If paused, click "Restore" or "Resume" to reactivate it
5. Wait 1-2 minutes for the project to fully start

## 2. Verify Connection String

Your current connection string:
```
postgresql://postgres:[Kk4132231441]@db.ftcqzuzpyebtwihizqfl.supabase.co:5432/postgres
```

### Check in Supabase Dashboard:
1. Go to **Settings** → **Database**
2. Find **Connection string** section
3. Select **URI** format
4. Copy the exact connection string
5. Verify it matches what we're using

## 3. Check Database Password

The password in the connection string might be incorrect.

### Solution:
1. Go to **Settings** → **Database**
2. If you forgot the password, you can reset it
3. Update the connection string with the new password

## 4. Check IP Restrictions

Supabase might have IP restrictions enabled.

### Solution:
1. Go to **Settings** → **Database**
2. Check **Connection Pooling** settings
3. Ensure "Allow connections from anywhere" is enabled
4. Or add your current IP to the allowed list

## 5. Use Connection Pooler (Recommended)

Supabase recommends using the connection pooler for better reliability.

### Pooled Connection String:
```
postgresql://postgres.ftcqzuzpyebtwihizqfl:[Kk4132231441]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

Note the differences:
- `postgres.ftcqzuzpyebtwihizqfl` (with project ID)
- Port `6543` (pooler port) instead of `5432`
- `pooler.supabase.com` domain

## 6. Test Connection with psql

Test the connection directly:

```bash
psql "postgresql://postgres:[Kk4132231441]@db.ftcqzuzpyebtwihizqfl.supabase.co:5432/postgres"
```

If this works, the connection string is correct and the issue is with Python/psycopg2.

## 7. Check Supabase Dashboard

1. Go to your Supabase project dashboard
2. Check the **Database** section
3. Look for any error messages or warnings
4. Check if the project is in "Active" status

## Quick Fix Steps

1. ✅ **Check project status** - Make sure it's not paused
2. ✅ **Verify connection string** - Copy fresh from Supabase dashboard
3. ✅ **Try connection pooler** - Use port 6543 instead of 5432
4. ✅ **Test with psql** - Verify connection works at all
5. ✅ **Check firewall** - Ensure port 5432/6543 isn't blocked

## Alternative: Use Supabase REST API

If direct database connection doesn't work, we can use Supabase's REST API instead:

```python
from supabase import create_client

url = "https://ftcqzuzpyebtwihizqfl.supabase.co"
key = "your-anon-key"  # Get from Settings → API

supabase = create_client(url, key)
```

## Next Steps

Once the connection is working, I can help you:
- Create the database tables
- Set up the cache system
- Test database operations
- Deploy to Railway

Let me know once you've checked the project status and we can try again!


