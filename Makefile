# PortaRun pipeline — plain Python 3, no pip installs required.

.PHONY: fetch build test serve

## Pull real data from the live APIs (needs internet). Run locally.
fetch:
	python3 -m pipeline.fetch

## Build web/data/potties.geojson from fetched data (falls back to fixtures).
build:
	python3 -m pipeline.normalize

## Run the test suite (fixtures only, no network).
test:
	python3 -m unittest discover -s pipeline/tests -t . -v

## Serve the map at http://localhost:8000/web/
serve:
	python3 -m http.server 8000
