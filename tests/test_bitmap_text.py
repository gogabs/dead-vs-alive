import importlib
import json
import os
from pathlib import Path
import struct
import sys
import types
import unittest
from unittest.mock import Mock
import zlib

ROOT=Path(os.environ.get('DVA_TEST_ROOT',str(Path(__file__).resolve().parents[1])))
sys.path.insert(0,str(ROOT))
from dva.bitmap_text import BitmapText,line_png


class BitmapTests(unittest.TestCase):
    def test_png_matches_glyph_pixels_without_smoothing(self):
        glyphs=json.loads((ROOT/'graphics/font-source.json').read_text(encoding='utf8'))
        png=line_png('ABC',glyphs)
        self.assertEqual(png[:8],b'\x89PNG\r\n\x1a\n')
        position=8
        while position<len(png):
            size=struct.unpack('>I',png[position:position+4])[0]
            kind=png[position+4:position+8]
            if kind==b'IDAT': raw=zlib.decompress(png[position+8:position+8+size])
            position+=size+12
        stride=1+18*4
        for y in range(7):
            for x in range(18):
                bits=glyphs['ABC'[x//6]]
                expected=255 if x%6<5 and bits[y*5+x%6]=='1' else 0
                self.assertEqual(raw[y*stride+1+x*4+3],expected)

    def test_line_cache_one_draw_reuse_limit_and_cleanup(self):
        gfx=Mock()
        gfx.image.side_effect=lambda path: types.SimpleNamespace(texture=object())
        glyphs=json.loads((ROOT/'graphics/font-source.json').read_text(encoding='utf8'))
        cache=BitmapText(gfx,glyphs,limit=2)
        directory=cache.temp.name
        try:
            cache.draw('vidas 3',0,0)
            cache.draw('VIDAS 3',0,0,scale=1)
            self.assertEqual(gfx.image.call_count,1)
            self.assertEqual(gfx.draw.call_count,2)
            self.assertEqual(list(Path(directory).iterdir()),[])
            cache.draw('vidas 2',0,0)
            cache.draw('vidas 1',0,0)
            self.assertEqual(len(cache.images),2)
            gfx.sdl.SDL_DestroyTexture.assert_called_once()
        finally:
            cache.close()
        self.assertFalse(Path(directory).exists())
        self.assertEqual(gfx.sdl.SDL_DestroyTexture.call_count,3)
