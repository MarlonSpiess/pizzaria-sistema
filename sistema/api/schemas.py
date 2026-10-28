"""Modelos de entrada (pydantic estrito). Toda entrada passa por aqui antes de tocar no banco."""
import re
from datetime import date
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


# ---------------------------------------------------------------- produção (fatia 1D)
class MotivoIn(Base):
    nome: str
    avisa_estoque: bool = False

    @field_validator("nome")
    @classmethod
    def _n(cls, v):
        return _nome(v)


class MotivoUpdate(Base):
    nome: Optional[str] = None
    avisa_estoque: Optional[bool] = None
    ativo: Optional[bool] = None

    @field_validator("nome")
    @classmethod
    def _n(cls, v):
        return None if v is None else _nome(v)


class MotivoRef(Base):
    motivo_id: int


class LoteMassaIn(Base):
    tamanho: str
    quantidade: int

    @field_validator("tamanho")
    @classmethod
    def _t(cls, v):
        if v not in ("grande", "broto"):
            raise ValueError("Tamanho deve ser grande ou broto.")
        return v

    @field_validator("quantidade")
    @classmethod
    def _q(cls, v):
        if not 1 <= v <= 1000:
            raise ValueError("Quantidade de 1 a 1000.")
        return v


class ContagemMassaIn(LoteMassaIn):
    @field_validator("quantidade")
    @classmethod
    def _q(cls, v):
        if not 0 <= v <= 1000:
            raise ValueError("Quantidade de 0 a 1000.")
        return v


class PerdaMassaIn(LoteMassaIn):
    motivo_id: int


# ---------------------------------------------------------------- caixa (fatia 1E)
class CaixaAbrir(Base):
    fundo_troco: Optional[ReaisOuZero] = None  # vazio usa o padrão dos parâmetros


class MovimentoIn(Base):
    tipo: str
    valor: Reais
    motivo_id: int
    observacao: Optional[str] = None
    comprovante: Optional[str] = None
    autorizacao: Optional[Autorizacao] = None

    @field_validator("tipo")
    @classmethod
    def _t(cls, v):
        if v not in ("sangria", "suprimento"):
            raise ValueError("Tipo deve ser sangria ou suprimento.")
        return v

    @field_validator("observacao", "comprovante")
    @classmethod
    def _o(cls, v):
        return _texto_opcional(200)(v)


class ContagemLinha(Base):
    forma: str
    valor: ReaisOuZero

    @field_validator("forma")
    @classmethod
    def _f(cls, v):
        if v not in FORMAS:
            raise ValueError("Forma de pagamento inválida.")
        return v


class ContagemIn(Base):
    contagens: list[ContagemLinha]


class FecharIn(Base):
    justificativa: Optional[str] = None
    autorizacao: Optional[Autorizacao] = None

    @field_validator("justificativa")
    @classmethod
    def _j(cls, v):
        return _texto_opcional(300)(v)


class MotivoMovimentoIn(Base):
    nome: str
    tipo: str
    vira_despesa: bool = False

    @field_validator("nome")
    @classmethod
    def _n(cls, v):
        return _nome(v)

    @field_validator("tipo")
    @classmethod
    def _t(cls, v):
        if v not in ("sangria", "suprimento"):
            raise ValueError("Tipo deve ser sangria ou suprimento.")
        return v


class MotivoMovimentoUpdate(Base):
    nome: Optional[str] = None
    vira_despesa: Optional[bool] = None
    ativo: Optional[bool] = None

    @field_validator("nome")
    @classmethod
    def _n(cls, v):
        return None if v is None else _nome(v)


class MaquininhaIn(Base):
    nome: str

    @field_validator("nome")
    @classmethod
    def _n(cls, v):
        return _nome(v)


class MaquininhaUpdate(Base):
    nome: Optional[str] = None
    ativo: Optional[bool] = None

    @field_validator("nome")
    @classmethod
    def _n(cls, v):
        return None if v is None else _nome(v)


class RegraRecebimentoIn(Base):
    forma: str
    maquininha_id: Optional[int] = None
    taxa_pct: Percentual = "0"
    prazo_dias: int = 0

    @field_validator("forma")
    @classmethod
    def _f(cls, v):
        if v not in FORMAS:
            raise ValueError("Forma de pagamento inválida.")
        return v

    @field_validator("prazo_dias")
    @classmethod
    def _p(cls, v):
        if not 0 <= v <= 365:
            raise ValueError("Prazo de 0 a 365 dias.")
        return v


