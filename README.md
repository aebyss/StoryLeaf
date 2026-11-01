# Storyleaf

A self-hosted FreshRSS reader with category selection and a visual story interface. Tap a category chip such as DevOps or Tech, see its ten newest entries in the circular stories row, and swipe through their pictures, headlines, and short feed excerpts. Viewed stories have muted rings. The home screen keeps a compact header without a hero banner. Keeps the original warm palette and serif headlines. No Ollama, LLM, model download, Python packages, or database required.

## Start

1. Copy `.env.example` to `.env`.
2. In FreshRSS, enable API access under Administration → Authentication. Set a separate API password in your user profile. Copy the exact API address from the profile into `FRESHRSS_API_URL`; fill in `FRESHRSS_USER` and `FRESHRSS_API_PASSWORD`.
3. Run:

```sh
podman-compose up -d --build
```

Docker Compose also works: `docker compose up -d --build`.

Open `http://YOUR_SERVER_IP:8088`. Without FreshRSS credentials, the app shows a clearly labelled fictional demo library. The demo has fewer than ten stories; live categories show up to ten entries when available.

## Updating the earlier Ollama version

Keep your existing `.env`. Stop the old project before replacing its files:

```sh
cd ~/Storyleaf
podman-compose down
```

If the new ZIP is saved as `~/storyleaf.zip`, extract it into a temporary directory and copy its files into your existing checkout:

```sh
mkdir -p /tmp/storyleaf-update
unzip -o ~/storyleaf.zip -d /tmp/storyleaf-update
cp -a /tmp/storyleaf-update/storyleaf/. ~/Storyleaf/
cd ~/Storyleaf
podman-compose up -d --build --force-recreate
```

The archive does not include `.env` or any Git metadata. Existing credentials remain intact. `OLLAMA_URL`, `OLLAMA_MODEL`, `STORY_LANGUAGE`, and `DATA_PATH` are no longer used and may be removed from `.env`. Old named volumes are not deleted; the new version does not use them. The bundled Ollama service is removed from Compose. Your separate Ollama server is unaffected.

## How stories work

- Categories come from FreshRSS’s Google Reader-compatible tag list, selecting folders rather than user tags. Older servers without type markers expose their labels.
- FreshRSS filters by category **before** returning the ten most recent entries. This is not client-side filtering of a limited global list. Entries include both read and unread articles in FreshRSS’s newest-first stream order.
- Each article is one full-screen story: image, headline, source, and up to roughly 560 characters of preview text. Swipe or use the arrow buttons/keyboard to move between articles. “Read stories” starts with the first visible article.
- The API’s `summary.content` is feed content, not a guaranteed generated TL;DR. We strip HTML and shorten it at a word boundary. The interface labels it “Feed excerpt” rather than claiming it is an AI summary. A publisher-provided summary is used when that is what the feed supplies; otherwise the opening article text is used.
- Images come from image enclosures or HTML images in the feed. Relative URLs are resolved against the article. Missing/broken images use decorative artwork. We do not scrape publishers’ pages or generate pictures. Remote images load directly in the browser and may be blocked by publisher rules or browser mixed-content restrictions; the fallback remains available.
- Bookmarks and selected category stay in this browser’s local storage. Bookmarks do not sync to FreshRSS or other devices. Original article links remain available.

## Mobile use and access

Use Safari on Apple devices or Chrome on Android. For home-screen installation, serve the app over HTTPS through your reverse proxy or private VPN setup; browser support and icon presentation vary. This is a responsive web app, not an App Store or Play Store binary. A live connection is required; offline reading and background refresh are not implemented.

Your FreshRSS address `192.168.178.53` is reachable only on your LAN or an appropriate VPN. Keep credentials server-side in `.env`; never commit that file. Set both `APP_USER` and `APP_PASSWORD` to require app login. Use HTTPS outside a trusted LAN. API calls do not change FreshRSS’s read/unread or starred state.

## Checks

```sh
python -m unittest discover -s tests -v
node --check public/app.js
```

Tests cover upstream category filtering, request encoding, newest-first limits, feed text/image extraction, missing content, authentication, and removal of the Ollama endpoint. The demo was checked in a browser for category switching, circular story selection, and next-story navigation. Live FreshRSS connectivity and mobile-device rendering still need verification on your network.

For logs: `podman logs --tail 50 storyleaf_storyleaf_1`. For a connection error, verify the exact API URL, API password, and Docker/Podman network access to FreshRSS.

API references: [FreshRSS API](https://freshrss.github.io/FreshRSS/en/developers/06_GoogleReader_API.html), [FreshRSS implementation](https://github.com/FreshRSS/FreshRSS/blob/edge/p/api/greader.php).
