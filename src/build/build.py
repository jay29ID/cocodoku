#!/usr/bin/env python3
"""Build the flat-colour games from one source.

trixdoku.html is the source of truth. Every other flat-colour game is
generated from it, so a change only has to be made once.
"""
import sys, pathlib

SRC = pathlib.Path(__file__).parent / 'trixdoku.html'

GAMES = {
    'cocodoku.html': {
        'title': 'Cocodoku',
        'character': 'Coco',
        'piece': 'art/coco-piece.png',
        'key': 'cocodoku.v1',
    },
}

def build(out, cfg):
    s = SRC.read_text(encoding='utf-8')
    s = s.replace('Trixdoku', cfg['title'])
    s = s.replace('trixdoku.v1', cfg['key'])
    s = s.replace('art/trix-piece.png', cfg['piece'])
    s = s.replace('Trix', cfg['character'])   # after Trixdoku, so the name is safe
    (SRC.parent / out).write_text(s, encoding='utf-8')
    print('built', out, len(s), 'bytes')

for out, cfg in GAMES.items():
    build(out, cfg)
