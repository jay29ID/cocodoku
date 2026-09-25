# Cowdoku, Trixdoku and Cocodoku

Three versions of the same logic puzzle. Put one animal in every coloured
field, one in every row and one in every column, and never two touching, not
even corner to corner. Tap a square once to rule it out, twice to place your
animal.

| | |
|---|---|
| **Cocodoku** | 80 levels, 6x6 up to 11x11, with Coco. Served at `/`. |
| **Trixdoku** | The same 80 levels, with Trixie. `/trixdoku` |
| **Cowdoku** | Free play on hand-painted fields. `/cowdoku` |

`/games` lists all three.

## Ways to play

Every level can be played four ways. The rules change, the puzzle does not, so
eighty levels are worth four times as much without a new puzzle being
generated. Each one keeps its own scores, stars and leaderboard, and the
harder the rules the more a finish is worth.

| | |
|---|---|
| **Normal** | Three lives, and you can rule squares out as you go. |
| **No marks** | No X marks at all: a tap places the piece. Scores 1.6x. |
| **One life** | One wrong placement ends the round. Scores 1.5x. |
| **Against the clock** | The three-star time is the whole budget, counting down. Scores 1.4x. |

Pick one at the top of the Levels screen. A level opens once the one before it
has been finished in any mode.

Forty-three badges sit on the profile, from finishing a first level to three
stars on all eighty, forty levels with no marks, or playing on thirty
different days. They are worked out in the browser from progress the game
already keeps, so they need no storage of their own; a locked one shows how
far along it is.

## Running it

```sh
bun server.ts            # serves ./web on $PORT (default 3000)
bun run dev              # port 3111, records kept in ./records.json
```

`server.ts` is the whole backend: it serves the files in `web/`, keeps the
accounts and keeps the shared leaderboard.

Scores:

- `GET /api/records?game=cocodoku&mode=nomark` — the top five for every level
  in that mode (`mode` is empty for the ordinary game)
- `POST /api/records` `{game, mode, level, ini, sc, t}` — kept if it reaches that
  level's top five. Signed in, the account supplies the name and the score
  replaces that player's own earlier one rather than taking a second place.
- `GET /api/health`

Accounts:

- `POST /api/signup` `{handle, pass, name, ini}` and `POST /api/login`
  `{handle, pass}` — both set the session cookie
- `POST /api/logout`, `GET /api/me`
- `POST /api/profile` `{name, ini, bio, avatar}` and `POST /api/password`
  `{old, pass}`
- `POST /api/avatar` — the picture itself as the body
- `GET /api/user?handle=` — anyone's public profile
- `GET|POST /api/progress` — the player's stars, best times and clean runs, so
  an account picks up where it left off on another phone

Scores are keyed by game, mode, level and player, so each mode has its own
board and a new best replaces that player's own row rather than taking a
second place on it.

Everything lives under `DATA_DIR` (`/data` in production, which is a Railway
volume, so it survives redeploys): `app.db`, a SQLite database Bun opens
itself, and `avatars/` beside it. A `records.json` left over from before the
database is imported once on boot and then set aside as `records.json.imported`.

Passwords are hashed with argon2id (`Bun.password`). The session cookie is
httpOnly, SameSite=Lax and Secure behind Railway's proxy. Sign-in, sign-up,
uploads and score posts are rate limited per address. Uploaded pictures are
squared and shrunk to 256px in the browser, then checked by magic bytes on the
way in: PNG, JPEG, GIF and WebP only, never SVG, which can carry script.

Playing signed out still works and still keeps three initials on the board;
nothing about an account is required.

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
  -> build/add_levels.py     the level ladder
  -> build/add_scores.py     scoring, records, the Records screen
  -> build/build.py          emits cocodoku.html from trixdoku.html
  -> build/add_server.py     points the leaderboard at /api/records,
                             writes web/
  -> build/add_accounts.py   profiles, avatars and badges, over web/
  -> build/add_modes.py      the challenge modes, over web/
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
is a volume mounted at `/data`, which is where the database and the avatars
live, so accounts and scores survive a redeploy.