class EntregaIn(Base):
    entregador_id: int
    valor_entrega: Optional[ReaisOuZero] = None  # vazio usa o padrão dos parâmetros


class AcertoIn(Base):
    entregador_id: int
    diaria: Optional[ReaisOuZero] = None  # vazio usa o padrão; só vale na primeira vez do dia


class CfIn(Base):
    numero_cf: str

    @field_validator("numero_cf")
    @classmethod
    def _c(cls, v):
        v = v.strip()
        if not v or len(v) > 40:
            raise ValueError("Informe o número do CF, até 40 caracteres.")
        return v


# ---------------------------------------------------------------- estoques (fatia 2A)
_QTD0 = re.compile(r"^[0-9]{1,9}([.,][0-9]{1,4})?$")
_PRECO4 = re.compile(r"^[0-9]{1,8}([.,][0-9]{1,4})?$")
QuantidadeOuZero = Annotated[str, AfterValidator(lambda v: _numero(_QTD0, v, rotulo="Quantidade"))]
DataISO = Annotated[str, AfterValidator(lambda v: date.fromisoformat(v))]  # entra como texto AAAA-MM-DD; o valor validado já é date
PrecoUnit = Annotated[str, AfterValidator(lambda v: _numero(_PRECO4, v, positivo=True, rotulo="Preço"))]


class LocalIn(Base):
    nome: str
    _n = field_validator("nome")(_nome)


class LocalUpdate(Base):
    nome: Optional[str] = None
    ativo: Optional[bool] = None

    @field_validator("nome")
    @classmethod
    def _n(cls, v):
        return None if v is None else _nome(v)


class ItemEstoqueIn(Base):
    unidade_compra: Optional[str] = None
    fator_compra: Optional[Quantidade] = None
    local_padrao_id: Optional[int] = None
    estoque_minimo: Optional[QuantidadeOuZero] = None
    ponto_pedido: Optional[QuantidadeOuZero] = None
    estoque_maximo: Optional[QuantidadeOuZero] = None
    controla_lote: Optional[bool] = None
    critico: Optional[bool] = None
    fornecedor_habitual_id: Optional[int] = None

    @field_validator("unidade_compra")
    @classmethod
    def _u(cls, v):
        return _texto_opcional(20)(v.strip() if v else v)


class MovimentoEstoqueIn(Base):
    tipo: str
    item_id: int
    quantidade: Quantidade
    local_id: Optional[int] = None
    destino_id: Optional[int] = None
    lote_id: Optional[int] = None
    motivo: Optional[str] = None
    custo_unit: Optional[PrecoUnit] = None
    lote_codigo: Optional[str] = None
    validade: Optional[DataISO] = None

    @field_validator("tipo")
    @classmethod
    def _t(cls, v):
        if v not in ("perda", "consumo_interno", "entrada_inicial", "transferencia"):
            raise ValueError("Tipo deve ser perda, consumo_interno, entrada_inicial ou transferencia.")
        return v

    @field_validator("motivo", "lote_codigo")
    @classmethod
    def _m(cls, v):
        return _texto_opcional(200)(v.strip() if v else v)


class InventarioIn(Base):
    tipo: str
    item_ids: Optional[list[int]] = None
    observacao: Optional[str] = None

    @field_validator("tipo")
    @classmethod
    def _t(cls, v):
        if v not in ("diario", "mensal", "avulso"):
            raise ValueError("Tipo deve ser diario, mensal ou avulso.")
        return v

    @field_validator("observacao")
    @classmethod
    def _o(cls, v):
        return _texto_opcional(200)(v)


class ContagemInventarioLinha(Base):
    item_id: int
    contado: QuantidadeOuZero


class ContagemInventarioIn(Base):
    linhas: list[ContagemInventarioLinha]

    @field_validator("linhas")
    @classmethod
    def _l(cls, v):
        if not v or len({x.item_id for x in v}) != len(v) or len(v) > 500:
            raise ValueError("Informe de 1 a 500 itens, sem repetir.")
        return v


class MotivoAjuste(Base):
    item_id: int
    motivo: str

    @field_validator("motivo")
    @classmethod
    def _m(cls, v):
        v = v.strip()
        if not v or len(v) > 200:
            raise ValueError("Motivo obrigatório, até 200 caracteres.")
        return v


