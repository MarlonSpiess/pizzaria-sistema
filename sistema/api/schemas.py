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

def _reais_positivo(v: str) -> str:
    r = parse_reais(v)
    if r <= 0:
        raise ValueError("O preço deve ser maior que zero.")
    return str(r)


Reais = Annotated[str, AfterValidator(_reais_positivo)]
TIPOS_PRODUTO = ("pizza", "calzone", "bebida", "acompanhamento")


def _nome(v: str) -> str:
    v = unicodedata.normalize("NFC", v or "")
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
    if len(v) > 30 or any(c not in "0123456789()+-. " for c in v):
        raise ValueError("Telefone inválido: use só números, espaço, parênteses, hífen e +.")
    digitos = "".join(c for c in v if c in "0123456789")
    if len(digitos) in (12, 13) and digitos.startswith("55"):
        digitos = digitos[2:]  # DDI do Brasil: o mesmo número não vira dois cadastros
    if not 8 <= len(digitos) <= 15:
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


# ---------------------------------------------------------------- itens, fichas e etapas (fatia 1B2)
_QTD = re.compile(r"^[0-9]{1,9}([.,][0-9]{1,4})?$")
_PCT = re.compile(r"^[0-9]{1,3}([.,][0-9]{1,2})?$")
_MIN = re.compile(r"^[0-9]{1,4}([.,][0-9]{1,2})?$")


def _numero(regex, texto, maximo=None, positivo=False, rotulo="Valor"):
    from decimal import Decimal
    if not isinstance(texto, str) or not regex.match(texto.strip()):
        raise ValueError(f"{rotulo} inválido. Use números, com ponto ou vírgula.")
    n = Decimal(texto.strip().replace(",", "."))
    if (positivo and n <= 0) or (maximo is not None and n > maximo):
        raise ValueError(f"{rotulo} fora da faixa permitida.")
    return str(n)


Quantidade = Annotated[str, AfterValidator(lambda v: _numero(_QTD, v, positivo=True, rotulo="Quantidade"))]
Percentual = Annotated[str, AfterValidator(lambda v: _numero(_PCT, v, maximo=100, rotulo="Percentual"))]
Minutos = Annotated[str, AfterValidator(lambda v: _numero(_MIN, v, rotulo="Tempo"))]

CLASSES_ITEM = ("insumo", "preparo", "embalagem", "revenda", "consumo")
UNIDADES_ITEM = ("g", "kg", "ml", "l", "un", "fatia")
FUNCOES_ETAPA = ("massa", "pizzaiolo", "acabamento", "automatica")


class ItemCreate(Base):
    nome: str
    classe: str
    unidade: str
    _n = field_validator("nome")(_nome)

    @model_validator(mode="after")
    def _dominio(self):
        if self.classe not in CLASSES_ITEM or self.unidade not in UNIDADES_ITEM:
            raise ValueError("Classe ou unidade inválida.")
        return self


class ItemUpdate(Base):
    nome: Optional[str] = None
    ativo: Optional[bool] = None

    @model_validator(mode="after")
    def _ok(self):
        for campo in self.model_fields_set:
            if getattr(self, campo) is None:
                raise ValueError(f"{campo} não pode ser nulo.")
        if self.nome is not None:
            self.nome = _nome(self.nome)
        return self


class FichaLinha(Base):
    item_id: int
    quantidade: Quantidade
    perda_pct: Optional[Percentual] = None
    fase: str = "montagem"

    @field_validator("fase")
    @classmethod
    def _fase(cls, v):
        if v not in ("montagem", "pos_forno"):
            raise ValueError("Fase deve ser montagem ou pos_forno.")
        return v


class FichaIn(Base):
    linhas: list[FichaLinha]

    @field_validator("linhas")
    @classmethod
    def _l(cls, v):
        if len(v) > 60 or len({x.item_id for x in v}) != len(v):
            raise ValueError("Até 60 linhas, sem repetir o item.")
        return v


class EtapaCreate(Base):
    nome: str
    funcao: str
    _n = field_validator("nome")(_nome)

    @field_validator("funcao")
    @classmethod
    def _f(cls, v):
        if v not in FUNCOES_ETAPA:
            raise ValueError("Função inválida.")
        return v


class EtapaUpdate(Base):
    nome: Optional[str] = None
    funcao: Optional[str] = None
    ativo: Optional[bool] = None

    @model_validator(mode="after")
    def _ok(self):
        for campo in self.model_fields_set:
            if getattr(self, campo) is None:
                raise ValueError(f"{campo} não pode ser nulo.")
        if self.nome is not None:
            self.nome = _nome(self.nome)
        if self.funcao is not None and self.funcao not in FUNCOES_ETAPA:
            raise ValueError("Função inválida.")
        return self


class EtapaPasso(Base):
    etapa_id: int
    tempo_min: Optional[Minutos] = None


class EtapasIn(Base):
    etapas: list[EtapaPasso]

    @field_validator("etapas")
    @classmethod
    def _e(cls, v):
        if len(v) > 20 or len({x.etapa_id for x in v}) != len(v):
            raise ValueError("Até 20 etapas, sem repetir.")
        return v


# ---------------------------------------------------------------- vendas (fatia 1C)
FORMAS = ("dinheiro", "pix", "credito", "debito")


