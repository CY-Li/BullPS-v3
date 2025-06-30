from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from backend.main import app as backend_app
from starlette.responses import FileResponse
import os

app = FastAPI()

# 掛載 API
app.mount("/api", backend_app)

# 掛載前端靜態檔
app.mount("/", StaticFiles(directory="frontend_dist", html=True), name="static")

# 讓 SPA 路由都回傳 index.html
@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    index_path = os.path.join("frontend_dist", "index.html")
    return FileResponse(index_path) 