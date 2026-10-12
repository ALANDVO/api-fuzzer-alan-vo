FROM node:24-slim AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci --no-audit --no-fund

COPY . .
RUN npm run build

FROM node:24-slim

WORKDIR /app

RUN npm install -g serve --no-audit --no-fund

COPY --from=builder /app/dist ./dist

USER node

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s \
    CMD node -e "fetch('http://127.0.0.1:3000').then(r=>r.ok?process.exit(0):process.exit(1)).catch(()=>process.exit(1))"

CMD ["serve", "-s", "dist", "-l", "3000"]
