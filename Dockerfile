FROM python:3.13-slim

WORKDIR /app

COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8001
ENV MCP_PATH=/mcp
ENV MCP_ALLOWED_HOSTS=0.0.0.0:*,127.0.0.1:*,localhost:*
ENV MCP_ALLOWED_ORIGINS=http://127.0.0.1:*,http://localhost:*
ENV MCP_API_KEY=
ENV MCP_RATE_LIMIT_REQUESTS=60
ENV MCP_RATE_LIMIT_WINDOW_SECONDS=60
ENV SESSION_TTL_SECONDS=1800
ENV SESSION_MAX_SESSIONS=1000
ENV INFERENCE_PROVIDER=mock
ENV BEDROCK_MODEL_ID=
ENV AWS_REGION=us-east-1

EXPOSE 8001

CMD ["python", "-m", "server.mcp_server"]