class FecharInventarioIn(Base):
    motivos: list[MotivoAjuste] = []
    confirmar_nao_contados: bool = False


# ---------------------------------------------------------------- compras (fatia 2B)
FORMAS_FORNECEDOR = ("dinheiro", "pix", "boleto", "cartao", "prazo", "outro")


def _forma_forn(v):
    if v is not None and v not in FORMAS_FORNECEDOR:
        raise ValueError("Forma de pagamento inválida.")
    return v


class FornecedorIn(Base):
    nome: str
    contato: Optional[str] = None
    telefone: Optional[str] = None
    prazo_dias: Optional[int] = None
    forma_pagamento: Optional[str] = None
    observacao: Optional[str] = None
    _n = field_validator("nome")(_nome)
    _f = field_validator("forma_pagamento")(_forma_forn)

    @field_validator("contato", "telefone")
    @classmethod
    def _c(cls, v):
        return _texto_opcional(60)(v.strip() if v else v)

    @field_validator("observacao")
    @classmethod
    def _o(cls, v):
        return _texto_opcional(200)(v)

    @field_validator("prazo_dias")
    @classmethod
    def _p(cls, v):
        if v is not None and not 0 <= v <= 365:
            raise ValueError("Prazo de 0 a 365 dias.")
        return v


class FornecedorUpdate(Base):
    nome: Optional[str] = None
    contato: Optional[str] = None
    telefone: Optional[str] = None
    prazo_dias: Optional[int] = None
    forma_pagamento: Optional[str] = None
    observacao: Optional[str] = None
    ativo: Optional[bool] = None
    _f = field_validator("forma_pagamento")(_forma_forn)

    @field_validator("nome")
    @classmethod
    def _n(cls, v):
        return None if v is None else _nome(v)

    @field_validator("prazo_dias")
    @classmethod
    def _p(cls, v):
        if v is not None and not 0 <= v <= 365:
            raise ValueError("Prazo de 0 a 365 dias.")
        return v


class ItemQtd(Base):
    item_id: int
    quantidade: Quantidade


class ListaGerarIn(Base):
    incluir_sugeridos: bool = True
    itens: list[ItemQtd] = []
    observacao: Optional[str] = None

    @field_validator("itens")
    @classmethod
    def _i(cls, v):
        if len(v) > 200 or len({x.item_id for x in v}) != len(v):
            raise ValueError("Até 200 itens, sem repetir.")
        return v

    @field_validator("observacao")
    @classmethod
    def _o(cls, v):
        return _texto_opcional(200)(v)


class ListaItemUpdate(Base):
    quantidade: Optional[Quantidade] = None
    removido: Optional[bool] = None
    motivo: Optional[str] = None

    @field_validator("motivo")
    @classmethod
    def _m(cls, v):
        return _texto_opcional(200)(v.strip() if v else v)


class CotacaoIn(Base):
    lista_item_id: int
    fornecedor_id: int
    preco: PrecoUnit  # por unidade de compra do item
    prazo_dias: Optional[int] = None
    condicao: Optional[str] = None

    @field_validator("condicao")
    @classmethod
    def _c(cls, v):
        return _texto_opcional(120)(v.strip() if v else v)

    @field_validator("prazo_dias")
    @classmethod
    def _p(cls, v):
        if v is not None and not 0 <= v <= 365:
            raise ValueError("Prazo de 0 a 365 dias.")
        return v


class EscolhaIn(Base):
    lista_item_id: int
    fornecedor_id: int
    quantidade: Quantidade
    preco: Optional[PrecoUnit] = None  # vazio usa a cotação do fornecedor ou, se for o habitual, o último preço pago


class DefinirIn(Base):
    escolhas: list[EscolhaIn]

    @field_validator("escolhas")
    @classmethod
    def _e(cls, v):
        if not v or len(v) > 400:
            raise ValueError("Informe de 1 a 400 escolhas.")
        return v


class PedidoItemIn(Base):
    item_id: int
    quantidade: Quantidade
    preco: PrecoUnit


class PedidoCompraIn(Base):
    fornecedor_id: int
    itens: list[PedidoItemIn]
    prazo_dias: Optional[int] = None
    forma_pagamento: Optional[str] = None
    previsao_entrega: Optional[DataISO] = None
    observacao: Optional[str] = None
    _f = field_validator("forma_pagamento")(_forma_forn)

    @field_validator("itens")
    @classmethod
    def _i(cls, v):
        if not v or len(v) > 200 or len({x.item_id for x in v}) != len(v):
            raise ValueError("Informe de 1 a 200 itens, sem repetir.")
        return v

    @field_validator("observacao")
    @classmethod
    def _o(cls, v):
        return _texto_opcional(200)(v)


