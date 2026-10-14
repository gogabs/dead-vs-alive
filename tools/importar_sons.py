#!/usr/bin/env python3
"""Importa os sons da coleção local para sounds/ (precisa de numpy).

    python tools/importar_sons.py "D:/Sons e músicas"

Para cada som do jogo, copia os arquivos de origem como variações
(nome_1, nome_2...), converte para mono os que são posicionados em 3D e
grava sounds/CREDITOS.md com a origem de cada um. Sons sem origem aqui
continuam com a versão provisória de tools/gerar_sons_provisorios.py.
"""
import glob
import os
import shutil
import subprocess
import sys
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "sounds")

KINDS = {"comum": "Normal", "corredor": "Stalker", "brutamontes": "Behemoth",
         "rastejante": "Lamprey"}
IMPACTS = {"bala": "Bullet", "chumbo": "Shell", "rifle": "Sniper", "flecha": "Arrow",
           "taco": "Hammer"}
# piso do jogo -> (pasta de passos, queda do zumbi)
FLOORS = {"ladrilho": ("Tile", "FallHard"), "marmore": ("Marble", "FallHard"),
          "concreto": ("Concrete", "FallHard"), "metal": ("Metal", "FallMetal"),
          "cimento": ("Cement", "FallHard"), "madeira": ("Wood", "FallWood"),
          "folhas": ("Leaves", "FallGrass")}
WEAPONS = {"pistola": "G17", "espingarda": "SPAS12", "rifle": "M40", "revolver": "Python",
           "taco": "Hammer", "besta": "Crossbow"}
AMBIENCE = {
    "hospital_quarto": "swamp/Ambience/EKG.wav",
    "hospital_corredor": "sbyw/loop_hallway.ogg",
    "estacionamento": "sbyw/loop_rainoncars.ogg",
    "cozinha": "sbyw/loop_kitchen_industrial.ogg",
    "metro": "sbyw/loop_subway_tunnel.ogg",
    "igreja": "swamp/Ambience/Church.wav",
    "floresta": "sbyw/loop_forest_night.ogg",
}


def plan():
    """Lista de (nome no jogo, padrão de origem, posicionado em 3D)."""
    items = []
    for kind, src in KINDS.items():
        z = "swamp/Zombies/%s/" % src
        items.append(("rosnado_" + kind, z + "Growl*.wav", True))
        items.append(("ataque_" + kind, z + "Attack*.wav", True))
        for impact, prefix in IMPACTS.items():
            items.append(("impacto_%s_%s" % (impact, kind), z + prefix + "[0-9]*.wav", True))
        for floor, (_, fall) in FLOORS.items():
            items.append(("queda_%s_%s" % (kind, floor), z + fall + ".wav", True))
    items.append(("passo_brutamontes", "swamp/Zombies/Behemoth/Walk*.wav", True))
    for floor, (steps, _) in FLOORS.items():
        items.append(("passo_" + floor, "swamp/Steps/%s/*.wav" % steps, True))
    for key, src in WEAPONS.items():
        w = "swamp/Weapons/%s/" % src
        melee = key == "taco"
        items.append((("golpe_" if melee else "tiro_") + key, w + "Fire.wav", False))
        items.append(("sacar_" + key, w + "Draw.wav", False))
        if not melee:
            items.append(("vazia_" + key, w + "Empty.wav", False))
            if key != "revolver":   # o revólver recarrega bala a bala
                items.append(("recarga_" + key, w + "Reloading.wav", False))
                items.append(("pronta_" + key, w + "Reloaded.wav", False))
    items.append(("morte", "swamp/Player/Death*.wav", False))
    for room, src in AMBIENCE.items():
        items.append(("ambiente_" + room, src, False))
    return items


def to_mono_wav(src, dst):
    with wave.open(src, "rb") as w:
        ch, width, rate = w.getnchannels(), w.getsampwidth(), w.getframerate()
        data = w.readframes(w.getnframes())
    if width != 2:
        raise ValueError("só WAV de 16 bits")
    samples = np.frombuffer(data, dtype="<i2")
    if ch == 2:
        samples = samples.reshape(-1, 2).astype(np.int32).mean(axis=1).astype("<i2")
    with wave.open(dst, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(samples.tobytes())


AMBIENCE_SECONDS = 40
CROSSFADE = 1.5


def ambience_wav(src, dst):
    """Ambiente: decodifica (ffmpeg), corta em 40 s e emenda o fim no começo.

    OGG longo demora segundos para decodificar no console; WAV curto abre na hora.
    """
    rate = 22050
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", src, "-t", str(AMBIENCE_SECONDS + CROSSFADE),
         "-ac", "2", "-ar", str(rate), "-f", "s16le", "-"],
        check=True, stdout=subprocess.PIPE).stdout
    x = np.frombuffer(raw, dtype="<i2").reshape(-1, 2).astype(np.float64)
    n = int(rate * CROSSFADE)
    if len(x) > 3 * n:
        ramp = np.linspace(0, 1, n)[:, None]
        head, tail = x[:n], x[-n:]
        x = x[n:].copy()
        x[-n:] = tail * (1 - ramp) + head * ramp
    with wave.open(dst, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(np.clip(x, -32768, 32767).astype("<i2").tobytes())


def remove_existing(name):
    for f in glob.glob(os.path.join(OUT, name + ".*")) + glob.glob(os.path.join(OUT, name + "_[0-9]*.*")):
        os.remove(f)


def main(root):
    credits = []
    missing = []
    for name, pattern, positional in plan():
        sources = sorted(glob.glob(os.path.join(root, pattern)))
        if not sources:
            missing.append((name, pattern))
            continue
        remove_existing(name)
        for i, src in enumerate(sources, 1):
            ext = os.path.splitext(src)[1].lower()
            base = name if len(sources) == 1 else "%s_%d" % (name, i)
            if name.startswith("ambiente_"):
                ext = ".wav"
            dst = os.path.join(OUT, base + ext)
            if name.startswith("ambiente_"):
                ambience_wav(src, dst)
            elif positional and ext == ".wav":
                to_mono_wav(src, dst)
            else:
                shutil.copyfile(src, dst)
            credits.append((base + ext, os.path.relpath(src, root).replace(os.sep, "/")))
    with open(os.path.join(OUT, "CREDITOS.md"), "w", encoding="utf-8") as f:
        f.write("# Origem dos sons\n\n")
        f.write("Sons importados da coleção local do autor com tools/importar_sons.py.\n")
        f.write("Os que não aparecem aqui são provisórios, gerados por "
                "tools/gerar_sons_provisorios.py.\n\n")
        f.write("| Arquivo | Origem |\n|---|---|\n")
        for dst, src in credits:
            f.write("| %s | %s |\n" % (dst, src))
    print("%d arquivos importados" % len(credits))
    for name, pattern in missing:
        print("sem origem: %s (%s)" % (name, pattern))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "D:/Sons e músicas")
