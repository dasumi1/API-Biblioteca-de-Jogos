from fastapi import APIRouter, HTTPException, status
from schemas import LoginSchema

#definir prefixo para as rotas de autenticação
login_router= APIRouter(prefix="/login", tags=["login"])


@login_router.post("/", status_code=status.HTTP_200_OK)
async def validar_login(dados_login: LoginSchema):
    '''
    Rota para validar as credenciais de login.
    '''
    if dados_login.email == "usuario@esoft.com" and dados_login.password == "Abc123":
        return {"token": "550e8400-e29b-41d4-a716-446655440000"} 
    raise HTTPException(status_code=401, detail="Credenciais inválidas")