class RecebItemIn(Base):
    item_id: int
    quantidade: Quantidade
    preco: PrecoUnit
    lote_codigo: Optional[str] = None
    validade: Optional[DataISO] = None
    diferenca_motivo: Optional[str] = None

    @field_validator("lote_codigo", "diferenca_motivo")
    @classmethod
    def _t(cls, v):
        return _texto_opcional(120)(v.strip() if v else v)


class RecebimentoIn(Base):
    pedido_id: Optional[int] = None
    fornecedor_id: Optional[int] = None
    numero_nota: Optional[str] = None
    data_nota: DataISO
    conferente_id: Optional[int] = None
    itens: list[RecebItemIn]
    frete: Optional[ReaisOuZero] = None
    desconto: Optional[ReaisOuZero] = None
    forma_pagamento: Optional[str] = None
    vencimento: Optional[DataISO] = None
    movimento_caixa_id: Optional[int] = None
    observacao: Optional[str] = None
    _f = field_validator("forma_pagamento")(_forma_forn)

    @field_validator("itens")
    @classmethod
    def _i(cls, v):
        if not v or len(v) > 200 or len({x.item_id for x in v}) != len(v):
            raise ValueError("Informe de 1 a 200 itens, sem repetir.")
        return v

    @field_validator("numero_nota", "observacao")
    @classmethod
    def _t(cls, v):
        return _texto_opcional(120)(v.strip() if v else v)


# ---------------------------------------------------------------- contas
from decimal import Decimal  # noqa: E402

FORMAS_BAIXA = ("dinheiro", "pix", "credito", "debito", "boleto", "transferencia")
NATUREZAS = ("fixa", "variavel", "pessoal", "tributo", "financiamento", "retirada", "outra")
TIPOS_CONTA = ("corrente", "poupanca", "caixa_fisico", "outro")


class ContaBancariaIn(Base):
    nome: str
    banco: Optional[str] = None
    agencia: Optional[str] = None
    numero: Optional[str] = None
    tipo: str = "corrente"
    saldo_inicial: ReaisOuZero = "0"
    saldo_inicial_data: DataISO
    _n = field_validator("nome")(_nome)

    @field_validator("banco", "agencia", "numero")
    @classmethod
    def _t(cls, v):
        return _texto_opcional(60)(v.strip() if v else v)

    @field_validator("tipo")
    @classmethod
    def _tp(cls, v):
        if v not in TIPOS_CONTA:
            raise ValueError("Tipo de conta inválido.")
        return v


class AtivoIn(Base):
    ativo: bool


class TipoDespesaIn(Base):
    nome: str
    natureza: str
    _n = field_validator("nome")(_nome)

    @field_validator("natureza")
    @classmethod
    def _nt(cls, v):
        if v not in NATUREZAS:
            raise ValueError("Natureza inválida.")
        return v


class CanalRepasseIn(Base):
    canal: str
    taxa_pct: str = "0"
    prazo_dias: int = 0
    _n = field_validator("canal")(_nome)

    @field_validator("taxa_pct")
    @classmethod
    def _tx(cls, v):
        try:
            x = Decimal(v.replace(",", "."))
            if not x.is_finite():
                raise ValueError("Valor inválido.")
        except Exception as e:
            raise ValueError("Taxa inválida.") from e
        if x < 0 or x > 100:
            raise ValueError("A taxa fica entre 0 e 100.")
        return str(x.quantize(Decimal("0.01")))

    @field_validator("prazo_dias")
    @classmethod
    def _pz(cls, v):
        if not 0 <= v <= 365:
            raise ValueError("O prazo fica entre 0 e 365 dias.")
        return v


class RecorrenteIn(Base):
    descricao: str
    tipo_despesa_id: int
    fornecedor_id: Optional[int] = None
    valor: Reais
    dia_vencimento: int
    inicio: DataISO
    fim: Optional[DataISO] = None

    @field_validator("descricao")
    @classmethod
    def _d(cls, v):
        return _nome(v)

    @field_validator("dia_vencimento")
    @classmethod
    def _dv(cls, v):
        if not 1 <= v <= 28:
            raise ValueError("O dia de vencimento fica entre 1 e 28.")
        return v


