import React, { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import { SafeAreaView, useSafeAreaInsets } from "react-native-safe-area-context";
import { WebView } from "react-native-webview";

const DEMO_HTML = require("../../api/demo/mobile.html");

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
    // Keep this asynchronous so Retry can reset the same loading flow.
    Promise.resolve(DEMO_HTML)
      .then((source) => { if (typeof source !== "string") throw new Error("Bundled demo is invalid"); if (active) setHtml(source); })
      .catch(() => { if (active) setFailed(true); });
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
