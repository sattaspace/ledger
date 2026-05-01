#sattaledger/frontend/Dockerfile
# Stage 1: Build
FROM node:24-alpine AS build-stage

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Stage 2: Production Server
FROM node:24-alpine AS production-stage
WORKDIR /app
RUN npm install -g serve
COPY --from=build-stage /app/dist ./dist

USER node
EXPOSE 4321

# Serve the build folder
CMD ["serve", "dist", "-l", "4321"]