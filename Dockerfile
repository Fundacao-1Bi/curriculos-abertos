ARG NODE_IMAGE=node:22.23.4-bookworm-slim
FROM ${NODE_IMAGE} AS dependencies
WORKDIR /app
RUN npm install --global npm@11.6.2 --cache /tmp/npm-cache \
 && rm -rf /tmp/npm-cache \
 && chown node:node /app
COPY --chown=node:node package.json package-lock.json ./
USER node
RUN npm ci --cache /tmp/npm-cache && rm -rf /tmp/npm-cache

FROM dependencies AS build
COPY --chown=node:node . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM build AS production
USER root
COPY pipeline/requirements.txt /tmp/pipeline-requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv poppler-utils tesseract-ocr tesseract-ocr-por tesseract-ocr-osd ca-certificates && rm -rf /var/lib/apt/lists/* \
 && python3 -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir -r /tmp/pipeline-requirements.txt
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PATH="/opt/venv/bin:$PATH"
RUN mkdir -p /app/var /app/data/raw /app/data/extracted && chown node:node /app/var /app/data /app/data/raw /app/data/extracted
USER node
EXPOSE 3000
CMD ["npm", "start"]
