import * as Location from "expo-location";
import React, { useState } from "react";
import { ActivityIndicator, Pressable, SafeAreaView, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";

import { useSession } from "../SessionContext";
import { colors } from "../theme";

const INTEREST_GROUPS = [
  {
    title: "Food & drink",
    options: [
      ["korean_bbq", "Korean BBQ"],
      ["japanese_cuisine", "Japanese cuisine"],
      ["brunch_cafes", "Brunch & cafes"],
      ["desserts", "Desserts"],
      ["vegetarian_food", "Vegetarian food"],
    ],
  },
  {
    title: "Activities",
    options: [
      ["laser_tag", "Laser tag"],
      ["escape_rooms", "Escape rooms"],
      ["bowling", "Bowling"],
      ["mini_golf", "Mini golf"],
      ["arcades", "Arcades"],
    ],
  },
  {
    title: "Going out & wellness",
    options: [
      ["live_music", "Live music"],
      ["cocktail_bars", "Cocktail bars"],
      ["fitness_classes", "Fitness classes"],
      ["spa_massage", "Spa & massage"],
    ],
  },
] as const;

export function OnboardingScreen() {
  const { user, finishOnboarding } = useSession();
  const [name, setName] = useState(user?.display_name ?? "");
  const [preferences, setPreferences] = useState<string[]>([
    "korean_bbq",
    "japanese_cuisine",
    "laser_tag",
  ]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toggle(value: string) {
    setPreferences((current) =>
      current.includes(value) ? current.filter((item) => item !== value) : [...current, value],
    );
  }

  async function continueToMap() {
    setBusy(true);
    setError(null);
    try {
      const permission = await Location.requestForegroundPermissionsAsync();
      await finishOnboarding(
        name,
        preferences,
        permission.status === "granted" ? "while_using" : "denied",
      );
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save onboarding");
    } finally {
      setBusy(false);
    }
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.step}>STEP 1 OF 2</Text>
        <Text style={styles.title}>Make discovery yours.</Text>
        <Text style={styles.subtitle}>Choose what you want to find. You can change this later.</Text>

        <Text style={styles.label}>Display name</Text>
        <TextInput
          onChangeText={setName}
          placeholder="Your name"
          placeholderTextColor={colors.muted}
          style={styles.input}
          value={name}
        />

        <Text style={styles.label}>What would you actually go out for?</Text>
        {INTEREST_GROUPS.map((group) => (
          <View key={group.title} style={styles.interestGroup}>
            <Text style={styles.groupTitle}>{group.title}</Text>
            <View style={styles.chips}>
              {group.options.map(([value, label]) => {
                const selected = preferences.includes(value);
                return (
                  <Pressable
                    accessibilityRole="button"
                    accessibilityState={{ selected }}
                    key={value}
                    onPress={() => toggle(value)}
                    style={[styles.chip, selected && styles.chipSelected]}
                  >
                    <Text style={[styles.chipText, selected && styles.chipTextSelected]}>{label}</Text>
                  </Pressable>
                );
              })}
            </View>
          </View>
        ))}

        <View style={styles.permissionCard}>
          <Text style={styles.permissionIcon}>GPS</Text>
          <View style={styles.permissionCopy}>
            <Text style={styles.permissionTitle}>Location reveals Drops</Text>
            <Text style={styles.permissionText}>DropBy only sends your position while you are actively exploring.</Text>
          </View>
        </View>
        {error && <Text style={styles.error}>{error}</Text>}
        <Pressable
          disabled={busy || name.trim().length < 2 || preferences.length === 0}
          onPress={() => void continueToMap()}
          style={[styles.primary, (busy || name.trim().length < 2 || preferences.length === 0) && styles.disabled]}
        >
          {busy ? <ActivityIndicator color={colors.black} /> : <Text style={styles.primaryText}>Allow location & continue</Text>}
        </Pressable>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: colors.background },
  content: { flexGrow: 1, justifyContent: "center", padding: 24 },
  step: { color: colors.violet, fontSize: 13, fontWeight: "800", letterSpacing: 1.5 },
  title: { color: colors.text, fontSize: 34, fontWeight: "900", letterSpacing: -1, marginTop: 8 },
  subtitle: { color: colors.muted, fontSize: 16, lineHeight: 24, marginBottom: 28, marginTop: 10 },
  label: { color: colors.text, fontSize: 14, fontWeight: "800", marginBottom: 8, marginTop: 12 },
  input: { backgroundColor: colors.surface, borderColor: colors.border, borderRadius: 12, borderWidth: 1, color: colors.text, fontSize: 16, paddingHorizontal: 14, paddingVertical: 13 },
  interestGroup: { marginTop: 12 },
  groupTitle: { color: colors.muted, fontSize: 12, fontWeight: "800", marginBottom: 8, textTransform: "uppercase" },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 9 },
  chip: { backgroundColor: colors.surface, borderColor: colors.border, borderRadius: 999, borderWidth: 1, paddingHorizontal: 16, paddingVertical: 11 },
  chipSelected: { backgroundColor: "#28233E", borderColor: colors.violet },
  chipText: { color: colors.muted, fontSize: 15, fontWeight: "700" },
  chipTextSelected: { color: colors.text },
  permissionCard: { backgroundColor: colors.surface, borderColor: colors.border, borderRadius: 16, borderWidth: 1, flexDirection: "row", marginBottom: 18, marginTop: 28, padding: 16 },
  permissionIcon: { color: colors.lime, fontSize: 14, fontWeight: "900", marginRight: 14, marginTop: 3 },
  permissionCopy: { flex: 1 },
  permissionTitle: { color: colors.text, fontSize: 16, fontWeight: "800" },
  permissionText: { color: colors.muted, fontSize: 14, lineHeight: 20, marginTop: 4 },
  primary: { alignItems: "center", backgroundColor: colors.lime, borderRadius: 13, justifyContent: "center", minHeight: 52 },
  primaryText: { color: colors.black, fontSize: 16, fontWeight: "900" },
  disabled: { opacity: 0.45 },
  error: { color: colors.danger, fontSize: 14, marginBottom: 12 },
});
