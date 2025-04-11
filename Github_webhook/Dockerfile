FROM node:22-alpine

WORKDIR /app
COPY package*.json ./
RUN npm install --omit=dev \
 && npm ls --depth=0 --omit=dev

COPY ./src ./

EXPOSE 3000

CMD ["npm", "start"]