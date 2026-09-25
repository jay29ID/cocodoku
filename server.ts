// Cowdoku / Trixdoku / Cocodoku — static host, accounts and shared leaderboard.
//
// The games themselves are plain files in web/ and ship with the image. What
// has to survive a redeploy — accounts, profiles, avatars, scores and each
// player's progress — lives on the Railway volume mounted at /data: app.db
// (SQLite, which Bun ships with) and an avatars/ folder beside it.

import { Database } from "bun:sqlite";
import { mkdirSync } from "node:fs";

const SITE = Bun.env.SITE_DIR || "./web";
const DATA = Bun.env.DATA_DIR || "/data";
const AVDIR = DATA + "/avatars";

const GAMES: Record<string, string> = {
  trixdoku: "Trixdoku",
  cocodoku: "Cocodoku",
  cowdoku: "Cowdoku",
};

// The challenge modes play the same levels under different rules, so each one
// keeps its own board. "" is the ordinary game.
const MODES: Record<string, string> = {
  "": "Normal",
  nomark: "No marks",
  onelife: "One life",
  rush: "Against the clock",
};

const KEEP = 5; // rows shown per level
const CAP = 200; // rows kept per level
const YEAR = 365 * 24 * 3600;

mkdirSync(AVDIR, { recursive: true });
const db = new Database(DATA + "/app.db", { create: true });
db.exec("pragma journal_mode = WAL; pragma synchronous = NORMAL; pragma foreign_keys = ON;");
db.exec(`
create table if not exists users(
  id integer primary key autoincrement,
  handle text unique not null,
  name text not null,
  ini text not null,
  pass text not null,
  avatar text,
  bio text not null default '',
  created integer not null,
  seen integer not null
);
create table if not exists sessions(
  tok text primary key,
  uid integer not null references users(id) on delete cascade,
  created integer not null,
  seen integer not null
);
create table if not exists scores(
  game text not null,
  mode text not null default '',
  level integer not null,
  who text not null,           -- 'u<id>' for an account, 'a<initials>' otherwise
  uid integer references users(id) on delete set null,
  ini text not null,
  sc integer not null,
  t integer not null,
  at integer not null,
  primary key(game, mode, level, who)
);
create index if not exists scores_rank on scores(game, mode, level, sc desc, t asc);
create table if not exists progress(
  uid integer not null references users(id) on delete cascade,
  game text not null,
  data text not null,
  updated integer not null,
  primary key(uid, game)
);
`);

// Scores predate the challenge modes, and mode is part of the key, so a table
// without it is rebuilt rather than altered: SQLite cannot widen a primary key.
const scoreCols = db.query<{ name: string }, []>("pragma table_info(scores)").all();
if (scoreCols.length && !scoreCols.some((c) => c.name === "mode")) {
  db.exec(`
    alter table scores rename to scores_old;
    create table scores(
      game text not null, mode text not null default '', level integer not null,
      who text not null, uid integer references users(id) on delete set null,
      ini text not null, sc integer not null, t integer not null, at integer not null,
      primary key(game, mode, level, who)
    );
    insert into scores(game,mode,level,who,uid,ini,sc,t,at)
      select game,'',level,who,uid,ini,sc,t,at from scores_old;
    drop table scores_old;
    create index if not exists scores_rank on scores(game, mode, level, sc desc, t asc);
  `);
  console.log("scores table rebuilt with a mode column");
}

// The leaderboard used to be a JSON file. Move it in once, then keep the file
// as .imported so a redeploy cannot replay it over newer scores.
const OLDRECS = DATA + "/records.json";
try {
  const raw: any = await Bun.file(OLDRECS).json();
  const ins = db.prepare(
    "insert into scores(game,mode,level,who,uid,ini,sc,t,at) values(?,'',?,?,null,?,?,?,?) " +
      "on conflict(game,mode,level,who) do update set sc=excluded.sc,t=excluded.t,at=excluded.at where excluded.sc>sc",
  );
  let n = 0;
  db.transaction(() => {
    for (const g of Object.keys(raw || {})) {
      if (!(g in GAMES)) continue;
      for (const k of Object.keys(raw[g] || {})) {
        const v = raw[g][k];
        for (const r of Array.isArray(v) ? v : [v]) {
          if (!r || typeof r.sc !== "number") continue;
          const ini = String(r.ini || "---").toUpperCase().slice(0, 3);
          ins.run(g, Number(k) | 0, "a" + ini, ini, Math.round(r.sc), Math.round(r.t || 1), r.at || Date.now());
          n++;
        }
      }
    }
  })();
  await Bun.write(OLDRECS + ".imported", await Bun.file(OLDRECS).text());
  await Bun.file(OLDRECS).delete();
  console.log("imported", n, "scores from records.json");
} catch {
  /* no file, or already imported */
}

