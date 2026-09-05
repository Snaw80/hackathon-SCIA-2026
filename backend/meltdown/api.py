from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from dotenv import load_dotenv
from .models import AnswerRequest, CommandRequest, ConfirmationRequest, RetryRequest
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
        return {
            "status": "ok",
            "agent": "llm",
            "model": getattr(app.state.service.policy, "name", type(app.state.service.policy).__name__),
        }

    @app.post("/api/games", status_code=201)
    def create_game():
        return app.state.service.create()

    @app.get("/api/games/{game_id}")
    def get_game(game_id: str):
        try:
            return app.state.service.get(game_id)
        except KeyError:
            raise HTTPException(404, "This game could not be found.") from None

    @app.post("/api/games/{game_id}/turns", status_code=202)
    def advance(game_id: str, request: CommandRequest):
        try:
            return app.state.service.start_turn(game_id, request)
        except KeyError:
            raise HTTPException(404, "This game could not be found.") from None
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from None

    @app.post("/api/games/{game_id}/runs/{run_id}/confirmation", status_code=202)
    def confirm(game_id: str, run_id: str, request: ConfirmationRequest):
        try:
            return app.state.service.confirm(game_id, run_id, request)
        except KeyError:
            raise HTTPException(404, "This round could not be found.") from None
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from None

    @app.post("/api/games/{game_id}/runs/{run_id}/answers", status_code=202)
    def answer(game_id: str, run_id: str, request: AnswerRequest):
        try:
            return app.state.service.answer(game_id, run_id, request)
        except KeyError:
            raise HTTPException(404, "This round could not be found.") from None
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from None

    @app.post("/api/games/{game_id}/runs/{run_id}/retry", status_code=202)
    def retry(game_id: str, run_id: str, request: RetryRequest):
        try:
            return app.state.service.retry(game_id, run_id, request)
        except KeyError:
            raise HTTPException(404, "This round could not be found.") from None
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
