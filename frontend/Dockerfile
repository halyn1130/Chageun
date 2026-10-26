# ---- build ----
FROM node:22-alpine AS build
WORKDIR /src/frontend
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# src/maintenanceRules.js가 ../../ai_data/chageun_ai/maintenance_rules.json을 import한다 (compose additional_contexts)
COPY --from=chageun_ai maintenance_rules.json /src/ai_data/chageun_ai/
# 프론트에는 TTS 제공자 플래그만 넣는다 (API 키 금지)
ARG VITE_TTS_PROVIDER=typecast
ENV VITE_TTS_PROVIDER=$VITE_TTS_PROVIDER
RUN npm run build

# ---- run ----
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /src/frontend/dist /usr/share/nginx/html
EXPOSE 80