class TituloIn(Base):
    sentido: str
    descricao: str
    valor: Reais
    vencimento: DataISO
    fornecedor_id: Optional[int] = None
    tipo_despesa_id: Optional[int] = None
    canal: Optional[str] = None
    competencia: Optional[DataISO] = None
    parcelas: int = 1
    comprovante: Optional[str] = None

    @field_validator("sentido")
    @classmethod
    def _s(cls, v):
        if v not in ("pagar", "receber"):
            raise ValueError("Sentido: pagar ou receber.")
        return v

    @field_validator("descricao")
    @classmethod
    def _d(cls, v):
        return _nome(v)

    @field_validator("canal", "comprovante")
    @classmethod
    def _t(cls, v):
        return _texto_opcional(120)(v.strip() if v else v)

    @field_validator("parcelas")
    @classmethod
    def _p(cls, v):
        if not 1 <= v <= 60:
            raise ValueError("Parcelas: de 1 a 60.")
        return v


class CancelarTituloIn(Base):
    motivo: str

    @field_validator("motivo")
    @classmethod
    def _m(cls, v):
        if not v or len(v) > 200:
            raise ValueError("Motivo obrigatório, até 200 caracteres.")
        return v


class BaixaIn(Base):
    data: Optional[DataISO] = None
    valor: Optional[Reais] = None
    desconto: ReaisOuZero = "0"
    juros: ReaisOuZero = "0"
    multa: ReaisOuZero = "0"
    forma: str
    conta_id: int

    @field_validator("forma")
    @classmethod
    def _f(cls, v):
        if v not in FORMAS_BAIXA:
            raise ValueError("Forma de pagamento inválida.")
        return v


class ExtratoIn(Base):
    conta_id: int
    data: DataISO
    descricao: str
    valor: str  # com sinal: entrada positiva, saída negativa

    @field_validator("descricao")
    @classmethod
    def _d(cls, v):
        return _nome(v)

    @field_validator("valor")
    @classmethod
    def _v(cls, v):
        neg = v.startswith("-")
        x = parse_reais(v[1:] if neg else v)
        if x == 0:
            raise ValueError("Valor zero não é aceito.")
        return ("-" if neg else "") + str(x)


class ConciliarIn(Base):
    extrato_id: int
    baixa_id: int


def _dec3(v):
    x = Decimal(v.replace(",", "."))
    if not x.is_finite():
        raise ValueError("Número inválido.")
    return str(x.quantize(Decimal("0.001")))


# ---------------------------------------------------------------- custos
class FatorCorrecaoIn(Base):
    fator_correcao: str

    @field_validator("fator_correcao")
    @classmethod
    def _f(cls, v):
        try:
            x = Decimal(v.replace(",", "."))
            if not x.is_finite():
                raise ValueError("Valor inválido.")
        except Exception as e:
            raise ValueError("Fator inválido.") from e
        if x < 1 or x > 10:
            raise ValueError("O fator de correção fica entre 1 e 10 (1 quando não houver perda na limpeza).")
        return str(x.quantize(Decimal("0.001")))


class FecharCmvIn(Base):
    mes: str  # AAAA-MM

    @field_validator("mes")
    @classmethod
    def _m(cls, v):
        if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", v):
            raise ValueError("Mês no formato AAAA-MM.")
        return v


# ---------------------------------------------------------------- imobilizado
METODOS_DEP = ("fiscal", "vida_util")
TIPOS_BAIXA = ("venda", "perda", "descarte", "doacao")
TIPOS_OS = ("preventiva", "preditiva", "corretiva")


class CategoriaBemIn(Base):
    nome: str
    taxa_fiscal_pct: str
    veiculo: bool = False
    _n = field_validator("nome")(_nome)

    @field_validator("taxa_fiscal_pct")
    @classmethod
    def _t(cls, v):
        try:
            x = Decimal(v.replace(",", "."))
            if not x.is_finite():
                raise ValueError("Valor inválido.")
        except Exception as e:
            raise ValueError("Taxa inválida.") from e
        if not x.is_finite() or x < 1 or x > 100:
            raise ValueError("A taxa anual fica entre 1 e 100.")
        return str(x.quantize(Decimal("0.01")))


def _data_bem(v):
    if v is not None and not 2000 <= v.year <= 2100:
        raise ValueError("Data fora do intervalo (2000 a 2100).")
    return v


