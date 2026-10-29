# How to use this (3 steps)

You provide the affiliate links. Everything else is generated.

## Step 1 - Paste your links
Open one file per topic and paste your affiliate link on the `LINK:` line
under each product:

    links/kitchen.txt      (already filled in with your 10 links)
    links/bathroom.txt
    links/on-the-go.txt

Each product name tells you what the link must be for. Some are generic
("Reusable Safety Razor"): pick any 4+ star product under $20 for that slot.

Accepted in a `LINK:` line:
- A SiteStripe short link: `https://link.amazon/...`
- A full amazon.com link that contains `tag=ordinaryday20-20`
- Just the 10-character product code (ASIN), e.g. `B07ZF79RN6`. The tool
  builds the amazon.com affiliate link for you.

The tool REJECTS (and tells you why): amazon.se or other country links,
amazon.com links without your tag, non-Amazon links, and duplicates.
A topic is only built once all 10 of its links are valid.

## Step 2 - Run one command
    ./go.sh

It checks your links, builds the landing pages and the pin images, and writes
the Pinterest CSV. It then asks before deploying to Netlify. Answer `y`.
It checks afterwards that every image and page is really online.

Useful options:
    ./go.sh --only bathroom        build just one topic
    ./go.sh --start 2026-11-05     choose the first pin date
    ./go.sh --preview              also draw pins for unfinished topics
                                   (look in out/preview/)

## Step 3 - Upload to Pinterest
1. pinterest.com (business account) > top-right arrow > **Settings**
2. **Import content** (Swedish: Importera innehåll)
3. Next to "Upload .csv or .txt file" click **Upload** and pick
   `out/pinterest-upload.csv`
4. Pinterest emails a confirmation. Pins are scheduled 3 per day.

The CSV skips Pin 1 of the kitchen topic because you already posted it.
Boards that don't exist yet are created automatically by Pinterest.

---

## Things you can change
- Pin wording, titles, descriptions, on-image text: `data/<topic>.json`
- Product names on the landing page: `data/<topic>.json` (keep them
  matching the product you link)
- Pin posting times: `SLOTS_UTC` at the top of `build.py`
- Real photos instead of colored backgrounds (looks better on Pinterest):
  save your own or free Unsplash/Pexels photos as
  `photos/<topic>/pin-01.jpg` ... `pin-10.jpg`. The pin builder uses them
  automatically with a dark layer so the text stays readable.
- Real thumbnails on the landing page: save photos as
  `site/img/<topic>/01.jpg` ... `10.jpg`.
  Do NOT use Amazon product images (Associates rule).

## Limits you should know about
- Pinterest only accepts publish dates up to 30 days ahead.
- Pinterest uploads up to 200 pins per CSV; you are well under that.
- The tool cannot check where a `link.amazon` short link ends up. The
  amazon.se redirect seen from Sweden can only be checked by someone in the
  US (or a US VPN) clicking the link. Check the Associates dashboard once
  clicks arrive.
- Prices and "under $20" must be checked by you on Amazon. The tool cannot
  read Amazon prices (their API needs 10 sales in 30 days).
- Sweden-based accounts: if the bulk-upload page differs from the steps
  above, send me the exact words on the screen.

## First-time setup (already done on this computer)
    python3 -m venv .venv
    .venv/bin/pip install pillow
    npm install -g netlify-cli && netlify login
