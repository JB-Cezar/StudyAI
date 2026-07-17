import logging

from dotenv import load_dotenv

# Precisa rodar antes de importar os routers: app.auth.service lê
# GOOGLE_CLIENT_ID/SECRET e JWT_SECRET como constantes de módulo (não
# preguiçosamente, diferente do gemini_client), então o .env já tem que
# estar carregado no momento do import.
load_dotenv()

# Sem isso, logger.exception() em módulos como app.ai.router não tem garantia
# de aparecer no stdout capturado pelo Render — fica só no "handler de
# último recurso" do Python, que nem sempre é visível.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from app.ai.router import router as chat_router  # noqa: E402
from app.auth.router import router as auth_router  # noqa: E402
from app.calendar.router import router as calendar_router  # noqa: E402
from app.core.env import clean_env  # noqa: E402

app = FastAPI(title="StudyAI API")

ENVIRONMENT = clean_env("ENVIRONMENT", "development")
FRONTEND_URL = clean_env("FRONTEND_URL", "http://localhost:5173")

if ENVIRONMENT == "production":
    # Origem exata do frontend hospedado — nada de regex em produção.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[FRONTEND_URL],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        # Regex (não lista fixa) porque o Vite sobe em outra porta quando a
        # 5173 já está ocupada por outro projeto na máquina.
        allow_origin_regex=r"http://localhost:\d+",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(auth_router)
app.include_router(calendar_router)
app.include_router(chat_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
