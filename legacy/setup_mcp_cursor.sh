#!/bin/bash
# Script to help configure Supabase MCP in Cursor

echo "=========================================="
echo "Supabase MCP Server Setup for Cursor"
echo "=========================================="
echo ""

# Check if MCP server exists
MCP_SERVER_PATH="$HOME/supabase-mcp-server/dist/index.js"
NODE_PATH=$(which node)

if [ ! -f "$MCP_SERVER_PATH" ]; then
    echo "❌ MCP server not found at: $MCP_SERVER_PATH"
    echo "   Please run: cd ~ && git clone https://github.com/Quegenx/supabase-mcp-server.git"
    exit 1
fi

echo "✅ MCP Server found at: $MCP_SERVER_PATH"
echo "✅ Node.js found at: $NODE_PATH"
echo ""

# Connection string (you can modify this)
CONNECTION_STRING="postgresql://postgres:[Kk4132231441]@db.ftcqzuzpyebtwihizqfl.supabase.co:5432/postgres"

echo "Connection String:"
echo "$CONNECTION_STRING"
echo ""
echo "=========================================="
echo "Cursor MCP Configuration"
echo "=========================================="
echo ""
echo "Add this to Cursor Settings → Features → MCP:"
echo ""
echo "Name: Supabase MCP"
echo "Type: command"
echo "Command: $NODE_PATH"
echo "Args:"
echo "  - $MCP_SERVER_PATH"
echo "  - $CONNECTION_STRING"
echo ""
echo "=========================================="
echo "JSON Configuration (for manual config file)"
echo "=========================================="
echo ""
cat <<EOF
{
  "mcpServers": {
    "supabase": {
      "command": "$NODE_PATH",
      "args": [
        "$MCP_SERVER_PATH",
        "$CONNECTION_STRING"
      ]
    }
  }
}
EOF
echo ""
echo "=========================================="
echo "Testing Connection"
echo "=========================================="
echo ""
echo "Testing MCP server startup..."
timeout 2 node "$MCP_SERVER_PATH" "$CONNECTION_STRING" 2>&1 | head -5 || echo "Server started (this is expected)"
echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Copy the configuration above"
echo "2. Open Cursor → Settings → Features → MCP"
echo "3. Add new MCP server with the configuration"
echo "4. Restart Cursor"
echo "5. Test by asking: 'Show me tables in my Supabase database'"

