FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# Dummy values so Auth0Client can instantiate during `next build`.
# These are NOT used at runtime — Railway injects the real secrets via env vars.
ENV AUTH0_SECRET=build-placeholder-secret-at-least-32-characters-long
ENV AUTH0_ISSUER_BASE_URL=https://placeholder.auth0.com
ENV AUTH0_CLIENT_ID=placeholder
ENV AUTH0_CLIENT_SECRET=placeholder
ENV AUTH0_BASE_URL=http://localhost:3000
ENV AUTH0_AUDIENCE=https://placeholder.api

RUN npm run build

FROM node:20-alpine

WORKDIR /app

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

CMD ["node", "server.js"]
