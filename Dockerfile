# 1. Build frontend
FROM node:20 AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend ./
RUN npm run build

# 2. Build backend
FROM python:3.12-slim AS backend
WORKDIR /app
COPY backend ./backend
COPY --from=frontend-build /app/frontend/dist ./frontend_dist
COPY serve_static.py ./serve_static.py
RUN pip install --upgrade pip
RUN pip install -r backend/requirements.txt

# 3. Expose port and run
EXPOSE 8000
CMD ["uvicorn", "serve_static:app", "--host", "0.0.0.0", "--port", "8000"] 