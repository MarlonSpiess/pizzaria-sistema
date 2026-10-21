"""Modelos de entrada (pydantic estrito). Toda entrada passa por aqui antes de tocar no banco."""
import re
import unicodedata
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from api.config import SENHA_MIN
from api.security import PERFIS

_LOGIN = re.compile(r"^[a-z0-9._-]{3,40}$")


def _senha_valida(v: str) -> str:
    if len(v) < SENHA_MIN:
        raise ValueError(f"A senha precisa ter pelo menos {SENHA_MIN} caracteres.")
    if len(v.encode("utf-8")) > 72:  # limite do bcrypt é em bytes (acentos ocupam mais de 1)
        raise ValueError("A senha pode ter no máximo 72 bytes (cerca de 72 caracteres sem acento).")
    if v.lower() in _SENHAS_FRACAS:
        raise ValueError("Senha fraca demais: escolha outra.")
    return v


_SENHAS_FRACAS = {"12345678", "123456789", "87654321", "11111111", "00000000", "password", "senha123", "12341234"}


def _texto_limpo(v: str) -> str:
    """Recusa NUL, caracteres de controle e marcas de formatação (inclui as bidirecionais, que enganam a leitura)."""
    if any(unicodedata.category(c) in ("Cc", "Cf") for c in v):
        raise ValueError("Texto com caracteres de controle ou invisíveis não é aceito.")
    return v


class Base(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def _sem_controle(self):
        """Todo texto de entrada passa pelo filtro, menos senhas (só NUL é recusado nelas)."""
        for nome in self.model_fields_set:
            v = getattr(self, nome)
            valores = v if isinstance(v, list) else [v]
            for x in valores:
                if isinstance(x, str):
                    if "senha" in nome:
                        if "\x00" in x:
                            raise ValueError("Senha com caractere inválido.")
                    else:
                        _texto_limpo(x)
        return self


class LoginIn(Base):
    usuario: str
    senha: str

    @field_validator("usuario")
    @classmethod
    def _u(cls, v):
        v = v.strip().lower()
        if len(v) > 40:
            raise ValueError("Usuário ou senha inválidos.")
        return v

    @field_validator("senha")
    @classmethod
    def _s(cls, v):
        if len(v) > 256:
            raise ValueError("Usuário ou senha inválidos.")
        return v


class TrocarSenhaIn(Base):
    senha_atual: str
    senha_nova: str

    @field_validator("senha_atual")
    @classmethod
    def _a(cls, v):
        if len(v) > 256:
            raise ValueError("Senha atual incorreta.")
        return v

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

    @model_validator(mode="after")
    def _senha_diferente_do_usuario(self):
        if self.senha.lower() == self.usuario:
            raise ValueError("A senha não pode ser igual ao usuário.")
        return self


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


    @model_validator(mode="after")
    def _sem_nulos(self):
        for campo in self.model_fields_set:
            if getattr(self, campo) is None:
                raise ValueError(f"{campo} não pode ser nulo.")
        return self


class RedefinirSenhaIn(Base):
    senha_nova: str

    @field_validator("senha_nova")
    @classmethod
    def _s(cls, v):
        return _senha_valida(v)


class ParametroIn(Base):
    # None limpa o valor (volta a "não definido").
    valor: Optional[str | list[str]] = None
