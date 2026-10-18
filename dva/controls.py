"""Ações do jogo e o nome delas no que o jogador está usando.

No R36S valem os botões de sempre. No PC: setas ou WASD miram, Espaço ou o
clique esquerdo atiram, R recarrega, Tab fala a situação, Esc pausa e Enter
confirma no tutorial. Num controle, os botões ficam no lugar dos do R36S.
"""

ACTIONS = {
    "cima": {"r36s": "up", "key": ["up", "w"]},
    "baixo": {"r36s": "down", "key": ["down", "s"]},
    "esquerda": {"r36s": "left", "key": ["left", "a"]},
    "direita": {"r36s": "right", "key": ["right", "d"]},
    "atirar": {"r36s": "r2", "key": ["space", "j"], "mouse": "left"},
    "recarregar": {"r36s": "x", "key": ["r", "k"]},
    "situacao": {"r36s": "select", "key": ["tab", "q"]},
    "pausa": {"r36s": "start", "key": ["escape", "p"]},
    "confirmar": {"r36s": "b", "key": ["return", "e"]},
}

AIM = {"cima": "up", "baixo": "down", "esquerda": "left", "direita": "right"}

# Sem SDK com ações (ou nos testes), os nomes do R36S.
R36S_NAMES = {"atirar": "R2", "recarregar": "X", "situacao": "Select", "pausa": "Start",
              "confirmar": "B"}


def label(game, action):
    """ "Espaço" no teclado, "R2" no R36S, "RT" no Xbox..."""
    fn = getattr(game, "label", None)
    if fn is None or not hasattr(game, "action_map") or action not in game.action_map:
        return R36S_NAMES[action]
    return fn(action)


def aim_controls(game):
    """Como mirar, no que o jogador está usando."""
    if getattr(game, "device", "r36s") == "keyboard":
        return "as setas ou W A S D"
    return "os direcionais ou o analógico"
