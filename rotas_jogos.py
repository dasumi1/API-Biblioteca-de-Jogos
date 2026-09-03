from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import asc, desc, func
from sqlalchemy.orm import Session

from dependencies import pegar_sessao
from models import Jogo
from schemas import JogoResponse, JogoSchema


jogos_router = APIRouter(prefix="/jogos", tags=["jogos"])


# -----------------------------------------------------------------------------
# Schemas auxiliares
# -----------------------------------------------------------------------------


class JogoPatchSchema(BaseModel):
    """Campos opcionais usados para atualização parcial de um jogo."""

    nome: Optional[str] = Field(default=None, min_length=1, max_length=100)
    tipo: Optional[str] = Field(default=None, min_length=1, max_length=50)
    nota: Optional[int] = Field(default=None, ge=0, le=10)
    review: Optional[str] = Field(default=None, min_length=1, max_length=255)


class JogoResumoResponse(BaseModel):
    """Resumo estatístico da biblioteca de jogos."""

    total_jogos: int
    nota_media: float
    maior_nota: Optional[int]
    menor_nota: Optional[int]
    total_tipos: int


class TipoResumoResponse(BaseModel):
    """Quantidade de jogos e média de nota para um determinado tipo."""

    tipo: str
    quantidade: int
    nota_media: float


class PaginacaoResponse(BaseModel):
    """Resposta paginada usada na rota de listagem avançada."""

    pagina: int
    por_pagina: int
    total_itens: int
    total_paginas: int
    itens: list[JogoResponse]


class BulkDeleteRequest(BaseModel):
    """Lista de IDs usada para remoção em lote."""

    ids: list[int] = Field(min_length=1, max_length=100)


class BulkDeleteResponse(BaseModel):
    """Resultado da remoção em lote."""

    removidos: int
    ids_removidos: list[int]
    ids_nao_encontrados: list[int]


class NotaDistribuicaoResponse(BaseModel):
    """Representa quantos jogos existem para determinada nota."""

    nota: int
    quantidade: int


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _normalizar_texto(valor: str) -> str:
    """Remove espaços externos e rejeita textos vazios."""

    valor_normalizado = valor.strip()
    if not valor_normalizado:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O valor informado não pode ser vazio.",
        )
    return valor_normalizado


def _validar_nota(nota: int) -> int:
    """Garante que a nota permaneça na escala de zero a dez."""

    if nota < 0 or nota > 10:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A nota deve estar entre 0 e 10.",
        )
    return nota


def _buscar_jogo_ou_404(db: Session, jogo_id: int) -> Jogo:
    """Busca um jogo por ID ou encerra a requisição com 404."""

    jogo = db.query(Jogo).filter(Jogo.id == jogo_id).first()
    if jogo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jogo não encontrado",
        )
    return jogo


def _normalizar_payload_completo(jogo_schema: JogoSchema) -> dict:
    """Converte o schema existente em dados normalizados para persistência."""

    return {
        "nome": _normalizar_texto(jogo_schema.nome),
        "tipo": _normalizar_texto(jogo_schema.tipo),
        "nota": _validar_nota(jogo_schema.nota),
        "review": _normalizar_texto(jogo_schema.review),
    }


def _calcular_total_paginas(total_itens: int, por_pagina: int) -> int:
    """Calcula o número de páginas sem depender de bibliotecas externas."""

    if total_itens == 0:
        return 0
    return (total_itens + por_pagina - 1) // por_pagina


def _ordenacao_coluna(campo: str):
    """Mapeia nomes públicos de ordenação para colunas do SQLAlchemy."""

    mapa = {
        "id": Jogo.id,
        "nome": Jogo.nome,
        "tipo": Jogo.tipo,
        "nota": Jogo.nota,
    }
    return mapa[campo]


# -----------------------------------------------------------------------------
# Rotas de consulta agregada
# Devem aparecer antes de /{id} para evitar conflito com rotas dinâmicas.
# -----------------------------------------------------------------------------


