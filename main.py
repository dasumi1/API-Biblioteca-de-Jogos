from fastapi import FastAPI

app = FastAPI()

from rotas_login import login_router
from rotas_jogos import jogos_router

app.include_router(login_router)
app.include_router(jogos_router)


