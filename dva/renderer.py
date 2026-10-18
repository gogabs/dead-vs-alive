"""Optional SDK texture renderer, independent of combat and speech.

Uses the new SDK Graphics API with preserved local compatibility fixes.
Rendering is capped at 30 Hz while
the original game update rate stays unchanged. Pillow is never imported here.
"""
import json
import os
import time

from . import config as C
from .bitmap_text import BitmapText


OPPOSITE = {'up': 'down', 'down': 'up', 'left': 'right', 'right': 'left'}
PLAYER = (320, 302)


def project(direction, distance):
    vx, vz = C.DIRECTIONS[direction][1]
    d = min(18.0, max(0, distance))
    return (round(PLAYER[0]+vx*d*11), round(PLAYER[1]+vz*d*8))


def preference_on():
    if os.environ.get('A11Y_GRAPHICS') == '0':
        return False
    try:
        with open(os.environ.get('A11Y_SISTEMA_CONF', '/opt/a11y/etc/sistema.conf')) as f:
            for line in f:
                key, sep, value = line.strip().partition('=')
                if sep and key == 'SCREEN':
                    return value.strip("'\"") != '0'
    except OSError:
        pass
    return True


def frame_interval():
    try:
        with open(os.environ.get('A11Y_SISTEMA_CONF', '/opt/a11y/etc/sistema.conf')) as f:
            for line in f:
                key, sep, value = line.strip().partition('=')
                if sep and key == 'ENERGY':
                    return {'moderate': .05, 'aggressive': .1}.get(value.strip("'\""), 1/30.0)
    except OSError:
        pass
    return 1/30.0


