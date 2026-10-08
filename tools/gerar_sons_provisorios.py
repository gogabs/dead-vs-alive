#!/usr/bin/env python3
"""Gera sons provisórios sintetizados para o Dead vs. Alive (precisa de numpy).

São só para testar a jogabilidade. Para trocar por sons de verdade, coloque
um arquivo com o mesmo nome (ou nome_1, nome_2... para variações) em sounds/
e apague o provisório.

    python tools/gerar_sons_provisorios.py
"""
import os
import wave

import numpy as np

RATE = 22050
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sounds")
rng = np.random.default_rng(42)


def t(sec):
    return np.arange(int(RATE * sec)) / RATE


def noise(sec):
    return rng.uniform(-1, 1, int(RATE * sec))


def band(x, lo, hi):
    """Filtro passa-faixa por FFT."""
    spec = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(len(x), 1 / RATE)
    spec[(freqs < lo) | (freqs > hi)] = 0
    return np.fft.irfft(spec, len(x))


def env_exp(n_sec, decay):
    return np.exp(-t(n_sec) / decay)


def fade(x, a=0.005, b=0.02):
    x = x.copy()
    na, nb = int(RATE * a), int(RATE * b)
    if na:
        x[:na] *= np.linspace(0, 1, na)
    if nb:
        x[-nb:] *= np.linspace(1, 0, nb)
    return x


def saw(freq, sec):
    ph = np.cumsum(np.broadcast_to(freq, int(RATE * sec)) / RATE)
    return 2 * (ph % 1.0) - 1


def pad(x, sec):
    return np.concatenate([x, np.zeros(int(RATE * sec))])


def mix(length_sec, *parts):
    out = np.zeros(int(RATE * length_sec))
    for start, x in parts:
        i = int(RATE * start)
        x = x[: max(0, len(out) - i)]
        out[i:i + len(x)] += x
    return out


def save(name, x, peak=0.8):
    x = np.asarray(x, dtype=float)
    m = np.max(np.abs(x)) or 1.0
    data = (x / m * peak * 32767).astype("<i2")
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data.tobytes())


def loopable(x, cross=0.5):
    """Faz o fim emendar no começo sem estalo."""
    n = int(RATE * cross)
    head, tail = x[:n], x[-n:]
    ramp = np.linspace(0, 1, n)
    x = x[n:].copy()
    x[-n:] = tail * (1 - ramp) + head * ramp
    return x


# --- tiros e armas --------------------------------------------------------
def gunshot(sec, lo, hi, decay, thump):
    x = band(noise(sec), lo, hi) * env_exp(sec, decay)
    x += 0.8 * np.sin(2 * np.pi * thump * t(sec)) * env_exp(sec, decay * 1.5)
    return fade(x, 0.001, 0.05)


def click(freq=2500, sec=0.015):
    return fade(np.sin(2 * np.pi * freq * t(sec)) * env_exp(sec, 0.004), 0.0005, 0.003)


def metal_click():
    x = band(noise(0.04), 2000, 8000) * env_exp(0.04, 0.006)
    return x + 0.4 * np.sin(2 * np.pi * 3100 * t(0.04)) * env_exp(0.04, 0.01)


def pluck(freq, sec):
    n = int(RATE / freq)
    buf = rng.uniform(-1, 1, n)
    out = np.zeros(int(RATE * sec))
    for i in range(len(out)):
        out[i] = buf[i % n]
        buf[i % n] = 0.5 * (buf[i % n] + buf[(i + 1) % n]) * 0.996
    return out


def weapons():
    save("tiro_pistola", gunshot(0.5, 200, 6000, 0.07, 110))
    save("tiro_revolver", gunshot(0.6, 150, 5000, 0.09, 90))
    save("tiro_rifle", gunshot(0.7, 400, 9000, 0.05, 140))
    save("tiro_espingarda", gunshot(0.9, 80, 4000, 0.14, 60))
    whoosh = band(noise(0.25), 800, 3000) * np.sin(np.pi * t(0.25) / 0.25)
    save("tiro_besta", mix(0.6, (0, 0.6 * pluck(180, 0.5)), (0.02, whoosh)))
    swing = band(noise(0.25), 400, 2500) * np.sin(np.pi * t(0.25) / 0.25) ** 2
    save("golpe", swing)
    save("golpe_taco", band(noise(0.3), 200, 1500) * np.sin(np.pi * t(0.3) / 0.3) ** 2)
    save("impacto", fade(band(noise(0.18), 60, 1200) * env_exp(0.18, 0.04)
                         + 0.7 * np.sin(2 * np.pi * 70 * t(0.18)) * env_exp(0.18, 0.05)))
    save("vazia", mix(0.1, (0, metal_click())))
    save("sem_balas", mix(0.2, (0, click(1800)), (0.08, click(1400))))
    save("negado", fade(0.6 * saw(110, 0.18) * env_exp(0.18, 0.1)))
    save("cartucho", mix(0.25, (0, metal_click()), (0.1, click(3500, 0.03))))
    save("pronta", mix(0.4, (0, metal_click()), (0.18, metal_click()), (0.2, click(900))))
    rec = [(i * 0.22, metal_click()) for i in range(5)]
    save("recarga", mix(1.2, *rec))
    save("recarga_espingarda", mix(2.0, *[(i * 0.5, metal_click()) for i in range(3)]))


