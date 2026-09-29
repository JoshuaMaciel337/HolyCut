# HolyCut web — Next.js em modo standalone
FROM node:22-alpine AS dependencias
WORKDIR /repo/apps/web
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM node:22-alpine AS build
WORKDIR /repo
COPY brand /repo/brand
COPY apps/web /repo/apps/web
COPY --from=dependencias /repo/apps/web/node_modules /repo/apps/web/node_modules
WORKDIR /repo/apps/web
# Endereço da API dentro da rede do Docker. Entra no build porque os rewrites são gerados nele.
ARG API_URL_INTERNA=http://api:8000
ENV API_URL_INTERNA=$API_URL_INTERNA \
    NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0
COPY --from=build --chown=node /repo/apps/web/.next/standalone ./
COPY --from=build --chown=node /repo/apps/web/.next/static ./.next/static
COPY --from=build --chown=node /repo/apps/web/public ./public
USER node
EXPOSE 3000
CMD ["node", "server.js"]
