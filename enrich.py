#!/usr/bin/env python3
"""
enrich.py - fill in posters, creators, seasons, episodes, status, network, runtime,
cast and ratings for shows.json using TMDB (required) and OMDb (optional, adds IMDb/RT/Metacritic).

    python3 enrich.py shows.json --tmdb YOUR_TMDB_KEY [--omdb YOUR_OMDB_KEY] [--limit 50]

Keys may also come from the TMDB_KEY / OMDB_KEY environment variables.
Safe to re-run: it only fills blanks (never overwrites what you typed), skips shows already
matched (they have a tmdb_id), caches API replies in .enrich_cache.json, and saves as it goes.
Shows it can't match confidently are listed in enrich_unmatched.txt.
"""
import argparse, json, os, re, sys, time, unicodedata, urllib.parse, urllib.request, urllib.error
from pathlib import Path

TMDB = "https://api.themoviedb.org/3"
STATUS = {"Returning Series": "Ongoing", "In Production": "Ongoing", "Planned": "Ongoing", "Pilot": "Ongoing",
          "Ended": "Ended", "Canceled": "Cancelled"}
NETWORKS = [(r"^hbo", "HBO"), (r"^netflix", "Netflix"), (r"apple tv", "Apple TV+"), (r"amazon|prime video", "Prime Video"),
            (r"disney\+|disney plus", "Disney+"), (r"^bbc", "BBC"), (r"^abc$|^abc \(", "ABC"), (r"^amc$", "AMC"), (r"^stan\.?$", "Stan")]
cache = {}

def norm(t):
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", re.sub(r"\b(the|a|an)\b", "", t))

def get(url, params):
    key = url + "?" + urllib.parse.urlencode(sorted(params.items()))
    if key in cache: return cache[key]
    q = dict(params)
    q["api_key" if url.startswith(TMDB) else "apikey"] = KEYS[url.startswith(TMDB)]
    full = url + "?" + urllib.parse.urlencode(q)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(full, timeout=20) as r:
                cache[key] = json.loads(r.read().decode("utf-8")); return cache[key]
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(int(e.headers.get("Retry-After", 2)) + 1); continue
            if e.code in (401, 403): sys.exit("API key rejected (%s) for %s" % (e.code, url.split("/")[2]))
            cache[key] = None; return None
        except Exception: time.sleep(1.5)
    return None

def best_match(show):
    year = show.get("year")
    for params in ([{"query": show["title"], "first_air_date_year": year}] if year else []) + [{"query": show["title"]}]:
        res = (get(TMDB + "/search/tv", params) or {}).get("results", [])
        scored = []
        for r in res[:8]:
            ry = int((r.get("first_air_date") or "0000")[:4] or 0)
            same = norm(r.get("name")) == norm(show["title"]) or norm(r.get("original_name")) == norm(show["title"])
            near = year and ry and abs(ry - year) <= 1
            contains = norm(show["title"]) in norm(r.get("name")) or norm(r.get("name")) in norm(show["title"])
            if same or (near and contains):
                scored.append((same * 3 + bool(near) * 2 + min(r.get("popularity", 0), 50) / 100, r))
        if scored: return max(scored, key=lambda x: x[0])[1]
    return None

def fill(show, key, value):
    if value not in (None, "", [], 0) and show.get(key) in (None, "", [], 0): show[key] = value

def enrich(show, use_omdb):
    m = best_match(show)
    if not m: return False
    d = get(TMDB + "/tv/%d" % m["id"], {"append_to_response": "external_ids,aggregate_credits"})
    if not d: return False
    show["tmdb_id"] = d["id"]
    if d.get("poster_path"): fill(show, "poster", "https://image.tmdb.org/t/p/w342" + d["poster_path"])
    fill(show, "synopsis", d.get("overview"))
    fill(show, "seasons", d.get("number_of_seasons")); fill(show, "episodes", d.get("number_of_episodes"))
    fill(show, "status", STATUS.get(d.get("status")))
    fill(show, "director", ", ".join(c["name"] for c in d.get("created_by", [])[:3]))
    net = (d.get("networks") or [{}])[0].get("name", "")
    fill(show, "distributor", next((n for p, n in NETWORKS if re.search(p, net.lower())), net))
    rt = (d.get("episode_run_time") or [None])[0] or (d.get("last_episode_to_air") or {}).get("runtime")
    fill(show, "runtime", rt)
    fill(show, "cast", [c["name"] for c in (d.get("aggregate_credits") or {}).get("cast", [])[:3]])
    imdb = (d.get("external_ids") or {}).get("imdb_id"); fill(show, "imdb_id", imdb)
    if d.get("vote_average"): fill(show, "score", round(d["vote_average"], 1))   # base score; app averages in IMDb/RT when present
    if use_omdb and show.get("imdb_id"):
        o = get("https://www.omdbapi.com/", {"i": show["imdb_id"]}) or {}
        if o.get("Response") == "True":
            try: fill(show, "imdb_score", float(o["imdbRating"]))
            except (KeyError, ValueError): pass
            for r in o.get("Ratings", []):
                if r["Source"] == "Rotten Tomatoes": fill(show, "rt_score", round(int(r["Value"].rstrip("%")) / 100, 2))
            try: fill(show, "mc_score", int(o["Metascore"]))
            except (KeyError, ValueError): pass
    return True

def main():
    global KEYS
    ap = argparse.ArgumentParser(); ap.add_argument("file"); ap.add_argument("--tmdb"); ap.add_argument("--omdb")
    ap.add_argument("--limit", type=int, default=0, help="only process this many shows this run")
    a = ap.parse_args()
    tmdb = a.tmdb or os.environ.get("TMDB_KEY"); omdb = a.omdb or os.environ.get("OMDB_KEY")
    if not tmdb: sys.exit("Need a TMDB API key: --tmdb KEY (or set TMDB_KEY)")
    KEYS = {True: tmdb, False: omdb}
    path, cpath = Path(a.file), Path(".enrich_cache.json")
    if cpath.exists(): cache.update(json.loads(cpath.read_text(encoding="utf-8")))
    shows = json.loads(path.read_text(encoding="utf-8"))
    todo = [s for s in shows if not s.get("tmdb_id")]
    if a.limit: todo = todo[:a.limit]
    miss, done = [], 0
    for i, s in enumerate(todo, 1):
        ok = enrich(s, bool(omdb)); done += ok
        if not ok: miss.append("%s (%s)" % (s["title"], s.get("year")))
        print("[%d/%d] %s %s" % (i, len(todo), "ok  " if ok else "MISS", s["title"]))
        if i % 20 == 0:
            path.write_text(json.dumps(shows, indent=1, ensure_ascii=False), encoding="utf-8")
            cpath.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        time.sleep(0.05)
    path.write_text(json.dumps(shows, indent=1, ensure_ascii=False), encoding="utf-8")
    cpath.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    Path("enrich_unmatched.txt").write_text("\n".join(miss), encoding="utf-8")
    print("\nMatched %d of %d. %d unmatched -> enrich_unmatched.txt" % (done, len(todo), len(miss)))

if __name__ == "__main__":
    main()
