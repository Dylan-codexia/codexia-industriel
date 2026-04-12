from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from core.database import engine, Base
from routers import auth, users, progression, missions, objectifs, notifications

# ──────────────────────────────────────────────
# CRÉATION DES TABLES EN BASE
# ──────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

# ──────────────────────────────────────────────
# APPLICATION FASTAPI
# ──────────────────────────────────────────────
app = FastAPI(
    title="CODEX INDUSTRIEL API",
    description="Backend du système de progression industrielle gamifié",
    version="1.0.0",
)

# CORS — autorise le frontend à communiquer avec le backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production : remplacer par l'URL exacte du frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
# ROUTES API
# ──────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(progression.router)
app.include_router(missions.router)
app.include_router(objectifs.router)
app.include_router(notifications.router)

# ──────────────────────────────────────────────
# SERVIR LE FRONTEND HTML
# ──────────────────────────────────────────────
frontend_path = os.path.join(os.path.dirname(__file__), "../frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/", include_in_schema=False)
    def serve_frontend():
        return FileResponse(os.path.join(frontend_path, "index.html"))

# ──────────────────────────────────────────────
# ROUTE DE SANTÉ (vérifier que le serveur tourne)
# ──────────────────────────────────────────────
@app.get("/health")
def health_check():
    return {"status": "ok", "app": "CODEX INDUSTRIEL", "version": "1.0.0"}
