# ADM1 MCP Server Setup Guide

Simple setup instructions for the ADM1 MCP Server to work with MCP clients like Claude Desktop.

## Prerequisites

- Python 3.8 or higher
- MCP client (e.g., Claude Desktop)
- Google API Key for AI assistant functionality

## Installation

### Step 1: Clone Repository

```bash
git clone https://github.com/puran-water/adm1-mcp.git
cd adm1-mcp
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Environment Configuration

```bash
# Copy environment template
cp .env.example .env
```

Edit the `.env` file and add your Google API key:
```bash
GOOGLE_API_KEY=your_google_api_key_here
```

## Google API Key Setup

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the generated API key
5. Add it to your `.env` file

**Security Note**: Never share or commit your API key to version control.

## MCP Client Configuration

### Claude Desktop Setup

1. **Locate Claude Desktop configuration file:**
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Linux**: `~/.config/claude/claude_desktop_config.json`

2. **Add the ADM1 server configuration:**

```json
{
  "mcpServers": {
    "adm1-mcp": {
      "command": "C:\\path\\to\\your\\venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\adm1-mcp\\server.py"],
      "env": {
        "MCP_TIMEOUT": "600000"
      }
    }
  }
}
```

**Important**: Replace the paths with your actual installation paths:
- `command`: Path to your virtual environment's Python executable
- `args`: Path to the server.py file in your adm1-mcp directory

3. **Example configuration with actual paths:**

```json
{
  "mcpServers": {
    "adm1-mcp": {
      "command": "C:\\Users\\yourusername\\adm1-mcp\\venv\\Scripts\\python.exe",
      "args": ["C:\\Users\\yourusername\\adm1-mcp\\server.py"],
      "env": {
        "MCP_TIMEOUT": "600000"
      }
    }
  }
}
```

4. **Restart Claude Desktop** to load the new server configuration.

## Verify Installation

### Test Basic Functionality

In your activated virtual environment, run:

```bash
# Test core imports
python -c "import qsdsan; print('QSDsan: OK')"
python -c "import google.generativeai; print('Google AI: OK')"
python -c "from server import simulation_state; print('Server: OK')"
```

### Test in Claude Desktop

After restarting Claude Desktop, you should be able to use prompts like:

```
"List the available ADM1 tools"
"Describe a feedstock with 50% vegetables and 50% food waste"
```

## Troubleshooting

### Common Issues

**1. Import Errors**
```bash
# Ensure virtual environment is activated
# Re-install dependencies
pip install -r requirements.txt --force-reinstall
```

**2. API Key Issues**
```bash
# Verify .env file format
cat .env
# Should show: GOOGLE_API_KEY=your_key_here

# Test API key
python -c "import os; print('Key found:', bool(os.getenv('GOOGLE_API_KEY')))"
```

**3. Claude Desktop Not Finding Server**
- Check file paths in configuration are correct
- Ensure Python executable path is correct
- Restart Claude Desktop after configuration changes
- Check Claude Desktop logs for error messages

**4. Path Issues on Windows**
- Use forward slashes or escaped backslashes in JSON
- Ensure no spaces in paths or quote the entire path
- Use absolute paths, not relative paths

**5. Permission Issues**
- Ensure Python executable has proper permissions
- Run Claude Desktop as administrator if needed
- Check that the virtual environment is accessible

### Getting Help

If you encounter issues:

1. Verify all paths in the MCP configuration are correct
2. Check that the virtual environment contains all dependencies
3. Ensure the Google API key is valid and properly configured
4. Check Claude Desktop logs for detailed error messages

## Next Steps

Once setup is complete:

1. **Test basic functionality** with simple ADM1 prompts
2. **Try the example workflow** from the README
3. **Generate your first report** using the ADM1 tools
4. **Explore advanced features** like custom feedstock analysis

## Performance Notes

- The MCP_TIMEOUT is set to 600000ms (10 minutes) to accommodate complex simulations
- Report generation may take 1-3 minutes depending on system performance
- Large simulations benefit from systems with 8GB+ RAM

---

Setup complete! Your ADM1 MCP Server is ready for professional anaerobic digestion modeling through Claude Desktop.