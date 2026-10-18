"""Tutorial guiado: mirar, atirar, recarregar e ouvir a situação."""
from .controls import aim_controls, label
from .run import Run


class Tutorial:
    def __init__(self, game, bank, on_finish):
        self.game = game
        self.bank = bank
        self.on_finish = on_finish
        self.run = Run(game, bank, on_over=lambda *a: None, tutorial=True)
        self.run.on_kill = self._killed
        self.run.on_reloaded = self._reloaded
        self.step = 0
        self.waiting_confirm = False

    def start(self):
        self.run.state = "fighting"
        self.run.game.sound.set_reverb("quarto")
        self._say("Tutorial. Os zumbis vêm de quatro direções: frente, direita, trás e "
                  "esquerda. Use %s para mirar. Cada direção "
                  "tem um clique diferente. Experimente agora e aperte %s quando terminar."
                  % (aim_controls(self.game), label(self.game, "confirmar")))
        self.waiting_confirm = True

    def _say(self, text, then=None):
        self.game.say(text, on_done=(lambda done: then()) if then else None)

    def confirm(self):
        if self.waiting_confirm:
            self.waiting_confirm = False
            self._next()

    def _next(self):
        self.step += 1
        r = self.run
        if self.step == 1:
            self._say("Um zumbi vem da frente. Mire para cima. Quando um zumbi está na "
                      "sua mira, você ouve um bipe: grave e lento se ele está longe, "
                      "agudo e rápido se está perto. Atire com %s." % label(self.game, "atirar"),
                      lambda: r.spawn("comum", "up", 9.0))
        elif self.step == 2:
            self._say("Muito bem. Agora um vem da esquerda.",
                      lambda: r.spawn("comum", "left", 9.0))
        elif self.step == 3:
            self._say("Ouça bem: este vem de trás de você.",
                      lambda: r.spawn("comum", "down", 9.0))
        elif self.step == 4:
            r.ammo = 0
            self._say("Sua arma ficou vazia. Ao apertar %s sem balas, você ouve um clique "
                      "seco. Aperte %s para recarregar."
                      % (label(self.game, "atirar"), label(self.game, "recarregar")))
        elif self.step == 5:
            self._say("Dois zumbis de lados diferentes. A qualquer momento, %s fala a "
                      "situação: arma, balas e onde estão os zumbis." % label(self.game, "situacao"),
                      lambda: (r.spawn("comum", "right", 12.0), r.spawn("comum", "up", 15.0)))
        else:
            self._say("Fim do tutorial. No jogo, cada sala tem uma onda de zumbis, e ao "
                      "limpá-la você pode achar uma arma nova. A troca é obrigatória. "
                      "Boa sorte!", self.finish)

    def _killed(self, zombie):
        alive = [z for z in self.run.zombies if z.alive]
        if not alive:
            self.game.after(0.6, self._next)

    def _reloaded(self):
        if self.step == 4:
            self.game.after(0.4, self._next)

    def finish(self):
        self.run.stop_sounds()
        self.run.state = "over"
        self.on_finish()

    def update(self, dt):
        self.run.update(dt)
