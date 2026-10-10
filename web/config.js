// Runtime config. Kept empty in source — the CARTO basemap key is injected
// here at deploy time from the CARTO_API_KEY GitHub Actions secret (see
// .github/workflows/deploy.yml). With no key the app falls back to CARTO's
// keyless endpoint, which works but is aggressively rate-limited.
window.CARTO_KEY = "";
