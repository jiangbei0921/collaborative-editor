FROM node:20 AS web-builder
WORKDIR /app/web
COPY apps/web/package*.json ./
RUN npm ci
COPY apps/web/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
WORKDIR /app

COPY apps/server/requirements.txt ./server/
RUN pip install --no-cache-dir -r server/requirements.txt

COPY apps/server/ ./server/

COPY --from=web-builder /app/web/dist ./web/dist

ENV PYTHONPATH=/app/server
ENV PORT=8000
ENV DATABASE_PATH=/app/data/editor.db

RUN mkdir -p /app/data

EXPOSE 8000

CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]