class BemIn(Base):
    codigo: str
    nome: str
    categoria_id: int
    valor_aquisicao: Reais
    data_aquisicao: DataISO
    inicio_uso: Optional[DataISO] = None
    fornecedor_id: Optional[int] = None
    numero_nota: Optional[str] = None
    local_texto: Optional[str] = None
    responsavel: Optional[str] = None
    numero_serie: Optional[str] = None
    placa: Optional[str] = None
    quilometragem: Optional[int] = None
    critico: bool = False
    metodo: str = "fiscal"
    vida_util_meses: Optional[int] = None
    valor_residual: ReaisOuZero = "0"
    garantia_ate: Optional[DataISO] = None
    seguro_ate: Optional[DataISO] = None
    apolice: Optional[str] = None
    _n = field_validator("nome")(_nome)

    @field_validator("codigo")
    @classmethod
    def _c(cls, v):
        if not v or len(v) > 40:
            raise ValueError("Plaqueta obrigatória, até 40 caracteres.")
        return v

    @field_validator("numero_nota", "local_texto", "responsavel", "numero_serie", "placa", "apolice")
    @classmethod
    def _o(cls, v):
        return _texto_opcional(80)(v.strip() if v else v)

    @field_validator("metodo")
    @classmethod
    def _m(cls, v):
        if v not in METODOS_DEP:
            raise ValueError("Método de depreciação inválido.")
        return v

    @field_validator("vida_util_meses")
    @classmethod
    def _v(cls, v):
        if v is not None and not 1 <= v <= 600:
            raise ValueError("Vida útil entre 1 e 600 meses.")
        return v

    @field_validator("quilometragem")
    @classmethod
    def _k(cls, v):
        if v is not None and not 0 <= v <= 5_000_000:
            raise ValueError("Quilometragem inválida.")
        return v

    _db = field_validator("data_aquisicao", "inicio_uso")(_data_bem)


class BemUpdate(Base):
    nome: Optional[str] = None
    local_texto: Optional[str] = None
    responsavel: Optional[str] = None
    numero_serie: Optional[str] = None
    placa: Optional[str] = None
    quilometragem: Optional[int] = None
    critico: Optional[bool] = None
    inicio_uso: Optional[DataISO] = None
    metodo: Optional[str] = None
    vida_util_meses: Optional[int] = None
    valor_residual: Optional[ReaisOuZero] = None
    garantia_ate: Optional[DataISO] = None
    seguro_ate: Optional[DataISO] = None
    apolice: Optional[str] = None
    _n = field_validator("nome")(lambda cls, v: _nome(v) if v is not None else v)

    @field_validator("local_texto", "responsavel", "numero_serie", "placa", "apolice")
    @classmethod
    def _o(cls, v):
        return _texto_opcional(80)(v.strip() if v else v)

    @field_validator("metodo")
    @classmethod
    def _m(cls, v):
        if v is not None and v not in METODOS_DEP:
            raise ValueError("Método de depreciação inválido.")
        return v

    _db = field_validator("inicio_uso")(_data_bem)


class BaixaBemIn(Base):
    tipo: str
    data: DataISO
    valor: ReaisOuZero = "0"
    motivo: str

    @field_validator("tipo")
    @classmethod
    def _t(cls, v):
        if v not in TIPOS_BAIXA:
            raise ValueError("Tipo de baixa inválido.")
        return v

    @field_validator("motivo")
    @classmethod
    def _m(cls, v):
        if not v or len(v) > 200:
            raise ValueError("Motivo obrigatório, até 200 caracteres.")
        return v


class ConferenciaBemIn(Base):
    encontrado: bool
    local_encontrado: Optional[str] = None
    observacao: Optional[str] = None

    @field_validator("local_encontrado", "observacao")
    @classmethod
    def _o(cls, v):
        return _texto_opcional(120)(v.strip() if v else v)


class PlanoIn(Base):
    tarefa: str
    periodicidade_dias: int
    antecedencia_dias: int = 7
    base_em: Optional[DataISO] = None

    @field_validator("tarefa")
    @classmethod
    def _t(cls, v):
        return _nome(v)

    @field_validator("periodicidade_dias")
    @classmethod
    def _p(cls, v):
        if not 1 <= v <= 3650:
            raise ValueError("Periodicidade de 1 a 3650 dias.")
        return v

    @field_validator("antecedencia_dias")
    @classmethod
    def _a(cls, v):
        if not 0 <= v <= 365:
            raise ValueError("Antecedência de 0 a 365 dias.")
        return v


