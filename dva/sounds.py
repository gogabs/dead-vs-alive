"""Carrega os sons da pasta sounds/ por nome, com variações.

Um som "tiro_pistola" pode ser um arquivo (tiro_pistola.ogg / .wav) ou
várias variações (tiro_pistola_1.ogg, tiro_pistola_2.ogg...). play() sorteia
uma variação. Trocar os sons do jogo é só trocar os arquivos.
"""
import os
import random
import re

EXTENSIONS = (".ogg", ".wav")


class SoundBank:
    def __init__(self, audio, folder):
        self.audio = audio
        self.folder = folder
        self.variants = {}
        self._scan()

    def _scan(self):
        try:
            files = sorted(os.listdir(os.path.join(self.audio.base_dir, self.folder)))
        except OSError:
            files = []
        for f in files:
            base, ext = os.path.splitext(f)
            if ext.lower() not in EXTENSIONS:
                continue
            m = re.match(r"^(.*)_(\d+)$", base)
            name = m.group(1) if m else base
            path = os.path.join(self.folder, f)
            sound = self.audio.load(base, path)
            self.variants.setdefault(name, []).append(sound)

    def has(self, name):
        return name in self.variants

    def get(self, name):
        options = self.variants.get(name)
        if not options:
            return None
        return random.choice(options)

    def play(self, name, **kwargs):
        sound = self.get(name)
        if sound is None:
            return None
        return sound.play(**kwargs)
