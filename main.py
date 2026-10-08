#!/usr/bin/env python3
"""Dead vs. Alive: sobreviva às ondas de zumbis ouvindo de onde eles vêm."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
# Durante o desenvolvimento, usa a biblioteca do repositório vizinho se não houver cópia aqui.
if not os.path.isdir(os.path.join(HERE, "r36s_a11y")):
    sys.path.insert(1, os.path.join(HERE, "..", "r36s-a11y-sdk", "python"))

import r36s_a11y as a11y

from dva import config as C
from dva.run import Run
from dva.sounds import SoundBank
from dva.tutorial import Tutorial

game = a11y.Game(axes=True)
bank = SoundBank(game.sound, "sounds")
menu_sounds = {"move": bank.get("menu_mover"), "select": bank.get("menu_confirmar")}
RECORD_FILE = os.path.join(game.save_dir, "recorde.json")

current = {"run": None, "tutorial": None}


# --- recorde -------------------------------------------------------------
def load_record():
    try:
        with open(RECORD_FILE) as f:
            data = json.load(f)
        return data.get("sala", 0), data.get("mortes", 0)
    except (OSError, ValueError):
        return 0, 0


def save_record(room, kills):
    with open(RECORD_FILE, "w") as f:
        json.dump({"sala": room, "mortes": kills}, f)


def record_text():
    room, kills = load_record()
    if not room:
        return "Ainda não há recorde."
    return "Recorde: sala %d, %d zumbis." % (room, kills)


# --- fluxo ----------------------------------------------------------------
def start_run():
    main_menu.close()
    run = Run(game, bank, on_over=game_over)
    current["run"] = run
    run.start()


def game_over(room, kills):
    best_room, best_kills = load_record()
    text = "Você morreu. Chegou à sala %d e matou %d zumbis." % (room, kills)
    if (room, kills) > (best_room, best_kills):
        save_record(room, kills)
        text += " Novo recorde!"
    current["run"] = None
    game.after(1.5, lambda: game.say(text, on_done=lambda done: main_menu.open(announce_help=False)))


def start_tutorial():
    main_menu.close()
    tutorial = Tutorial(game, bank, on_finish=end_tutorial)
    current["tutorial"] = tutorial
    tutorial.start()


def end_tutorial():
    current["tutorial"] = None
    main_menu.open(announce_help=False)


def active_run():
    if current["tutorial"] is not None:
        return current["tutorial"].run
    return current["run"]


INSTRUCTIONS = (
    "Zumbis vêm da frente, da direita, de trás e da esquerda. Ouça os passos e os "
    "gemidos: quanto mais alto, mais perto. Mire com os direcionais ou o analógico "
    "esquerdo, atire ou golpeie com R2 e recarregue a arma vazia com X. Select fala "
    "a situação. Start pausa. Ao limpar uma sala você recupera uma vida e pode achar "
    "uma arma nova; a troca é obrigatória. Use fone de ouvido."
)


def on_main(index, item):
    if item == "Jogar":
        start_run()
    elif item == "Tutorial":
        start_tutorial()
    elif item == "Instruções":
        game.say(INSTRUCTIONS)
    elif item == "Recorde":
        game.say(record_text())
    else:
        game.quit()


main_menu = a11y.Menu(game, "Dead vs. Alive",
                      ["Jogar", "Tutorial", "Instruções", "Recorde", "Sair"],
                      on_select=on_main, on_back=game.quit, sounds=menu_sounds)


def on_pause(index, item):
    run = active_run()
    pause_menu.close()
    if item == "Continuar":
        game.say("Continuando.", on_done=lambda done: run.resume() if run else None)
        return
    if run is not None:
        run.stop_sounds()
        run.state = "over"
    current["run"] = None
    current["tutorial"] = None
    main_menu.open(announce_help=False)


pause_menu = a11y.Menu(game, "Pausa", ["Continuar", "Sair para o menu"],
                       on_select=on_pause, on_back=lambda: on_pause(0, "Continuar"),
                       sounds=menu_sounds)


# --- controles ------------------------------------------------------------
@game.on_button
def button(b, state, ms):
    run = active_run()
    if run is None or state != a11y.DOWN:
        return
    if b in C.DIRECTIONS:
        run.set_aim(b)
    elif b == "r2":
        run.fire()
    elif b == "x":
        run.reload()
    elif b == "select":
        run.situation()
    elif b == "start":
        run.pause()
        pause_menu.open()
    elif b == "b" and current["tutorial"] is not None:
        current["tutorial"].confirm()


@game.on_axis
def axis(name, value, ms):
    run = active_run()
    if run is None or name not in ("lx", "ly"):
        return
    x, y = game.input.axis_value.get("lx", 0.0), game.input.axis_value.get("ly", 0.0)
    if max(abs(x), abs(y)) < 0.6:
        return
    if abs(x) > abs(y):
        run.set_aim("right" if x > 0 else "left")
    else:
        run.set_aim("down" if y > 0 else "up")


@game.on_update
def update(dt):
    if current["tutorial"] is not None:
        current["tutorial"].update(dt)
    elif current["run"] is not None:
        current["run"].update(dt)


@game.on_start
def start():
    main_menu.open()


game.run()
