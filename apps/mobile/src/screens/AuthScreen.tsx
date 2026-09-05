import React, { useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import { useSession } from "../SessionContext";
import { colors } from "../theme";

export function AuthScreen() {
  const { login, register } = useSession();
  const [creating, setCreating] = useState(false);
  const [email, setEmail] = useState("explorer@dropbyapp.com");
  const [password, setPassword] = useState("dropby12345");
  const [displayName, setDisplayName] = useState("Melbourne Explorer");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      if (creating) {
        await register(email, password, displayName);
      } else {
        await login(email, password);
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not connect");
    } finally {
      setBusy(false);
    }
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={styles.flex}
      >
        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
          <View style={styles.brandMark}><Text style={styles.brandLetter}>D</Text></View>
          <Text style={styles.eyebrow}>DROPBY</Text>
          <Text style={styles.title}>Catch experiences nearby.</Text>
          <Text style={styles.subtitle}>
            Sign in to discover live Drops and assemble a squad.
          </Text>

          <View style={styles.card}>
            <View style={styles.tabs}>
              <Pressable
                accessibilityRole="button"
                onPress={() => setCreating(false)}
                style={[styles.tab, !creating && styles.tabActive]}
              >
                <Text style={[styles.tabText, !creating && styles.tabTextActive]}>Sign in</Text>
              </Pressable>
              <Pressable
                accessibilityRole="button"
                onPress={() => setCreating(true)}
                style={[styles.tab, creating && styles.tabActive]}
              >
                <Text style={[styles.tabText, creating && styles.tabTextActive]}>Create account</Text>
              </Pressable>
            </View>

            {creating && (
              <TextInput
                accessibilityLabel="Display name"
                autoCapitalize="words"
                onChangeText={setDisplayName}
                placeholder="Display name"
                placeholderTextColor={colors.muted}
                style={styles.input}
                value={displayName}
              />
            )}
            <TextInput
              accessibilityLabel="Email"
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="email-address"
              onChangeText={setEmail}
              placeholder="Email"
              placeholderTextColor={colors.muted}
              style={styles.input}
              value={email}
            />
            <TextInput
              accessibilityLabel="Password"
              onChangeText={setPassword}
              placeholder="Password"
              placeholderTextColor={colors.muted}
              secureTextEntry
              style={styles.input}
              value={password}
            />
            {error && <Text style={styles.error}>{error}</Text>}
            <Pressable
              disabled={busy || !email.trim() || password.length < 10}
              onPress={() => void submit()}
              style={({ pressed }) => [
                styles.primary,
                pressed && styles.pressed,
                (busy || !email.trim() || password.length < 10) && styles.disabled,
              ]}
            >
              {busy ? (
                <ActivityIndicator color={colors.black} />
              ) : (
                <Text style={styles.primaryText}>{creating ? "Create account" : "Sign in"}</Text>
              )}
            </Pressable>
          </View>

          <Text style={styles.connection}>Connects to your DropBy backend over JWT-protected REST.</Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  safeArea: { flex: 1, backgroundColor: colors.background },
  content: { flexGrow: 1, justifyContent: "center", padding: 24 },
  brandMark: {
    alignItems: "center", backgroundColor: colors.lime, borderRadius: 16,
    height: 54, justifyContent: "center", marginBottom: 24, transform: [{ rotate: "-5deg" }], width: 54,
  },
  brandLetter: { color: colors.black, fontSize: 28, fontWeight: "900" },
  eyebrow: { color: colors.violet, fontSize: 13, fontWeight: "800", letterSpacing: 2 },
  title: { color: colors.text, fontSize: 36, fontWeight: "900", letterSpacing: -1.2, marginTop: 8 },
  subtitle: { color: colors.muted, fontSize: 17, lineHeight: 25, marginBottom: 28, marginTop: 10 },
  card: { backgroundColor: colors.surface, borderColor: colors.border, borderRadius: 22, borderWidth: 1, padding: 18 },
  tabs: { backgroundColor: colors.background, borderRadius: 12, flexDirection: "row", marginBottom: 16, padding: 4 },
  tab: { alignItems: "center", borderRadius: 9, flex: 1, paddingVertical: 10 },
  tabActive: { backgroundColor: colors.surfaceRaised },
  tabText: { color: colors.muted, fontSize: 14, fontWeight: "700" },
  tabTextActive: { color: colors.text },
  input: { backgroundColor: colors.background, borderColor: colors.border, borderRadius: 12, borderWidth: 1, color: colors.text, fontSize: 16, marginBottom: 10, paddingHorizontal: 14, paddingVertical: 13 },
  error: { color: colors.danger, fontSize: 14, marginBottom: 10 },
  primary: { alignItems: "center", backgroundColor: colors.lime, borderRadius: 12, minHeight: 50, justifyContent: "center", marginTop: 4 },
  primaryText: { color: colors.black, fontSize: 16, fontWeight: "900" },
  pressed: { opacity: 0.82 },
  disabled: { opacity: 0.45 },
  connection: { color: colors.muted, fontSize: 13, lineHeight: 19, marginTop: 18, textAlign: "center" },
});
