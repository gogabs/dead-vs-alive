"""Uma partida: salas, ondas, zumbis, armas e vidas."""
import random

from . import config as C
from .graphics_events import emit, target


def audio_pos(direction, distance):
    vx, vz = C.DIRECTIONS[direction][1]
    d = distance * C.AUDIO_SCALE
    return (vx * d, 0.0, vz * d)


def band_of(distance):
    for limit, band, interval in C.TARGET_BANDS:
        if distance < limit:
            return band, interval
    return C.TARGET_BANDS[-1][1:]


def distance_word(distance):
    return C.BAND_WORDS[band_of(distance)[0]]


class Zombie:
    def __init__(self, run, kind, direction, distance, speed_mult=1.0):
        spec = C.ZOMBIES[kind]
        self.run = run
        self.kind = kind
        self.direction = direction
        self.distance = distance
        self.hp = spec["hp"]
        self.speed = spec["speed"] * speed_mult * random.uniform(0.9, 1.1)
        self.step_every = spec["step"]
        self.step_timer = random.uniform(0, self.step_every)
        self.quiet_until = spec["quiet_until"]
        self.groan_volume = spec["groan_volume"]
        self.growl_every = spec["growl"]
        self.growl_timer = random.uniform(0.2, 1.5)
        self.voice_pitch = random.uniform(0.92, 1.08)
        self.alive = True
        self.groan = None   # rosnado tocando agora (acompanha o zumbi)

    def _name(self, base):
        specific = "%s_%s" % (base, self.kind)
        return specific if self.run.bank.has(specific) else base

    def pos(self):
        return audio_pos(self.direction, self.distance)

    def audible(self):
        return self.quiet_until is None or self.distance <= self.quiet_until

    def _update_groan(self, dt):
        self.growl_timer -= dt
        if self.growl_timer <= 0:
            self.growl_timer = random.uniform(*self.growl_every)
            # um rosnado por vez: o anterior ainda tocando segue o zumbi e
            # para quando ele morre; um novo por cima ficaria solto no lugar
            busy = self.groan is not None and self.groan.playing
            if self.audible() and not busy and self.run.voice_free(self):
                self.groan = self.run.track(self.run.bank.play(
                    self._name("rosnado"), pos=self.pos(),
                    volume=self.groan_volume, pitch=self.voice_pitch))
        if self.groan is not None:
            if self.groan.playing:
                self.groan.set_position(*self.pos())
            else:
                self.groan = None

    def update(self, dt):
        if self.distance > C.BITE_DISTANCE:
            self.distance = max(C.BITE_DISTANCE, self.distance - self.speed * dt)
        self.step_timer -= dt
        if self.step_timer <= 0:
            self.step_timer += self.step_every
            if self.quiet_until is None or self.distance <= self.quiet_until + 2:
                floor = self.run.floor
                pitch = random.uniform(0.9, 1.1)
                if self.run.voice_free(self):
                    self.run.track(self.run.bank.play_first(
                        ["passo_%s" % self.kind, "passo_%s" % floor, "passo"],
                        pos=self.pos(), volume=0.8, pitch=pitch))
        self._update_groan(dt)

    def push(self, meters):
        self.distance = min(C.SPAWN_DISTANCE[1], self.distance + meters)

    def kill(self):
        emit(self.run, 'death', **target(self))
        self.alive = False
        if self.groan is not None:
            self.groan.stop(fade=0.15)
        floor, pos = self.run.floor, self.pos()
        self.run.game.after(0.25, lambda: self.run.bank.play_first(
            ["queda_%s_%s" % (self.kind, floor), "queda_%s" % floor, "morte_zumbi"],
            pos=pos))

    def silence(self):
        if self.groan is not None:
            self.groan.stop()


