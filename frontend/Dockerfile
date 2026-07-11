FROM node:22-alpine AS build
WORKDIR /app
COPY package.json tsconfig.json index.html ./
COPY src src
RUN npm install && npm run build
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
HEALTHCHECK --interval=10s --timeout=3s --retries=5 CMD wget -qO- http://127.0.0.1/health || exit 1