class LimiteLeituraIn(Base):
    grandeza: str
    unidade: Optional[str] = None
    minimo: Optional[str] = None
    maximo: Optional[str] = None

    @field_validator("grandeza")
    @classmethod
    def _g(cls, v):
        return _nome(v)

    @field_validator("unidade")
    @classmethod
    def _u(cls, v):
        return _texto_opcional(20)(v.strip() if v else v)

    @field_validator("minimo", "maximo")
    @classmethod
    def _n(cls, v):
        if v is None:
            return v
        try:
            return _dec3(v)
        except Exception as e:
            raise ValueError("Número inválido.") from e


class LeituraIn(Base):
    grandeza: str
    valor: str
    data: Optional[DataISO] = None

    @field_validator("valor")
    @classmethod
    def _v(cls, v):
        try:
            return _dec3(v)
        except Exception as e:
            raise ValueError("Valor inválido.") from e


class OsIn(Base):
    bem_id: int
    tipo: str
    descricao: str
    plano_id: Optional[int] = None
    parou: bool = False

    @field_validator("tipo")
    @classmethod
    def _t(cls, v):
        if v not in TIPOS_OS:
            raise ValueError("Tipo de ordem inválido.")
        return v

    @field_validator("descricao")
    @classmethod
    def _d(cls, v):
        if not v or len(v) > 300:
            raise ValueError("Descrição obrigatória, até 300 caracteres.")
        return v


class OsIniciarIn(Base):
    executor_tipo: str
    executor_nome: Optional[str] = None
    fornecedor_id: Optional[int] = None

    @field_validator("executor_tipo")
    @classmethod
    def _t(cls, v):
        if v not in ("funcionario", "terceiro"):
            raise ValueError("Executor: funcionário ou terceiro.")
        return v

    @field_validator("executor_nome")
    @classmethod
    def _n(cls, v):
        return _texto_opcional(80)(v.strip() if v else v)


class OsPecaIn(Base):
    item_id: int
    quantidade: str

    @field_validator("quantidade")
    @classmethod
    def _q(cls, v):
        try:
            x = Decimal(v.replace(",", "."))
            if not x.is_finite():
                raise ValueError("Valor inválido.")
        except Exception as e:
            raise ValueError("Quantidade inválida.") from e
        if x <= 0 or x > 1_000_000:
            raise ValueError("Quantidade inválida.")
        return str(x.quantize(Decimal("0.0001")))


class OsFecharIn(Base):
    servico_feito: str
    causa: Optional[str] = None
    mao_obra: ReaisOuZero = "0"
    tipo_despesa_id: Optional[int] = None
    vencimento: Optional[DataISO] = None

    @field_validator("servico_feito")
    @classmethod
    def _s(cls, v):
        if not v or len(v) > 300:
            raise ValueError("Descreva o serviço feito, até 300 caracteres.")
        return v

    @field_validator("causa")
    @classmethod
    def _c(cls, v):
        return _texto_opcional(200)(v.strip() if v else v)


# ---------------------------------------------------------------- rh
TIPOS_CONTRATO = ("clt", "intermitente", "freelancer", "diarista", "prolabore", "outro")
FORMAS_PAGTO_RH = ("mensal", "diaria", "hora")
TIPOS_AUSENCIA = ("ferias", "afastamento", "atestado", "falta")
HORA = r"^([01]\d|2[0-3]):[0-5]\d$"


def _hora(v):
    if not re.fullmatch(HORA, v):
        raise ValueError("Hora no formato HH:MM.")
    return v


class FuncaoRhIn(Base):
    nome: str
    _n = field_validator("nome")(_nome)


class EscalaTipoIn(Base):
    nome: str
    dias_trabalho: int
    dias_folga: int
    horas_semana: str
    _n = field_validator("nome")(_nome)

    @field_validator("dias_trabalho")
    @classmethod
    def _dt(cls, v):
        if not 1 <= v <= 7:
            raise ValueError("Dias de trabalho de 1 a 7.")
        return v

    @field_validator("dias_folga")
    @classmethod
    def _df(cls, v):
        if not 0 <= v <= 7:
            raise ValueError("Dias de folga de 0 a 7.")
        return v

    @field_validator("horas_semana")
    @classmethod
    def _hs(cls, v):
        try:
            x = Decimal(v.replace(",", "."))
            if not x.is_finite():
                raise ValueError("Valor inválido.")
        except Exception as e:
            raise ValueError("Horas inválidas.") from e
        if x <= 0 or x > 60:
            raise ValueError("Horas por semana de 1 a 60.")
        return str(x.quantize(Decimal("0.01")))


