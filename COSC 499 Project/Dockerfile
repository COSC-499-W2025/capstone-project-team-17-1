FROM node:20-bullseye
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
# default does a dependency smoke step; override with CMD in compose when needed
CMD ["npm","run","start"]