# --- zumbis ---------------------------------------------------------------
def groan(base, sec, rough=0.3):
    tt = t(sec)
    freq = base * (1 + 0.08 * np.sin(2 * np.pi * 0.7 * tt) + 0.03 * np.sin(2 * np.pi * 5 * tt))
    voice = saw(freq, sec)
    voice = band(voice, 250, 900) + 0.5 * band(voice, 80, 250)
    voice += rough * band(noise(sec), 300, 1200)
    swell = 0.5 + 0.5 * np.sin(2 * np.pi * tt / sec * 2 - np.pi / 2)
    return voice * (0.3 + 0.7 * swell)


def step(lo, hi, sec, decay):
    return fade(band(noise(sec), lo, hi) * env_exp(sec, decay), 0.002, 0.02)


def zombies():
    save("rosnado", fade(groan(95, 2.2), 0.05, 0.4))
    save("rosnado_corredor", fade(groan(140, 1.5, 0.6), 0.05, 0.3))
    save("rosnado_brutamontes", fade(groan(65, 2.8, 0.2), 0.05, 0.5))
    save("rosnado_rastejante", fade(groan(110, 2.0, 0.8), 0.05, 0.4))
    for i in range(1, 4):
        save("passo_%d" % i, step(60, 600 + 100 * i, 0.14, 0.03))
        save("passo_brutamontes_%d" % i, step(30, 300 + 50 * i, 0.25, 0.06))
        scrape = band(noise(0.35), 800 + 200 * i, 4000) * np.sin(np.pi * t(0.35) / 0.35)
        save("passo_rastejante_%d" % i, scrape)
    death = groan(110, 0.9, 0.5) * np.linspace(1, 0, int(RATE * 0.9))
    save("morte_zumbi", fade(death))
    crunch = mix(0.35, *[(i * 0.06, band(noise(0.05), 500, 5000) * env_exp(0.05, 0.01))
                         for i in range(5)])
    save("mordida", crunch)
    save("dor", fade(band(saw(np.linspace(220, 160, int(RATE * 0.35)), 0.35), 200, 1500)
                     * env_exp(0.35, 0.15)))
    fall = band(saw(np.linspace(180, 60, int(RATE * 1.5)), 1.5), 100, 1200) * np.linspace(1, 0, int(RATE * 1.5))
    save("morte", fade(fall))


# --- interface -------------------------------------------------------------
def interface():
    save("mira", click(2000, 0.02))
    for name, freq, sec in (("alvo_longe", 520, 0.09), ("alvo_medio", 880, 0.07),
                            ("alvo_perto", 1500, 0.05)):
        beep = np.sin(2 * np.pi * freq * t(sec)) + 0.3 * np.sin(2 * np.pi * 2 * freq * t(sec))
        save(name, fade(beep, 0.003, 0.02), 0.6)
    save("menu_mover", click(1600, 0.02), 0.5)
    save("menu_confirmar", mix(0.2, (0, click(1200, 0.05)), (0.07, click(1800, 0.06))), 0.5)
    notes = [523, 659, 784, 1047]
    chime = mix(0.9, *[(i * 0.1, np.sin(2 * np.pi * f * t(0.5)) * env_exp(0.5, 0.15))
                       for i, f in enumerate(notes)])
    save("arma_achada", chime)
    save("avancar", mix(2.0, *[(i * 0.45, step(60, 900, 0.14, 0.03)) for i in range(4)]))


# --- ambientes --------------------------------------------------------------
def ambience():
    sec = 20.0
    tt = t(sec)
    hum = 0.15 * np.sin(2 * np.pi * 60 * tt) + 0.05 * np.sin(2 * np.pi * 120 * tt)
    beeps = mix(sec, *[(i * 1.0, 0.3 * np.sin(2 * np.pi * 1000 * t(0.12)) * np.hanning(int(RATE * 0.12)))
                       for i in range(20)])
    save("ambiente_hospital_quarto", loopable(hum + beeps + 0.03 * band(noise(sec), 200, 2000)), 0.5)
    buzz = 0.08 * band(saw(120, sec), 100, 3000)
    save("ambiente_hospital_corredor", loopable(hum + buzz + 0.04 * band(noise(sec), 100, 800)), 0.5)
    rain = band(noise(sec), 400, 6000) * 0.5
    drops = mix(sec, *[(rng.uniform(0, sec - 0.05), click(rng.uniform(1500, 4000), 0.03) * 0.6)
                       for _ in range(200)])
    save("ambiente_estacionamento", loopable(rain + drops), 0.5)
    fan = band(noise(sec), 150, 900) * 0.6 + 0.2 * np.sin(2 * np.pi * 100 * tt)
    save("ambiente_cozinha", loopable(fan), 0.5)
    rumble = band(noise(sec), 20, 200) * (0.6 + 0.4 * np.sin(2 * np.pi * tt / 10))
    save("ambiente_metro", loopable(rumble), 0.5)
    bells = mix(sec, *[(s, sum(np.sin(2 * np.pi * f * t(4.0)) / (k + 1) for k, f in enumerate((392, 784, 1176)))
                        * env_exp(4.0, 1.2)) for s in (2.0, 12.0)])
    wind_c = band(noise(sec), 100, 600) * 0.2
    save("ambiente_igreja", loopable(bells * 0.3 + wind_c), 0.4)
    wind = band(noise(sec), 150, 1500) * (0.5 + 0.5 * np.sin(2 * np.pi * tt / 7) ** 2)
    twigs = mix(sec, *[(rng.uniform(0, sec - 0.05), band(noise(0.04), 1000, 6000) * env_exp(0.04, 0.008))
                       for _ in range(15)])
    save("ambiente_floresta", loopable(wind + twigs), 0.5)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    weapons()
    zombies()
    interface()
    ambience()
    print("sons gerados em", os.path.abspath(OUT))
