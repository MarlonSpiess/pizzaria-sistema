"""Monta o vídeo final a partir das cenas gravadas (gravar.js), da narração (gerar_narracao.py) e da trilha (musica.py).

Para cada versão (completa e curta): corta cada cena no ponto exato, põe a narração no tempo certo, junta tudo,
mistura a trilha baixinha por baixo da voz, queima as legendas e grava também o .srt ao lado.

Uso (Linux, ffmpeg com libass e a fonte Inter instalada): python montar.py <pasta_cenas> <pasta_saida> [completa|curta|ambas]
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ROTEIRO = json.loads((AQUI / "narracao.json").read_text(encoding="utf-8"))
AUDIO = AQUI / "audio"
ENTRADA = 0.6  # igual ao gravar.js: a narração começa 0,6 s depois do início da cena
FADE = 0.3
LIMITE_LINHA = 46


def ff(*args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *map(str, args)], check=True)


def duracao(arq):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(arq)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def instante_da_marca(arq):
    """Tempo (s) do primeiro quadro com o traço magenta que gravar.js acende na primeira linha da tela."""
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(arq), "-t", "5", "-vf", "crop=2:2:960:0", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       capture_output=True, check=True)
    px = r.stdout  # 2x2 pixels por quadro (o traço tem 4 px de altura, para sobreviver ao yuv420)
    for q in range(len(px) // 12):
        if px[12 * q] > 200 and px[12 * q + 1] < 80 and px[12 * q + 2] > 200:
            return q / 30
    raise SystemExit(f"[erro] {arq.name}: marca de sincronia não encontrada; grave a cena de novo")


def conferir(cena):
    """Recusa cena com erro, atraso ou duração que não bate com a narração atual."""
    if cena.get("erro") or cena.get("atraso", 0) > 0.3:
        raise SystemExit(f"[erro] {cena['id']}: gravada com erro ou atraso ({cena.get('erro') or cena['atraso']}); grave de novo")
    taxa = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=sample_rate", "-of", "csv=p=0",
                           str(AUDIO / f"{cena['id']}.mp3")], capture_output=True, text=True).stdout.strip()
    if taxa != "24000":  # o edge-tts entrega 24 kHz; outro valor indica arquivo provisório ou trocado
        raise SystemExit(f"[erro] {cena['id']}.mp3 não parece a narração do gerar_narracao.py ({taxa} Hz)")
    palavras = json.loads((AUDIO / f"{cena['id']}.json").read_text(encoding="utf-8"))["palavras"]
    esperado = ENTRADA + palavras[-1]["fim"] + 1.0
    if abs(esperado - cena["duracao"]) > 0.05:
        raise SystemExit(f"[erro] {cena['id']}: a narração mudou depois da gravação ({cena['duracao']} s gravados, {esperado:.2f} s agora)")


def segmento(cena, pasta_cenas, tmp):
    """Cena cortada no tempo da narração, com a voz já posicionada. Saída em formato idêntico para o concat."""
    conferir(cena)
    cid, dur = cena["id"], cena["duracao"]
    ini = instante_da_marca(pasta_cenas / f"{cid}.mp4") + cena["marca_antes"]
    saida = tmp / f"{cid}.mp4"
    voz = AUDIO / f"{cid}.mp3"
    atraso = int(ENTRADA * 1000)
    ff("-ss", f"{ini:.3f}", "-i", pasta_cenas / f"{cid}.mp4", "-i", voz,
       "-filter_complex",
       f"[0:v]tpad=stop_mode=clone:stop_duration=2,trim=duration={dur:.3f},setpts=PTS-STARTPTS,fps=30,fade=t=in:st=0:d={FADE},fade=t=out:st={dur - FADE:.3f}:d={FADE}[v];"
       f"[1:a]aresample=48000,adelay={atraso}|{atraso},apad,atrim=duration={dur:.3f},asetpts=PTS-STARTPTS[a]",
       "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
       "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", saida.with_suffix(".mkv"))
    return saida.with_suffix(".mkv")


def fmt_srt(t):
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", ",")


def fmt_ass(t):
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def legendas(cenas):
    """Frases curtas a partir das marcas de tempo de cada palavra: quebra em pontuação ou no limite de caracteres."""
    cues, base = [], 0.0
    for cena in cenas:
        dados = json.loads((AUDIO / f"{cena['id']}.json").read_text(encoding="utf-8"))
        palavras, texto_cena = dados["palavras"], dados["texto"].split()
        # O serviço de voz devolve as palavras sem pontuação: um ponteiro no texto original recupera a escrita com pontuação.
        # Se uma marca não casar com nada adiante, usa a palavra como veio e o ponteiro não anda.
        grupo, ini, ptr = [], None, 0
        limpa = lambda w: w.strip(".,:;?!\"'").lower()
        for i, p in enumerate(palavras):
            escrita = p["palavra"]
            for k in range(ptr, min(ptr + 4, len(texto_cena))):
                if limpa(texto_cena[k]) == limpa(p["palavra"]):
                    escrita, ptr = texto_cena[k], k + 1
                    break
            if ini is None:
                ini = p["inicio"]
            grupo.append(escrita)
            fim_frase = escrita[-1] in ".?!:"
            proxima = palavras[i + 1]["palavra"] if i + 1 < len(palavras) else ""
            longa = len(" ".join(grupo + [proxima])) > LIMITE_LINHA
            if fim_frase or longa or i == len(palavras) - 1 or (escrita[-1] in ",;" and len(" ".join(grupo)) > 24):
                cues.append((base + ENTRADA + ini, base + ENTRADA + p["fim"] + 0.15, " ".join(grupo)))
                grupo, ini = [], None
        base += cena["duracao_real"]
    # sem sobreposição
    for k in range(len(cues) - 1):
        if cues[k][1] > cues[k + 1][0]:
            cues[k] = (cues[k][0], cues[k + 1][0] - 0.02, cues[k][2])
    return cues


def escrever_legendas(cues, srt, ass):
    srt.write_text("".join(f"{i}\n{fmt_srt(a)} --> {fmt_srt(b)}\n{t}\n\n" for i, (a, b, t) in enumerate(cues, 1)), encoding="utf-8")
    cab = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\nWrapStyle: 2\n\n[V4+ Styles]\n"
           "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
           "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
           "Style: Leg,Inter,46,&H00FFFFFF,&H00FFFFFF,&H00000000,&H9A120D0A,1,0,0,0,100,100,0,0,3,14,0,2,80,80,34,1\n\n"
           "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    ass.write_text(cab + "".join(f"Dialogue: 0,{fmt_ass(a)},{fmt_ass(b)},Leg,,0,0,0,,{t}\n" for a, b, t in cues), encoding="utf-8")


def versao(nome, ids, pasta_cenas, pasta_saida, relatorio):
    cenas = [relatorio[i] for i in ids]
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        segs = [segmento(c, pasta_cenas, tmp) for c in cenas]
        for c, sg in zip(cenas, segs):  # legendas somam a duração real de cada trecho (quadros inteiros), sem deriva
            c["duracao_real"] = duracao(sg)
        lista = tmp / "lista.txt"
        lista.write_text("".join(f"file '{s}'\n" for s in segs))
        corpo = tmp / "corpo.mkv"
        ff("-f", "concat", "-safe", "0", "-i", lista, "-c", "copy", corpo)
        total = duracao(corpo)
        trilha = tmp / "trilha.wav"
        subprocess.run([sys.executable, str(AQUI / "musica.py"), f"{total:.3f}", str(trilha)], check=True)
        cues = legendas(cenas)
        srt, ass = pasta_saida / f"{nome}.srt", tmp / "leg.ass"
        escrever_legendas(cues, srt, ass)
        final = pasta_saida / f"{nome}.mp4"
        # Voz normalizada; trilha com passa-baixa, bem abaixo da voz e abaixando mais quando há fala (sidechain).
        assert ":" not in str(ass) and "'" not in str(ass), "caminho temporário inesperado para o filtro de legendas"
        ff("-i", corpo, "-i", trilha, "-filter_complex",
           f"[0:a]loudnorm=I=-16:TP=-1.5:LRA=11,asplit=2[voz][chave];"
           f"[1:a]lowpass=f=2200,volume=0.32,atrim=duration={total:.3f}[mus];"
           f"[mus][chave]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[musd];"
           f"[voz][musd]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a];"
           f"[0:v]subtitles={ass}:fontsdir=/usr/share/fonts[v]",
           "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", final)
        print(f"[ok] {final.name}: {duracao(final):.1f} s, {final.stat().st_size / 1e6:.1f} MB")


def main():
    pasta_cenas, pasta_saida = Path(sys.argv[1]), Path(sys.argv[2])
    qual = sys.argv[3] if len(sys.argv) > 3 else "ambas"
    pasta_saida.mkdir(parents=True, exist_ok=True)
    relatorio = {c["id"]: c for c in json.loads((pasta_cenas / "cenas.json").read_text(encoding="utf-8"))}
    if qual in ("completa", "ambas"):
        versao("Sistema_Pizzaria_Apresentacao_Completa", ROTEIRO["versao_completa"], pasta_cenas, pasta_saida, relatorio)
    if qual in ("curta", "ambas"):
        versao("Sistema_Pizzaria_Apresentacao_Curta", ROTEIRO["versao_curta"], pasta_cenas, pasta_saida, relatorio)


if __name__ == "__main__":
    main()
