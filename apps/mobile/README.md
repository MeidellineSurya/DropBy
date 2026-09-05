# DropBy mobile (React Native)

This is a JS-layer skeleton only — the native `ios/`/`android/` projects
haven't been generated yet. Before running on a device/simulator:

```
npx react-native@0.75.4 init DropByNative --skip-install
# then copy the generated ios/ and android/ folders into this directory,
# and point them at this package.json / src/ instead of the generated app.
```

or use `npx react-native-community/cli init` per the current React Native docs,
since native project generation depends on the exact RN/Xcode/Android SDK
versions in use at build time and shouldn't be hand-written.

## Structure
- `src/screens/` — Map (live Drops), DropDetail, Squad, Redeem/QRScan, Profile
- `src/navigation/` — React Navigation stack
- `src/services/` — REST client + WebSocket client (consumes `@dropby/shared-types`)
- `src/components/` — shared UI (DropPin, RarityBadge, SquadProgress, CountdownTimer)
