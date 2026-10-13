"""Editable pixel art and offline previews; never imports or launches the game.

Pillow is an authoring dependency on the PC only. Exported PNG atlases use
straight RGBA, integer coordinates and feet/hand anchors for SDK.draw(src=...).
"""
import argparse
import ast
import hashlib
import json
import math
from pathlib import Path
import random
import unicodedata

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / 'previews'
DIRECTIONS = ('down', 'up', 'right', 'left')
WEAPONS = ('pistola', 'espingarda', 'rifle', 'revolver', 'facao', 'taco', 'besta')
ZOMBIES = ('comum', 'corredor', 'brutamontes', 'rastejante')
VIEW_LABELS = {'down': 'FRENTE', 'up': 'COSTAS', 'right': 'DIREITA', 'left': 'ESQUERDA'}
GREY = ('#131313', '#292929', '#494949', '#737373', '#a3a3a3', '#d1d1d1', '#f1f1f1')
RED = ('#280b10', '#50121c', '#822132', '#b53343', '#df5360', '#f68888', '#ffc0bb')
GREEN = ('#0d2112', '#183d24', '#285735', '#3f8045', '#70a65a', '#a4cb7c', '#dbecae')
ROOM_NAMES = {'hospital_quarto': 'HOSPITAL', 'hospital_corredor': 'CORREDOR', 'estacionamento': 'ESTACIONAMENTO', 'cozinha': 'COZINHA', 'metro': 'METRO', 'igreja': 'IGREJA', 'floresta': 'FLORESTA'}
NEAREST = Image.Resampling.NEAREST


def blank(size):
    return Image.new('RGBA', size)


def bitmap_font():
    return json.loads((ROOT/'graphics/font-source.json').read_text(encoding='utf8'))


FONT = bitmap_font()


