# Cursor MCP Configuration for Supabase

## ✅ MCP Server Setup Complete!

The Supabase MCP server has been installed and built successfully.

**Location:** `~/supabase-mcp-server/dist/index.js`

## Figma MCP Server

The Figma MCP server is configured to connect via Server-Sent Events (SSE) at:
- **URL:** `http://127.0.0.1:3845/sse`

**Note:** Make sure the Figma MCP server is running on port 3845 before using it in Cursor.

## Configuration for Cursor

### Method 1: Cursor Settings UI

#### Adding Supabase MCP:

1. Open **Cursor** → **Settings** (Cmd+,)
2. Go to **Features** → **MCP**
3. Click **+ Add New MCP Server**
4. Fill in:

**Name:** `Supabase MCP`

**Command:** `/usr/local/bin/node`

**Args (add each on a new line):**
```
/Users/kalp/supabase-mcp-server/dist/index.js
postgresql://postgres:[Kk4132231441]@db.ftcqzuzpyebtwihizqfl.supabase.co:5432/postgres
```

#### Adding Figma MCP:

1. Open **Cursor** → **Settings** (Cmd+,)
2. Go to **Features** → **MCP**
3. Click **+ Add New MCP Server**
4. Fill in:

**Name:** `Figma`

**URL:** `http://127.0.0.1:3845/sse`

**Note:** Ensure the Figma MCP server is running on port 3845 before adding this configuration.

### Method 2: JSON Config File

If you need to edit the config file directly, use this JSON:

```json
{
  "mcpServers": {
    "supabase": {
      "command": "/usr/local/bin/node",
      "args": [
        "/Users/kalp/supabase-mcp-server/dist/index.js",
        "postgresql://postgres:[Kk4132231441]@db.ftcqzuzpyebtwihizqfl.supabase.co:5432/postgres"
      ]
    },
    "Figma": {
      "url": "http://127.0.0.1:3845/sse"
    }
  }
}
```

**Config file location:**
- Mac: `~/Library/Application Support/Cursor/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json`
- Or check Cursor settings for exact path

## After Configuration

1. **Restart Cursor completely** (important!)
2. **Verify MCP is connected:**
   - Look for MCP indicator in Cursor
   - Should show "Supabase MCP" and "Figma" as available

3. **Test the connections:**
   - **Supabase:** Ask me: "Show me the tables in my Supabase database" or "What's in the extraction_cache table?"
   - **Figma:** Ask me: "List my Figma files" or "Show me designs from Figma"

## What You Can Do Now

Once MCP is connected, I can help you:

### Supabase MCP:
- ✅ Create database tables directly
- ✅ Query your database
- ✅ Set up the cache system schema
- ✅ Debug database issues
- ✅ Insert test data
- ✅ Check table structures

### Figma MCP:
- ✅ Access Figma designs and files
- ✅ Read design specifications
- ✅ Extract design tokens and styles
- ✅ Work with Figma components and frames

## Troubleshooting

### MCP Not Appearing

1. **Check paths are correct:**
   - Node: `/usr/local/bin/node`
   - MCP Server: `/Users/kalp/supabase-mcp-server/dist/index.js`

2. **Verify MCP server works:**
   ```bash
   node /Users/kalp/supabase-mcp-server/dist/index.js "postgresql://postgres:[Kk4132231441]@db.ftcqzuzpyebtwihizqfl.supabase.co:5432/postgres"
   ```
   (This will start the server - press Ctrl+C to stop)

3. **Check Cursor logs:**
   - Help → Toggle Developer Tools → Console
   - Look for MCP-related errors

### Connection Errors

- Verify your Supabase connection string is correct
- Check that your Supabase project is active
- Ensure your IP isn't blocked in Supabase settings

## Security Note

⚠️ **This file contains your database password!**

- Don't commit this file to git (it's in .gitignore)
- Consider using environment variables in production
- Rotate your password if it's been exposed

---

**Ready to go!** Once you've added the MCP server in Cursor settings and restarted, I'll be able to interact with your Supabase database directly.

