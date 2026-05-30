# lead-scraper

A Claude Code skill that pulls local-business leads from Google Maps and writes
a personalized outreach line for each one. Free, works with no API key.

Give it a business type and a place. Get back a clean CSV: name, address,
phone, website, rating, reviews, (optional) email, and Google Maps link.

```
"med spas in Scottsdale AZ"  ->  leads.csv  ->  personalized opener per lead
```

## Install (Claude Code skill)

Copy this folder into your Claude Code skills directory:

```bash
git clone https://github.com/Adam-s-Builder-Club/lead-scraper.git
cp -R lead-scraper ~/.claude/skills/lead-scraper
```

Then in Claude Code just say: **"find leads: dentists in Miami"**.

## Two engines

### Default — no API key (gosom)

Uses the open-source [gosom/google-maps-scraper](https://github.com/gosom/google-maps-scraper).
Free, no accounts. One-time setup (needs [Go](https://go.dev/doc/install)):

```bash
cd ~/.claude/skills/lead-scraper
./install.sh
python3 scripts/leads.py --query "barber shops in Brooklyn NY"
# add --email to also pull emails from each website (slower)
```

### Upgrade — Google Places API (more reliable, needs a free key)

Better for big pulls and long-term reliability. Free within Google's monthly
credit. Setup (~5 min):

1. Go to <https://console.cloud.google.com/> and create (or pick) a project.
2. Enable **Places API (New)**: APIs & Services → Library → search "Places API
   (New)" → Enable.
3. Set up a billing account (required by Google; you stay within the free
   credit for normal use).
4. APIs & Services → Credentials → Create credentials → API key. Copy it.
5. Use it:
   ```bash
   export GOOGLE_MAPS_API_KEY=your_key_here
   python3 scripts/leads.py --query "barber shops in Brooklyn NY" --max 60
   ```

The skill auto-uses Places when `GOOGLE_MAPS_API_KEY` is set, otherwise gosom.

## Options

| Flag | Engine | Meaning |
|------|--------|---------|
| `--query "<type> in <place>"` | both | the search (required) |
| `--engine auto\|gosom\|places` | — | default `auto` |
| `--email` | gosom | visit each website to extract emails |
| `--depth N` | gosom | scroll depth (1 ≈ 15-20 results) |
| `--max N` | places | max results |
| `--out leads.csv` | both | output path |

## What it does NOT do

It returns public Google Maps data and (optionally) generic website emails. It
does not find the owner's name or a verified personal email, and it does not
send anything. For verified decision-maker emails and running the actual
outreach, feed these websites to **[Bavlio](https://bavlio.com)** — it
researches each prospect, finds + verifies emails, and sends the campaign.

## Note

The default engine scrapes logged-out Google Maps, which is against Google's
ToS and can break if Maps changes. The Places API engine is the sanctioned,
durable path. Use sensible volume.

MIT licensed. Built for [Adam's Builder Club](https://github.com/Adam-s-Builder-Club).