class Renderer:
    def __init__(self, game, active_run, menu):
        self.game, self.active_run, self.menu = game, active_run, menu
        self.root = os.path.join(game.dir, 'graphics')
        with open(os.path.join(self.root, 'manifest.json'), encoding='utf-8') as f:
            self.manifest = json.load(f)
        self.gfx = None
        self.textures = {}
        self.bitmap_text = None
        self.animations = {}
        for name, atlas in self.manifest['atlases'].items():
            for anim in atlas['animations']:
                self.animations[(name, anim['state'], anim['direction'])] = anim
        self.clock = 0.0
        self.frame_due = 0.0
        self.last_config = -1
        self.run = None
        self.effects = []
        self.attack = None
        self.hurt = -10
        self.positions = {}
        self.failed = False
        self.frame_count = 0
        self.render_seconds = []
        # No PC a janela é do Game (dela vem o teclado): desenha nela, no on_draw.
        self.shared = getattr(game, 'pc', False)
        game.on_update(self.update)
        game.on_quit(self.close)
        if self.shared:
            game.on_draw(self.draw_frame)

    def open(self):
        from r36s_a11y.graphics import Graphics
        os.environ.setdefault('SDL_RENDER_SCALE_QUALITY', '0')
        if self.shared:
            gfx = self.game.gfx
            if not gfx.available:
                self.failed = True
                return False
            gfx.base_dir = self.root
            self.gfx = gfx
        else:
            gfx = Graphics('Dead vs. Alive', self.root)
            self.gfx = gfx
            if not gfx.open():
                self.failed = True
                self.close()
                return False
        paths = {a['file'] for a in self.manifest['atlases'].values()}
        paths.update(self.manifest['rooms'].values())
        paths.add(self.manifest['font']['file'])
        for path in paths:
            self.textures[path] = gfx.image(path)
        with open(os.path.join(self.root,'font-source.json'),encoding='utf-8') as f:
            self.bitmap_text = BitmapText(gfx,json.load(f))
        return True

    def close(self):
        if self.gfx is not None:
            if self.bitmap_text is not None:
                self.bitmap_text.close()
                self.bitmap_text = None
            for image in self.textures.values():
                self.gfx.sdl.SDL_DestroyTexture(image.texture)
            self.textures.clear()
            if self.shared:
                pass  # a janela é do Game, que a fecha ao sair
            elif self.gfx.available:
                self.gfx.close()
            else:
                # Failed/partial SDL initialization also relinquishes video.
                sdl = getattr(self.gfx, 'sdl', None)
                if sdl:
                    if self.gfx.renderer:
                        sdl.SDL_DestroyRenderer(self.gfx.renderer)
                    if self.gfx.window:
                        sdl.SDL_DestroyWindow(self.gfx.window)
                    sdl.SDL_QuitSubSystem(0x20)
            self.gfx = None

    def sprite(self, name, state, direction, index, x, y):
        atlas = self.manifest['atlases'][name]
        anim = self.animations[(name, state, direction)]
        frames = anim['frames']
        index = int(index)
        index = index % len(frames) if anim['loop'] else min(len(frames)-1, max(0, index))
        self.gfx.draw(self.textures[atlas['file']], int(x), int(y), src=frames[index], scale=2)

    def text(self, words, x, y, color=(209, 209, 209), scale=2):
        self.bitmap_text.draw(words,x,y,color,scale)

    def sync(self, run, dt):
        menu = self.menu()
        if run is None and self.run is not None and self.run.state == 'over' and menu is None:
            run = self.run  # show death while the existing game-over speech waits
        if run is not self.run:
            self.effects = []
            self.positions = {}
            self.attack = None
            self.hurt = -10
            self.run = run
        if run is None:
            return
        if not run.paused:
            self.clock += dt
        for event in run._visual_events:
            kind = event['event']
            if kind == 'room':
                self.effects = []
                self.positions = {}
                self.attack = None
            elif kind == 'attack':
                self.attack = dict(event, at=self.clock)
                self.effects.append(dict(event, at=self.clock))
            elif kind in ('death', 'impact'):
                pos = self.positions.get(event['target'], project(event['direction'], event['distance']))
                self.effects.append(dict(event, at=self.clock, pos=pos))
            elif kind == 'hurt':
                self.hurt = self.clock
            elif kind == 'over':
                self.effects.append(dict(event, at=self.clock))
        run._visual_events[:] = []
        self.effects = [e for e in self.effects if self.clock-e['at'] < (8.5 if e['event'] == 'death' else .6)]
        self.effects = self.effects[-128:]

    def update(self, dt):
        self.sync(self.active_run(), dt)
        now = time.monotonic()
        if now-self.last_config >= .5:
            self.last_config = now
            self.enabled = preference_on()
            self.interval = frame_interval()
            if not self.enabled:
                self.close()
        if not getattr(self, 'enabled', False) or self.failed or self.shared:
            return
        self.frame_due += dt
        if self.frame_due < self.interval:
            return
        self.frame_due %= self.interval
        try:
            if self.gfx is None and not self.open():
                return
            start = time.monotonic()
            self.gfx.begin()
            self.draw()
            self.gfx.end()
            self.frame_count += 1
            self.render_seconds.append(time.monotonic()-start)
            self.render_seconds = self.render_seconds[-300:]
        except Exception as exc:
            # A graphical failure must not abort audio gameplay.
            print('[dva] gráficos indisponíveis: %s' % exc)
            self.failed = True
            self.close()

    def menu_help(self):
        label = getattr(self.game, 'button_label', None)
        if label is None:
            return 'B CONFIRMA / A VOLTA'
        return ('%s CONFIRMA / %s VOLTA' % (label('b'), label('a'))).upper()

    def draw_frame(self, gfx):
        """Quadro no PC, chamado pelo Game a cada on_draw."""
        if not getattr(self, 'enabled', False) or self.failed:
            caption = getattr(self.game, '_draw_caption', None)
            if caption:
                caption(gfx)
            return
        try:
            if self.gfx is None and not self.open():
                return
            self.draw()
        except Exception as exc:
            print('[dva] gráficos indisponíveis: %s' % exc)
            self.failed = True
            self.close()

    def player(self, run):
        x, y = PLAYER
        state, frame = 'idle', int(self.clock/.18)
        if run.state == 'over':
            state = 'death'
            over = next((e for e in self.effects if e['event'] == 'over'), None)
            frame = int((self.clock-over['at'])/.1) if over else 5
        elif self.clock-self.hurt < .18:
            state, frame = 'hurt', int((self.clock-self.hurt)/.09)
        elif run.reload_timer > 0:
            state = 'reload'
            frame = int((1-run.reload_timer/max(.001, run.weapon['reload']))*6)
        elif self.attack and self.clock-self.attack['at'] < .28:
            state, frame = 'attack', int((self.clock-self.attack['at'])/.07)
        direction = run.aim
        hands = self.manifest['atlases']['protagonista']['anchor']['hands'][direction]
        wx, wy = x-32+hands[0]*2-48, y-92+hands[1]*2-48
        weapon_state = state if state in ('idle', 'attack', 'reload') else 'idle'
        if direction == 'up' and state != 'death':
            self.sprite('arma-'+run.weapon_key, weapon_state, direction, frame, wx, wy)
        self.sprite('protagonista', state, direction, frame, x-32, y-92)
        if direction != 'up' and state != 'death':
            self.sprite('arma-'+run.weapon_key, weapon_state, direction, frame, wx, wy)

    def draw(self):
        run = self.run
        room = C.ROOMS[(max(1, run.room_number)-1) % len(C.ROOMS)][0] if run else 'hospital_quarto'
        self.gfx.draw(self.textures[self.manifest['rooms'][room]], 0, 0, scale=2)
        if run:
            for event in self.effects:
                if event['event'] == 'death':
                    age = self.clock-event['at']
                    state, frame = ('burst', int(age/.05)) if age < .5 else ('stain', int(age-.5))
                    x, y = event['pos']
                    self.sprite('sangue', state, 'all', frame, x-64, y-74)
            living = [z for z in run.zombies if z.alive]
            counts = {}
            objects = [(PLAYER[1], None, PLAYER)]
            for z in living:
                index = counts.get(z.direction, 0)
                counts[z.direction] = index+1
                x, y = project(z.direction, z.distance)
                jitter = (0, -8, 8, -16, 16)[index % 5]
                if z.direction in ('up', 'down'):
                    x += jitter
                else:
                    y += jitter
                self.positions[id(z)] = (x, y)
                objects.append((y, z, (x, y)))
            self.positions = {id(z): self.positions[id(z)] for z in living}
            for _, z, (x, y) in sorted(objects, key=lambda obj: obj[0]):
                self.gfx.rect(x-22, y-4, 44, 8, (20, 20, 20))
                if z is None:
                    self.player(run)
                else:
                    hit = next((e for e in reversed(self.effects) if e['event']=='impact' and e['target']==id(z) and self.clock-e['at']<.16), None)
                    state = 'hurt' if hit else ('attack' if z.distance <= C.BITE_DISTANCE+.1 else 'walk')
                    frame = int((self.clock-hit['at'])/.08) if hit else int(self.clock/(.09 if z.kind=='corredor' else .16))
                    self.sprite('zumbi-'+z.kind, state, OPPOSITE[z.direction], frame, x-32, y-92)
            for event in self.effects:
                if event['event'] == 'attack' and self.clock-event['at'] < .28:
                    self.sprite('efeito-'+event['weapon'], 'attack', event['direction'],
                                int((self.clock-event['at'])/.04), PLAYER[0]-128, PLAYER[1]-54-128)
            self.gfx.rect(0, 0, 640, 32, (17, 17, 17))
            self.text('SALA %02d / %s' % (run.room_number, C.ROOMS[(max(1,run.room_number)-1)%len(C.ROOMS)][1]), 12, 8)
            self.gfx.rect(0, 444, 640, 36, (17, 17, 17))
            self.text('VIDAS %d' % run.lives, 12, 456)
            self.text(run.weapon['name'], 164, 456)
            self.text('BALAS %d' % run.ammo if not run.weapon['melee'] else 'CORPO A CORPO', 320, 456)
            self.text('MORTES %d' % run.kills, 12, 426, scale=1)
            if run.reload_timer > 0:
                self.text('RECARREGANDO', 320, 426, scale=1)
        menu = self.menu()
        if menu:
            self.gfx.rect(112, 104, 416, 278, (17,17,17,245))
            self.gfx.rect(112, 104, 416, 278, (115,115,115), fill=False)
            self.text(menu.title, 132, 128)
            for i, label in enumerate(menu.items):
                if i == menu.index:
                    self.gfx.rect(124, 164+i*36, 390, 30, (65,65,65))
                self.text(label, 142, 172+i*36, (241,241,241) if i==menu.index else (163,163,163))
            self.text(self.menu_help(), 132, 360, scale=1)


def attach(game, active_run, menu):
    try:
        return Renderer(game, active_run, menu)
    except (OSError, ValueError, KeyError) as exc:
        print('[dva] sem arquivos gráficos: %s' % exc)
        return None
