# Storyleaf

A self-hosted FreshRSS reader with individual accounts and a visual story interface. Tap a category, explore its ten newest articles in story circles, and swipe through images and short feed excerpts. Each household member signs in to the same Storyleaf address with their own FreshRSS account.

## Household setup / upgrading

On the k3s node, from your existing checkout:

```sh
git pull
bash k8s/deploy.sh
```

Then open your existing **HTTPS** address. The deployment script preserves the separate Ingress and TLS Secret. It adds a 1 GiB persistent volume for account data. This version needs a default StorageClass; see [k3s instructions](k8s/README.md) for diagnostics and optional TLS setup.

Configure only your shared FreshRSS base/API URLs in `.env`. Old `FRESHRSS_USER`, `FRESHRSS_API_PASSWORD`, `APP_USER`, and `APP_PASSWORD` values are ignored; remove them when convenient. No shared account is exposed to unsigned-in visitors.

For every person:

1. Create a separate user in your FreshRSS installation if they do not already have one.
2. Enable FreshRSS API access centrally, and set an API password in that user's profile.
3. Open Storyleaf and enter that user's FreshRSS username and **API password**, not their usual web-login password.
4. Their categories, articles, bookmarks, selected category, and viewed-story markers belong to that account.

## Persistent login and privacy

- A random HttpOnly, Secure, SameSite=Strict cookie keeps a device signed in for up to 30 days. It is a fixed expiry, not an indefinite login. Logging out invalidates that session and clears the account's displayed content.
- Sessions survive pod restarts when `/data` is mounted persistently. The browser holds only an opaque session token; the server stores its hash and the upstream FreshRSS authentication token. API passwords are used for login and are not written to the database.
- Bookmarks, preferences, and viewed-story markers are stored server-side per FreshRSS identity. They sync between devices signed into the same account. The browser does not store new feed content in local storage. A harmless session-change signal makes other tabs refresh authentication when accounts change.
- The old shared browser-local bookmark cache is no longer read or automatically assigned to any user. It is left untouched for manual recovery. Old saves do not appear automatically in the new per-account collection.
- The SQLite file is permission-restricted, but not encrypted. It contains sensitive upstream authentication tokens and saved feed data. Treat volume backups as private. The app's server administrator can access this storage.
- Each read request uses the authenticated user's upstream token, never a username from the browser or old environment credentials. Same-origin checks, custom request headers, bounded requests, and basic login throttling protect authentication and preference mutations.
- FreshRSS access revocation is detected on upstream API requests; the app then invalidates the session and asks the user to sign in again. Session deletion is available through logout.
- This is a household deployment, not a hardened public multi-tenant SaaS. Keep a single replica for its SQLite/local-volume design. No cookies or passwords are sent to feed image hosts.

## Docker / Podman Compose

Copy `.env.example` to `.env` and configure the FreshRSS API URL, then:

```sh
podman-compose up -d --build
```

Compose persists data in the `storyleaf-data` volume and enables Secure cookies. Put it behind HTTPS to sign in. For **local Python-only HTTP development**:

```sh
COOKIE_SECURE=false python server.py
```

Open `http://localhost:8080`. Do not disable Secure cookies for the normal HTTPS installation. Compose and k3s explicitly enable them. HTTP NodePort 30088 still serves public static assets, but signed-in use requires HTTPS.

## Reader features

- Categories are FreshRSS folders. The upstream API filters the selected category before returning up to ten newest entries, including read and unread articles.
- A story is a feed image, source, headline, and up to roughly 560 characters of plain feed text. Swipe, arrow keys, or buttons move between articles. Original-source links remain available.
- The API's `summary.content` can be full article text; excerpts are shortened at a word boundary and are not claimed to be generated TL;DRs.
- Images come from feed image enclosures or HTML images. Relative URLs are resolved against the article URL. Missing/broken images use decorative artwork. The app does not scrape publisher pages or generate pictures.
- A fictional, clearly labelled demo is available without signing in. No FreshRSS feeds are fetched for demo visitors.
- No Ollama, cloud AI, analytics, external fonts, or database service is needed. SQLite is part of Python.
- The app does not modify FreshRSS read/unread or starred state. A live connection is needed; offline article reading and background sync are not implemented.

## iPhone and Android

Open your HTTPS URL and add the app to your home screen. Apple touch icons and Android PNG icons are included. Persistent cookies work in the app's browser context; reinstalling a shortcut or clearing website data may require signing in again. Home-network-only deployments need home Wi-Fi or a suitable private VPN.

## Checks

```sh
python -m unittest discover -s tests -v
node --check public/app.js
```

Tests cover two-account isolation, per-account preferences, stale-account writes, session expiry and persistence, cookie security, password non-storage, logout, origin validation, login throttling, and rejection of legacy shared credentials. Browser checks with mock FreshRSS accounts cover login, saved-story separation, account switching, and reload persistence. The actual household FreshRSS accounts and cluster volume provisioning still need verification after deployment.

References: [FreshRSS API](https://freshrss.github.io/FreshRSS/en/developers/06_GoogleReader_API.html), [k3s deployment](k8s/README.md).