@jogos_router.get(
    "/estatisticas",
    status_code=status.HTTP_200_OK,
    response_model=JogoResumoResponse,
)
async def obter_estatisticas(db: Session = Depends(pegar_sessao)):
    """Retorna indicadores gerais da biblioteca de jogos."""

    total_jogos = db.query(func.count(Jogo.id)).scalar() or 0
    nota_media = db.query(func.avg(Jogo.nota)).scalar()
    maior_nota = db.query(func.max(Jogo.nota)).scalar()
    menor_nota = db.query(func.min(Jogo.nota)).scalar()
    total_tipos = db.query(func.count(func.distinct(Jogo.tipo))).scalar() or 0

    return JogoResumoResponse(
        total_jogos=total_jogos,
        nota_media=round(float(nota_media or 0), 2),
        maior_nota=maior_nota,
        menor_nota=menor_nota,
        total_tipos=total_tipos,
    )


@jogos_router.get(
    "/tipos",
    status_code=status.HTTP_200_OK,
    response_model=list[TipoResumoResponse],
)
async def listar_tipos(db: Session = Depends(pegar_sessao)):
    """Agrupa jogos por tipo e informa quantidade e nota média."""

    resultados = (
        db.query(
            Jogo.tipo,
            func.count(Jogo.id).label("quantidade"),
            func.avg(Jogo.nota).label("nota_media"),
        )
        .group_by(Jogo.tipo)
        .order_by(asc(Jogo.tipo))
        .all()
    )

    return [
        TipoResumoResponse(
            tipo=tipo,
            quantidade=quantidade,
            nota_media=round(float(nota_media or 0), 2),
        )
        for tipo, quantidade, nota_media in resultados
    ]


@jogos_router.get(
    "/distribuicao-notas",
    status_code=status.HTTP_200_OK,
    response_model=list[NotaDistribuicaoResponse],
)
async def distribuicao_notas(db: Session = Depends(pegar_sessao)):
    """Retorna a distribuição de jogos por nota, de zero a dez."""

    resultados = (
        db.query(Jogo.nota, func.count(Jogo.id).label("quantidade"))
        .group_by(Jogo.nota)
        .order_by(asc(Jogo.nota))
        .all()
    )

    contagem = {nota: quantidade for nota, quantidade in resultados}

    return [
        NotaDistribuicaoResponse(
            nota=nota,
            quantidade=contagem.get(nota, 0),
        )
        for nota in range(0, 11)
    ]


@jogos_router.get(
    "/top",
    status_code=status.HTTP_200_OK,
    response_model=list[JogoResponse],
)
async def listar_melhores_jogos(
    limite: int = Query(default=5, ge=1, le=50),
    tipo: Optional[str] = Query(default=None, min_length=1, max_length=50),
    db: Session = Depends(pegar_sessao),
):
    """Lista os jogos de maior nota, opcionalmente filtrados por tipo."""

    query = db.query(Jogo)

    if tipo is not None:
        tipo_normalizado = tipo.strip()
        query = query.filter(func.lower(Jogo.tipo) == tipo_normalizado.lower())

    return (
        query.order_by(desc(Jogo.nota), asc(Jogo.nome))
        .limit(limite)
        .all()
    )


@jogos_router.get(
    "/buscar",
    status_code=status.HTTP_200_OK,
    response_model=list[JogoResponse],
)
async def buscar_jogos(
    termo: str = Query(min_length=1, max_length=100),
    limite: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(pegar_sessao),
):
    """Busca jogos pelo nome, tipo ou conteúdo da review."""

    termo_normalizado = termo.strip()
    if not termo_normalizado:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O termo de busca não pode ser vazio.",
        )

    padrao = f"%{termo_normalizado}%"

    return (
        db.query(Jogo)
        .filter(
            (Jogo.nome.ilike(padrao))
            | (Jogo.tipo.ilike(padrao))
            | (Jogo.review.ilike(padrao))
        )
        .order_by(desc(Jogo.nota), asc(Jogo.nome))
        .limit(limite)
        .all()
    )