def text(im, words, xy, color='#d1d1d1', scale=1):
    d = ImageDraw.Draw(im)
    words = ''.join(c for c in unicodedata.normalize('NFD', words.upper()) if not unicodedata.combining(c))
    x, y = xy
    for char in words:
        glyph = FONT.get(char, FONT[' '])
        for i, bit in enumerate(glyph):
            if bit == '1':
                px, py = x + (i % 5)*scale, y + (i // 5)*scale
                d.rectangle((px, py, px+scale-1, py+scale-1), fill=color)
        x += 6*scale


def girl(direction='down', state='idle', frame=0):
    if direction == 'left':
        return girl('right', state, frame).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    im = blank((32, 48))
    d = ImageDraw.Draw(im)
    p = GREY
    bob = (0, 0, -1, 0)[frame % 4] if state == 'idle' else 0
    sway = (0, 1, 0, -1)[frame % 4]
    side = direction == 'right'
    back = direction == 'up'
    # Ponytail sits behind the neck; side view includes a tied, tapered tail.
    if side:
        d.polygon([(9, 7), (5, 6), (3+sway, 11), (4+sway, 21), (8+sway, 23), (10, 17)], fill=p[0])
        d.line([(6, 9), (6+sway, 18), (8+sway, 20)], fill=p[2], width=2)
        d.rectangle((7, 8, 10, 10), fill=p[5])
    else:
        tailx = 17 if back else 7
        d.polygon([(tailx, 7), (tailx+5, 9), (tailx+6+sway, 19),
                   (tailx+3+sway, 24), (tailx+sway, 20)], fill=p[0])
        d.line([(tailx+3, 11), (tailx+4+sway, 18), (tailx+2+sway, 21)], fill=p[2], width=2)
    # Legs, socks, chunky boots: no sexualized proportions.
    d.rectangle((10, 32, 14, 42), fill=p[0])
    d.rectangle((18, 32, 22, 42), fill=p[0])
    d.rectangle((11, 33, 13, 38), fill=p[5])
    d.rectangle((19, 33, 21, 38), fill=p[4])
    d.rectangle((10, 39, 14, 42), fill=p[2])
    d.rectangle((18, 39, 22, 42), fill=p[2])
    d.rectangle((8, 42, 14, 45), fill=p[0])
    d.rectangle((18, 42, 24, 45), fill=p[0])
    d.line((9, 42, 13, 42), fill=p[3])
    d.line((19, 42, 23, 42), fill=p[3])
    # Blouse, collar, sleeves and pleated skirt.
    d.polygon([(11, 16+bob), (20, 16+bob), (23, 23), (21, 28), (10, 28), (8, 23)], fill=p[0])
    d.polygon([(12, 17+bob), (19, 17+bob), (21, 22), (19, 28), (12, 28), (10, 22)], fill=p[4])
    d.rectangle((13, 20+bob, 18, 25), fill=p[3])
    if not back:
        d.polygon([(12, 17+bob), (16, 20+bob), (19, 17+bob)], fill=p[6])
        d.rectangle((15, 20+bob, 16, 23+bob), fill=p[0])
    d.polygon([(11, 27), (20, 27), (24+sway, 34), (22+sway, 36),
               (9+sway, 36), (7+sway, 34)], fill=p[0])
    d.polygon([(12, 28), (19, 28), (22+sway, 34), (10+sway, 34)], fill=p[2])
    d.line([(13, 29), (12+sway, 34)], fill=p[4])
    d.line([(17, 29), (18+sway, 34)], fill=p[3])
    d.line((10+sway, 35, 21+sway, 35), fill=p[4])
    # Arms change pose for attack and reload rather than rotating the whole body.
    lift = -2 if state == 'attack' and frame in (1, 2) else 0
    if side:
        d.polygon([(19, 19), (22, 19), (24, 23+lift), (28, 23+lift), (28, 26+lift), (21, 26)], fill=p[0])
        d.line([(20, 21), (23, 24+lift), (27, 24+lift)], fill=p[5], width=2)
    elif state == 'reload':
        d.rectangle((9, 20, 12, 25), fill=p[2])
        d.line([(11, 24), (16, 23-frame % 2), (21, 24)], fill=p[5], width=2)
    else:
        d.rectangle((8, 20, 11, 26+lift), fill=p[2])
        d.rectangle((21, 20, 24, 26+lift), fill=p[2])
        d.rectangle((9, 25+lift, 11, 27+lift), fill=p[5])
        d.rectangle((21, 25+lift, 23, 27+lift), fill=p[4])
    # Pixel head: back has hair instead of a mirrored face.
    d.polygon([(10, 3+bob), (20, 3+bob), (23, 6+bob), (23, 13+bob),
               (20, 17+bob), (11, 17+bob), (8, 13+bob), (8, 7+bob)], fill=p[0])
    if back:
        d.rectangle((10, 5+bob, 20, 14+bob), fill=p[1])
        d.line([(11, 6+bob), (11, 12+bob)], fill=p[2], width=2)
        d.rectangle((15, 13+bob, 19, 15+bob), fill=p[5])
    else:
        d.rectangle((11, 7+bob, 21, 13+bob), fill=p[5])
        d.rectangle((12, 13+bob, 19, 15+bob), fill=p[4])
        d.polygon([(9, 5+bob), (19, 4+bob), (22, 7+bob), (18, 9+bob),
                   (15, 7+bob), (12, 10+bob), (9, 11+bob)], fill=p[1])
        d.line((11, 5+bob, 17, 5+bob), fill=p[2])
        eyes = (19,) if side else (12, 19)
        for ex in eyes:
            d.rectangle((ex, 10+bob, ex+1, 12+bob), fill=p[0])
            d.point((ex, 10+bob), fill=p[6])
        if side:
            d.rectangle((22, 10+bob, 24, 12+bob), fill=p[5])
        d.line((15, 14+bob, 17, 14+bob), fill=p[2])
    if state == 'hurt':
        # Grayscale damage reaction: ink silhouette with bright contour.
        if frame % 2:
            moved = blank(im.size)
            moved.alpha_composite(im, (1, 2))
            im = moved
    if state == 'death':
        # Collapse without dismemberment, remains inside the 32x48 cell.
        if frame >= 2:
            head = im.crop((8, 2, 25, 18))
            im = blank((32, 48))
            d = ImageDraw.Draw(im)
            fall = min(frame-2, 2)
            d.rectangle((2, 41, 6, 45), fill=p[0])
            d.line((6, 42, 13, 43), fill=p[4], width=3)
            d.polygon([(10, 38), (16, 38), (18, 44), (10, 45)], fill=p[0])
            d.line((12, 39, 15, 43), fill=p[3], width=2)
            d.rectangle((16, 37+fall, 24, 43), fill=p[3])
            d.line((17, 42, 23, 45), fill=p[5], width=2)
            # Preserve a recognizable head instead of vertically squashing it.
            head = head.rotate(-20, resample=NEAREST)
            im.alpha_composite(head, (15, 29+fall))
            d.line([(27, 37), (29, 41), (30, 44)], fill=p[1], width=2)
        else:
            tilted = im.rotate((-8, -20)[frame], resample=NEAREST, expand=False)
            im = tilted
    return im


def zombie(kind='comum', direction='down', state='walk', frame=0):
    if direction == 'left':
        return zombie(kind, 'right', state, frame).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    im = blank((32, 48))
    d = ImageDraw.Draw(im)
    p = GREEN
    side, back = direction == 'right', direction == 'up'
    step = (0, 2, 0, -2)[frame % 4]
    hulk, crawler, runner = kind == 'brutamontes', kind == 'rastejante', kind == 'corredor'
    if crawler:
        d.polygon([(5, 34), (12, 30), (23, 32), (27, 36), (25, 41), (8, 42)], fill=p[0])
        d.polygon([(8, 34), (18, 32), (24, 35), (22, 39), (9, 39)], fill=p[2])
        d.rectangle((6+step, 41, 11+step, 44), fill=p[3])
        d.rectangle((21-step, 39, 28-step, 43), fill=p[3])
        d.rectangle((11, 29, 22, 36), fill=p[0])
        d.rectangle((12, 29, 21, 33), fill=p[4])
        if not back:
            d.rectangle((13, 31, 15, 32), fill=p[0])
            d.rectangle((19, 31, 21, 32), fill=p[0])
            d.line((15, 34, 20, 34), fill=p[5])
    else:
        left, right = (4, 28) if hulk else ((11, 22) if runner else (8, 25))
        head_y = 1 if hulk else (6 if runner else 4)
        # Broken hems, different bulk and gait distinguish the four kinds.
        d.polygon([(11, 30), (15, 30), (14+step, 41), (13+step, 44), (8+step, 44)], fill=p[0])
        d.polygon([(18, 30), (22, 30), (23-step, 42), (24-step, 45), (18-step, 45)], fill=p[0])
        d.line((12, 33, 11+step, 41), fill=p[2], width=2)
        d.line((20, 33, 21-step, 42), fill=p[3], width=2)
        d.polygon([(left+3, 15), (right-3, 15), (right, 29), (23, 34),
                   (18, 31), (12, 34), (left, 30)], fill=p[0])
        d.polygon([(left+5, 17), (right-5, 17), (right-2, 28), (19, 31),
                   (12, 31), (left+2, 28)], fill=p[2])
        d.line([(13, 19), (18, 23), (12, 26), (18, 28)], fill=p[4], width=2)
        if hulk:
            d.rectangle((6, 18, 10, 28), fill=p[3])
            d.rectangle((23, 18, 27, 29), fill=p[3])
        reach = 3 if state == 'attack' else 0
        d.line([(left+2, 18), (left, 27), (left-1+step, 31+reach)], fill=p[0], width=4)
        d.line([(right-2, 18), (right, 25), (right-step, 30+reach)], fill=p[0], width=4)
        d.rectangle((max(0, left-2+step), 29+reach, left+1+step, 32+reach), fill=p[4])
        d.rectangle((right-step-1, 28+reach, min(31, right-step+2), 32+reach), fill=p[4])
        d.polygon([(12, head_y), (21, head_y), (24, head_y+4), (22, head_y+12),
                   (16, head_y+15), (10, head_y+11), (9, head_y+5)], fill=p[0])
        d.rectangle((11, head_y+3, 21, head_y+9), fill=p[3])
        d.rectangle((13, head_y+9, 20, head_y+12), fill=p[2])
        d.line((11, head_y+2, 19, head_y+2), fill=p[1], width=2)
        if not back:
            for x in ((20,) if side else (12, 19)):
                d.rectangle((x, head_y+6, x+2, head_y+8), fill=p[0])
                d.point((x+1, head_y+7), fill=p[6])
            d.line((14, head_y+11, 19, head_y+11), fill=p[0], width=2)
            d.point((16, head_y+11), fill=p[5])
        else:
            d.line((12, head_y+4, 12, head_y+9), fill=p[4])
    if state == 'hurt':
        shifted = blank(im.size)
        shifted.alpha_composite(im, ((-2, 1)[frame % 2], 0))
        im = shifted
    return im


def weapon(key, direction='right', state='idle', frame=0):
    """48x48 layer, hand pivot=(24,24), facing right before cardinal turn."""
    im = blank((48, 48))
    d = ImageDraw.Draw(im)
    p = GREY
    recoil = -2 if state == 'attack' and frame in (1, 2) else 0
    x, y = 24+recoil, 24
    if key == 'pistola':
        d.rectangle((x-2, y-5, x+10, y), fill=p[0])
        d.rectangle((x, y-4, x+9, y-2), fill=p[5])
        d.rectangle((x, y, x+3, y+5), fill=p[0])
        d.rectangle((x+1, y+1, x+2, y+4), fill=p[2])
    elif key == 'revolver':
        d.rectangle((x-3, y-5, x+12, y-1), fill=p[0])
        d.rectangle((x+4, y-4, x+11, y-3), fill=p[5])
        d.rectangle((x-1, y-5, x+4, y), fill=p[4])
        d.line((x, y-4, x+3, y-4), fill=p[6])
        d.rectangle((x-3, y, x, y+5), fill=p[1])
    elif key in ('espingarda', 'rifle'):
        d.polygon([(x-11, y), (x-9, y-5), (x-4, y-4), (x-1, y-6),
                   (x+15, y-6), (x+15, y-2), (x, y-1), (x-4, y+3)], fill=p[0])
        d.rectangle((x-1, y-5, x+14, y-4), fill=p[5])
        d.line((x-8, y-3, x-3, y-2), fill=p[3], width=2)
        if key == 'espingarda':
            d.rectangle((x+3, y-2, x+9, y), fill=p[3])
            d.line((x+3, y-1, x+8, y-1), fill=p[5])
        else:
            d.rectangle((x, y-9, x+7, y-7), fill=p[0])
            d.line((x+1, y-8, x+6, y-8), fill=p[4])
            d.rectangle((x-2, y, x+1, y+5), fill=p[3])
    elif key == 'facao':
        d.rectangle((x-4, y-2, x+1, y), fill=p[0])
        d.polygon([(x+2, y-4), (x+16, y-7), (x+18, y-5), (x+14, y-2), (x+2, y)], fill=p[0])
        d.polygon([(x+3, y-3), (x+15, y-6), (x+16, y-5), (x+13, y-3), (x+3, y-1)], fill=p[5])
        d.line((x+5, y-2, x+13, y-4), fill=p[6])
    elif key == 'taco':
        d.polygon([(x-4, y-1), (x-4, y+2), (x+10, y+1), (x+17, y-1),
                   (x+18, y-4), (x+15, y-6), (x+7, y-3)], fill=p[0])
        d.line([(x-2, y), (x+8, y-1), (x+15, y-3)], fill=p[4], width=2)
        d.line((x+9, y-2, x+15, y-4), fill=p[5])
    else:
        d.rectangle((x-8, y-2, x+13, y+1), fill=p[0])
        d.line((x-6, y-1, x+12, y-1), fill=p[4], width=2)
        d.line([(x+8, y-12), (x+13, y-7), (x+14, y), (x+11, y+7), (x+8, y+11)], fill=p[0], width=3)
        d.line([(x+8, y-11), (x+12, y-6), (x+13, y), (x+10, y+6), (x+8, y+10)], fill=p[5])
        string_x = x+11 if state == 'attack' and frame == 1 else x-2
        d.line([(x+8, y-10), (string_x, y), (x+8, y+10)], fill=p[3])
    if state == 'reload':
        shift = (0, 2, 4, 3, 1, 0)[frame % 6]
        if key == 'revolver':
            d.rectangle((x-2, y+2, x+4, y+6), fill=p[0])
            d.rectangle((x-1, y+3, x+3, y+5), fill=p[4])
            d.rectangle((x+7-shift, y+7-shift, x+8-shift, y+10-shift), fill=p[6])
        elif key == 'besta':
            d.line((x-8+shift, y-5, x+10, y-5), fill=p[5])
            d.line((x+7, y-7, x+10, y-5), fill=p[6])
        elif key not in ('facao', 'taco'):
            d.rectangle((x-2, y+3+shift, x+1, y+9+shift), fill=p[0])
            d.line((x-1, y+4+shift, x-1, y+8+shift), fill=p[4])
    if key in ('facao', 'taco') and state == 'attack':
        im = im.rotate((40, 15, -35, -60)[frame % 4], resample=NEAREST, center=(24, 24))
    angles = {'right': 0, 'up': 90, 'left': 180, 'down': 270}
    return im.rotate(angles[direction], resample=NEAREST, center=(24, 24))


def actor(direction='down', state='idle', frame=0, key='pistola'):
    im = blank((80, 80))
    body = girl(direction, state, frame)
    layer = weapon(key, direction, state, frame)
    # Grip anchors in character coordinates, independent of sprite corners.
    hand = {'right': (27, 24), 'left': (4, 24), 'down': (21, 27), 'up': (21, 21)}[direction]
    offset = (24, 14)
    wp = (offset[0]+hand[0]-24, offset[1]+hand[1]-24)
    if direction == 'up' and state != 'death':
        im.alpha_composite(layer, wp)
    im.alpha_composite(body, offset)
    if direction != 'up' and state != 'death':
        im.alpha_composite(layer, wp)
    return im


def blood(age, seed=36):
    im = blank((64, 64))
    d = ImageDraw.Draw(im)
    rng = random.Random(seed)
    if age >= 8.5:
        return im
    alpha = int(255 * min(1, max(0, (8.5-age)/3)))
    # Seeded droplets and stains never consume gameplay randomness.
    for _ in range(16):
        x, y = rng.randint(17, 46), rng.randint(30, 41)
        d.rectangle((x, y, x+rng.randint(2, 6), y+rng.randint(1, 3)), fill=(112, 26, 40, alpha))
    if age < .5:
        radius = 4+age*48
        for i in range(28):
            angle = rng.random()*math.tau
            r = radius * rng.uniform(.35, 1)
            x, y = round(32+math.cos(angle)*r), round(28+math.sin(angle)*r*.75-age*15)
            size = rng.choice((1, 2, 3))
            color = RED[3+i % 3]
            d.rectangle((x, y, x+size, y+size), fill=color)
    return im


def attack_effect(key, direction, phase):
    im = blank((128, 128))
    d = ImageDraw.Draw(im)
    if 0 <= phase < .25:
        if key in ('facao', 'taco'):
            d.arc((45, 25, 100, 94), -80+phase*350, 20+phase*350, fill='#f1f1f1', width=2)
        elif key == 'besta':
            x = min(123, 80+int(phase*160))
            d.line((x-16, 61, x, 61), fill='#f7d17b', width=2)
            d.line((x-3, 59, x, 61), fill='#fff3cb')
        else:
            muzzle = 79 if key in ('pistola', 'revolver') else 91
            if phase < .12:
                size = 9 if key == 'espingarda' else 5
                d.polygon([(muzzle, 61), (muzzle+size, 56), (muzzle+size-2, 61),
                           (muzzle+size+5, 62), (muzzle+size, 64), (muzzle, 64)], fill='#ef9e43')
                d.line((muzzle+1, 61, muzzle+size, 61), fill='#fff1b8', width=2)
            end = min(125, 95+int(phase*150))
            for spread in ((-5, 0, 5) if key == 'espingarda' else (0,)):
                d.line((end-8, 61+spread, end, 61+spread*2), fill='#ffd478', width=1)
    return im.rotate({'right': 0, 'up': 90, 'left': 180, 'down': 270}[direction], resample=NEAREST, center=(64, 64))


def hospital():
    im = Image.new('RGBA', (320, 240), GREY[0])
    d = ImageDraw.Draw(im)
    # Low-contrast floor avoids competing with silhouettes.
    for y in range(45, 222, 16):
        for x in range(0, 320, 16):
            shade = 39 + ((x//16+y//16) % 2)*3
            d.rectangle((x, y, x+15, y+15), fill=(shade, shade, shade))
            d.line((x, y, x+15, y), fill='#353535')
            d.line((x, y, x, y+15), fill='#353535')
    d.rectangle((0, 16, 319, 44), fill='#484848')
    d.line((0, 17, 319, 17), fill='#737373')
    d.rectangle((0, 39, 319, 43), fill='#171717')
    # Windows, scuffed wall panels, double doors.
    for x in (18, 242):
        d.rectangle((x, 20, x+56, 35), fill='#161616')
        d.rectangle((x+2, 22, x+54, 32), fill='#888888')
        d.rectangle((x+4, 23, x+52, 27), fill='#a3a3a3')
        for xx in range(x+6, x+53, 13):
            d.line((xx, 22, xx, 32), fill='#494949', width=2)
    d.rectangle((133, 18, 187, 44), fill='#1c1c1c')
    for x in (136, 162):
        d.rectangle((x, 20, x+23, 41), fill='#606060')
        d.rectangle((x+4, 23, x+17, 29), fill='#202020')
        d.line((x+17, 33, x+19, 33), fill='#d1d1d1', width=2)
    # Hospital beds along side walls, casting a hard pixel shadow.
    for x, y in ((10, 62), (269, 62), (10, 151), (269, 151)):
        d.rectangle((x+3, y+4, x+43, y+49), fill='#1c1c1c')
        d.rectangle((x, y, x+38, y+43), fill='#151515')
        d.rectangle((x+2, y+3, x+36, y+38), fill='#737373')
        d.rectangle((x+4, y+6, x+34, y+13), fill='#c4c4c4')
        d.rectangle((x+5, y+15, x+33, y+36), fill='#a3a3a3')
        d.line((x+6, y+17, x+32, y+17), fill='#d1d1d1')
        d.line((x+6, y+33, x+32, y+33), fill='#858585')
        for xx in (x, x+37):
            d.rectangle((xx, y+5, xx+1, y+35), fill='#d1d1d1')
        d.rectangle((x+2, y+40, x+36, y+42), fill='#494949')
    # IV stand and cabinets: kept at the edge of combat lanes.
    for x in (54, 263):
        d.line((x, 56, x, 87), fill='#a3a3a3')
        d.line((x-5, 56, x+5, 56), fill='#a3a3a3')
        d.rectangle((x+2, 57, x+5, 65), fill='#737373')
        d.line((x-4, 88, x+4, 88), fill='#a3a3a3')
    for x in (67, 220):
        d.rectangle((x, 22, x+25, 37), fill='#313131')
        d.rectangle((x+2, 23, x+23, 26), fill='#858585')
        d.line((x+3, 29, x+22, 29), fill='#5c5c5c')
        d.point((x+20, 31), fill='#a3a3a3')
    # Hairline cracks with deliberately small visual weight.
    d.line([(103, 80), (106, 84), (103, 87), (108, 91)], fill='#1e1e1e')
    d.line([(219, 173), (214, 175), (215, 179)], fill='#1e1e1e')
    return im


def place(im, sprite, feet):
    x, y = feet
    ImageDraw.Draw(im).ellipse((x-11, y-3, x+11, y+2), fill='#151515')
    im.alpha_composite(sprite, (x-16, y-46))


def place_actor(im, direction, state, frame, key, feet=(160, 151)):
    x, y = feet
    ImageDraw.Draw(im).ellipse((x-13, y-3, x+13, y+3), fill='#151515')
    im.alpha_composite(actor(direction, state, frame, key), (x-40, y-60))


def room_background(room):
    if room == 'hospital_quarto':
        return hospital()
    im = Image.new('RGBA', (320, 240), '#252525')
    d = ImageDraw.Draw(im)
    for y in range(44, 223, 16):
        for x in range(0, 320, 16):
            d.rectangle((x, y, x+15, y+15), fill='#292929' if (x//16+y//16)%2 else '#262626')
            d.line((x, y, x+15, y), fill='#333333')
    d.rectangle((0, 16, 319, 43), fill='#494949')
    d.rectangle((0, 40, 319, 44), fill='#151515')
    if room == 'hospital_corredor':
        for x in (6, 58, 226, 278):
            d.rectangle((x, 18, x+34, 42), fill='#1c1c1c')
            d.rectangle((x+2, 20, x+32, 39), fill='#737373')
            d.rectangle((x+6, 23, x+28, 29), fill='#292929')
            d.line((x+26, 34, x+29, 34), fill='#d1d1d1')
        for x in (6, 303):
            d.rectangle((x, 48, x+10, 210), fill='#484848')
            d.line((x+2, 50, x+2, 208), fill='#a3a3a3')
        d.rectangle((25, 174, 52, 191), fill='#737373')
        d.rectangle((28, 169, 49, 180), fill='#a3a3a3')
    elif room == 'estacionamento':
        for y in (52, 136):
            for x in (5, 263):
                d.rectangle((x, y, x+51, y+61), outline='#737373', width=2)
                d.rectangle((x+9, y+7, x+42, y+51), fill='#111111')
                d.rectangle((x+11, y+9, x+40, y+49), fill='#737373')
                d.rectangle((x+14, y+17, x+37, y+25), fill='#292929')
                d.rectangle((x+14, y+37, x+37, y+42), fill='#292929')
                d.line((x+12, y+11, x+39, y+11), fill='#a3a3a3')
        for y in range(56, 211, 32):
            d.rectangle((113, y, 115, y+12), fill='#494949')
            d.rectangle((206, y, 208, y+12), fill='#494949')
        text(im, 'P / 01', (15, 26))
    elif room == 'cozinha':
        for x in (8, 249):
            d.rectangle((x, 52, x+61, 95), fill='#161616')
            d.rectangle((x+2, 54, x+59, 78), fill='#737373')
            d.line((x+3, 56, x+58, 56), fill='#d1d1d1')
            for xx in (x+14, x+42):
                d.ellipse((xx-6, 58, xx+6, 70), fill='#313131', outline='#a3a3a3')
            d.rectangle((x+5, 81, x+54, 89), fill='#313131')
        for x in (10, 268):
            d.rectangle((x, 152, x+42, 199), fill='#131313')
            d.rectangle((x+2, 154, x+40, 174), fill='#a3a3a3')
            d.rectangle((x+7, 158, x+35, 169), fill='#494949')
            d.line((x+8, 157, x+34, 157), fill='#d1d1d1')
            d.line((x+4, 182, x+38, 182), fill='#737373')
    elif room == 'metro':
        d.rectangle((0, 17, 319, 68), fill='#151515')
        d.rectangle((5, 21, 314, 57), fill='#737373')
        d.line((5, 54, 314, 54), fill='#a3a3a3')
        for x in range(10, 300, 48):
            d.rectangle((x, 24, x+35, 42), fill='#202020')
            d.rectangle((x+2, 26, x+33, 28), fill='#494949')
        d.rectangle((0, 64, 319, 67), fill='#a3a3a3')
        for x in range(0, 320, 8):
            d.rectangle((x, 70, x+3, 72), fill='#494949')
        for x in (16, 275):
            d.rectangle((x, 162, x+27, 165), fill='#a3a3a3')
            d.rectangle((x, 170, x+27, 179), fill='#737373')
            d.line((x+2, 180, x+2, 190), fill='#494949', width=2)
            d.line((x+24, 180, x+24, 190), fill='#494949', width=2)
    elif room == 'igreja':
        d.rectangle((135, 23, 185, 43), fill='#a3a3a3')
        d.rectangle((156, 17, 162, 34), fill='#292929')
        d.rectangle((148, 23, 170, 27), fill='#292929')
        for y in (67, 108, 157, 198):
            for x in (6, 249):
                d.rectangle((x, y, x+63, y+8), fill='#111111')
                d.rectangle((x+2, y, x+61, y+3), fill='#737373')
                d.rectangle((x+4, y+8, x+59, y+16), fill='#494949')
                d.line((x+5, y+10, x+58, y+10), fill='#a3a3a3')
    elif room == 'floresta':
        d.rectangle((0, 16, 319, 221), fill='#242424')
        rng = random.Random(3326)
        for _ in range(160):
            x, y = rng.randrange(320), rng.randrange(18, 220)
            d.line((x, y, x+2, y), fill='#303030')
        for x, y in ((15, 27), (58, 18), (271, 20), (303, 35), (21, 97), (286, 110), (36, 179), (271, 183)):
            d.rectangle((x-2, y+25, x+3, y+42), fill='#151515')
            for off in (0, 10, 20):
                d.polygon([(x, y+off), (x-17, y+off+23), (x+18, y+off+23)], fill='#151515')
                d.line([(x, y+off+3), (x-12, y+off+20)], fill='#494949', width=2)
        d.ellipse((85, 168, 100, 175), fill='#494949')
    return im


def hud(im, key='pistola', ammo=7, kills=1, room='hospital_quarto'):
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 319, 15), fill='#111111')
    d.line((0, 15, 319, 15), fill='#737373')
    text(im, 'DEAD VS. ALIVE', (8, 4), '#f1f1f1')
    text(im, 'SALA 01 / '+ROOM_NAMES[room], (158, 4), '#a3a3a3')
    d.rectangle((0, 222, 319, 239), fill='#111111')
    d.line((0, 222, 319, 222), fill='#737373')
    text(im, 'VIDAS 3', (7, 228))
    text(im, key, (77, 228), '#f1f1f1')
    text(im, 'BALAS '+str(ammo) if key not in ('facao', 'taco') else 'CORPO A CORPO', (153, 228))
    text(im, 'MORTES '+str(kills), (259, 228))


def scene(t=0, key='pistola', direction='right', animated=False, room='hospital_quarto'):
    im = room_background(room)
    frame = int(t*8) % 4
    cycle = t % 3
    shoot = animated and .8 <= cycle < 1.2
    dead = animated and cycle >= 1.0
    state = 'attack' if shoot else ('reload' if animated and 1.6 <= cycle < 2.6 and key not in ('facao', 'taco') else 'idle')
    positions = [('comum', (160, 85), 'down'), ('corredor', (239-int(cycle*5), 151), 'left'),
                 ('brutamontes', (80, 151), 'right'), ('rastejante', (160, 205), 'up')]
    if animated and key == 'taco' and cycle >= 1:
        positions[1] = ('corredor', (248, 151), 'left')
        dead = False  # first bat hit pushes, does not kill a full-health target
    if dead:
        im.alpha_composite(blood(cycle-1), (234-32, 151-37))
    # Painter order sorts by feet; actors above and below are occluded correctly.
    actors = [(feet[1], kind, feet, facing) for kind, feet, facing in positions
              if not (dead and kind == 'corredor')]
    actors.append((151, None, (160, 151), direction))
    for _, kind, feet, facing in sorted(actors, key=lambda a: a[0]):
        if kind is None:
            place_actor(im, direction, state, frame, key, feet)
        else:
            place(im, zombie(kind, facing, 'walk', frame), feet)
    if shoot:
        im.alpha_composite(attack_effect(key, direction, cycle-.8), (160-64, 124-64))
    capacity = {'pistola': 8, 'espingarda': 2, 'rifle': 5, 'revolver': 6, 'besta': 1, 'facao': 0, 'taco': 0}
    ammo = capacity[key] - (1 if animated and cycle >= .8 and key not in ('facao', 'taco') else 0)
    if animated and cycle >= 2.6:
        ammo = capacity[key]
    hud(im, key, ammo, int(dead), room)
    return im.resize((640, 480), NEAREST).convert('RGB')


def board(title):
    im = Image.new('RGBA', (320, 240), '#1c1c1c')
    d = ImageDraw.Draw(im)
    d.rectangle((5, 5, 314, 234), outline='#494949')
    text(im, title, (13, 14), '#f1f1f1')
    d.line((13, 26, 305, 26), fill='#737373')
    return im


def scaled(im):
    return im.resize((640, 480), NEAREST).convert('RGB')


def save_gif(path, frames, duration=100):
    # A single palette prevents flashing colors between GIF frames.
    sample = Image.new('RGB', (640, 480*min(8, len(frames))))
    for i, frame in enumerate(frames[:8]):
        sample.paste(frame, (0, 480*i))
    palette = sample.quantize(colors=128, dither=Image.Dither.NONE)
    # Ensure later blood/shot frames also have their colors represented.
    palette_list = palette.getpalette()
    extra = [tuple(bytes.fromhex(c[1:])) for c in RED+GREEN+GREY+('#ef9e43', '#fff1b8', '#ffd478', '#f7d17b', '#fff3cb')]
    for i, rgb in enumerate(extra):
        palette_list[(128+i)*3:(129+i)*3] = rgb
    palette.putpalette(palette_list)
    indexed = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    indexed[0].save(path, save_all=True, append_images=indexed[1:], duration=duration,
                    loop=0, disposal=2, optimize=False)


def export_sheet(out, name, cell_size, sequences, anchor, manifest):
    columns = max(len(frames) for _, _, frames, _ in sequences)
    w, h = cell_size
    sheet = blank((columns*w, len(sequences)*h))
    animations = []
    for row, (state, direction, frames, duration) in enumerate(sequences):
        rects = []
        for col, im in enumerate(frames):
            sheet.alpha_composite(im, (col*w, row*h))
            rects.append([col*w, row*h, w, h])
        animations.append({'state': state, 'direction': direction, 'frames': rects,
                           'duration_ms': duration, 'loop': state in ('idle', 'walk')})
    path = out / 'sprites' / (name+'.png')
    sheet.save(path)
    manifest['atlases'][name] = {'file': 'sprites/'+path.name, 'cell_size': [w, h],
                                'anchor': anchor, 'animations': animations}


def export_assets(out):
    manifest = {'format': 1, 'status': 'preview-only', 'screen': [640, 480],
                'art_scale': 2, 'sampling': 'nearest', 'directions': list(DIRECTIONS),
                'atlases': {}, 'commits_consulted': {
                    'dead-vs-alive': 'bea7e592b52a3516da4c928e236fdd8c6b9688fa',
                    'r36s-a11y': '806048413c3fef1abc63ca0f993855fd6530371c',
                    'r36s-a11y-sdk': '76bb5a8d4fbf3b329355c27cbbae320c15494195'}}
    sequences = []
    for direction in DIRECTIONS:
        for state, count, duration in (('idle', 4, 180), ('attack', 4, 70), ('reload', 6, 140), ('hurt', 2, 90), ('death', 6, 100)):
            sequences.append((state, direction, [girl(direction, state, i) for i in range(count)], duration))
    export_sheet(out, 'protagonista', (32, 48), sequences, {'feet': [16, 46],
                 'hands': {'down': [21, 27], 'up': [21, 21], 'right': [27, 24], 'left': [4, 24]}}, manifest)
    for kind in ZOMBIES:
        seq = [(state, direction, [zombie(kind, direction, state, i) for i in range(count)], duration)
               for direction in DIRECTIONS for state, count, duration in (('walk', 4, 90 if kind == 'corredor' else 160), ('attack', 4, 100), ('hurt', 2, 80))]
        export_sheet(out, 'zumbi-'+kind, (32, 48), seq, {'feet': [16, 46]}, manifest)
    for key in WEAPONS:
        seq = [(state, direction, [weapon(key, direction, state, i) for i in range(count)], duration)
               for direction in DIRECTIONS for state, count, duration in
               (('idle', 1, 100), ('attack', 4, 70), ('reload', 6, 120)) if not (state == 'reload' and key in ('facao', 'taco'))]
        export_sheet(out, 'arma-'+key, (48, 48), seq, {'hand': [24, 24]}, manifest)
        seq = [('attack', direction, [attack_effect(key, direction, i*.04) for i in range(7)], 40) for direction in DIRECTIONS]
        export_sheet(out, 'efeito-'+key, (128, 128), seq, {'origin': [64, 64]}, manifest)
    seq = [('burst', 'all', [blood(i*.05) for i in range(10)], 50),
           ('stain', 'all', [blood(.5+i) for i in range(9)], 1000)]
    export_sheet(out, 'sangue', (64, 64), seq, {'feet': [32, 37]}, manifest)
    glyphs = blank((len(FONT)*6, 7))
    for i, char in enumerate(FONT):
        text(glyphs, char, (i*6, 0), '#ffffff')
    glyphs.save(out/'sprites/font-bitmap.png')
    manifest['font'] = {'file': 'sprites/font-bitmap.png', 'characters': ''.join(FONT), 'cell_size': [6, 7]}
    manifest['rooms'] = {}
    for room in ROOM_NAMES:
        room_background(room).save(out/('sprites/'+room+'.png'))
        manifest['rooms'][room] = 'sprites/'+room+'.png'
    icons = blank((48*len(WEAPONS), 48))
    for i, key in enumerate(WEAPONS):
        icons.alpha_composite(weapon(key), (i*48, 0))
    icons.save(out/'sprites/icones-armas.png')
    manifest['icons'] = {'file': 'sprites/icones-armas.png', 'order': list(WEAPONS), 'cell_size': [48, 48]}
    (out/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    (out/'font-source.json').write_text(json.dumps(FONT)+'\n',encoding='utf-8')
    return manifest


def previews(out):
    scene().save(out/'hospital.png')
    for room in ROOM_NAMES:
        scene(room=room).save(out/('mapa-'+room+'.png'))
    save_gif(out/'combate.gif', [scene(i/10, animated=True) for i in range(60)])
    # Overview uses live hand layers so every weapon is visible on the heroine.
    im = board('DEAD VS. ALIVE / ELENCO E ARMAS')
    for i, direction in enumerate(DIRECTIONS):
        im.alpha_composite(actor(direction, key='pistola'), (8+i*75, 27))
        text(im, VIEW_LABELS[direction], (17+i*75, 101))
    for i, kind in enumerate(ZOMBIES):
        im.alpha_composite(zombie(kind), (30+i*75, 119))
        text(im, kind, (13+i*75, 171), GREEN[5])
    text(im, 'CINZAS / ZUMBIS VERDES / PIXELS 2X', (13, 198), '#737373')
    text(im, 'PREVIA / SEM ALTERAR O JOGO INSTALADO', (13, 213), '#a3a3a3')
    scaled(im).save(out/'elenco.png')
    im = board('SETE ARMAS / SPRITES INDEPENDENTES')
    for i, key in enumerate(WEAPONS):
        col, row = i % 4, i // 4
        im.alpha_composite(actor('right', key=key), (col*76+6, 31+row*89))
        text(im, key, (col*76+15, 107+row*89))
    text(im, 'TIROS COLORIDOS / GOLPES MONOCROMATICOS', (13, 217), '#737373')
    scaled(im).save(out/'armas.png')
    frames = []
    states = ('idle', 'attack', 'reload', 'hurt', 'death')
    for n in range(80):
        im = board('PROTAGONISTA / SAIA E RABO DE CAVALO')
        state = states[(n//16) % 5]
        for i, direction in enumerate(DIRECTIONS):
            im.alpha_composite(actor(direction, state, (n//2) % (6 if state in ('death', 'reload') else 4)), (i*75+8, 63))
            text(im, VIEW_LABELS[direction], (i*75+14, 150))
        text(im, {'idle':'REPOUSO', 'attack':'ATAQUE', 'reload':'RECARGA', 'hurt':'DANO', 'death':'MORTE'}[state], (13, 200), '#f1f1f1')
        frames.append(scaled(im))
    save_gif(out/'protagonista.gif', frames)
    for kind in ZOMBIES:
        frames = []
        for n in range(36):
            im = board('ZUMBI / '+kind)
            state = ('walk', 'attack', 'hurt')[n//12]
            for i, direction in enumerate(DIRECTIONS):
                im.alpha_composite(zombie(kind, direction, state, n//2), (i*75+31, 88))
                text(im, VIEW_LABELS[direction], (i*75+14, 151))
            text(im, {'walk':'APROXIMACAO', 'attack':'ATAQUE', 'hurt':'IMPACTO'}[state], (13, 200), RED[5])
            frames.append(scaled(im))
        save_gif(out/('zumbi-'+kind+'.gif'), frames)
    for key in WEAPONS:
        frames = []
        for n in range(48):
            im = board('ARMA / '+key)
            state = 'idle' if n < 8 else ('attack' if n < 20 else 'reload')
            if key in ('facao', 'taco') and state == 'reload':
                state = 'idle'
            for i, direction in enumerate(DIRECTIONS):
                x = i*75+8
                column = blank((75, 120))
                column.alpha_composite(actor(direction, state, n//2 % (6 if state == 'reload' else 4), key), (0, 25))
                if state == 'attack':
                    column.alpha_composite(attack_effect(key, direction, (n-8) % 4*.05), (-24, -1))
                im.alpha_composite(column, (x, 40))
                text(im, VIEW_LABELS[direction], (i*75+14, 169))
            text(im, {'idle':'PRONTA', 'attack':'GOLPE' if key in ('facao','taco') else 'DISPARO', 'reload':'UMA BALA POR VEZ' if key == 'revolver' else 'RECARGA'}[state], (13, 200))
            frames.append(scaled(im))
        save_gif(out/('arma-'+key+'.gif'), frames)
    frames = []
    for n in range(90):
        im = board('SANGUE / EXPLOSAO E MANCHA TEMPORARIA')
        age = n/10
        if age < .2:
            place(im, zombie('comum'), (160, 136))
        else:
            im.alpha_composite(blood(age-.2), (128, 99))
        text(im, 'EXPLOSAO 0.5S / MANCHA 8S', (13, 200), RED[5])
        frames.append(scaled(im))
    save_gif(out/'sangue.gif', frames)


def validate(out, manifest):
    checks = {}
    # Verify exported coordinates and actual transparency, not just functions.
    for name, atlas in manifest['atlases'].items():
        im = Image.open(out/atlas['file']).convert('RGBA')
        checks[name+'-transparent'] = im.getextrema()[3][0] == 0
        for anim in atlas['animations']:
            for x, y, w, h in anim['frames']:
                assert x >= 0 and y >= 0 and x+w <= im.width and y+h <= im.height
                assert im.crop((x, y, x+w, y+h)).getbbox() or (name == 'sangue' or name.startswith('efeito-'))
        colors = set(im.get_flattened_data() if hasattr(im, 'get_flattened_data') else im.getdata())
        if name == 'protagonista' or name.startswith('arma-'):
            checks[name+'-monochrome'] = all(r == g == b for r, g, b, a in colors if a)
        elif name.startswith('zumbi-'):
            checks[name+'-green'] = all(g > r and g > b for r, g, b, a in colors if a)
        elif name == 'sangue':
            checks[name+'-red'] = all(r > g and r > b for r, g, b, a in colors if a)
    checks['death-burst-clears'] = blood(.6).tobytes() != blood(.1).tobytes()
    checks['stain-expires'] = blood(8.5).getbbox() is None
    checks['distinct-weapons'] = len({weapon(k).tobytes() for k in WEAPONS}) == 7
    checks['distinct-zombies'] = len({zombie(k).tobytes() for k in ZOMBIES}) == 4
    checks['front-back-distinct'] = girl('down').tobytes() != girl('up').tobytes()
    checks['left-mirrors-right'] = girl('left').tobytes() == girl('right').transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes()
    checks['pure-visual-randomness'] = True
    saved = random.getstate()
    blood(.2)
    checks['pure-visual-randomness'] = random.getstate() == saved
    for file in list(out.glob('*.gif')) + list(out.glob('*.png')):
        with Image.open(file) as im:
            checks[file.name+'-640x480'] = im.size == (640, 480)
            if file.suffix == '.gif':
                checks[file.name+'-animated'] = im.n_frames > 1
                for i in range(im.n_frames):
                    im.seek(i)
                    im.load()
    result = {'passed': all(checks.values()), 'checks': checks,
              'scope': 'Offline art/export only; no gameplay or R36S performance claims'}
    (out/'validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    if not result['passed']:
        raise RuntimeError('Art export validation failed')
    return result


def gallery(out):
    cards = [('hospital.png','Hospital / cena 640 x 480'), ('elenco.png','Personagem e quatro zumbis'),
             ('armas.png','Sprites das sete armas'), ('combate.gif','Sequência ilustrativa de combate'),
             ('protagonista.gif','Protagonista / quatro direções / cinco estados')]
    cards += [('arma-'+k+'.gif', k) for k in WEAPONS]
    cards += [('zumbi-'+k+'.gif', 'Zumbi '+k) for k in ZOMBIES]
    cards += [('sangue.gif','Explosão de sangue e mancha temporária')]
    cards += [('mapa-'+room+'.png', ROOM_NAMES[room]) for room in ROOM_NAMES]
    contents = ''.join('<section><h2>'+label+'</h2><a href="'+file+'"><img src="'+file+'" alt="'+label+'"></a></section>' for file,label in cards)
    (out/'index.html').write_text('''<!doctype html><html lang="pt-BR"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Dead vs. Alive — prévias pixelart</title>
<style>body{background:#111;color:#ddd;font:16px monospace;max-width:1340px;margin:auto;padding:24px}
h1{color:#fff}p{max-width:850px;line-height:1.6}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:24px}
section{background:#191919;padding:12px;border:1px solid #444}h2{font-size:16px}img{width:100%;max-width:640px;image-rendering:pixelated}a{color:#f68888}</style>
<h1>Dead vs. Alive / pixelart</h1><p>Primeira rodada de prévias. Menina de saia e rabo de cavalo em cinzas;
zumbis verdes; armas independentes e efeitos coloridos. As sequências são demonstrações visuais,
não uma partida executada. O jogo instalado permanece intacto.</p><p><a href="manifest.json">Manifesto dos sprites</a> ·
<a href="validation.json">Validação da exportação</a></p><main>'''+contents+'</main></html>', encoding='utf-8')


def qa_contacts(out):
    for name, picks in [('protagonista', [0, 12, 25, 42]), ('arma-revolver', [0, 9, 26, 37]),
                        ('combate', [0, 9, 12, 22]), ('sangue', [1, 3, 6, 65])]:
        with Image.open(out/(name+'.gif')) as gif:
            contact = Image.new('RGB', (640, 480))
            for i, n in enumerate(picks):
                gif.seek(min(n, gif.n_frames-1))
                contact.paste(gif.convert('RGB').resize((320, 240), NEAREST), ((i % 2)*320, (i//2)*240))
            contact.save(out/('qa-'+name+'.png'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out/'sprites').mkdir(exist_ok=True)
    manifest = export_assets(out)
    previews(out)
    qa_contacts(out)
    result = validate(out, manifest)
    gallery(out)
    files = {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(out.rglob('*')) if p.is_file() and p.name != 'sha256.json'}
    (out/'sha256.json').write_text(json.dumps(files, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'output': str(out), 'passed': result['passed'], 'atlases': len(manifest['atlases']),
                      'animations': sum(len(a['animations']) for a in manifest['atlases'].values()),
                      'files': len(files)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