/* ---------------- helpers ---------------- */

function json(body: unknown, status = 200, extra?: Record<string, string>) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      ...(extra || {}),
    },
  });
}

function token() {
  const b = new Uint8Array(24);
  crypto.getRandomValues(b);
  return Buffer.from(b).toString("base64url");
}

function cleanIni(v: unknown) {
  return String(v ?? "").toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 3);
}

function cleanName(v: unknown) {
  return String(v ?? "").replace(/[\u0000-\u001f\u007f]/g, "").trim().slice(0, 24);
}

function cleanHandle(v: unknown) {
  return String(v ?? "").toLowerCase().trim();
}

const HANDLE = /^[a-z0-9_]{3,20}$/;

// Attempts per key in a rolling window; used on the two endpoints that guess.
const hits = new Map<string, { n: number; until: number }>();
function tooMany(key: string, max: number, windowMs: number) {
  const now = Date.now();
  const h = hits.get(key);
  if (!h || h.until < now) {
    hits.set(key, { n: 1, until: now + windowMs });
    return false;
  }
  h.n++;
  if (hits.size > 5000) for (const [k, v] of hits) if (v.until < now) hits.delete(k);
  return h.n > max;
}
function forgive(key: string) {
  hits.delete(key);
}

function ipOf(req: Request, server: any) {
  const fwd = req.headers.get("x-forwarded-for");
  if (fwd) return fwd.split(",")[0].trim();
  return server?.requestIP?.(req)?.address || "?";
}

function cookieOf(req: Request, name: string) {
  const raw = req.headers.get("cookie");
  if (!raw) return null;
  for (const part of raw.split(";")) {
    const i = part.indexOf("=");
    if (i > 0 && part.slice(0, i).trim() === name) return decodeURIComponent(part.slice(i + 1).trim());
  }
  return null;
}

function secure(req: Request) {
  return (req.headers.get("x-forwarded-proto") || new URL(req.url).protocol.replace(":", "")) === "https";
}

function setCookie(req: Request, tok: string | null) {
  const base = `sid=${tok || ""}; Path=/; HttpOnly; SameSite=Lax${secure(req) ? "; Secure" : ""}`;
  return { "set-cookie": tok ? `${base}; Max-Age=${YEAR}` : `${base}; Max-Age=0` };
}

/* ---------------- accounts ---------------- */

type User = {
  id: number; handle: string; name: string; ini: string; pass: string;
  avatar: string | null; bio: string; created: number; seen: number;
};

const qUserByHandle = db.query<User, [string]>("select * from users where handle=?");
const qUserById = db.query<User, [number]>("select * from users where id=?");
const qSession = db.query<{ tok: string; uid: number; seen: number }, [string]>("select * from sessions where tok=?");

function whoIs(req: Request): User | null {
  const tok = cookieOf(req, "sid");
  if (!tok) return null;
  const s = qSession.get(tok);
  if (!s) return null;
  const u = qUserById.get(s.uid);
  if (!u) return null;
  const now = Date.now();
  if (now - s.seen > 3600e3) {
    db.run("update sessions set seen=? where tok=?", [now, tok]);
    db.run("update users set seen=? where id=?", [now, u.id]);
  }
  return u;
}

function publicUser(u: User) {
  return { id: u.id, handle: u.handle, name: u.name, ini: u.ini, avatar: u.avatar, bio: u.bio, created: u.created };
}