@jogos_router.get(
    "/paginados",
    status_code=status.HTTP_200_OK,
    response_model=PaginacaoResponse,
)
async def listar_jogos_paginados(
    pagina: int = Query(default=1, ge=1),
    por_pagina: int = Query(default=10, ge=1, le=100),
    nome: Optional[str] = Query(default=None, max_length=100),
    tipo: Optional[str] = Query(default=None, max_length=50),
    nota_minima: Optional[int] = Query(default=None, ge=0, le=10),
    nota_maxima: Optional[int] = Query(default=None, ge=0, le=10),
    ordenar_por: Literal["id", "nome", "tipo", "nota"] = Query(default="id"),
    ordem: Literal["asc", "desc"] = Query(default="asc"),
    db: Session = Depends(pegar_sessao),
):
    """Lista jogos com paginação, filtros e ordenação configuráveis."""

    if (
        nota_minima is not None
        and nota_maxima is not None
        and nota_minima > nota_maxima
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="nota_minima não pode ser maior que nota_maxima.",
        )

    query = db.query(Jogo)

    if nome:
        query = query.filter(Jogo.nome.ilike(f"%{nome.strip()}%"))

    if tipo:
        query = query.filter(Jogo.tipo.ilike(f"%{tipo.strip()}%"))

    if nota_minima is not None:
        query = query.filter(Jogo.nota >= nota_minima)

    if nota_maxima is not None:
        query = query.filter(Jogo.nota <= nota_maxima)

    total_itens = query.count()
    coluna = _ordenacao_coluna(ordenar_por)
    criterio = desc(coluna) if ordem == "desc" else asc(coluna)
    deslocamento = (pagina - 1) * por_pagina

    itens = (
        query.order_by(criterio, asc(Jogo.id))
        .offset(deslocamento)
        .limit(por_pagina)
        .all()
    )

    return PaginacaoResponse(
        pagina=pagina,
        por_pagina=por_pagina,
        total_itens=total_itens,
        total_paginas=_calcular_total_paginas(total_itens, por_pagina),
        itens=itens,
    )


# -----------------------------------------------------------------------------
# CRUD principal
# -----------------------------------------------------------------------------


@jogos_router.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=list[JogoResponse],
)
async def get_jogos(
    tipo: Optional[str] = Query(default=None, max_length=50),
    nota_minima: Optional[int] = Query(default=None, ge=0, le=10),
    nota_maxima: Optional[int] = Query(default=None, ge=0, le=10),
    ordenar_por: Literal["id", "nome", "tipo", "nota"] = Query(default="id"),
    ordem: Literal["asc", "desc"] = Query(default="asc"),
    limite: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(pegar_sessao),
):
    """Obtém jogos com filtros simples sem alterar o formato original da resposta."""

    if (
        nota_minima is not None
        and nota_maxima is not None
        and nota_minima > nota_maxima
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="nota_minima não pode ser maior que nota_maxima.",
        )

    query = db.query(Jogo)

    if tipo:
        query = query.filter(Jogo.tipo.ilike(f"%{tipo.strip()}%"))

    if nota_minima is not None:
        query = query.filter(Jogo.nota >= nota_minima)

    if nota_maxima is not None:
        query = query.filter(Jogo.nota <= nota_maxima)

    coluna = _ordenacao_coluna(ordenar_por)
    criterio = desc(coluna) if ordem == "desc" else asc(coluna)

    return query.order_by(criterio, asc(Jogo.id)).limit(limite).all()


@jogos_router.get(
    "/{id}",
    status_code=status.HTTP_200_OK,
    response_model=JogoResponse,
)
async def get_jogo(id: int, db: Session = Depends(pegar_sessao)):
    """Obtém um jogo específico pelo ID."""

    return _buscar_jogo_ou_404(db, id)


