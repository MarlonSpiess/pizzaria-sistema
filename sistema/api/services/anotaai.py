"""Adaptador do Anota Ai. PENDENTE: a API não é pública; endereços, autenticação e formato dependem da documentação.

Enquanto ANOTAAI_URL e ANOTAAI_TOKEN não estiverem definidos (variáveis de ambiente, nunca no banco), `configurado()` é falso e nada é chamado.
"""
import os


class AnotaAi:
    codigo = "anotaai"

    def __init__(self):
        self.url = os.getenv("ANOTAAI_URL", "").strip()
        self.token = os.getenv("ANOTAAI_TOKEN", "").strip()

    def configurado(self) -> bool:
        return bool(self.url and self.token)

    def buscar_novos(self) -> list[dict]:
        raise NotImplementedError("Aguardando a documentação da API do Anota Ai.")

    def avisar(self, id_externo: str, evento: str) -> None:
        raise NotImplementedError("Aguardando a documentação da API do Anota Ai.")
