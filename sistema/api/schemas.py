"""Modelos de entrada (pydantic estrito). Toda entrada passa por aqui antes de tocar no banco."""
import re
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from api.config import SENHA_MIN
from api.security import PERFIS

_LOGIN = re.compile(r"^[a-z0-9._-]{3,40}$")


def _senha_valida(v: str) -> str:
    if len(v) < SENHA_MIN:
        raise ValueError(f"A senha precisa ter pelo menos {SENHA_MIN} caracteres.")
    if len(v) > 72:  # limite do bcrypt
        raise ValueError("A senha pode ter no máximo 72 caracteres.")
    return v


class Base(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", str_strip_whitespace=True)


class LoginIn(Base):
    usuario: str
    senha: str

    @field_validator("usuario")
    @classmethod
    def _u(cls, v):
        return v.strip().lower()


class TrocarSenhaIn(Base):
    senha_atual: str
    senha_nova: str

    @field_validator("senha_nova")
    @classmethod
    def _s(cls, v):
        return _senha_valida(v)


class UsuarioCreate(Base):
    usuario: str
    nome: str
    perfil: str
    senha: str

    @field_validator("usuario")
    @classmethod
    def _u(cls, v):
        v = v.strip().lower()
        if not _LOGIN.match(v):
            raise ValueError("Usuário: 3 a 40 caracteres, só letras minúsculas, números, ponto, hífen e sublinhado.")
        return v

    @field_validator("nome")
    @classmethod
    def _n(cls, v):
        if not v or len(v) > 120:
            raise ValueError("Nome obrigatório, até 120 caracteres.")
        return v

    @field_validator("perfil")
    @classmethod
    def _p(cls, v):
        if v not in PERFIS:
            raise ValueError("Perfil inválido.")
        return v

    @field_validator("senha")
    @classmethod
    def _s(cls, v):
        return _senha_valida(v)


class UsuarioUpdate(Base):
    nome: Optional[str] = None
    perfil: Optional[str] = None
    ativo: Optional[bool] = None

    @field_validator("nome")
    @classmethod
    def _n(cls, v):
        if v is not None and (not v or len(v) > 120):
            raise ValueError("Nome obrigatório, até 120 caracteres.")
        return v

    @field_validator("perfil")
    @classmethod
    def _p(cls, v):
        if v is not None and v not in PERFIS:
            raise ValueError("Perfil inválido.")
        return v


class RedefinirSenhaIn(Base):
    senha_nova: str

    @field_validator("senha_nova")
    @classmethod
    def _s(cls, v):
        return _senha_valida(v)


class ParametroIn(Base):
    # None limpa o valor (volta a "não definido").
    valor: Optional[str | list[str]] = None