@jogos_router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=JogoResponse,
)
async def cadastrar_review(
    jogo_schema: JogoSchema,
    db: Session = Depends(pegar_sessao),
):
    """Cadastra um novo jogo com sua respectiva review."""

    dados = _normalizar_payload_completo(jogo_schema)

    novo_jogo = Jogo(
        nome=dados["nome"],
        tipo=dados["tipo"],
        nota=dados["nota"],
        review=dados["review"],
    )

    db.add(novo_jogo)
    db.commit()
    db.refresh(novo_jogo)

    return novo_jogo


@jogos_router.put(
    "/{id}",
    status_code=status.HTTP_200_OK,
    response_model=JogoResponse,
)
async def atualizar_jogo(
    id: int,
    jogo_schema: JogoSchema,
    db: Session = Depends(pegar_sessao),
):
    """Atualiza todos os campos de um jogo existente."""

    jogo = _buscar_jogo_ou_404(db, id)
    dados = _normalizar_payload_completo(jogo_schema)

    jogo.nome = dados["nome"]
    jogo.tipo = dados["tipo"]
    jogo.nota = dados["nota"]
    jogo.review = dados["review"]

    db.commit()
    db.refresh(jogo)

    return jogo


@jogos_router.patch(
    "/{id}",
    status_code=status.HTTP_200_OK,
    response_model=JogoResponse,
)
async def atualizar_jogo_parcialmente(
    id: int,
    jogo_schema: JogoPatchSchema,
    db: Session = Depends(pegar_sessao),
):
    """Atualiza somente os campos enviados no corpo da requisição."""

    jogo = _buscar_jogo_ou_404(db, id)
    alteracoes = jogo_schema.model_dump(exclude_unset=True)

    if not alteracoes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe ao menos um campo para atualização.",
        )

    if "nome" in alteracoes and alteracoes["nome"] is not None:
        jogo.nome = _normalizar_texto(alteracoes["nome"])

    if "tipo" in alteracoes and alteracoes["tipo"] is not None:
        jogo.tipo = _normalizar_texto(alteracoes["tipo"])

    if "nota" in alteracoes and alteracoes["nota"] is not None:
        jogo.nota = _validar_nota(alteracoes["nota"])

    if "review" in alteracoes and alteracoes["review"] is not None:
        jogo.review = _normalizar_texto(alteracoes["review"])

    db.commit()
    db.refresh(jogo)

    return jogo


@jogos_router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def deletar_jogo(id: int, db: Session = Depends(pegar_sessao)):
    """Remove um jogo pelo ID."""

    jogo = _buscar_jogo_ou_404(db, id)

    db.delete(jogo)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# -----------------------------------------------------------------------------
# Operações em lote
# -----------------------------------------------------------------------------


@jogos_router.post(
    "/remover-em-lote",
    status_code=status.HTTP_200_OK,
    response_model=BulkDeleteResponse,
)
async def remover_jogos_em_lote(
    payload: BulkDeleteRequest,
    db: Session = Depends(pegar_sessao),
):
    """Remove até cem jogos em uma única operação."""

    ids_unicos = list(dict.fromkeys(payload.ids))

    jogos_encontrados = (
        db.query(Jogo)
        .filter(Jogo.id.in_(ids_unicos))
        .all()
    )

    ids_encontrados = {jogo.id for jogo in jogos_encontrados}
    ids_nao_encontrados = [
        jogo_id
        for jogo_id in ids_unicos
        if jogo_id not in ids_encontrados
    ]

    for jogo in jogos_encontrados:
        db.delete(jogo)

    db.commit()

    return BulkDeleteResponse(
        removidos=len(jogos_encontrados),
        ids_removidos=sorted(ids_encontrados),
        ids_nao_encontrados=ids_nao_encontrados,
    )
