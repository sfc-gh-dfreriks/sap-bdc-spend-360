# syntax=docker/dockerfile:1
# Multi-stage build for the Supply Chain 360 Native App container.
# Stage 1 builds the Vite React client and compiles the Express server;
# stage 2 is a slim runtime that serves both the API and the static client.

FROM node:20-bookworm-slim AS build
WORKDIR /app
# Install all workspace deps (root package.json declares client + server workspaces)
COPY package.json package-lock.json ./
COPY client/package.json ./client/package.json
COPY server/package.json ./server/package.json
RUN npm ci
# Build client (-> client/dist) and server (-> server/dist)
COPY . .
RUN npm run build

FROM node:20-bookworm-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production
# Hoisted production deps + build outputs
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/package.json ./package.json
COPY --from=build /app/server/package.json ./server/package.json
COPY --from=build /app/server/dist ./server/dist
COPY --from=build /app/client/dist ./client/dist

# SPCS listens on this port; align with service_spec.yml + readinessProbe
ENV PORT=8080
ENV CLIENT_DIST=/app/client/dist
EXPOSE 8080
CMD ["node", "server/dist/index.js"]
