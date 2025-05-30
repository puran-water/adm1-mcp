# ADM1 MCP Server Deployment Guide

Deployment instructions for the ADM1 MCP Server across different environments and MCP client configurations.

## Overview

The ADM1 MCP Server is designed to run as a Model Context Protocol server that interfaces with MCP clients like Claude Desktop. This guide covers various deployment scenarios from development to production environments.

## Development Deployment

### Local Development Setup

```bash
# Clone repository
git clone https://github.com/puran-water/adm1-mcp.git
cd adm1-mcp

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your Google API key

# Test server locally
python server.py --test-mode
```

### Development with Hot Reload

For development with automatic restarts on code changes:

```bash
# Install development dependencies
pip install watchdog

# Create dev script
echo "watchmedo auto-restart --directory=. --pattern=*.py --recursive -- python server.py" > dev_run.sh
chmod +x dev_run.sh

# Run with hot reload
./dev_run.sh
```

## MCP Client Integration

### Claude Desktop Integration

#### Production Configuration

Add to your Claude Desktop MCP configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "adm1-mcp": {
      "command": "/path/to/your/venv/bin/python",
      "args": ["/path/to/adm1-mcp/server.py"],
      "env": {
        "MCP_TIMEOUT": "600000",
        "GOOGLE_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

#### Development Configuration

For development with debug output:

```json
{
  "mcpServers": {
    "adm1-mcp-dev": {
      "command": "/path/to/your/venv/bin/python",
      "args": ["/path/to/adm1-mcp/server.py", "--debug"],
      "env": {
        "MCP_TIMEOUT": "600000",
        "GOOGLE_API_KEY": "your_api_key_here",
        "DEBUG": "true"
      }
    }
  }
}
```

### Other MCP Clients

The server follows the standard MCP protocol and should work with any compliant MCP client. Basic client implementation:

```python
import json
import subprocess
import sys

class ADM1MCPClient:
    def __init__(self, server_path, python_path):
        self.process = subprocess.Popen(
            [python_path, server_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    
    def call_tool(self, tool_name, arguments):
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            },
            "id": 1
        }
        
        self.process.stdin.write(json.dumps(request) + "\n")
        self.process.stdin.flush()
        
        response = self.process.stdout.readline()
        return json.loads(response)
```

## Production Deployment

### Docker Deployment

#### Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m adm1user && chown -R adm1user:adm1user /app
USER adm1user

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Run the MCP server
CMD ["python", "server.py"]
```

#### Docker Compose

```yaml
version: '3.8'
services:
  adm1-mcp-server:
    build: .
    environment:
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
    volumes:
      - ./generated_reports:/app/generated_reports
    stdin_open: true
    tty: true
```

#### Build and Run

```bash
# Build Docker image
docker build -t adm1-mcp-server .

# Run with environment variables
docker run -it --env-file .env adm1-mcp-server
```

### Virtual Environment Deployment

For production deployment on a server:

```bash
# Create production virtual environment
python3 -m venv /opt/adm1-mcp/venv
source /opt/adm1-mcp/venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up service
sudo tee /etc/systemd/system/adm1-mcp.service > /dev/null <<EOF
[Unit]
Description=ADM1 MCP Server
After=network.target

[Service]
Type=simple
User=adm1
Environment=GOOGLE_API_KEY=your_api_key_here
ExecStart=/opt/adm1-mcp/venv/bin/python /opt/adm1-mcp/server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl enable adm1-mcp
sudo systemctl start adm1-mcp
```

## Configuration Management

### Environment Variables

Production environment variables:

```bash
# Required
GOOGLE_API_KEY=your_production_api_key

# Optional
DEBUG=false
MCP_TIMEOUT=600000
MAX_SIMULATION_TIME=300
REPORT_CACHE_TTL=3600
```

### Configuration File

Create `config.yaml` for advanced configuration:

```yaml
server:
  debug: false
  max_workers: 4
  timeout: 600

simulation:
  max_time: 300
  default_timestep: 0.1
  cache_results: true

reports:
  cache_ttl: 3600
  output_format: html
  include_technical: false

ai_assistant:
  provider: google
  model: gemini-pro
  timeout: 30
```

## Security Considerations

### API Key Management

**Development:**
```bash
# Use .env file
GOOGLE_API_KEY=your_dev_key
```

**Production:**
```bash
# Use environment variables or secrets management
export GOOGLE_API_KEY="your_prod_key"

# Or use systemd service with Environment directive
# Or use Docker secrets
```

### Input Validation

The server includes built-in input validation for all tools. Additional validation can be added:

```python
from pydantic import BaseModel, validator

class FeedstockInput(BaseModel):
    description: str
    
    @validator('description')
    def description_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Description cannot be empty')
        if len(v) > 10000:
            raise ValueError('Description too long')
        return v
```

## Monitoring and Logging

### Basic Logging

```python
import logging
import sys
from datetime import datetime

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'adm1_server_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler(sys.stderr)
    ]
)
```

### Health Monitoring

Create a simple health check:

```python
# Add to server.py
@mcp.tool()
def health_check():
    """Check server health and dependencies"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "dependencies": {
            "qsdsan": True,
            "google_ai": bool(os.getenv("GOOGLE_API_KEY")),
            "templates": os.path.exists("templates/professional_template.ipynb")
        }
    }
```

## Performance Optimization

### Memory Management

```python
import gc
import psutil

def cleanup_after_simulation():
    gc.collect()
    
    # Monitor memory usage
    memory_percent = psutil.virtual_memory().percent
    if memory_percent > 80:
        logging.warning(f"High memory usage: {memory_percent}%")
```

### Caching

```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=100)
def cached_simulation(feedstock_hash, params_hash):
    # Implement caching for repeated simulations
    pass
```

## Troubleshooting

### Common Production Issues

**1. Memory Issues**
```bash
# Monitor memory usage
ps aux | grep python | grep server.py

# Add memory limits in Docker
docker run --memory=2g adm1-mcp-server
```

**2. API Rate Limits**
```bash
# Implement exponential backoff
# Monitor Google API usage in console
# Consider caching AI responses
```

**3. Report Generation Failures**
```bash
# Check disk space
df -h

# Verify Quarto installation
quarto --version

# Check template permissions
ls -la templates/
```

### Debug Mode

Enable debug mode for troubleshooting:

```bash
# Set environment variable
export DEBUG=true

# Or pass command line argument
python server.py --debug
```

## Testing Deployment

### Smoke Tests

```bash
#!/bin/bash
# smoke_test.sh

echo "Testing ADM1 MCP Server deployment..."

# Test basic imports
python -c "import qsdsan; print('QSDsan: OK')"
python -c "import google.generativeai; print('Google AI: OK')"

# Test server startup
timeout 10s python server.py --test-mode

echo "Deployment tests completed"
```

### Integration Tests

```python
# test_integration.py
def test_mcp_client_integration():
    # Test that server responds to MCP protocol
    client = ADM1MCPClient("server.py", "python")
    
    # Test tool listing
    response = client.call_tool("list_tools", {})
    assert "describe_feedstock" in [tool["name"] for tool in response["tools"]]
    
    # Test basic tool call
    response = client.call_tool("describe_feedstock", {
        "description": "Test feedstock"
    })
    assert response["success"] == True
```

## Deployment Checklist

### Pre-Deployment
- [ ] Virtual environment created and dependencies installed
- [ ] Environment variables configured securely
- [ ] Google API key tested and validated
- [ ] All tests passing
- [ ] Documentation updated

### Deployment
- [ ] Server deployed to target environment
- [ ] MCP client configuration updated
- [ ] Health checks passing
- [ ] Monitoring configured
- [ ] Backup procedures documented

### Post-Deployment
- [ ] Smoke tests completed
- [ ] MCP client integration verified
- [ ] Performance monitoring active
- [ ] Error handling tested
- [ ] Documentation accessible

---

Your ADM1 MCP Server is ready for deployment across development, staging, and production environments with proper monitoring and security measures.