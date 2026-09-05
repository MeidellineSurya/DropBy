# DropBy mobile demo

This is a working Expo/React Native client for the real-time discovery backend.
It runs on Android or iPhone through Expo Go; generated `android/` and `ios/`
projects are not required for the demo.

## Fastest way to run it on a phone

Requirements: Docker Desktop, Node.js, the Expo Go phone app, and a phone on
the same Wi-Fi network as this computer.

From the repository root, use two Command Prompt windows:

```bat
dev.cmd
```

Wait for the backend to become ready. Then, in the second window:

```bat
mobile.cmd
```

The mobile launcher installs dependencies the first time, detects this
computer's LAN address, creates the untracked `apps\mobile\.env`, and displays
an Expo QR code. Scan the QR code in Expo Go.

If the app says it cannot reach the backend, open `apps\mobile\.env` and make
sure it contains this computer's current Wi-Fi IPv4 address, for example:

```env
EXPO_PUBLIC_API_URL=http://192.168.0.63:8000
```

Restart `mobile.cmd` after changing the file. Windows may also ask you to allow
Node.js and Docker through the private-network firewall.

For an Android emulator, use `http://10.0.2.2:8000`. For an iOS simulator, use
`http://localhost:8000`. Production builds must use an HTTPS backend.

## Demo flow

1. Create a new account in the app and choose onboarding interests.
2. On the discovery screen, press **Detect**, **Reveal**, and **Discover** to
   simulate moving toward the seeded Melbourne Drops.
3. Open a discovered squad Drop and press **Create squad**.
4. Share the squad ID. On a second signed-in phone, press **Discover** for the
   same Drop, paste the ID, and press **Join squad**.
5. Both phones update the squad count in real time through the authenticated
   WebSocket connection.

The seeded `explorer@dropbyapp.com` account is already onboarded, but for a
multi-phone squad demo create a different account on each phone.

## Manual commands

```bat
cd apps\mobile
copy .env.example .env
npm.cmd install
npm.cmd start -- --lan
```

Useful checks:

```bat
npm.cmd run typecheck
npx.cmd expo export --platform android
```

## What this client exercises

- JWT registration, login, stored sessions, and protected API calls
- onboarding preferences and foreground location permission
- a real native map and device GPS
- Detect -> Reveal -> Discover field gating
- discovered Drop markers and details
- squad creation, sharing, joining, leaving, and capacity progress
- authenticated WebSocket updates for Drop stages and squad membership
