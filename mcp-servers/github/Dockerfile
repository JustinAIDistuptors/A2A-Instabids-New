FROM node:18-alpine
WORKDIR /app
RUN apk add --no-cache git
COPY mcp-servers/github/package*.json ./
RUN npm install
COPY . .
EXPOSE 3001
CMD ["node", "server.js"]
