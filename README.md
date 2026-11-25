# The Archive · TV

Spin-off of the film collection app, built for TV shows. Static site: open `index.html` from any web host
(or `python3 -m http.server`). Starting data is your aggregated "greatest TV shows" list (497 shows).

## Files
| File | Purpose |
|---|---|
| `index.html` | the app (collection grid, stats, Watch Next, creator pages, add-show form) |
| `shows.json` | your library. Starts as the 497-show consensus list, all unwatched |
| `tv-wishlist.json` | optional "want to watch/buy" list (empty). Only feeds the creator pages for now |
| `enrich.py` | local script that fills in posters, creators, seasons, ratings (see below) |
| `sw.js`, `manifest.webmanifest` | offline shell / home-screen install. Add an `icon-192.png` |

## Fill in the missing data (do this once)
The list gives title, year, country, genre, consensus rank and which lists a show is on. Posters, ratings,
creators, seasons, network and runtime come from TMDB/OMDb:

    python3 enrich.py shows.json --tmdb YOUR_TMDB_KEY --omdb YOUR_OMDB_KEY

Re-runnable and resumable (`--limit 50` to try a small batch first). Unmatched titles go to `enrich_unmatched.txt`.
Until it has run, Watch Next stays empty (it needs a poster and a score) and the network/episode filters match nothing.

## Data fields
Kept the film app's field names so all its logic still works:
`director` = creator(s) · `distributor` = network/streamer · `format` = Streaming/Blu-ray/DVD · `runtime` = **episode** minutes ·
`score` = 0–10 rating. TV fields: `seasons`, `episodes`, `status` (Ongoing/Ended/Cancelled). From your list: `rank`,
`lists` (of 9), `sources` (rank per list), `note`, `gap_pick`, `points` (consensus score, not a rating).

## Saving "watched" changes
Ticks are saved in the browser immediately. To commit them to `shows.json` on GitHub the site reads the token from the
`add_cfg` setting your film site already stores (same browser/domain) and writes to the repo named in
`localStorage.tv_repo` (default `robgordon-stack/tv`, **not** your movies repo). Set it once in the browser console:
`localStorage.setItem("tv_repo","your-user/your-tv-repo")`. Without a token it just queues and offers a JSON download.

## Removed from the film app
All 12 ranked-list pages and the Lists menu, the embedded Letterboxd 500 tab, the Criterion Spine tab and badges,
4K / label / female-director filters, Letterboxd links, the `ownsearch.js` hook, the film wishlist page link.
Storage keys are all `tv_`-prefixed so it can share a domain with the film site safely.

## Not done yet
- A TV wishlist page (the film one is large and film-specific).
- A dedicated add page (the in-page "Add Show" form works: OMDb search, then Download shows.json).
- Per-season / per-episode progress (a show is watched or not).
