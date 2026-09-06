import React, { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import * as Location from "expo-location";
import { SafeAreaView, useSafeAreaInsets } from "react-native-safe-area-context";
import { WebView } from "react-native-webview";

const DEMO_HTML = require("../../api/demo/mobile.html");
const API_ORIGIN = (process.env.EXPO_PUBLIC_API_URL ?? "").replace(/\/$/, "");
const HOME_TIMER_INJECTION = `
  (function () {
    var homeEndsAt = Date.now() + (28 * 60 + 19) * 1000;
    var dropEndsAt = Date.now() + (24 * 60 + 39) * 1000;
    function format(endsAt) {
      var seconds = Math.max(0, Math.ceil((endsAt - Date.now()) / 1000));
      return String(Math.floor(seconds / 60)).padStart(2, "0") + ":" + String(seconds % 60).padStart(2, "0");
    }
    function updateClock() {
      var homeElement = document.getElementById("homeClock");
      var exploreElement = document.getElementById("exploreTimeLeft");
      if (homeElement) homeElement.textContent = format(homeEndsAt);
      if (exploreElement) exploreElement.textContent = format(dropEndsAt);
    }
    updateClock();
    window.setInterval(updateClock, 1000);
  })();
  true;
`;

/**
 * Expo Go shell for the browser frontend used by mobile.cmd. The HTML is a
 * bundled local asset, so the phone and browser use the same source file.
 */
export function BrowserDemoApp() {
  const insets = useSafeAreaInsets();
  const [failed, setFailed] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const [html, setHtml] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setHtml(null);
    setFailed(false);
    // The HTML demo owns its map UI, while Expo supplies the real iPhone
    // location. If permission is declined it retains its Melbourne fallback.
    void (async () => {
      let startLocation: { latitude: number; longitude: number } | null = null;
      try {
        const permission = await Location.requestForegroundPermissionsAsync();
        if (permission.status === "granted") {
          const position = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
          startLocation = { latitude: position.coords.latitude, longitude: position.coords.longitude };
        }
      } catch {
        // The bundled demo has a deliberate fallback for offline simulators.
      }
      const source = DEMO_HTML.replace(
        "<head>",
        `<head><script>window.__DROPBY_API_ORIGIN=${JSON.stringify(API_ORIGIN)};window.__DROPBY_START_LOCATION=${JSON.stringify(startLocation)};</script>`,
      );
      if (typeof source !== "string") throw new Error("Bundled demo is invalid");
      if (active) setHtml(source);
    })().catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [reloadKey]);

  if (failed) {
    return (
      <SafeAreaView style={styles.errorPage}>
        <Text style={styles.errorTitle}>Couldn’t load the DropBy demo</Text>
        <Text style={styles.errorBody}>Restart Expo, then try again.</Text>
        <Pressable onPress={() => setReloadKey((value) => value + 1)} style={styles.retry}>
          <Text style={styles.retryText}>Retry</Text>
        </Pressable>
      </SafeAreaView>
    );
  }

  if (!html) return <SafeAreaView edges={[]} style={[styles.safeArea, { paddingTop: insets.top }]}><View style={styles.loading}><ActivityIndicator color="#D9FF43" size="large" /></View></SafeAreaView>;

  return (
    <SafeAreaView
      edges={[]}
      style={[styles.safeArea, { paddingBottom: insets.bottom, paddingTop: insets.top }]}
    >
      <WebView
        cacheEnabled={false}
        javaScriptEnabled
        key={reloadKey}
        onError={() => setFailed(true)}
        injectedJavaScript={HOME_TIMER_INJECTION}
        originWhitelist={["*"]}
        renderLoading={() => (
          <View style={styles.loading}>
            <ActivityIndicator color="#D9FF43" size="large" />
          </View>
        )}
        source={{ html }}
        style={styles.webview}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { backgroundColor: "#090B0F", flex: 1 },
  webview: { backgroundColor: "#090B0F", flex: 1 },
  loading: { alignItems: "center", backgroundColor: "#090B0F", flex: 1, justifyContent: "center" },
  errorPage: { alignItems: "center", backgroundColor: "#090B0F", flex: 1, justifyContent: "center", padding: 28 },
  errorTitle: { color: "#F5F7FB", fontSize: 22, fontWeight: "800", textAlign: "center" },
  errorBody: { color: "#A8B0C0", fontSize: 16, lineHeight: 23, marginTop: 10, textAlign: "center" },
  retry: { backgroundColor: "#D9FF43", borderRadius: 14, marginTop: 24, paddingHorizontal: 24, paddingVertical: 13 },
  retryText: { color: "#090B0F", fontSize: 16, fontWeight: "800" },
});
