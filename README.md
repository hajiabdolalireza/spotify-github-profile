# spotify-github-profile

Create Spotify now playing card on your github profile

Running on Vercel serverless function, store data in Firebase (store only access_token, refresh_token, token_expired_timestamp)

## Annoucements

**2024-06-21**

Vercel change the package the free tier is not enough for our usage. I moved service to self-host at Digital Ocean.

Please replace your old endpoint `https://spotify-github-profile.vercel.app` to `https://spotify-github-profile.kittinanx.com`

## Table of Contents  
[Connect And Grant Permission](#connect-and-grant-permission)  
[Example](#example)  
[Running for development locally](#running-for-development-locally)  
[Setting up Vercel](#setting-up-vercel)  
[Setting up Firebase](#setting-up-firebase)  
[Setting up Spotify dev](#setting-up-spotify-dev)  
[Running locally](#running-locally)  
[How to Contribute](#how-to-contribute)  
[Known Bugs](#known-bugs)  
[Features in Progress](#features-in-progress)  
[Credit](#credit)  

## Connect And Grant Permission

- Click `Connect with Spotify` button below to grant permission

[<img src="/img/btn-spotify.png">](https://spotify-github-profile.kittinanx.com/api/login)

## Example

- Default theme

![spotify-github-profile](/img/default.svg)

- Compact theme

![spotify-github-profile](/img/compact.svg)

- Natemoo-re theme

![spotify-github-profile](/img/natemoo-re.svg)

- Novatorem theme

![spotify-github-profile](/img/novatorem.svg)

- Karaoke theme

![spotify-github-profile](/img/karaoke.svg)



### Recently Played

Render a list of the last tracks you've listened to:

```
<img src="https://spotify-github-profile.kittinanx.com/api/recently-played?uid=YOUR_SPOTIFY_ID" />
```

Embed directly in your README:

```
![Spotify Recently Played](https://<your-app>.vercel.app/api/recently-played?uid=<YOUR_SPOTIFY_USER>&limit=5)
```

Query parameters:

- `uid` or `user` – Spotify user id. If omitted and only one user token exists in Firestore, that user will be used.
- `limit` – number of tracks to display (1–10, default 5).

Aliases `/api/recently_played` and `/api/recentlyplayed` redirect to the primary `/api/recently-played` endpoint.

### 🎧 Recently Played (Spotify Theme)
![Spotify Recently Played](https://<your-app>.vercel.app/api/recently-played.png?theme=spotify&limit=5)

<details>
<summary>SVG fallback</summary>

![Spotify Recently Played](https://<your-app>.vercel.app/api/recently-played?theme=spotify&limit=5)

</details>

> Note: GitHub blocks external resources inside SVG. Use the PNG endpoint above for reliable rendering.

Optional width in Markdown:

<img src="https://<your-app>.vercel.app/api/recently-played.png?theme=spotify&limit=5" width="720" />

Health check endpoint:

```
GET /api/ping -> {"ok": true, "time": 1234567890, "version": "dev"}
```

## Running for development locally

To develop locally, you need:

- A fork of this project as your repository
- A Vercel project connected with the forked repository
- A Firebase project with Cloud Firestore setup
- A Spotify developer account

### Setting up Vercel

- [Create a new Vercel project by importing](https://vercel.com/import) the forked project on GitHub

### Setting up Firebase

- Create [a new Firebase project](https://console.firebase.google.com/u/0/)
- Create a new Cloud Firestore in the project
- Download configuration JSON file from _Project settings_ > _Service accounts_ > _Generate new private key_
- Convert private key content as BASE64
  - You can use Encode/Decode extension in VSCode to do so
  - This key will be used in step explained below

### Setting up Spotify dev

- Login to [developer.spotify.com](https://developer.spotify.com/dashboard/applications)
- Create a new project
- Edit settings to add _Redirect URIs_
  - add `http://localhost:3000/api/callback`

### Running locally

- Install [Vercel command line](https://vercel.com/download) with `npm i -g vercel`
- Create `.env` file at the root of the project 
- Paste your keys in `SPOTIFY_CLIENT_ID`, `SPOTIFY_SECRET_ID`, and insert the name of your downloaded JSON file in `FIREBASE`


```sh
BASE_URL='http://localhost:3000/api'
SPOTIFY_CLIENT_ID='____'
SPOTIFY_SECRET_ID='____'
FIREBASE='__BASE64_FIREBASE_JSON_FILE__'
```

- Run `vercel dev`

```sh
$ vercel dev
Vercel CLI 20.1.2 dev (beta) — https://vercel.com/feedback
> Ready! Available at http://localhost:3000
```

- Now try to access http://localhost:3000/api/login

### Handy cURL commands

```
curl -i 'https://<app>.vercel.app/api/ping'
curl -i 'https://<app>.vercel.app/api/recently_played?uid=TEST'
curl -i 'https://<app>.vercel.app/api/recently-played?uid=TEST&limit=5'
```

## Troubleshooting

- **404** – verify `vercel.json` rewrites and that the route file is in the deployment output.
- **No logs** – ensure Flask logs to stdout; check Vercel project is not paused; verify requests hit the Python route (try `/api/ping`).
- **Slow/blank images** – check timeouts/retries; GitHub caching via ETag works; try lowering the `limit`.

## How to Contribute

- Develop locally and submit a pull request!
- Submit newly encountered bugs to the [Issues](https://github.com/kittinan/spotify-github-profile/issues) page
- Submit feature suggestions to the [Issues](https://github.com/kittinan/spotify-github-profile/issues) page, with the label [Feature Suggestion]

## Known Bugs

[404/500 Error when playing local files](https://github.com/kittinan/spotify-github-profile/issues/19)

## Other Platforms
- [Apple Music GitHub Profile](https://github.com/rayriffy/apple-music-github-profile)

## Credit

Inspired by https://github.com/natemoo-re
