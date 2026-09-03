from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from dotenv import load_dotenv
from .models import TurnRequest
from .service import GameService

load_dotenv()


def create_app(db_path=None, policy=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.service = GameService(
            db_path or Path(os.environ.get("MELTDOWN_DB", ".data/meltdown.sqlite")), policy=policy
        )
        yield
        app.state.service.close()

    app = FastAPI(title="Project Meltdown", version="0.1.0", lifespan=lifespan)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "mode": app.state.service.policy.mode}

    @app.post("/api/games", status_code=201)
    def create_game():
        return app.state.service.create()

    @app.get("/api/games/{game_id}")
    def get_game(game_id: str):
        try:
            return app.state.service.get(game_id)
        except KeyError:
            raise HTTPException(404, "Cette partie est introuvable.") from None

    @app.post("/api/games/{game_id}/turns")
    def advance(game_id: str, request: TurnRequest):
        try:
            return app.state.service.advance(game_id, request)
        except KeyError:
            raise HTTPException(404, "Cette partie est introuvable.") from None
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from None

    @app.get("/api/games/{game_id}/export")
    def export(game_id: str):
        game = get_game(game_id)
        return Response(
            json.dumps(game, indent=2, ensure_ascii=False),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="meltdown-{game["id"]}.json"'},
        )

    return app


app = create_app()
