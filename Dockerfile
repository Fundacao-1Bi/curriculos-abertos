ARG NODE_IMAGE=node:22.23.4-bookworm-slim
FROM ${NODE_IMAGE} AS dependencies
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm install --global npm@11.6.2 && npm ci

FROM dependencies AS build
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM ${NODE_IMAGE} AS production
WORKDIR /app
COPY pipeline/requirements.txt /tmp/pipeline-requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv poppler-utils tesseract-ocr tesseract-ocr-por tesseract-ocr-osd ca-certificates && rm -rf /var/lib/apt/lists/* \
 && python3 -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir -r /tmp/pipeline-requirements.txt && npm install --global npm@11.6.2
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PATH="/opt/venv/bin:$PATH"
COPY --from=build --chown=node:node /app ./
RUN mkdir -p /app/var /app/data/raw /app/data/extracted && chown -R node:node /app/var /app/data
USER node
EXPOSE 3000
CMD ["npm", "start"]
