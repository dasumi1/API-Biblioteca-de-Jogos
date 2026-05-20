from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

from rotas_login import login_router
from rotas_jogos import jogos_router

app.include_router(login_router)
app.include_router(jogos_router)


