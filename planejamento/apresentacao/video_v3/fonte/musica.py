"""Trilha de fundo gerada por síntese (sem amostras nem gravações de terceiros: livre de direitos por construção).

Pad quente em lá menor (Am, F, C, G), baixo suave e pulso leve a 96 batidas por minuto.
Uso: python musica.py <segundos> <saida.wav>   (montar.py ainda passa um filtro passa-baixa no ffmpeg)
"""
import sys
import wave

import numpy as np

TAXA = 44100
BPM = 96
ACORDES = [(57, 60, 64), (53, 57, 60), (48, 52, 55), (55, 59, 62)]  # Am, F, C, G (notas MIDI)


def hz(nota):
    return 440.0 * 2 ** ((nota - 69) / 12)


def pad(nota, dur):
    t = np.arange(int(dur * TAXA)) / TAXA
    f = hz(nota)
    som = sum(np.sin(2 * np.pi * f * k * t + 0.3 * np.sin(2 * np.pi * 0.2 * t)) / k ** 1.6 for k in (1, 2, 3, 4))
    som += 0.5 * np.sin(2 * np.pi * f * 1.004 * t)  # leve desafinação para encorpar
    env = np.minimum(1, t / 1.2) * np.minimum(1, (dur - t) / 1.2)
    return som * env


def main():
    total = float(sys.argv[1])
    saida = sys.argv[2]
    n = int(total * TAXA)
    mix = np.zeros(n + TAXA * 8)
    compasso = 4 * 60 / BPM  # 2,5 s
    dur_acorde = 2 * compasso  # 5 s por acorde
    pos, i = 0.0, 0
    while pos < total + 1:
        notas = ACORDES[i % len(ACORDES)]
        ini = int(pos * TAXA)
        bloco = sum(pad(nt, dur_acorde + 1.2) for nt in notas) * 0.10
        bloco += pad(notas[0] - 24, dur_acorde + 1.2) * 0.16  # baixo
        mix[ini:ini + len(bloco)] += bloco
        pos += dur_acorde
        i += 1
    batida = 60 / BPM
    tk = np.arange(int(0.35 * TAXA)) / TAXA
    bumbo = np.sin(2 * np.pi * (48 + 60 * np.exp(-tk * 30)) * tk) * np.exp(-tk * 9) * 0.22
    rng = np.random.default_rng(7)
    ruido = rng.standard_normal(int(0.05 * TAXA))
    chimbal = np.diff(ruido, prepend=0) * np.exp(-np.arange(len(ruido)) / TAXA * 70) * 0.02  # diferença = ruído mais agudo
    b = 0
    while b * batida < total:
        ini = int(b * batida * TAXA)
        if b % 2 == 0:
            mix[ini:ini + len(bumbo)] += bumbo
        meio = ini + int(batida / 2 * TAXA)
        mix[meio:meio + len(chimbal)] += chimbal
        b += 1
    mix = mix[:n]
    ent, sai = int(2 * TAXA), int(4 * TAXA)
    mix[:ent] *= np.linspace(0, 1, ent)
    mix[-sai:] *= np.linspace(1, 0, sai)
    mix = mix / (np.max(np.abs(mix)) + 1e-9) * 0.8
    estereo = np.stack([mix, np.roll(mix, int(0.012 * TAXA))], axis=1)
    with wave.open(saida, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(TAXA)
        w.writeframes((estereo * 32767).astype("<i2").tobytes())


if __name__ == "__main__":
    main()
