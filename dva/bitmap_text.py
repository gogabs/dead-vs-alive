"""Bounded bitmap line textures through SDK.image/draw, without Pillow.

PNG authoring uses only the standard library. Each unchanged HUD/menu line is
one SDL draw call instead of one call per glyph. Temporary PNGs are deleted
after upload, and all textures are released when video closes.
"""
from collections import OrderedDict
import os
import struct
import tempfile
import unicodedata
import zlib


def normalize(words):
    return ''.join(c for c in unicodedata.normalize('NFD', str(words).upper())
                   if not unicodedata.combining(c))


def line_png(words, glyphs):
    width=max(1, len(words)*6)
    data=bytearray()
    for y in range(7):
        data.append(0)  # PNG filter: none
        for char in words:
            bits=glyphs.get(char, glyphs[' '])
            for x in range(6):
                ink=x<5 and bits[y*5+x]=='1'
                data.extend(b'\xff\xff\xff\xff' if ink else b'\x00\x00\x00\x00')
        if not words:
            data.extend(b'\x00\x00\x00\x00')
    def chunk(kind, value):
        return struct.pack('>I', len(value))+kind+value+struct.pack('>I', zlib.crc32(kind+value)&0xffffffff)
    header=struct.pack('>IIBBBBB',width,7,8,6,0,0,0)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',header)+chunk(b'IDAT',zlib.compress(bytes(data)))+chunk(b'IEND',b'')


class BitmapText:
    def __init__(self, gfx, glyphs, limit=64):
        self.gfx, self.glyphs, self.limit=gfx,glyphs,limit
        self.images=OrderedDict()
        self.temp=tempfile.TemporaryDirectory(prefix='dva-bitmap-text-')

    def draw(self, words, x, y, color=(209,209,209), scale=2):
        words=normalize(words)
        if not words:
            return
        if words not in self.images:
            if len(self.images)>=self.limit:
                _, old=self.images.popitem(last=False)
                self.gfx.sdl.SDL_DestroyTexture(old.texture)
            path=os.path.join(self.temp.name,'line.png')
            try:
                with open(path,'wb') as f:
                    f.write(line_png(words,self.glyphs))
                self.images[words]=self.gfx.image(path)
            finally:
                if os.path.exists(path): os.unlink(path)
        self.images.move_to_end(words)
        self.gfx.draw(self.images[words],x,y,scale=scale,tint=color)

    def close(self):
        for image in self.images.values():
            self.gfx.sdl.SDL_DestroyTexture(image.texture)
        self.images.clear()
        self.temp.cleanup()
