FROM python:3.13-slim

WORKDIR /app

COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8001
ENV MCP_PATH=/mcp
ENV MCP_ALLOWED_HOSTS=0.0.0.0:*,127.0.0.1:*,localhost:*
ENV MCP_ALLOWED_ORIGINS=http://127.0.0.1:*,http://localhost:*
ENV MCP_API_KEY=
ENV MCP_RATE_LIMIT_REQUESTS=0
ENV MCP_RATE_LIMIT_WINDOW_SECONDS=60

EXPOSE 8001

CMD ["python", "-m", "server.mcp_server"]