// What the profile card shows: everything derived from that player's scores.
function statsFor(uid: number) {
  const rows = db
    .query<{ game: string; mode: string; levels: number; total: number; best: number }, [number]>(
      "select game, mode, count(*) levels, sum(sc) total, max(sc) best from scores where uid=? group by game, mode",
    )
    .all(uid);
  const firsts = db
    .query<{ n: number }, [number]>(
      "select count(*) n from scores s where s.uid=? and s.sc=" +
        "(select max(sc) from scores x where x.game=s.game and x.mode=s.mode and x.level=s.level)",
    )
    .get(uid);
  const by: Record<string, { levels: number; total: number; best: number }> = {};
  const modes: Record<string, number> = {};
  let levels = 0, total = 0;
  for (const r of rows) {
    const g = by[r.game] || (by[r.game] = { levels: 0, total: 0, best: 0 });
    g.levels += r.levels;
    g.total += r.total;
    g.best = Math.max(g.best, r.best);
    modes[r.mode] = (modes[r.mode] || 0) + r.levels;
    levels += r.levels;
    total += r.total;
  }
  return { levels, total, firsts: firsts?.n || 0, by, modes };
}

/* ---------------- scores ---------------- */

type Row = { level: number; who: string; uid: number | null; ini: string; sc: number; t: number; at: number; name?: string; avatar?: string | null };

const qBoard = db.query<Row, [string, string]>(`
  select level, who, uid, ini, sc, t, at, name, avatar from (
    select s.*, u.name, u.avatar,
           row_number() over (partition by s.level order by s.sc desc, s.t asc, s.at asc) rn
    from scores s left join users u on u.id = s.uid
    where s.game = ? and s.mode = ?
  ) where rn <= ${KEEP}
  order by level, sc desc`);

function board(game: string, mode: string) {
  const out: Record<string, any[]> = {};
  for (const r of qBoard.all(game, mode)) {
    (out[String(r.level)] || (out[String(r.level)] = [])).push({
      ini: r.ini, sc: r.sc, t: r.t, at: r.at,
      uid: r.uid || undefined, name: r.name || undefined, av: r.avatar || undefined,
    });
  }
  return out;
}

/* ---------------- avatars ---------------- */

const MAGIC: [string, number[]][] = [
  ["png", [0x89, 0x50, 0x4e, 0x47]],
  ["jpg", [0xff, 0xd8, 0xff]],
  ["webp", [0x52, 0x49, 0x46, 0x46]], // plus "WEBP" at 8
  ["gif", [0x47, 0x49, 0x46, 0x38]],
];

// Trust the bytes, never the content-type, and never accept SVG: it is a
// document that can carry script, and these are served from our own origin.
function imageKind(b: Uint8Array): string | null {
  for (const [ext, sig] of MAGIC) {
    if (sig.every((v, i) => b[i] === v)) {
      if (ext === "webp" && !(b[8] === 0x57 && b[9] === 0x45 && b[10] === 0x42 && b[11] === 0x50)) continue;
      return ext;
    }
  }
  return null;
}

/* ---------------- static files ---------------- */

const TYPES: Record<string, string> = {
  html: "text/html; charset=utf-8",
  css: "text/css; charset=utf-8",
  js: "text/javascript; charset=utf-8",
  json: "application/json; charset=utf-8",
  png: "image/png",
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  gif: "image/gif",
  svg: "image/svg+xml",
  webp: "image/webp",
  ico: "image/x-icon",
  webmanifest: "application/manifest+json",
};

// Only plain relative paths: no traversal, no absolute paths, no dotfiles.
function safeRel(p: string): string | null {
  if (!p || p.length > 200) return null;
  if (!/^[A-Za-z0-9][A-Za-z0-9._/-]*$/.test(p)) return null;
  if (p.includes("..") || p.includes("//")) return null;
  return p;
}

async function serveFile(dir: string, rel: string, cache: string) {
  const f = Bun.file(dir + "/" + rel);
  if (!(await f.exists())) return null;
  const ext = rel.slice(rel.lastIndexOf(".") + 1).toLowerCase();
  return new Response(f, {
    headers: {
      "content-type": TYPES[ext] || "application/octet-stream",
      "cache-control": cache,
      "x-content-type-options": "nosniff",
    },
  });
}

/* ---------------- routes ---------------- */

