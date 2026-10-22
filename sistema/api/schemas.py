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


# ---------------------------------------------------------------- cadastros (fatia 1B)
from typing import Annotated  # noqa: E402

from pydantic import AfterValidator  # noqa: E402

from api.services.dinheiro import parse_reais  # noqa: E402

Reais = Annotated[str, AfterValidator(lambda v: str(parse_reais(v)))]
TIPOS_PRODUTO = ("pizza", "calzone", "bebida", "acompanhamento")


def _nome(v: str) -> str:
    if not v or len(v) > 120:
        raise ValueError("Nome obrigatório, até 120 caracteres.")
    return v


def _texto_opcional(maximo: int):
    def _v(v):
        if v is not None and len(v) > maximo:
            raise ValueError(f"Até {maximo} caracteres.")
        return v or None
    return _v


def _telefone(v: str) -> str:
    digitos = "".join(c for c in v if c in "0123456789")
    if not 8 <= len(digitos) <= 15 or len(v) > 30:
        raise ValueError("Telefone inválido: informe de 8 a 15 dígitos (com DDD).")
    return digitos


class CategoriaCreate(Base):
    nome: str
    preco_padrao_grande: Optional[Reais] = None
    preco_padrao_broto: Optional[Reais] = None
    _n = field_validator("nome")(_nome)


class CategoriaUpdate(Base):
    nome: Optional[str] = None
    ativo: Optional[bool] = None
    preco_padrao_grande: Optional[Reais] = None  # explícito null limpa o padrão
    preco_padrao_broto: Optional[Reais] = None

    @model_validator(mode="after")
    def _sem_nulos_indevidos(self):
        for campo in ("nome", "ativo"):
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"{campo} não pode ser nulo.")
        if self.nome is not None:
            _nome(self.nome)
        return self


class ProdutoCreate(Base):
    tipo: str
    nome: str
    categoria_id: Optional[int] = None
    ingredientes: Optional[str] = None
    preco_grande: Optional[Reais] = None
    preco_broto: Optional[Reais] = None
    preco_unico: Optional[Reais] = None
    _n = field_validator("nome")(_nome)
    _i = field_validator("ingredientes")(_texto_opcional(500))

    @model_validator(mode="after")
    def _por_tipo(self):
        if self.tipo not in TIPOS_PRODUTO:
            raise ValueError("Tipo de produto inválido.")
        if self.tipo == "pizza":
            if self.categoria_id is None or self.preco_grande is None or self.preco_broto is None or self.preco_unico is not None:
                raise ValueError("Pizza exige categoria e preços Grande e Broto, e não tem preço único.")
        else:
            if self.categoria_id is not None or self.preco_unico is None or self.preco_grande is not None or self.preco_broto is not None:
                raise ValueError("Este tipo exige só o preço único e não tem categoria.")
        return self


class ProdutoUpdate(Base):
    nome: Optional[str] = None
    categoria_id: Optional[int] = None
    ingredientes: Optional[str] = None
    ativo: Optional[bool] = None
    preco_grande: Optional[Reais] = None
    preco_broto: Optional[Reais] = None
    preco_unico: Optional[Reais] = None
    _i = field_validator("ingredientes")(_texto_opcional(500))

    @model_validator(mode="after")
    def _sem_nulos_indevidos(self):
        for campo in ("nome", "ativo", "categoria_id", "preco_grande", "preco_broto", "preco_unico"):
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"{campo} não pode ser nulo.")
        if self.nome is not None:
            _nome(self.nome)
        return self


class AdicionalCreate(Base):
    tipo: str
    nome: str
    preco_grande: Reais
    preco_broto: Reais
    _n = field_validator("nome")(_nome)

    @field_validator("tipo")
    @classmethod
    def _t(cls, v):
        if v not in ("borda", "adicional"):
            raise ValueError("Tipo inválido.")
        return v


class AdicionalUpdate(Base):
    nome: Optional[str] = None
    ativo: Optional[bool] = None
    preco_grande: Optional[Reais] = None
    preco_broto: Optional[Reais] = None

    @model_validator(mode="after")
    def _sem_nulos(self):
        for campo in self.model_fields_set:
            if getattr(self, campo) is None:
                raise ValueError(f"{campo} não pode ser nulo.")
        if self.nome is not None:
            _nome(self.nome)
        return self


class ClienteCreate(Base):
    nome: str
    telefone: str
    endereco: Optional[str] = None
    _n = field_validator("nome")(_nome)
    _t = field_validator("telefone")(_telefone)
    _e = field_validator("endereco")(_texto_opcional(300))


class ClienteUpdate(Base):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None
    ativo: Optional[bool] = None
    _e = field_validator("endereco")(_texto_opcional(300))

    @model_validator(mode="after")
    def _sem_nulos(self):
        for campo in ("nome", "telefone", "ativo"):
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"{campo} não pode ser nulo.")
        if self.nome is not None:
            _nome(self.nome)
        if self.telefone is not None:
            self.telefone = _telefone(self.telefone)
        return self


class EntregadorCreate(Base):
    nome: str
    telefone: Optional[str] = None
    _n = field_validator("nome")(_nome)

    @field_validator("telefone")
    @classmethod
    def _t(cls, v):
        return None if v is None or v == "" else _telefone(v)


class EntregadorUpdate(Base):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    ativo: Optional[bool] = None

    @model_validator(mode="after")
    def _ok(self):
        for campo in ("nome", "ativo"):
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"{campo} não pode ser nulo.")
        if self.nome is not None:
            _nome(self.nome)
        if self.telefone == "":
            self.telefone = None
        elif self.telefone is not None:
            self.telefone = _telefone(self.telefone)
        return self


class PizzaSimular(Base):
    tamanho: str
    sabor1_id: int
    sabor2_id: Optional[int] = None
    adicional_ids: list[int] = []

    @field_validator("tamanho")
    @classmethod
    def _t(cls, v):
        if v not in ("grande", "broto"):
            raise ValueError("Tamanho deve ser grande ou broto.")
        return v

    @field_validator("adicional_ids")
    @classmethod
    def _a(cls, v):
        if len(v) > 10 or len(set(v)) != len(v):
            raise ValueError("Até 10 adicionais, sem repetir.")
        return v
