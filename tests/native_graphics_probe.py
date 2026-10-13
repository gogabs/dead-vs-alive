"""Native SDK/video/audio probe, always using a new private save directory."""
import importlib.util
import json
import os
from pathlib import Path
import statistics
import sys
import time

ROOT=Path(os.environ.get('DVA_GAME_ROOT','/opt/a11y/games/dead-vs-alive'))
OUT=Path(os.environ['DVA_PROBE_OUT'])
OUT.mkdir(parents=True,exist_ok=True)
STATE=OUT/'private-save'
if STATE.exists(): raise RuntimeError('A new private save directory is required')
os.environ['A11Y_GAME_DIR']=str(ROOT)
os.environ['A11Y_SAVE_DIR']=str(STATE)
os.environ['SDL_VIDEODRIVER']='kmsdrm'
os.environ['SDL_RENDER_SCALE_QUALITY']='0'
os.environ['SDL_NO_SIGNAL_HANDLERS']='1'
os.environ.setdefault('ALSOFT_CONF','/opt/a11y/etc/alsoft-hrtf.conf')
# Only a private SCREEN/ENERGY preference is used.
conf=OUT/'private-system.conf'
conf.write_text("SCREEN='1'\nENERGY='off'\n")
os.environ['A11Y_SISTEMA_CONF']=str(conf)
sys.path.insert(0,str(ROOT))
import r36s_a11y as a11y
original_run=a11y.Game.run
started=time.monotonic()
checks={}
progress={'stage':'start','map':0,'weapon':0,'next':0}
command_seconds=[]
update_dt=[]


def intercepted(self):
    @self.on_start
    def begin(): self.after(.2,entry.start_run)
    @self.on_update
    def inspect(dt):
        now=time.monotonic()
        if now-started>35:
            checks['finished']=False
            self.quit()
            return
        run=entry.active_run()
        graphics=entry.graphics_session
        if run is None or graphics is None: return
        if progress['stage']=='start' and run.state=='fighting':
            checks['speech']=self.speech.sock is not None
            checks['openal']=self.sound.available
            checks['ambience']=run.ambience is not None and run.ambience.playing
            run.spawn('comum','right',3)
            began=time.monotonic()
            self._dispatch(('button','right',a11y.DOWN,self.ms()))
            self._dispatch(('button','r2',a11y.DOWN,self.ms()))
            command_seconds.append(time.monotonic()-began)
            checks['combat']=run.kills==1 and run.ammo==7
            progress.update(stage='maps',next=now+.2)
            run.spawn_queue=[]
            # Prevent automatic room advancement while inspecting visual fixtures.
            run.tutorial=True
        elif progress['stage']=='maps' and now>=progress['next']:
            checks['renderer_available']=graphics.gfx is not None and not graphics.failed
            if not checks['renderer_available']:
                self.quit(); return
            index=progress['map']
            run.room_number=index+1
            if not run.zombies:
                for kind,direction in zip(entry.C.ZOMBIES,entry.C.DIRECTION_ORDER):
                    run.spawn(kind,direction,8)
            # Explicit drawing uses the same native renderer, independent of wall timing.
            for _ in range(3):
                graphics.gfx.begin(); graphics.draw(); graphics.gfx.end()
            graphics.gfx.screenshot(str(OUT/('map-%s.png'%entry.C.ROOMS[index][0])))
            progress['map']+=1
            progress['next']=now+.08
            if progress['map']==7: progress.update(stage='weapons',next=now+.1)
        elif progress['stage']=='weapons' and now>=progress['next']:
            key=list(entry.C.WEAPONS)[progress['weapon']]
            run.set_weapon(key)
            run.cooldown=0
            run.set_aim('right')
            began=time.monotonic()
            self._dispatch(('button','r2',a11y.DOWN,self.ms()))
            command_seconds.append(time.monotonic()-began)
            graphics.sync(run,0)
            for _ in range(3):
                graphics.gfx.begin(); graphics.draw(); graphics.gfx.end()
            graphics.gfx.screenshot(str(OUT/('weapon-'+key+'.png')))
            progress['weapon']+=1
            progress['next']=now+.12
            if progress['weapon']==7:
                entry.button('start',a11y.DOWN,0)
                progress.update(stage='pause',clock=graphics.clock,next=now+.3)
        elif progress['stage']=='pause' and now>=progress['next']:
            checks['pause_freezes_visuals']=run.paused and graphics.clock==progress['clock']
            entry.on_pause(0,'Continuar')
            progress['stage']='resume'
        elif progress['stage']=='resume' and not run.paused:
            checks['resume']=True
            graphics.render_seconds=[]
            progress.update(stage='sample',next=now+4,frames=graphics.frame_count,wall=now)
        elif progress['stage']=='sample' and now<progress['next']:
            update_dt.append(dt)
        elif progress['stage']=='sample' and now>=progress['next']:
            progress['sample_fps']=(graphics.frame_count-progress['frames'])/(now-progress['wall'])
            conf.write_text("SCREEN='0'\nENERGY='off'\n")
            progress.update(stage='audio-only',next=now+.7)
        elif progress['stage']=='audio-only' and now>=progress['next']:
            checks['audio_mode_releases_video']=graphics.gfx is None
            checks['sound_still_active']=self.sound.available
            checks['openal_no_error']=self.sound.al.alGetError()==0
            checks['finished']=True
            run.stop_sounds()
            self.quit()
    original_run(self)
    checks['audio_closed']=not self.sound.available
    renderer=entry.graphics_session
    checks['graphics_closed']=renderer.gfx is None
    result={'passed':bool(checks) and all(checks.values()),'checks':checks,
            'native_maps':progress['map'],'native_weapons':progress['weapon'],
            'sample_fps':progress.get('sample_fps'),
            'render_median_ms':statistics.median(renderer.render_seconds)*1000 if renderer.render_seconds else None,
            'render_max_ms':max(renderer.render_seconds)*1000 if renderer.render_seconds else None,
            'command_callback_median_ms':statistics.median(command_seconds)*1000,
            'command_callback_max_ms':max(command_seconds)*1000,
            'sample_update_max_ms':max(update_dt)*1000 if update_dt else None,
            'elapsed_seconds':time.monotonic()-started,
            'scope':'Private saves; SDK callbacks, native GPU and real audio, not a human campaign'}
    (OUT/'report.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
    if not result['passed']: raise SystemExit(1)


a11y.Game.run=intercepted
spec=importlib.util.spec_from_file_location('dva_native_entry',ROOT/'main.py')
entry=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=entry
spec.loader.exec_module(entry)