async function body(req: Request): Promise<any> {
  try {
    return await req.json();
  } catch {
    return null;
  }
}

Bun.serve({
  port: Number(Bun.env.PORT || 3000),
  idleTimeout: 30,
  async fetch(req, server) {
    const url = new URL(req.url);
    let path = decodeURIComponent(url.pathname);
    const ip = () => ipOf(req, server);

    if (path === "/api/health") {
      const n = db.query<{ n: number }, []>("select count(*) n from users").get();
      const s = db.query<{ n: number }, []>("select count(*) n from scores").get();
      return json({ ok: true, users: n?.n || 0, scores: s?.n || 0, site: await Bun.file(SITE + "/index.html").exists() });
    }

    /* ----- who am I ----- */
    if (path === "/api/me") {
      const u = whoIs(req);
      if (!u) return json({ user: null });
      return json({ user: publicUser(u), stats: statsFor(u.id) });
    }

    /* ----- create an account ----- */
    if (path === "/api/signup" && req.method === "POST") {
      if (tooMany("new:" + ip(), 8, 3600e3)) return json({ error: "Too many new accounts from here. Try later." }, 429);
      const b = await body(req);
      const handle = cleanHandle(b?.handle);
      const pass = String(b?.pass ?? "");
      if (!HANDLE.test(handle)) return json({ error: "Usernames are 3-20 letters, numbers or underscores." }, 400);
      if (pass.length < 8 || pass.length > 200) return json({ error: "Pick a password of at least 8 characters." }, 400);
      if (qUserByHandle.get(handle)) return json({ error: "That username is taken." }, 409);
      const name = cleanName(b?.name) || handle;
      const ini = cleanIni(b?.ini) || cleanIni(name) || handle.slice(0, 3).toUpperCase();
      const now = Date.now();
      const hash = await Bun.password.hash(pass);
      let id: number;
      try {
        db.run("insert into users(handle,name,ini,pass,avatar,bio,created,seen) values(?,?,?,?,?,'',?,?)", [
          handle, name, ini, hash, cleanAvatarPreset(b?.avatar), now, now,
        ]);
        id = Number(db.query<{ id: number }, []>("select last_insert_rowid() id").get()!.id);
      } catch {
        return json({ error: "That username is taken." }, 409);
      }
      const tok = token();
      db.run("insert into sessions(tok,uid,created,seen) values(?,?,?,?)", [tok, id, now, now]);
      const u = qUserById.get(id)!;
      return json({ user: publicUser(u), stats: statsFor(id) }, 200, setCookie(req, tok));
    }

    /* ----- sign in ----- */
    if (path === "/api/login" && req.method === "POST") {
      const b = await body(req);
      const handle = cleanHandle(b?.handle);
      const pass = String(b?.pass ?? "");
      if (tooMany("in:" + ip(), 20, 900e3) || tooMany("who:" + handle, 10, 900e3))
        return json({ error: "Too many attempts. Wait a few minutes." }, 429);
      const u = handle ? qUserByHandle.get(handle) : null;
      const ok = u ? await Bun.password.verify(pass, u.pass) : false;
      if (!u || !ok) return json({ error: "Wrong username or password." }, 401);
      forgive("in:" + ip());
      forgive("who:" + handle);
      const tok = token();
      const now = Date.now();
      db.run("insert into sessions(tok,uid,created,seen) values(?,?,?,?)", [tok, u.id, now, now]);
      db.run("update users set seen=? where id=?", [now, u.id]);
      return json({ user: publicUser(u), stats: statsFor(u.id) }, 200, setCookie(req, tok));
    }

    /* ----- sign out ----- */
    if (path === "/api/logout" && req.method === "POST") {
      const tok = cookieOf(req, "sid");
      if (tok) db.run("delete from sessions where tok=?", [tok]);
      return json({ user: null }, 200, setCookie(req, null));
    }

    /* ----- edit the profile ----- */
    if (path === "/api/profile" && req.method === "POST") {
      const u = whoIs(req);
      if (!u) return json({ error: "Sign in first." }, 401);
      const b = await body(req);
      const name = b?.name === undefined ? u.name : cleanName(b.name) || u.name;
      const ini = b?.ini === undefined ? u.ini : cleanIni(b.ini) || u.ini;
      const bio = b?.bio === undefined ? u.bio : cleanName(b.bio).slice(0, 140);
      const avatar = b?.avatar === undefined ? u.avatar : cleanAvatarPreset(b.avatar) ?? u.avatar;
      db.run("update users set name=?,ini=?,bio=?,avatar=? where id=?", [name, ini, bio, avatar, u.id]);
      db.run("update scores set ini=? where uid=?", [ini, u.id]);
      return json({ user: publicUser(qUserById.get(u.id)!), stats: statsFor(u.id) });
    }

    /* ----- change the password ----- */
    if (path === "/api/password" && req.method === "POST") {
      const u = whoIs(req);
      if (!u) return json({ error: "Sign in first." }, 401);
      const b = await body(req);
      if (tooMany("pw:" + u.id, 10, 900e3)) return json({ error: "Too many attempts. Wait a few minutes." }, 429);
      if (!(await Bun.password.verify(String(b?.old ?? ""), u.pass)))
        return json({ error: "That is not your current password." }, 401);
      const pass = String(b?.pass ?? "");
      if (pass.length < 8 || pass.length > 200) return json({ error: "Pick a password of at least 8 characters." }, 400);
      db.run("update users set pass=? where id=?", [await Bun.password.hash(pass), u.id]);
      // Every other device is signed out; this one keeps its cookie.
      db.run("delete from sessions where uid=? and tok<>?", [u.id, cookieOf(req, "sid") || ""]);
      return json({ ok: true });
    }

    /* ----- upload an avatar ----- */
    if (path === "/api/avatar" && req.method === "POST") {
      const u = whoIs(req);
      if (!u) return json({ error: "Sign in first." }, 401);
      if (tooMany("av:" + u.id, 20, 3600e3)) return json({ error: "Too many uploads. Try later." }, 429);
      const buf = new Uint8Array(await req.arrayBuffer());
      if (buf.length < 32) return json({ error: "That file is empty." }, 400);
      if (buf.length > 2 * 1024 * 1024) return json({ error: "Pictures have to be under 2MB." }, 413);
      const kind = imageKind(buf);
      if (!kind) return json({ error: "Use a PNG, JPEG, GIF or WebP picture." }, 415);
      const file = `${u.id}-${token().slice(0, 12)}.${kind}`;
      await Bun.write(AVDIR + "/" + file, buf);
      const old = u.avatar;
      db.run("update users set avatar=? where id=?", ["f:" + file, u.id]);
      if (old && old.startsWith("f:")) {
        try { await Bun.file(AVDIR + "/" + old.slice(2)).delete(); } catch {}
      }
      return json({ user: publicUser(qUserById.get(u.id)!) });
    }

    if (path.startsWith("/avatars/")) {
      const rel = safeRel(path.slice("/avatars/".length));
      if (!rel || rel.includes("/")) return new Response("Not found", { status: 404 });
      const res = await serveFile(AVDIR, rel, "public, max-age=31536000, immutable");
      return res || new Response("Not found", { status: 404 });
    }

    /* ----- someone else's profile ----- */
    if (path === "/api/user") {
      const h = cleanHandle(url.searchParams.get("handle"));
      const u = h ? qUserByHandle.get(h) : null;
      if (!u) return json({ error: "No such player." }, 404);
      return json({ user: publicUser(u), stats: statsFor(u.id) });
    }

    /* ----- progress, so an account carries its stars between devices ----- */
    if (path === "/api/progress") {
      const u = whoIs(req);
      if (!u) return json({ error: "Sign in first." }, 401);
      const g = String(url.searchParams.get("game") || "");
      if (req.method === "GET") {
        if (!(g in GAMES)) return json({ error: "unknown game" }, 400);
        const row = db.query<{ data: string; updated: number }, [number, string]>(
          "select data, updated from progress where uid=? and game=?",
        ).get(u.id, g);
        return json({ game: g, data: row ? JSON.parse(row.data) : null, updated: row?.updated || 0 });
      }
      if (req.method === "POST") {
        const b = await body(req);
        const game = String(b?.game ?? "");
        if (!(game in GAMES)) return json({ error: "unknown game" }, 400);
        const data = JSON.stringify(b?.data ?? {});
        if (data.length > 200000) return json({ error: "too big" }, 413);
        db.run(
          "insert into progress(uid,game,data,updated) values(?,?,?,?) " +
            "on conflict(uid,game) do update set data=excluded.data, updated=excluded.updated",
          [u.id, game, data, Date.now()],
        );
        return json({ ok: true });
      }
      return json({ error: "method not allowed" }, 405);
    }

    /* ----- the leaderboard ----- */
    if (path === "/api/records") {
      if (req.method === "GET") {
        const g = url.searchParams.get("game") || "";
        const m = url.searchParams.get("mode") || "";
        if (!(g in GAMES)) return json({ error: "unknown game" }, 400);
        if (!(m in MODES)) return json({ error: "unknown mode" }, 400);
        return json({ game: g, mode: m, records: board(g, m) });
      }
      if (req.method === "POST") {
        const b = await body(req);
        if (!b) return json({ error: "bad json" }, 400);
        const g = String(b?.game ?? "");
        if (!(g in GAMES)) return json({ error: "unknown game" }, 400);
        const m = String(b?.mode ?? "");
        if (!(m in MODES)) return json({ error: "unknown mode" }, 400);
        const lv = Number(b?.level);
        if (!Number.isInteger(lv) || lv < 0 || lv > 999) return json({ error: "bad level" }, 400);
        const sc = Math.round(Number(b?.sc));
        const t = Math.round(Number(b?.t));
        if (!Number.isFinite(sc) || sc < 1 || sc > 100000) return json({ error: "bad score" }, 400);
        if (!Number.isFinite(t) || t < 1 || t > 86400) return json({ error: "bad time" }, 400);
        const u = whoIs(req);
        const ini = u ? u.ini : cleanIni(b?.ini);
        if (!ini) return json({ error: "bad initials" }, 400);
        const who = u ? "u" + u.id : "a" + ini;
        if (tooMany("sc:" + (u ? "u" + u.id : ip()), 120, 600e3)) return json({ error: "slow down" }, 429);
        db.run(
          "insert into scores(game,mode,level,who,uid,ini,sc,t,at) values(?,?,?,?,?,?,?,?,?) " +
            "on conflict(game,mode,level,who) do update set sc=excluded.sc,t=excluded.t,at=excluded.at " +
            "where excluded.sc>scores.sc",
          [g, m, lv, who, u ? u.id : null, ini, sc, t, Date.now()],
        );
        const over = db.query<{ n: number }, [string, string, number]>(
          "select count(*) n from scores where game=? and mode=? and level=?",
        ).get(g, m, lv);
        if ((over?.n || 0) > CAP)
          db.run(
            "delete from scores where game=? and mode=? and level=? and who in " +
              "(select who from scores where game=? and mode=? and level=? order by sc asc, t desc limit ?)",
            [g, m, lv, g, m, lv, (over!.n - CAP)],
          );
        return json({ game: g, mode: m, records: board(g, m) });
      }
      return json({ error: "method not allowed" }, 405);
    }

    if (req.method !== "GET" && req.method !== "HEAD") return json({ error: "method not allowed" }, 405);

    if (path === "/") path = "/index.html";
    if (path.endsWith("/")) path = path.slice(0, -1);
    const rel = safeRel(path.slice(1));
    if (!rel) return new Response("Not found", { status: 404 });

    const ext = rel.slice(rel.lastIndexOf(".") + 1).toLowerCase();
    let res = await serveFile(SITE, rel, ext === "html" ? "no-cache" : "public, max-age=3600");
    if (!res && !rel.includes(".")) res = await serveFile(SITE, rel + ".html", "no-cache");
    if (res) return res;

    return new Response("Not found", { status: 404, headers: { "content-type": "text/plain" } });
  },
});

// Presets are picked by name from a fixed list in the game, so anything the
// client sends is either one of those keys or nothing at all.
function cleanAvatarPreset(v: unknown): string | null {
  const s = String(v ?? "");
  return /^p:[a-z0-9-]{1,24}$/.test(s) ? s : null;
}

console.log("listening on", Bun.env.PORT || 3000, "serving", SITE, "data in", DATA);
