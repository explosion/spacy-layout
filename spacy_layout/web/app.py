"""
Application FastAPI principale.
"""

import os
import asyncio
from typing import Dict, Optional
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
from datetime import datetime

from spacy_layout.training import AutoFineTuner
from spacy_layout.training.config import Config, AristoteConfig
from spacy_layout.training.data_loader import DataLoader


# État global de l'application
app_state = {
    "current_run": None,
    "is_running": False,
    "fine_tuner": None,
    "websocket_clients": [],
}


# Création de l'app FastAPI
app = FastAPI(
    title="spaCy Layout - Fine-Tuning Automatisé",
    description="Interface web pour le fine-tuning automatisé de modèles NER",
    version="0.1.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Monte les fichiers statiques
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ============================================================================
# WebSocket pour notifications temps réel
# ============================================================================

@app.websocket("/ws/training")
async def websocket_training(websocket: WebSocket):
    """WebSocket pour le suivi en temps réel du training."""
    await websocket.accept()
    app_state["websocket_clients"].append(websocket)

    try:
        while True:
            # Garde la connexion ouverte
            await websocket.receive_text()
    except WebSocketDisconnect:
        app_state["websocket_clients"].remove(websocket)


async def broadcast_message(message: Dict):
    """Envoie un message à tous les clients WebSocket connectés."""
    disconnected = []
    for client in app_state["websocket_clients"]:
        try:
            await client.send_json(message)
        except Exception:
            disconnected.append(client)

    # Nettoie les clients déconnectés
    for client in disconnected:
        app_state["websocket_clients"].remove(client)


# ============================================================================
# Routes API
# ============================================================================

@app.get("/")
async def root():
    """Page d'accueil."""
    templates_dir = Path(__file__).parent / "templates"
    index_file = templates_dir / "index.html"

    if index_file.exists():
        return FileResponse(index_file)
    else:
        return HTMLResponse(content="""
        <html>
            <head><title>spaCy Layout Fine-Tuning</title></head>
            <body>
                <h1>spaCy Layout - Fine-Tuning Automatisé</h1>
                <p>Interface web en cours de développement...</p>
                <p>Utilisez l'API REST directement :</p>
                <ul>
                    <li><a href="/docs">Documentation API (Swagger)</a></li>
                    <li><a href="/redoc">Documentation API (ReDoc)</a></li>
                </ul>
            </body>
        </html>
        """)


@app.get("/api/status")
async def get_status():
    """Récupère le statut actuel du training."""
    return {
        "is_running": app_state["is_running"],
        "current_run": app_state["current_run"],
    }


@app.get("/api/data/stats")
async def get_data_stats(data_dir: str = "./data"):
    """Récupère les statistiques des données."""
    try:
        loader = DataLoader(data_dir)
        stats = loader.get_stats()

        entities = loader.load_all_entities()
        entities_info = {}
        for label, entity_list in entities.items():
            if isinstance(entity_list, dict):
                entities_info[label] = {
                    school_type: len(el.entities)
                    for school_type, el in entity_list.items()
                }
            else:
                entities_info[label] = len(entity_list.entities)

        return {
            "stats": stats,
            "entities": entities_info,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/upload/entities")
async def upload_entities(
    file: UploadFile = File(...),
    entity_type: str = Form(...),
    school_type: Optional[str] = Form(None),
):
    """Upload un fichier d'entités."""
    try:
        # Détermine le répertoire de destination
        if entity_type == "STUDENT_NAME":
            dest_dir = Path("./data/entities/students")
        elif entity_type == "SCHOOL":
            if school_type:
                dest_dir = Path(f"./data/entities/schools")
            else:
                dest_dir = Path("./data/entities/schools")
        elif entity_type == "PROGRAM":
            dest_dir = Path("./data/entities/programs")
        else:
            dest_dir = Path(f"./data/entities/{entity_type.lower()}")

        dest_dir.mkdir(parents=True, exist_ok=True)

        # Sauvegarde le fichier
        file_path = dest_dir / file.filename
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        return {"message": f"Fichier {file.filename} uploadé avec succès", "path": str(file_path)}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/upload/document")
async def upload_document(
    file: UploadFile = File(...),
    split: str = Form("train"),  # train ou test
):
    """Upload un document d'entraînement ou de test."""
    try:
        dest_dir = Path(f"./data/documents/{split}")
        dest_dir.mkdir(parents=True, exist_ok=True)

        file_path = dest_dir / file.filename
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        return {"message": f"Document {file.filename} uploadé avec succès", "path": str(file_path)}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/training/start")
async def start_training(
    base_model: str = Form("fr_core_news_lg"),
    threshold: float = Form(98.0),
    max_iterations: int = Form(20),
    api_key: Optional[str] = Form(None),
):
    """Démarre le processus de fine-tuning."""
    if app_state["is_running"]:
        return JSONResponse(status_code=400, content={"error": "Un training est déjà en cours"})

    try:
        # Prépare la configuration
        config = Config(
            aristote_api=AristoteConfig(api_key=api_key),
            success_threshold=threshold,
            max_iterations=max_iterations,
        )

        # Callbacks pour WebSocket
        async def on_iteration_start(iteration: int):
            await broadcast_message({
                "type": "iteration_start",
                "iteration": iteration,
                "timestamp": datetime.now().isoformat(),
            })

        async def on_iteration_end(iteration: int, score: float):
            await broadcast_message({
                "type": "iteration_end",
                "iteration": iteration,
                "score": score,
                "timestamp": datetime.now().isoformat(),
            })

        async def on_prompt_display(prompt_type: str, prompt: str):
            await broadcast_message({
                "type": "prompt_display",
                "prompt_type": prompt_type,
                "prompt": prompt,
                "timestamp": datetime.now().isoformat(),
            })

        # Crée le fine-tuner
        fine_tuner = AutoFineTuner(
            base_model=base_model,
            data_dir="./data",
            config=config,
            on_iteration_start=lambda it: asyncio.create_task(on_iteration_start(it)),
            on_iteration_end=lambda it, sc: asyncio.create_task(on_iteration_end(it, sc)),
            on_prompt_display=lambda pt, pr: asyncio.create_task(on_prompt_display(pt, pr)),
        )

        # Marque comme en cours
        app_state["is_running"] = True
        app_state["fine_tuner"] = fine_tuner
        run_id = fine_tuner.metrics_manager.run_id if hasattr(fine_tuner, "metrics_manager") else "unknown"
        app_state["current_run"] = run_id

        # Lance le training en arrière-plan
        async def run_training():
            try:
                results = fine_tuner.run()
                app_state["is_running"] = False

                await broadcast_message({
                    "type": "training_complete",
                    "results": results,
                    "timestamp": datetime.now().isoformat(),
                })

            except Exception as e:
                app_state["is_running"] = False
                await broadcast_message({
                    "type": "training_error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                })

        # Lance en background
        asyncio.create_task(run_training())

        return {
            "message": "Training démarré",
            "run_id": run_id,
        }

    except Exception as e:
        app_state["is_running"] = False
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/models/list")
async def list_models():
    """Liste les modèles spaCy disponibles."""
    # TODO: implémenter la détection des modèles installés
    return {
        "models": [
            "fr_core_news_sm",
            "fr_core_news_md",
            "fr_core_news_lg",
        ]
    }


@app.get("/api/results/{run_id}")
async def get_results(run_id: str):
    """Récupère les résultats d'un run."""
    try:
        summary_file = Path(f"./logs/run_{run_id}/summary.json")

        if not summary_file.exists():
            return JSONResponse(status_code=404, content={"error": "Run non trouvé"})

        with open(summary_file, "r") as f:
            data = json.load(f)

        return data

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ============================================================================
# Point d'entrée
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
