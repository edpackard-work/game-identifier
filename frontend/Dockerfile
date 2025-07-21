# Stage 1: Build
FROM --platform=linux/amd64 node:22.17.1 AS builder
WORKDIR /app
COPY . .
RUN npm ci
RUN npm run build

# Stage 2: Serve with nginx
FROM nginx:1.25-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"] 