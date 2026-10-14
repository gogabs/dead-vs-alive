"""Números do jogo: direções, armas, zumbis e salas."""

# Direção -> (nome falado, vetor unitário no plano: x à direita, z negativo à frente)
DIRECTIONS = {
    "up": ("frente", (0.0, -1.0)),
    "right": ("direita", (1.0, 0.0)),
    "down": ("trás", (0.0, 1.0)),
    "left": ("esquerda", (-1.0, 0.0)),
}
DIRECTION_ORDER = ("up", "right", "down", "left")
# Direções perpendiculares a cada uma (para o golpe em varredura do taco).
PERPENDICULAR = {"up": ("left", "right"), "down": ("left", "right"),
                 "left": ("up", "down"), "right": ("up", "down")}

# Tom do clique de mira por direção: cada lado soa diferente.
AIM_PITCH = {"up": 1.25, "right": 1.0, "down": 0.75, "left": 0.88}

# O mundo é medido em metros; o áudio usa a metade, para os zumbis distantes
# não sumirem com a atenuação da OpenAL.
AUDIO_SCALE = 0.5

BITE_DISTANCE = 0.8    # zumbi a esta distância morde
BITE_PUSHBACK = 3.0    # depois de morder, o zumbi recua até aqui
MAX_LIVES = 3

# mode: "single" = o zumbi mais próximo na direção
#       "spread" = todos na direção dentro do alcance
#       "pierce" = todos na direção dentro do alcance (projétil atravessa)
#       "sweep"  = todos dentro do alcance na direção e nas duas perpendiculares
# reload: segundos para encher o pente; "per_round" = um cartucho por X
WEAPONS = {
    "pistola": dict(impact="bala", name="pistola", article="uma", mag=8, range=10.0, reload=1.4,
                    cooldown=0.25, damage=1.0, mode="single", knockback=0.0,
                    melee=False, per_round=False,
                    describe="Oito balas, alcance médio."),
    "espingarda": dict(impact="chumbo", name="espingarda", article="uma", mag=2, range=5.0, reload=2.2,
                       cooldown=0.6, damage=2.0, mode="spread", knockback=1.0,
                       melee=False, per_round=False,
                       describe="Dois tiros, curto alcance, acerta todos os zumbis na direção."),
    "rifle": dict(impact="rifle", name="rifle", article="um", mag=5, range=18.0, reload=1.8,
                  cooldown=0.5, damage=2.0, mode="single", knockback=0.0,
                  melee=False, per_round=False,
                  describe="Cinco tiros, longo alcance. Atire cedo."),
    "revolver": dict(impact="bala", name="revólver", article="um", mag=6, range=10.0, reload=0.45,
                     cooldown=0.35, damage=1.5, mode="single", knockback=0.0,
                     melee=False, per_round=True,
                     describe="Seis tiros. Recarrega uma bala por vez, a qualquer momento."),
    "taco": dict(impact="taco", name="taco", article="um", mag=0, range=1.5, reload=0.0,
                 cooldown=0.35, damage=4.0, mode="sweep", knockback=0.0,
                 melee=True, per_round=False,
                 describe="Corpo a corpo. Espere o zumbi chegar bem perto: um golpe mata, "
                          "na frente e dos dois lados."),
    "besta": dict(impact="flecha", name="besta", article="uma", mag=1, range=16.0, reload=1.6,
                  cooldown=0.3, damage=2.0, mode="pierce", knockback=0.0,
                  melee=False, per_round=False,
                  describe="Um disparo, longo alcance, atravessa todos na direção."),
}
START_WEAPON = "pistola"
WEAPON_FIND_CHANCE = 0.5

# speed em m/s; quiet_until: só é ouvido a menos dessa distância
# growl: intervalo (mín, máx) entre rosnados, em segundos
ZOMBIES = {
    "comum": dict(hp=1.0, speed=0.8, step=0.9, groan_volume=0.9, quiet_until=None,
                  growl=(2.5, 5.0)),
    "corredor": dict(hp=1.0, speed=1.9, step=0.35, groan_volume=0.8, quiet_until=None,
                     growl=(1.5, 3.0)),
    "brutamontes": dict(hp=4.0, speed=0.5, step=1.2, groan_volume=1.0, quiet_until=None,
                        growl=(3.0, 6.0)),
    "rastejante": dict(hp=1.0, speed=0.7, step=0.6, groan_volume=0.9, quiet_until=4.0,
                       growl=(2.0, 4.0)),
}

# (id, nome falado, preset de reverberação, volume do ambiente, piso)
# O piso escolhe os passos e o som da queda dos zumbis.
ROOMS = [
    ("hospital_quarto", "quarto de hospital", "quarto", 0.35, "ladrilho"),
    ("hospital_corredor", "corredor do hospital", "corredor", 0.35, "marmore"),
    ("estacionamento", "estacionamento", "estacionamento", 0.45, "concreto"),
    ("cozinha", "cozinha do restaurante", "cozinha", 0.35, "metal"),
    ("metro", "estação de metrô", "metro", 0.4, "cimento"),
    ("igreja", "igreja", "igreja", 0.3, "madeira"),
    ("floresta", "floresta", "floresta", 0.45, "folhas"),
]


# Ajustes sobre os presets de reverberação do SDK, por preset. Os originais
# de corredor, cozinha, metrô e igreja têm cauda longa e alta demais: a cada
# tiro o eco cobria os passos dos zumbis que se aproximam. Aqui a cauda
# encurta (decay, em segundos) e baixa (late_gain), mantendo o caráter da sala.
REVERB_TWEAKS = {
    "corredor": dict(decay=1.2, late_gain=1.0),
    "cozinha": dict(decay=0.9, reflections_gain=0.3, late_gain=0.8),
    "metro": dict(decay=2.0, late_gain=0.85),
    "igreja": dict(decay=3.0, reflections_gain=0.15, late_gain=0.75),
}

def wave_plan(room_number):
    """Zumbis da onda: lista de tipos e intervalo entre aparições."""
    n = room_number
    cycle = (n - 1) // len(ROOMS)
    count = 3 + 2 * n
    kinds = ["comum"]
    if n >= 3:
        kinds.append("corredor")
    if n >= 4:
        kinds.append("rastejante")
    if n >= 5:
        kinds.append("brutamontes")
    interval = max(1.0, 3.5 - 0.3 * (n - 1))
    speed_mult = 1.0 + 0.12 * cycle
    return count, kinds, interval, speed_mult


SPAWN_DISTANCE = (14.0, 18.0)

# Indicador de alvo na mira: (até esta distância, nome da faixa, intervalo entre bipes).
# Grave e lento quando longe, agudo e rápido quando perto. Funciona sem fone.
TARGET_BANDS = [
    (4.0, "perto", 0.22),
    (9.0, "medio", 0.45),
    (float("inf"), "longe", 0.9),
]
BAND_WORDS = {"perto": "perto", "medio": "a média distância", "longe": "longe"}
