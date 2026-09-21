// Cowdoku / Trixdoku / Cocodoku — static host + shared leaderboard.
//
// The games themselves are plain files in web/ and ship with the image.
// The only thing that has to survive a redeploy is the leaderboard, which
// lives in records.json on the Railway volume mounted at /data.

const SITE = Bun.env.SITE_DIR || "./web";
const DATA = Bun.env.DATA_DIR || "/data";
const RECS = DATA + "/records.json";

const GAMES: Record<string, string> = {
  trixdoku: "Trixdoku",
  cocodoku: "Cocodoku",
  cowdoku: "Cowdoku",
};

type Rec = { ini: string; sc: number; t: number; at: number };

// Each level keeps its own small high score table rather than one record.
const KEEP = 5;
let recs: Record<string, Record<string, Rec[]>> = {};

function rank(list: Rec[]) {
  list.sort((a, b) => b.sc - a.sc || a.t - b.t || a.at - b.at);
  if (list.length > KEEP) list.length = KEEP;
  return list;
}

// Levels used to hold a single record object; read those as a table of one.
function normalize(raw: any) {
  const out: Record<string, Record<string, Rec[]>> = {};
  for (const g of Object.keys(raw || {})) {
    const from = raw[g] || {};
    const to: Record<string, Rec[]> = {};
    for (const k of Object.keys(from)) {
      const v = from[k];
      to[k] = rank(Array.isArray(v) ? v.slice() : v ? [v] : []);
    }
    out[g] = to;
  }
  return out;
}

try {
  recs = normalize(await Bun.file(RECS).json());
} catch {
  recs = {};
}

// One write at a time, so two finishes in the same second cannot interleave.
let chain: Promise<unknown> = Promise.resolve();
function persist() {
  chain = chain.then(() =>
    Bun.write(RECS, JSON.stringify(recs)).catch((e) => console.error("could not save records:", e)),
  );
  return chain;
}

const TYPES: Record<string, string> = {
  html: "text/html; charset=utf-8",
  css: "text/css; charset=utf-8",
  js: "text/javascript; charset=utf-8",
  json: "application/json; charset=utf-8",
  png: "image/png",
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  svg: "image/svg+xml",
  webp: "image/webp",
  ico: "image/x-icon",
  webmanifest: "application/manifest+json",
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
  });
}

function cleanIni(v: unknown) {
  return String(v ?? "").toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 3);
}

// Only plain relative paths: no traversal, no absolute paths, no dotfiles.
function safeRel(p: string): string | null {
  if (!p || p.length > 200) return null;
  if (!/^[A-Za-z0-9][A-Za-z0-9._/-]*$/.test(p)) return null;
  if (p.includes("..") || p.includes("//")) return null;
  return p;
}

async function serveFile(rel: string) {
  const f = Bun.file(SITE + "/" + rel);
  if (!(await f.exists())) return null;
  const ext = rel.slice(rel.lastIndexOf(".") + 1).toLowerCase();
  return new Response(f, {
    headers: {
      "content-type": TYPES[ext] || "application/octet-stream",
      "cache-control": ext === "html" ? "no-cache" : "public, max-age=3600",
    },
  });
}

Bun.serve({
  port: Number(Bun.env.PORT || 3000),
  idleTimeout: 30,
  async fetch(req) {
    const url = new URL(req.url);
    let path = decodeURIComponent(url.pathname);

    if (path === "/api/health") {
      const counts: Record<string, number> = {};
      for (const g of Object.keys(GAMES)) counts[g] = Object.keys(recs[g] || {}).length;
      return json({ ok: true, records: counts, site: await Bun.file(SITE + "/index.html").exists() });
    }

    if (path === "/api/records") {
      if (req.method === "GET") {
        const g = url.searchParams.get("game") || "";
        if (!(g in GAMES)) return json({ error: "unknown game" }, 400);
        return json({ game: g, records: recs[g] || {} });
      }
      if (req.method === "POST") {
        let b: any;
        try {
          b = await req.json();
        } catch {
          return json({ error: "bad json" }, 400);
        }
        const g = String(b?.game ?? "");
        if (!(g in GAMES)) return json({ error: "unknown game" }, 400);
        const lv = Number(b?.level);
        if (!Number.isInteger(lv) || lv < 0 || lv > 999) return json({ error: "bad level" }, 400);
        const ini = cleanIni(b?.ini);
        if (!ini) return json({ error: "bad initials" }, 400);
        const sc = Math.round(Number(b?.sc));
        const t = Math.round(Number(b?.t));
        if (!Number.isFinite(sc) || sc < 1 || sc > 100000) return json({ error: "bad score" }, 400);
        if (!Number.isFinite(t) || t < 1 || t > 86400) return json({ error: "bad time" }, 400);
        const tbl = recs[g] || (recs[g] = {});
        const list = tbl[String(lv)] || (tbl[String(lv)] = []);
        const worst = list.length ? list[list.length - 1].sc : 0;
        if (list.length < KEEP || sc > worst) {
          list.push({ ini, sc, t, at: Date.now() });
          rank(list);
          await persist();
        }
        return json({ game: g, records: tbl });
      }
      return json({ error: "method not allowed" }, 405);
    }

    if (req.method !== "GET" && req.method !== "HEAD") return json({ error: "method not allowed" }, 405);

    if (path === "/") path = "/index.html";
    if (path.endsWith("/")) path = path.slice(0, -1);
    const rel = safeRel(path.slice(1));
    if (!rel) return new Response("Not found", { status: 404 });

    let res = await serveFile(rel);
    if (!res && !rel.includes(".")) res = await serveFile(rel + ".html");
    if (res) return res;

    return new Response("Not found", { status: 404, headers: { "content-type": "text/plain" } });
  },
});

console.log("listening on", Bun.env.PORT || 3000, "serving", SITE, "records in", RECS);
