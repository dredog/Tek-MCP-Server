# =============================================================================
# Tektronix MCP Server — Dockerfile for Railway deployment
# =============================================================================

FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (cached layer — only rebuilds when requirements change)
COPY requirements-railway.txt .
RUN pip install --no-cache-dir -r requirements-railway.txt

# Copy server and all supporting files
COPY tektronix_mcp_server.py .
COPY generate_usage_boosts.py .
COPY usage_boosts_generated.py .
COPY docs/ ./docs/
COPY PTA/ ./PTA/

# TEK_INSTALL_PATH tells the server where to find docs/ and PTA/
ENV TEK_INSTALL_PATH=/app

# Railway injects PORT automatically — the server detects it and switches
# to streamable-http transport. No need to set PORT here.
CMD ["python", "tektronix_mcp_server.py"]