def _motivo(v: str) -> str:
    v = (v or "").strip()
    if not v or len(v) > 200:
        raise ValueError("Informe o motivo, até 200 caracteres.")
    return v


Motivo = Annotated[str, AfterValidator(_motivo)]


def _reais_zero_ok(v: str) -> str:
    return str(parse_reais(v))


ReaisOuZero = Annotated[str, AfterValidator(_reais_zero_ok)]


class Autorizacao(Base):
    """Login de gerente, subgerente, proprietário ou administrador, digitado na hora, para passar do limite do perfil."""
    usuario: str
    senha: str

    @field_validator("usuario")
    @classmethod
    def _u(cls, v):
        v = v.strip()
        if not v or len(v) > 60:
            raise ValueError("Usuário do autorizador inválido.")
        return v

    @field_validator("senha")
    @classmethod
    def _s(cls, v):
        if not v or len(v) > 200:
            raise ValueError("Senha do autorizador inválida.")
        return v


class ItemPedidoIn(Base):
    tipo: str
    produto_id: int  # pizza: sabor 1; demais tipos: o próprio produto
    tamanho: Optional[str] = None
    sabor2_id: Optional[int] = None
    adicional_ids: list[int] = []
    quantidade: int = 1
    observacoes: Optional[str] = None

    @field_validator("tipo")
    @classmethod
    def _t(cls, v):
        if v not in TIPOS_PRODUTO:
            raise ValueError("Tipo de item inválido.")
        return v

    @field_validator("tamanho")
    @classmethod
    def _tam(cls, v):
        if v is not None and v not in ("grande", "broto"):
            raise ValueError("Tamanho deve ser grande ou broto.")
        return v

    @field_validator("quantidade")
    @classmethod
    def _q(cls, v):
        if not 1 <= v <= 99:
            raise ValueError("Quantidade de 1 a 99.")
        return v

    @field_validator("adicional_ids")
    @classmethod
    def _a(cls, v):
        if len(v) > 10 or len(set(v)) != len(v):
            raise ValueError("Até 10 adicionais, sem repetir.")
        return v

    @field_validator("observacoes")
    @classmethod
    def _o(cls, v):
        return _texto_opcional(200)(v)

    @model_validator(mode="after")
    def _coerente(self):
        if self.tipo == "pizza":
            if self.tamanho is None:
                raise ValueError("Pizza exige tamanho.")
        elif self.tamanho or self.sabor2_id or self.adicional_ids:
            raise ValueError("Só pizza tem tamanho, segundo sabor, borda e adicionais.")
        return self


class AjusteIn(Base):
    tipo: str
    valor: Reais
    motivo: Motivo

    @field_validator("tipo")
    @classmethod
    def _t(cls, v):
        if v not in ("desconto", "acrescimo"):
            raise ValueError("Ajuste deve ser desconto ou acrescimo.")
        return v


class PagamentoIn(Base):
    forma: str
    valor: Reais  # valor entregue pelo cliente; só o dinheiro pode passar do que falta e gerar troco

    @field_validator("forma")
    @classmethod
    def _f(cls, v):
        if v not in FORMAS:
            raise ValueError("Forma de pagamento inválida.")
        return v


class PedidoCalcular(Base):
    tipo: str = "retirada"
    itens: list[ItemPedidoIn]
    ajuste: Optional[AjusteIn] = None
    taxa_entrega: Optional[ReaisOuZero] = None

    @field_validator("tipo")
    @classmethod
    def _t(cls, v):
        if v not in ("retirada", "entrega"):
            raise ValueError("Tipo deve ser retirada ou entrega.")
        return v

    @field_validator("itens")
    @classmethod
    def _i(cls, v):
        if not 1 <= len(v) <= 40:
            raise ValueError("O pedido precisa de 1 a 40 itens.")
        return v


class PedidoCreate(PedidoCalcular):
    cliente_id: Optional[int] = None
    taxa_motivo: Optional[str] = None
    pagamentos: list[PagamentoIn]
    urgente: bool = False
    observacoes: Optional[str] = None
    autorizacao: Optional[Autorizacao] = None
    chave: Optional[str] = None  # gerada pela tela por pedido; reenvio com a mesma chave devolve o pedido já criado

    @field_validator("chave")
    @classmethod
    def _chave(cls, v):
        if v is not None and not re.fullmatch(r"[A-Za-z0-9-]{8,64}", v):
            raise ValueError("Chave inválida.")
        return v

    @field_validator("pagamentos")
    @classmethod
    def _p(cls, v):
        if not 1 <= len(v) <= 6:
            raise ValueError("Informe de 1 a 6 pagamentos.")
        return v

    @field_validator("observacoes", "taxa_motivo")
    @classmethod
    def _o(cls, v):
        return _texto_opcional(200)(v)


class PedidoCancelar(Base):
    motivo: Motivo
    autorizacao: Optional[Autorizacao] = None


class PedidoSituacao(Base):
    situacao: str

    @field_validator("situacao")
    @classmethod
    def _s(cls, v):
        if v not in ("em producao", "acabado", "despachado ou retirado"):
            raise ValueError("Situação inválida.")
        return v


class PedidoUrgente(Base):
    urgente: bool
