"""Combat parity and optional rendering, without audio devices or human saves."""
import importlib
import hashlib
import json
import os
from pathlib import Path
import random
import sys
import tempfile
import types
import unittest

ROOT = Path(os.environ.get('DVA_TEST_ROOT',str(Path(__file__).resolve().parents[1])))
STAGE = ROOT
REF = Path(os.environ.get('DVA_FIXTURE_ROOT',str(ROOT/'tests/fixtures')))


def package(name, path):
    module = types.ModuleType(name)
    module.__path__ = [str(path)]
    sys.modules[name] = module
    return importlib.import_module(name+'.run')


ORIGINAL = package('original_dva', REF/'dva')
PATCHED = package('patched_dva', STAGE/'dva')
VISUAL = importlib.import_module('patched_dva.renderer')


class Game:
    def __init__(self):
        self.dir = str(STAGE)
        self.calls = []
        self.sound = types.SimpleNamespace(set_reverb=lambda value,**kwargs:self.calls.append(('reverb',value,kwargs)), pause_all=lambda:None, resume_all=lambda:None)
        self.updates = []
        self.quits = []
    def say(self, text, **kw): self.calls.append(('say', text))
    def after(self, seconds, callback): self.calls.append(('after', seconds))
    def on_update(self, callback): self.updates.append(callback)
    def on_quit(self, callback): self.quits.append(callback)


class Bank:
    def __init__(self): self.calls=[]
    def has(self, name): return True
    def play(self, name, **kw):
        self.calls.append((name, kw))
        return types.SimpleNamespace(playing=False, stop=lambda **kw: None)
    def play_first(self, names, **kw): return self.play(names[0], **kw)


def execute(module, key):
    random.seed(3636)
    game, bank = Game(), Bank()
    run = module.Run(game, bank, lambda *args: game.calls.append(('over', args)))
    run.next_room()
    run.spawn_queue=[]
    run.tutorial=True
    run.state = 'fighting'
    run.set_weapon(key)
    for kind, distance in [('comum',1), ('comum',1.5), ('brutamontes',1.6)]:
        run.spawn(kind, 'right', distance)
    run.set_aim('right')
    run.fire()
    run.reload()
    run.update(.12)
    run.pause()
    run.update(.5)
    run.resume()
    run._finish_reload()
    run.cooldown=0
    run.fire()
    return (run.ammo, run.kills, run.lives, [(z.kind,z.hp,z.distance,z.alive) for z in run.zombies],
            bank.calls, game.calls, random.getstate())


class GraphicsTests(unittest.TestCase):
    def test_fixture_provenance_and_config_match(self):
        metadata=json.loads((REF/'origin.json').read_text(encoding='utf8'))
        for name,sha in metadata['sha256'].items():
            self.assertEqual(hashlib.sha256((REF/'dva'/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest(),sha)
        original={name:getattr(ORIGINAL.C,name) for name in dir(ORIGINAL.C) if name.isupper()}
        current={name:getattr(PATCHED.C,name) for name in dir(PATCHED.C) if name.isupper()}
        self.assertEqual(original,current,'Refresh the fixture from origin/main; see tools/update_fixtures.py')

    def test_combat_audio_timers_rng_parity_all_weapons(self):
        for key in ORIGINAL.C.WEAPONS:
            with self.subTest(weapon=key):
                self.assertEqual(execute(ORIGINAL,key), execute(PATCHED,key))

    def test_deaths_keep_visual_snapshot_after_removal(self):
        run=PATCHED.Run(Game(),Bank(),lambda *a:None)
        run.state='fighting'
        z=run.spawn('comum','up',3)
        run.fire()
        self.assertTrue(any(e['event']=='death' and e['distance']==3 for e in run._visual_events))
        self.assertFalse(z.alive)

    def test_facao_kills_close_zombies_ahead_and_to_the_sides(self):
        run=PATCHED.Run(Game(),Bank(),lambda *a:None)
        run.state='fighting'
        run.set_weapon('facao')
        hit=[run.spawn('brutamontes','up',1.4), run.spawn('corredor','left',1.0),
             run.spawn('comum','right',1.2), run.spawn('comum','up',1.0)]
        spared=[run.spawn('comum','down',1.0), run.spawn('comum','up',1.7),
                run.spawn('corredor','left',1.6)]
        run.fire()
        self.assertEqual([z.alive for z in hit],[False]*4)
        self.assertEqual([z.alive for z in spared],[True]*3)
        self.assertEqual([z.distance for z in spared],[1.0,1.7,1.6])
        self.assertEqual(run.kills,4)
        self.assertNotIn('taco',PATCHED.C.WEAPONS)

    def test_bounded_queue(self):
        run=PATCHED.Run(Game(),Bank(),lambda *a:None)
        events=importlib.import_module('patched_dva.graphics_events')
        for i in range(200): events.emit(run,'room')
        self.assertEqual(len(run._visual_events),128)

    def test_pause_and_room_clear(self):
        game=Game()
        run=PATCHED.Run(game,Bank(),lambda *a:None)
        renderer=VISUAL.Renderer(game,lambda:run,lambda:None)
        renderer.sync(run,.1)
        renderer.effects=[{'event':'death','at':renderer.clock}]
        run.paused=True
        renderer.sync(run,9)
        self.assertEqual(renderer.clock,.1)
        self.assertEqual(len(renderer.effects),1)
        run._visual_events=[{'event':'room'}]
        renderer.sync(run,.1)
        self.assertEqual(renderer.effects,[])

    def test_audio_mode_never_opens_graphics(self):
        game=Game()
        renderer=VISUAL.Renderer(game,lambda:None,lambda:None)
        old=os.environ.get('A11Y_GRAPHICS')
        os.environ['A11Y_GRAPHICS']='0'
        renderer.open=lambda: self.fail('Video opened in audio mode')
        try:
            for _ in range(30): renderer.update(.05)
            self.assertIsNone(renderer.gfx)
        finally:
            if old is None: os.environ.pop('A11Y_GRAPHICS',None)
            else: os.environ['A11Y_GRAPHICS']=old

    def test_all_rooms_and_sdk_extensions(self):
        manifest=json.loads((STAGE/'graphics/manifest.json').read_text(encoding='utf8'))
        self.assertEqual(set(manifest['rooms']),{r[0] for r in ORIGINAL.C.ROOMS})
        for path in manifest['rooms'].values(): self.assertTrue((STAGE/'graphics'/path).exists())
        for name in ('graphics.py','pc.py','streaming.py'): self.assertTrue((STAGE/'r36s_a11y'/name).exists())
        self.assertIn('self.input.fn_held', (STAGE/'r36s_a11y/game.py').read_text(encoding='utf8'))
        self.assertIn('self.pending', (STAGE/'r36s_a11y/input.py').read_text(encoding='utf8'))
        self.assertIn('voice_values', (STAGE/'r36s_a11y/speech.py').read_text(encoding='utf8'))


if __name__ == '__main__': unittest.main()
