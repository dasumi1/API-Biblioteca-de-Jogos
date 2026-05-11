from fastapi import APIRouter, HTTPException, status, Depends
from schemas import JogoSchema, JogoResponse
from models import Jogo
from sqlalchemy.orm import Session
from dependencies import pegar_sessao

#definir prefixo para as rotas de jogos
jogos_router = APIRouter(prefix="/jogos", tags=["jogos"])


@jogos_router.get("/", status_code=status.HTTP_200_OK, response_model=list[JogoResponse])
async def get_jogos(db: Session = Depends(pegar_sessao)):
    '''Rota para obter todos os jogos.
    '''
    return db.query(Jogo).all()


@jogos_router.get("/{id}", status_code=status.HTTP_200_OK, response_model=JogoResponse)
async def get_jogo(id: int, db: Session = Depends(pegar_sessao)):
    '''Rota para obter um jogo por ID.
    ''' 
    jogo = db.query(Jogo).filter(Jogo.id == id).first()
    if not jogo:
        raise HTTPException(status_code=404, detail="Jogo não encontrado")
    return jogo



@jogos_router.post("/", status_code=status.HTTP_201_CREATED, response_model=JogoResponse)
async def cadastrar_review(jogo_schema: JogoSchema, db: Session = Depends(pegar_sessao)):
    '''Rota para cadastrar uma nova review.
    '''
    novo_jogo = Jogo(
        nome=jogo_schema.nome,
        tipo=jogo_schema.tipo,
        nota=jogo_schema.nota,
        review=jogo_schema.review
    )
    db.add(novo_jogo)
    db.commit()     
    db.refresh(novo_jogo)
    return novo_jogo


@jogos_router.put("/{id}", status_code=status.HTTP_200_OK, response_model=JogoResponse)
async def atualizar_jogo(id: int, jogo_schema: JogoSchema, db: Session = Depends(pegar_sessao)):
    '''Atualiza todos os dados de um jogo.'''
    jogo = db.query(Jogo).filter(Jogo.id == id).first()
    if not jogo:
        raise HTTPException(status_code=404, detail="Jogo não encontrado")

    jogo.nome = jogo_schema.nome
    jogo.tipo = jogo_schema.tipo
    jogo.nota = jogo_schema.nota
    jogo.review = jogo_schema.review

    db.commit()
    db.refresh(jogo)
    return jogo
             

@jogos_router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT) 
async def deletar_jogo(id: int, db: Session = Depends(pegar_sessao)):
    '''Remove uma review.'''
    jogo = db.query(Jogo).filter(Jogo.id == id).first()
    if not jogo:
        raise HTTPException(status_code=404, detail="Jogo não encontrado")

    db.delete(jogo)
    db.commit()
    