class Run:
    """Uma partida. tutorial=True desliga ondas automáticas e vidas."""

    def __init__(self, game, bank, on_over, tutorial=False):
        self.game = game
        self.bank = bank
        self.on_over = on_over          # on_over(sala, mortes) ao morrer
        self.tutorial = tutorial
        self.room_number = 0
        self.kills = 0
        self.lives = C.MAX_LIVES
        self.zombies = []
        self.spawn_queue = []
        self.spawn_timer = 0.0
        self.spawn_interval = 3.0
        self.speed_mult = 1.0
        self.state = "idle"             # idle, intro, fighting, between, over
        self.paused = False
        self.ambience = None
        self.floor = "ladrilho"
        self.aim = "up"
        self.cooldown = 0.0
        self.reload_timer = 0.0
        self.target_band = None         # faixa do alvo na mira (indicador)
        self.target_timer = 0.0
        self.on_kill = None             # ganchos do tutorial
        self.on_reloaded = None
        self._visual_events = []
        self.zombie_voices = []         # passos e rosnados tocando (limite em config)
        self.set_weapon(C.START_WEAPON)

    # --- armas ---------------------------------------------------------
    def set_weapon(self, key, announce=False):
        if announce:
            self.bank.play_first(["sacar_" + key, "arma_achada"], reverb=False)
        self.weapon_key = key
        self.weapon = C.WEAPONS[key]
        self.ammo = self.weapon["mag"]
        self.reload_timer = 0.0
        self.cooldown = 0.0

    def _wname(self, base):
        specific = "%s_%s" % (base, self.weapon_key)
        return specific if self.bank.has(specific) else base

    def set_aim(self, direction):
        if direction == self.aim:
            return
        self.aim = direction
        vx, vz = C.DIRECTIONS[direction][1]
        self.bank.play("mira", pitch=C.AIM_PITCH[direction], pos=(vx, 0.0, vz),
                       reverb=False, volume=0.7)
        # o indicador toca logo depois do clique, se houver alvo
        self.target_band = None
        self.target_timer = 0.08

    def _target(self):
        """Zumbi mais próximo na direção da mira (só os que já dá para ouvir)."""
        candidates = [z for z in self.zombies
                      if z.alive and z.direction == self.aim and z.audible()]
        return min(candidates, key=lambda z: z.distance) if candidates else None

    def _update_target(self, dt):
        z = self._target()
        if z is None:
            self.target_band = None
            return
        band, interval = band_of(z.distance)
        if band != self.target_band:
            # alvo novo ou mudou de faixa: avisa já (ou logo após o clique da mira)
            self.target_band = band
            self.target_timer = min(self.target_timer, 0.08) if self.target_timer > 0 else 0.0
        self.target_timer -= dt
        if self.target_timer <= 0:
            self.target_timer += interval
            if self.target_timer <= 0:
                self.target_timer = interval
            vx, vz = C.DIRECTIONS[self.aim][1]
            self.bank.play("alvo_" + band, pos=(vx, 0.0, vz), reverb=False, volume=0.6)

    def fire(self):
        if self.state != "fighting" or self.paused:
            return
        w = self.weapon
        if self.reload_timer > 0 and not w["per_round"]:
            return
        if self.cooldown > 0:
            return
        if not w["melee"] and self.ammo <= 0:
            self.bank.play(self._wname("vazia"), reverb=False)
            return
        self.cooldown = w["cooldown"]
        if w["per_round"]:
            self.reload_timer = 0.0   # atirar interrompe a recarga bala a bala
        vx, vz = C.DIRECTIONS[self.aim][1]
        self.bank.play(self._wname("golpe" if w["melee"] else "tiro"),
                       pos=(vx * 0.3, 0.0, vz * 0.3))
        if not w["melee"]:
            self.ammo -= 1
        emit(self, 'attack', weapon=self.weapon_key, direction=self.aim)
        directions = (self.aim,)
        if w["mode"] == "sweep":
            directions += C.PERPENDICULAR[self.aim]
        in_line = sorted((z for z in self.zombies if z.alive and z.direction in directions
                          and z.distance <= w["range"]), key=lambda z: z.distance)
        targets = in_line[:1] if w["mode"] == "single" else in_line
        for z in targets:
            z.hp -= w["damage"]
            emit(self, "impact", **target(z))
            self.bank.play_first(["impacto_%s_%s" % (w["impact"], z.kind),
                                  "impacto_%s" % w["impact"], "impacto"],
                                 pos=z.pos(), pitch=random.uniform(0.95, 1.05))
            if z.hp <= 0:
                z.kill()
                self.kills += 1
                if self.on_kill:
                    self.on_kill(z)
            elif w["knockback"]:
                z.push(w["knockback"])
        if not w["melee"] and self.ammo == 0:
            self.game.after(0.25, lambda: self.bank.play("sem_balas", reverb=False))

    def reload(self):
        if self.state != "fighting" or self.paused:
            return
        w = self.weapon
        if w["melee"] or self.reload_timer > 0 or self.ammo >= w["mag"]:
            return
        if not w["per_round"] and self.ammo > 0:
            self.bank.play("negado", reverb=False)
            return
        self.reload_timer = w["reload"]
        if not w["per_round"]:
            self.bank.play(self._wname("recarga"), reverb=False)

    def _finish_reload(self):
        w = self.weapon
        if w["per_round"]:
            self.ammo = min(w["mag"], self.ammo + 1)
            self.bank.play(self._wname("cartucho"), reverb=False)
        else:
            self.ammo = w["mag"]
            self.bank.play(self._wname("pronta"), reverb=False)
        if self.on_reloaded:
            self.on_reloaded()

    # --- vozes dos zumbis ----------------------------------------------
    def track(self, voice):
        if voice is not None:
            self.zombie_voices.append(voice)
        return voice

    def voice_free(self, zombie):
        """Se este zumbi pode começar um passo ou rosnado agora.

        Com a sala cheia, passos e rosnados de todos os zumbis somados
        passavam do limite de fontes da OpenAL: a SDK então cortava sons
        no meio (inclusive o ambiente) e o mixer do console engasgava.
        Até ZOMBIE_VOICES todos tocam; acima disso, só os mais próximos,
        até ZOMBIE_VOICES_MAX. Tiros, impactos, mira e avisos não contam.
        """
        self.zombie_voices = [v for v in self.zombie_voices if v.playing]
        busy = len(self.zombie_voices)
        if busy < C.ZOMBIE_VOICES:
            return True
        if busy >= C.ZOMBIE_VOICES_MAX:
            return False
        nearer = sum(1 for z in self.zombies
                     if z.alive and z is not zombie and z.distance < zombie.distance)
        return nearer < C.ZOMBIE_VOICES_NEAREST

    # --- salas e ondas -------------------------------------------------
    def start(self):
        # Lê do cartão todos os sons de combate de uma vez (os ambientes,
        # maiores, ficam para quando a sala começa). Sem isso, cada som
        # novo era lido no meio da luta, travando o laço do jogo.
        self.bank.preload(exclude=("ambiente_",))
        self.next_room()

    def next_room(self):
        self.room_number += 1
        emit(self, "room")
        room_id, room_name, reverb, amb_volume, floor = C.ROOMS[(self.room_number - 1) % len(C.ROOMS)]
        self.floor = floor
        self.game.sound.set_reverb(reverb, **C.REVERB_TWEAKS.get(reverb, {}))
        if self.ambience is not None:
            self.ambience.stop(fade=1.0)
        self.ambience = self.bank.play("ambiente_" + room_id, loop=True,
                                       volume=amb_volume, reverb=False)
        count, kinds, interval, speed_mult = C.wave_plan(self.room_number)
        self.spawn_queue = [random.choice(kinds) for _ in range(count)]
        self.spawn_interval = interval
        self.speed_mult = speed_mult
        self.spawn_timer = 1.0
        self.state = "intro"
        text = "Sala %d: %s. Onda de %d zumbis." % (self.room_number, room_name, count)
        self.game.say(text, on_done=lambda done: self._begin_fight())

    def _begin_fight(self):
        if self.state == "intro":
            self.state = "fighting"

    def spawn(self, kind, direction=None, distance=None):
        direction = direction or random.choice(C.DIRECTION_ORDER)
        distance = distance or random.uniform(*C.SPAWN_DISTANCE)
        z = Zombie(self, kind, direction, distance, self.speed_mult)
        self.zombies.append(z)
        return z

    def _room_cleared(self):
        self.state = "between"
        parts = ["Sala limpa."]
        if self.lives < C.MAX_LIVES:
            self.lives += 1
            parts.append("Você recuperou uma vida. %s." % self._lives_text())
        if random.random() < C.WEAPON_FIND_CHANCE:
            key = random.choice([k for k in C.WEAPONS if k != self.weapon_key])
            self.set_weapon(key, announce=True)
            w = self.weapon
            parts.append("Você encontrou %s %s. %s" % (w["article"], w["name"], w["describe"]))
        self.game.say(" ".join(parts), on_done=lambda done: self._advance())

    def _advance(self):
        if self.state != "between":
            return
        self.bank.play("avancar", reverb=False)
        self.game.after(2.0, self.next_room)

    # --- vida ----------------------------------------------------------
    def _lives_text(self):
        return "1 vida" if self.lives == 1 else "%d vidas" % self.lives

    def _bite(self, z):
        self.bank.play_first(["ataque_" + z.kind, "mordida"], pos=z.pos())
        self.bank.play("dor", reverb=False)
        emit(self, "hurt")
        z.distance = C.BITE_PUSHBACK
        if self.tutorial:
            self.game.say("Ele te mordeu! No jogo de verdade, você perderia uma vida.",
                          queue=True)
            return
        self.lives -= 1
        if self.lives <= 0:
            self._game_over()
        else:
            self.game.say("Mordido! %s." % self._lives_text())

    def _game_over(self):
        emit(self, "over")
        self.state = "over"
        self.stop_sounds()
        self.bank.play("morte", reverb=False)
        self.on_over(self.room_number, self.kills)

    def stop_sounds(self):
        for z in self.zombies:
            z.silence()
        self.zombies = []
        if self.ambience is not None:
            self.ambience.stop(fade=0.5)
            self.ambience = None
        self.game.sound.set_reverb(None)

    # --- laço ----------------------------------------------------------
    def update(self, dt):
        if self.paused or self.state not in ("fighting", "between", "intro"):
            return
        if self.cooldown > 0:
            self.cooldown = max(0.0, self.cooldown - dt)
        if self.reload_timer > 0:
            self.reload_timer -= dt
            if self.reload_timer <= 0:
                self.reload_timer = 0.0
                self._finish_reload()
        if self.state != "fighting":
            return
        if self.spawn_queue:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                self.spawn_timer = self.spawn_interval * random.uniform(0.7, 1.3)
                self.spawn(self.spawn_queue.pop())
        for z in list(self.zombies):
            if not z.alive:
                self.zombies.remove(z)
                continue
            z.update(dt)
            if z.distance <= C.BITE_DISTANCE:
                self._bite(z)
                if self.state == "over":
                    return
        self._update_target(dt)
        if not self.tutorial and not self.spawn_queue and not self.zombies:
            self._room_cleared()

    def situation(self):
        w = self.weapon
        if w["melee"]:
            parts = ["%s." % w["name"].capitalize()]
        elif w["mag"] == 1:
            parts = ["%s %s." % (w["name"].capitalize(), "carregada" if self.ammo else "vazia")]
        else:
            parts = ["%s, %d de %d balas." % (w["name"].capitalize(), self.ammo, w["mag"])]
        if not self.tutorial:
            parts.append("%s." % self._lives_text())
        alive = [z for z in self.zombies if z.alive]
        if not alive:
            parts.append("Nenhum zumbi por perto.")
        else:
            by_dir = []
            for d in C.DIRECTION_ORDER:
                near = sorted(z.distance for z in alive if z.direction == d)
                if near:
                    by_dir.append("%s %s" % (C.DIRECTIONS[d][0], distance_word(near[0])))
            parts.append("Zumbis: %s." % ", ".join(by_dir))
        parts.append("Mirando para %s." % C.DIRECTIONS[self.aim][0])
        self.game.say(" ".join(parts))

    def pause(self):
        self.paused = True
        self.game.sound.pause_all()

    def resume(self):
        self.paused = False
        self.game.sound.resume_all()
