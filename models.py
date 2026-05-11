from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base
import os

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///banco.db")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

#cria a classes/tabelas do db
class Jogo(Base):
    __tablename__ = 'jogos'

    id = Column("id", Integer, primary_key=True, autoincrement=True)
    nome = Column("nome", String(100), nullable=False)
    tipo = Column("tipo", String(50), nullable=False)
    nota = Column("nota", Integer, nullable=False)
    review = Column("review", String(255), nullable=False)

    def __init__(self, nome, tipo, nota, review):
        self.nome = nome
        self.tipo = tipo
        self.nota = nota
        self.review = review

class Usuario(Base):
    __tablename__ = 'usuarios'

    id = Column("id", Integer, primary_key=True, autoincrement=True)
    email = Column("email", String(100), nullable=False, unique=True)
    password = Column("password", String(255), nullable=False)

    def __init__(self, email, password):
        self.email = email
        self.password = password

#executa a criação dos metadados do db
Base.metadata.create_all(bind=engine)
