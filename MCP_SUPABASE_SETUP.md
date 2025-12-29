# Setting Up Supabase MCP with Cursor

This guide will help you connect Supabase to Cursor using the Model Context Protocol (MCP), making it easier to interact with your database directly from Cursor.

## Prerequisites

1. **Node.js installed** (version 18 or higher)
   - Check: `node --version`
   - Install: https://nodejs.org/

2. **Supabase project** (you already have this!)
   - Connection string: `postgresql://postgres:[Kk4132231441]@db.ftcqzuzpyebtwihizqfl.supabase.co:5432/postgres`

## Step 1: Install Supabase MCP Server

### Option A: Using npm (Recommended)

```bash
# Install globally
npm install -g @supabase/mcp-server

# Or install locally in your project
cd /Users/kalp/Desktop/Plato
npm init -y
npm install @supabase/mcp-server
```

### Option B: Clone from GitHub

```bash
cd ~
git clone https://github.com/Quegenx/supabase-mcp-server.git
cd supabase-mcp-server
npm install
npm run build
```

## Step 2: Configure MCP Server in Cursor

### Method 1: Using Cursor Settings UI

1. **Open Cursor Settings**
   - Press `Cmd + ,` (Mac) or `Ctrl + ,` (Windows/Linux)
   - Or: `Cursor` → `Settings` → `Features` → `MCP`

2. **Add New MCP Server**
   - Click `+ Add New MCP Server`
   - Fill in the details:

**Configuration:**
```json
{
  "name": "Supabase MCP",
  "type": "command",
  "command": "node",
  "args": [
    "/path/to/supabase-mcp-server/dist/index.js",
    "postgresql://postgres:[Kk4132231441]@db.ftcqzuzpyebtwihizqfl.supabase.co:5432/postgres"
  ]
}
```

**Or if installed globally:**
```json
{
  "name": "Supabase MCP",
  "type": "command",
  "command": "npx",
  "args": [
    "@supabase/mcp-server",
    "postgresql://postgres:[Kk4132231441]@db.ftcqzuzpyebtwihizqfl.supabase.co:5432/postgres"
  ]
}
```

### Method 2: Using Cursor Config File

1. **Find Cursor Config File**
   - Mac: `~/Library/Application Support/Cursor/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json`
   - Or check Cursor settings for MCP config location

2. **Add Configuration**

```json
{
  "mcpServers": {
    "supabase": {
      "command": "node",
      "args": [
        "/path/to/supabase-mcp-server/dist/index.js",
        "postgresql://postgres:[Kk4132231441]@db.ftcqzuzpyebtwihizqfl.supabase.co:5432/postgres"
      ]
    }
  }
}
```

## Step 3: Verify Connection

1. **Restart Cursor** (important!)
2. **Check MCP Status**
   - Look for MCP indicator in Cursor
   - Should show "Supabase MCP" as connected

3. **Test Connection**
   - Try asking: "Show me the tables in my Supabase database"
   - Or: "What's in the extraction_cache table?"

## Step 4: Using MCP in Cursor

Once connected, you can:

1. **Query Database**
   - "Show all records in extraction_cache"
   - "Count rows in user_choices table"
   - "What's the schema of extraction_cache?"

2. **Create Tables**
   - "Create the extraction_cache table if it doesn't exist"
   - "Set up the database schema for the cache system"

3. **Insert/Update Data**
   - "Insert a test record into extraction_cache"
   - "Update the timestamp for pdf_hash 'abc123'"

4. **Debug Issues**
   - "Check if the tables exist"
   - "Show me the last 5 records"
   - "What's the structure of user_choices?"

## Security Note ⚠️

**Important:** Your connection string contains your password. 

1. **Don't commit this to git!**
   - Already in `.gitignore`: `.env`
   - Remove the connection string from `RAILWAY_SUPABASE_SETUP.md` before committing

2. **Use Environment Variables Instead**

Create `.env` file:
```env
SUPABASE_DATABASE_URL=postgresql://postgres:[Kk4132231441]@db.ftcqzuzpyebtwihizqfl.supabase.co:5432/postgres
```

Then reference it in MCP config:
```json
{
  "command": "node",
  "args": [
    "/path/to/index.js",
    "${SUPABASE_DATABASE_URL}"
  ],
  "env": {
    "SUPABASE_DATABASE_URL": "postgresql://postgres:[Kk4132231441]@db.ftcqzuzpyebtwihizqfl.supabase.co:5432/postgres"
  }
}
```

## Troubleshooting

### MCP Server Not Appearing

1. **Check Node.js Path**
   ```bash
   which node
   # Use full path in config: /usr/local/bin/node
   ```

2. **Check MCP Server Path**
   - Verify the path to `index.js` is correct
   - Use absolute paths, not relative

3. **Check Permissions**
   ```bash
   chmod +x /path/to/supabase-mcp-server/dist/index.js
   ```

### Connection Errors

1. **Test Connection String**
   ```bash
   psql "postgresql://postgres:[Kk4132231441]@db.ftcqzuzpyebtwihizqfl.supabase.co:5432/postgres"
   ```

2. **Check Firewall**
   - Supabase allows connections from anywhere by default
   - Verify your IP isn't blocked

3. **Verify Credentials**
   - Double-check password in Supabase dashboard
   - Settings → Database → Connection string

### MCP Tools Not Available

1. **Restart Cursor** completely
2. **Check Cursor Logs**
   - Help → Toggle Developer Tools → Console
   - Look for MCP errors

3. **Verify MCP Server is Running**
   - Check if process is running
   - Try running command manually in terminal

## Quick Setup Script

Save this as `setup_mcp.sh`:

```bash
#!/bin/bash

# Install Supabase MCP Server
npm install -g @supabase/mcp-server

# Get Node.js path
NODE_PATH=$(which node)

# Get connection string (you'll need to set this)
CONNECTION_STRING="postgresql://postgres:[Kk4132231441]@db.ftcqzuzpyebtwihizqfl.supabase.co:5432/postgres"

echo "Node.js path: $NODE_PATH"
echo "Connection string: $CONNECTION_STRING"
echo ""
echo "Add this to Cursor MCP settings:"
echo "{"
echo "  \"name\": \"Supabase MCP\","
echo "  \"command\": \"$NODE_PATH\","
echo "  \"args\": [\"-e\", \"require('@supabase/mcp-server')('$CONNECTION_STRING')\"]"
echo "}"
```

## Benefits of Using MCP

✅ **Direct Database Access** - Query and modify database from Cursor
✅ **Faster Development** - No need to switch to Supabase dashboard
✅ **Better Context** - I can see your database structure and data
✅ **Easier Debugging** - Check data without leaving Cursor
✅ **Schema Management** - Create/modify tables directly

## Next Steps

1. ✅ Install MCP server
2. ✅ Configure in Cursor
3. ✅ Test connection
4. ⏳ Use MCP to set up database tables
5. ⏳ Update cache.py to use Supabase
6. ⏳ Test end-to-end

## Resources

- **Supabase MCP Server**: https://github.com/Quegenx/supabase-mcp-server
- **MCP Documentation**: https://modelcontextprotocol.io
- **Cursor MCP Guide**: Check Cursor documentation

---

**Note:** After setting up MCP, I'll be able to help you:
- Create the database tables directly
- Test queries
- Debug database issues
- Set up the cache system with Supabase

Just ask me to interact with your Supabase database once MCP is configured!

