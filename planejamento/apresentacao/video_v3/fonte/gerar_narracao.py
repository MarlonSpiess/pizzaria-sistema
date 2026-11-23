"""Gera a narração do vídeo com voz neural (edge-tts), uma faixa por cena, mais as marcas de tempo de cada palavra.

Precisa de internet (serviço de voz da Microsoft usado pelo Edge). Roda em qualquer PC com Python 3.10+:
    pip install edge-tts==7.3.1
    python gerar_narracao.py [pasta_saida]
Saída: <pasta_saida>/<cena>.mp3 e <cena>.json (palavras com início e fim em segundos).
"""
import asyncio
import json
import sys
from pathlib import Path

import edge_tts

AQUI = Path(__file__).resolve().parent


async def gerar(cena, voz, velocidade, saida):
    com = edge_tts.Communicate(cena["texto"], voz, rate=velocidade, boundary="WordBoundary")
    audio, palavras = bytearray(), []
    async for parte in com.stream():
        if parte["type"] == "audio":
            audio += parte["data"]
        elif parte["type"] == "WordBoundary":
            ini = parte["offset"] / 1e7
            palavras.append({"palavra": parte["text"], "inicio": round(ini, 3), "fim": round(ini + parte["duration"] / 1e7, 3)})
    if not audio or not palavras:
        raise SystemExit(f"[erro] {cena['id']}: o serviço de voz não devolveu áudio ou marcas de tempo; rode de novo")
    (saida / f"{cena['id']}.mp3").write_bytes(bytes(audio))
    (saida / f"{cena['id']}.json").write_text(json.dumps({"texto": cena["texto"], "palavras": palavras}, ensure_ascii=False, indent=1),
                                               encoding="utf-8")
    print(f"[ok] {cena['id']}: {len(palavras)} palavras")


async def main():
    roteiro = json.loads((AQUI / "narracao.json").read_text(encoding="utf-8"))
    saida = Path(sys.argv[1]) if len(sys.argv) > 1 else AQUI / "audio"
    saida.mkdir(parents=True, exist_ok=True)
    for cena in roteiro["cenas"]:
        await gerar(cena, roteiro["voz"], roteiro["velocidade"], saida)


if __name__ == "__main__":
    asyncio.run(main())
