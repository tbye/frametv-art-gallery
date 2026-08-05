<p align="center">
    <picture>
      <img alt="Header" width="500" src="https://raw.githubusercontent.com/mrtncode/frametv-art-gallery/refs/heads/main/docs/header_dark.png" >
      <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/mrtncode/frametv-art-gallery/refs/heads/main/docs/header_light.png">
    </picture>
</p>


# frametv-art-gallery

[![Release](https://img.shields.io/github/v/release/mrtncode/frametv-art-gallery)](https://github.com/mrtncode/frametv-art-gallery/releases/latest) 
[![Build](https://github.com/mrtncode/frametv-art-gallery/actions/workflows/build_image.yaml/badge.svg)](https://github.com/mrtncode/frametv-art-gallery/actions/workflows/build_image.yaml) 
[![License](https://img.shields.io/github/license/mrtncode/frametv-art-gallery)](https://github.com/mrtncode/frametv-art-gallery/blob/main/LICENSE) 
[![Python](https://img.shields.io/badge/python-%3E%3D3.11-blue)](https://www.python.org/) 
[![Stars](https://img.shields.io/github/stars/mrtncode/frametv-art-gallery?style=social)](https://github.com/mrtncode/frametv-art-gallery/stargazers)

frametv-art-gallery is an independent, open-source, self-hosted gallery manager for Samsung Frame TVs. Not affiliated with Samsung. It lets you create and manage a personal gallery of images, photos, or artworks locally on your TV.


## Disclaimer

frametv-art-gallery is an unofficial, fun, open-source project and is **not affiliated with, endorsed by, or sponsored by Samsung** (or any other company). It is provided "as is" and use is entirely at your own risk. 

This project uses local websocket APIs provided by the TVs.

> ⚠️ **Security Warning:** This application does **not** implement authentication, authorization, or other hardening controls. It is intended for **private, local network use only**.
>
> - Do **not** expose this service to the public internet.
> - Do **not** run it on a publicly reachable IP/host without adding your own security layer (VPN, reverse proxy auth, firewall rules, etc.).
> - If you want to access it remotely, put it behind a secure tunnel or VPN and ensure only trusted devices can reach it.

> ⚠️ **No Warranty and Liability:** The author assumes **no liability** for any damages, data loss, device malfunction, or any other issues that may arise from using this application. You use frametv-art-gallery **entirely at your own risk**. The software is provided without any warranties, express or implied. 
>
> **Always create backups of your data before updating** to a new version. While we strive to maintain compatibility, updates may introduce breaking changes or require data migrations. You are responsible for ensuring you have a complete backup of your uploads and database before proceeding with any update.


## Images
You can use any kind of image! Either upload your own personal photos or import them from Immich. Or download copyright-free artwork from the internet and import it into Frame TV Gallery.

### Screenshots
<p align="center">
  <img alt="Screenshot 1" src="docs/Screenshot1.png" width="300" />
  <img alt="Screenshot 2" src="docs/Screenshot2.png" width="300" />
  <img alt="Screenshot 3" src="docs/Screenshot3.png" width="300" />
</p>
Example images from https://pixabay.com/

## tbye's changes

This fork ([tbye/frametv-art-gallery](https://github.com/tbye/frametv-art-gallery)) includes practical fixes and add-ons found while running the app against Immich and a local Docker setup. Upstream project: [mrtncode/frametv-art-gallery](https://github.com/mrtncode/frametv-art-gallery).

### Docker: build the frontend in the image
Local `docker compose build` previously produced a working API but **404 on `/`**, because the Dockerfile never built the React app. Official CI builds the UI *before* `docker build`; a plain local build did not.

- Multi-stage `Dockerfile`: **pnpm** installs the latest stable Node (**LTS** via `pnpm runtime set node lts`); project deps still use **npm** + `package-lock.json` (`npm ci` + `npm run build`)
- Runtime image overlays `frontend/build` so Flask can serve the SPA from `frontend/build/client`
- `docker-compose.yml` uses `build: .` and image tag `frametv-art-gallery:local`
- Host `frontend/build/` is ignored via `.dockerignore` so only the image-built UI is used

### Immich / external provider
Gallery load called `/api/provider/albums` on every visit. With Immich enabled, that path crashed and returned HTML 500s, which the frontend tried to parse as JSON (`Unexpected token '<'...`).

- Updated `ImmichProvider` for **aioimmich ≥ 0.16** (`async_setup()`, album images via search API, safer session cleanup)
- Provider API errors now return **JSON** (e.g. 502) instead of Flask HTML error pages
- Immich is treated as **optional** in the gallery UI: provider failures no longer block the local gallery or show a red error under the upload form

### HEIC / HEIF uploads
Phone photos are often HEIC. The app only accepted PNG/JPEG, and browsers don’t reliably display HEIC.

- Accepts `.heic` / `.heif` uploads
- Converts them server-side to **lossless PNG** (best quality among formats already supported by the gallery and Frame TV art mode)
- Applies EXIF orientation so phone photos aren’t rotated wrong
- Adds `pillow-heif` dependency; UI file picker and drop zone accept HEIC (including empty MIME types in Chromium)

### Frame TV aspect ratio
Non‑16:9 images (especially portraits) were **stretched** on the TV. Frame art mode fills 16:9 and distorts anything else.

- On **Upload to TV**, non‑16:9 images are letterboxed/pillarboxed onto a **3840×2160** canvas (black bars, aspect preserved)
- Gallery originals are **not** modified—only the TV upload is padded
- Already 16:9 images skip padding
- Optional override: `"preserve_aspect_ratio": false` on `/api/tv/send`
- UI thumbnails use `object-contain` more consistently so previews don’t crop awkwardly

### Quick local run (this fork)

```bash
docker compose build
docker compose up -d
# open http://localhost:8000
```

# Installation


## Docker
docker volume create frametv_uploads
docker volume create frametv_db

docker run -d \
  --name frametv \
  -v frametv_uploads:/app/uploads \
  -v frametv_db:/app/instance \
  -p 8000:8000 \
  frametvartgallery:latest

Or use the docker-compose.yml file: https://github.com/mrtncode/frametv-art-gallery/blob/main/docker-compose.yml

# Update
## Docker (docker run)
Pull the latest image and restart the container while keeping your data (persists in volumes)

Docker Compose (recommended):
1. `docker compose pull`
2. `docker compose up -d`

# Troubleshooting
## Errors when uploading images to the TV:

-> Check that the TV is on and has enough free storage space. When the storage space for art images is full, the upload fails. 

-> Try uploading an image with the SmartThings App. There will appear a more specific error message.


## The TV keeps asking for permission when uploading an image

Some TVs are asking for permission every time, to avoid this, go to:

Device Connection Manager > Access Notification Settings > First Time Only


# Techstack
Frontend:
- React.js
- TailwindCSS
- Shadcn/ui
- Lottie Animation 

https://lottiefiles.com/free-animation/image-VXYNYReCmq -> Thanks!

Backend:
- Flask (Python)

# Credits
Speical thanks to https://github.com/xchwarze/samsung-tv-ws-api and https://github.com/billyfw/frame-art-shuffler  