class FuncionarioIn(Base):
    nome: str
    telefone: Optional[str] = None
    funcao_id: int
    usuario_id: Optional[int] = None
    admissao: DataISO
    preco_especial: bool = False
    _n = field_validator("nome")(_nome)
    _t = field_validator("telefone")(lambda cls, v: _telefone(v) if v else None)


class FuncionarioUpdate(Base):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    funcao_id: Optional[int] = None
    usuario_id: Optional[int] = None
    preco_especial: Optional[bool] = None
    _n = field_validator("nome")(lambda cls, v: _nome(v) if v is not None else v)
    _t = field_validator("telefone")(lambda cls, v: _telefone(v) if v else None)


class DesligarIn(Base):
    data: DataISO
    motivo: str

    @field_validator("motivo")
    @classmethod
    def _m(cls, v):
        if not v or len(v) > 200:
            raise ValueError("Motivo obrigatório, até 200 caracteres.")
        return v


class ContratoIn(Base):
    tipo: str
    escala_id: Optional[int] = None
    forma_pagamento: str
    valor: Reais
    vigente_desde: DataISO

    @field_validator("tipo")
    @classmethod
    def _t(cls, v):
        if v not in TIPOS_CONTRATO:
            raise ValueError("Tipo de contrato inválido.")
        return v

    @field_validator("forma_pagamento")
    @classmethod
    def _f(cls, v):
        if v not in FORMAS_PAGTO_RH:
            raise ValueError("Forma de pagamento inválida.")
        return v


class BeneficioIn(Base):
    nome: str
    valor_mensal: Reais
    _n = field_validator("nome")(_nome)


class TurnoIn(Base):
    funcionario_id: int
    data: DataISO
    funcao_id: int
    inicio: str
    fim: str
    _i = field_validator("inicio")(lambda cls, v: _hora(v))
    _f = field_validator("fim")(lambda cls, v: _hora(v))


class PontoIn(Base):
    funcionario_id: int
    data: DataISO
    entrada: str
    saida: str
    _e = field_validator("entrada")(lambda cls, v: _hora(v))
    _s = field_validator("saida")(lambda cls, v: _hora(v))


class BancoHorasIn(Base):
    funcionario_id: int
    data: DataISO
    minutos: int
    motivo: str

    @field_validator("minutos")
    @classmethod
    def _m(cls, v):
        if v == 0 or abs(v) > 1440:
            raise ValueError("Minutos diferentes de zero, até 1440 por lançamento.")
        return v

    @field_validator("motivo")
    @classmethod
    def _mo(cls, v):
        if not v or len(v) > 200:
            raise ValueError("Motivo obrigatório, até 200 caracteres.")
        return v


class AusenciaIn(Base):
    funcionario_id: int
    tipo: str
    inicio: DataISO
    fim: DataISO
    motivo: Optional[str] = None

    @field_validator("tipo")
    @classmethod
    def _t(cls, v):
        if v not in TIPOS_AUSENCIA:
            raise ValueError("Tipo inválido.")
        return v

    @field_validator("motivo")
    @classmethod
    def _m(cls, v):
        return _texto_opcional(200)(v.strip() if v else v)


class DocumentoRhIn(Base):
    funcionario_id: int
    nome: str
    emitido: Optional[DataISO] = None
    validade: DataISO
    observacao: Optional[str] = None
    _n = field_validator("nome")(_nome)

    @field_validator("observacao")
    @classmethod
    def _o(cls, v):
        return _texto_opcional(200)(v.strip() if v else v)


class FolhaResumoIn(Base):
    competencia: str  # AAAA-MM
    funcionario_id: int
    bruto: Reais
    encargos: ReaisOuZero = "0"
    beneficios: ReaisOuZero = "0"

    @field_validator("competencia")
    @classmethod
    def _c(cls, v):
        if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", v):
            raise ValueError("Competência no formato AAAA-MM.")
        return v


class FolhaLancarIn(Base):
    competencia: str
    vencimento: Optional[DataISO] = None

    @field_validator("competencia")
    @classmethod
    def _c(cls, v):
        if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", v):
            raise ValueError("Competência no formato AAAA-MM.")
        return v
