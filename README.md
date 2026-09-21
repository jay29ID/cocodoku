# Cowdoku, Trixdoku and Cocodoku

Three versions of the same logic puzzle. Put one animal in every coloured
field, one in every row and one in every column, and never two touching, not
even corner to corner. Tap a square once to rule it out, twice to place your
animal.

| | |
|---|---|
| **Cocodoku** | 50 levels, 6x6 up to 11x11, with Coco. Served at `/`. |
| **Trixdoku** | The same 50 levels, with Trixie. `/trixdoku` |
| **Cowdoku** | Free play on hand-painted fields. `/cowdoku` |

`/games` lists all three.

## Running it

```sh
bun server.ts            # serves ./web on $PORT (default 3000)
bun run dev              # port 3111, records kept in ./records.json
```

`server.ts` is the whole backend: it serves the files in `web/` and keeps the
shared leaderboard.

- `GET /api/records?game=cocodoku` — every level's record holder
- `POST /api/records` `{game, level, ini, sc, t}` — kept only if it beats the
  standing record for that level
- `GET /api/health`

Records live in `records.json` under `DATA_DIR` (`/data` in production, which
is a Railway volume, so they survive redeploys). Nothing else is persisted;
each player's own progress and best times stay in their browser.

## Scoring

A finished level scores `size * size * 10`, adjusted three ways: par time
scores 1x and twice as fast scores 2x (capped), each life lost costs 20%, and
each hint costs 15%. Beat a level's standing record and the game asks for
three initials.

Par is `12 + 1.2 * cells` seconds. Three stars under par, two under 1.8x par,
one otherwise; a hint caps the level at two stars.

## How the games are built

`web/` is generated, not hand-edited. The source of truth is
`src/trixdoku.base.html`, and everything else is a patch over it:

```
src/trixdoku.base.html
  -> build/add_levels.py     the 50-level ladder
  -> build/add_scores.py     scoring, records, the Records screen
  -> build/build.py          emits cocodoku.html from trixdoku.html
  -> build/add_server.py     points the leaderboard at /api/records,
                             writes web/
```

`build/make.sh` runs the first three. Cowdoku (`src/cowdoku.html`) is separate:
it predates the levels and is free play only.

Level puzzles are pre-generated and baked into the file, because generating an
11x11 that is solvable by logic alone takes far too long to do on a phone.
`tools/` holds that machinery: `extract.py` lifts the generator out of the game
so it can run in node, `gen_levels.mjs` builds a pool, and `rate.mjs` grades
each puzzle by re-running the game's own solving rules and scoring how hard
they had to work. Each block of levels then ramps from easy to hard.

`tools/crop.mjs` crops character art to its opaque bounding box and downscales
it, which matters: the photos arrive around 3000px for a 40px game piece.

## Deploying

Railway builds the Dockerfile and runs `bun server.ts`. The one thing it needs
is a volume mounted at `/data` so the leaderboard survives a redeploy.
