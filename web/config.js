// Runtime config. Kept empty in source — the CARTO basemap key is injected
// here at deploy time from the CARTO_API_KEY GitHub Actions secret (see
// .github/workflows/deploy.yml). As of 2026-09-25 CARTO requires a key for
// raster tiles: with no key the basemap shows an "API key required" watermark
// instead of a map (local checkouts without the secret look like this).
window.CARTO_KEY = "";
