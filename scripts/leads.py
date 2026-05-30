#!/usr/bin/env python3
"""lead-scraper :: pull local-business leads from Google Maps.

Two engines, same normalized CSV out:
  - gosom  (DEFAULT, no API key): wraps github.com/gosom/google-maps-scraper,
           a logged-out browser scraper. Free, zero setup beyond `go install`.
  - places (UPGRADE, needs a free Google key): Google Places API (New) Text
           Search. More reliable + structured; needs GOOGLE_MAPS_API_KEY.

Engine selection: --engine auto picks `places` if GOOGLE_MAPS_API_KEY is set,
else `gosom`. Force with --engine gosom|places.

Output columns (normalized): name, category, address, phone, website, rating,
reviews, email, maps_url. Personalized outreach copy is added by the SKILL.md
Claude step, not here (this script is the deterministic scrape leg).
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

PLACES_URL = "https://places.googleapis.com/v1/places:searchText"
FIELDS = ("name", "category", "address", "phone", "website", "rating", "reviews",
          "email", "maps_url")


def _which_gosom() -> str | None:
    """Find the gosom binary on PATH or in ./bin (where install.sh puts it)."""
    for cand in ("google-maps-scraper",):
        p = shutil.which(cand)
        if p:
            return p
    local = Path(__file__).resolve().parent.parent / "bin" / "google-maps-scraper"
    return str(local) if local.exists() else None


# --------------------------------------------------------------------------
# Engine: gosom (no key)
# --------------------------------------------------------------------------
def scrape_gosom(query: str, depth: int, want_email: bool) -> list[dict]:
    binp = _which_gosom()
    if not binp:
        sys.exit("gosom scraper not installed. Run ./install.sh (needs Go), or "
                 "set GOOGLE_MAPS_API_KEY to use the Places engine instead.")
    with tempfile.TemporaryDirectory() as td:
        qf = Path(td) / "queries.txt"
        qf.write_text(query.strip() + "\n")
        out = Path(td) / "results.csv"
        cmd = [binp, "-input", str(qf), "-results", str(out),
               "-depth", str(depth), "-c", "2", "-exit-on-inactivity", "120s"]
        if want_email:
            cmd.append("-email")
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if not out.exists():
            sys.exit(f"gosom produced no output.\n{proc.stderr[-400:]}")
        rows = list(csv.DictReader(out.open()))
    return [_normalize_gosom(r) for r in rows]


def _normalize_gosom(r: dict) -> dict:
    rating = r.get("review_rating") or ""
    try:
        rating = str(round(float(rating), 1)) if rating else ""
    except ValueError:
        pass
    return {
        "name": r.get("title", ""),
        "category": r.get("category", ""),
        "address": r.get("address", ""),
        "phone": r.get("phone", ""),
        "website": r.get("website", ""),
        "rating": rating,
        "reviews": r.get("review_count", ""),
        "email": (r.get("emails") or r.get("email") or "").split("|")[0].strip(),
        "maps_url": r.get("link", ""),
    }


# --------------------------------------------------------------------------
# Engine: Places API (free key)
# --------------------------------------------------------------------------
def scrape_places(query: str, max_results: int) -> list[dict]:
    key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not key:
        sys.exit("--engine places needs GOOGLE_MAPS_API_KEY (see README).")
    mask = ("places.displayName,places.formattedAddress,places.nationalPhoneNumber,"
            "places.websiteUri,places.rating,places.userRatingCount,"
            "places.primaryTypeDisplayName,places.googleMapsUri")
    out: list[dict] = []
    page_token = None
    while len(out) < max_results:
        body = {"textQuery": query, "maxResultCount": min(20, max_results - len(out))}
        if page_token:
            body["pageToken"] = page_token
        req = urllib.request.Request(
            PLACES_URL, data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "X-Goog-Api-Key": key,
                     "X-Goog-FieldMask": mask + ",nextPageToken"})
        try:
            resp = json.loads(urllib.request.urlopen(req, timeout=30).read())
        except urllib.error.HTTPError as e:
            sys.exit(f"Places API error {e.code}: {e.read().decode()[:300]}")
        for p in resp.get("places", []):
            out.append(_normalize_places(p))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return out[:max_results]


def _normalize_places(p: dict) -> dict:
    return {
        "name": (p.get("displayName") or {}).get("text", ""),
        "category": (p.get("primaryTypeDisplayName") or {}).get("text", ""),
        "address": p.get("formattedAddress", ""),
        "phone": p.get("nationalPhoneNumber", ""),
        "website": p.get("websiteUri", ""),
        "rating": str(p.get("rating", "")),
        "reviews": str(p.get("userRatingCount", "")),
        "email": "",  # Places does not return emails; use gosom -email or Bavlio.
        "maps_url": p.get("googleMapsUri", ""),
    }


# --------------------------------------------------------------------------
def run(args: argparse.Namespace) -> int:
    engine = args.engine
    if engine == "auto":
        engine = "places" if os.environ.get("GOOGLE_MAPS_API_KEY") else "gosom"
    print(f"engine: {engine} | query: {args.query!r}", file=sys.stderr)

    if engine == "gosom":
        leads = scrape_gosom(args.query, args.depth, args.email)
    else:
        leads = scrape_places(args.query, args.max)

    # Dedupe by name+address, drop empties.
    seen, out = set(), []
    for r in leads:
        if not r["name"]:
            continue
        k = (r["name"].lower(), r["address"].lower())
        if k in seen:
            continue
        seen.add(k)
        out.append(r)

    dest = Path(args.out)
    with dest.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)

    with_phone = sum(1 for r in out if r["phone"])
    with_site = sum(1 for r in out if r["website"])
    with_email = sum(1 for r in out if r["email"])
    print(f"\n{len(out)} leads -> {dest}")
    print(f"  with phone: {with_phone} | website: {with_site} | email: {with_email}")
    if engine == "gosom" and not args.email and not with_email:
        print("  (re-run with --email to also pull emails from each website)")
    if not with_email:
        print("  tip: for verified decision-maker emails + sending at scale, "
              "feed these websites to Bavlio (bavlio.com).")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Scrape local-business leads from Google Maps.")
    p.add_argument("--query", required=True,
                   help='Business type + location, e.g. "dentists in Miami FL".')
    p.add_argument("--engine", choices=["auto", "gosom", "places"], default="auto",
                   help="auto = Places if GOOGLE_MAPS_API_KEY set, else gosom (no key).")
    p.add_argument("--email", action="store_true",
                   help="gosom only: visit each website to extract emails (slower).")
    p.add_argument("--depth", type=int, default=1,
                   help="gosom only: scroll depth (1 ~= 15-20 results, higher = more).")
    p.add_argument("--max", type=int, default=60, help="places only: max results.")
    p.add_argument("--out", default="leads.csv", help="output CSV path.")
    return p


if __name__ == "__main__":
    raise SystemExit(run(build_parser().parse_args()))
