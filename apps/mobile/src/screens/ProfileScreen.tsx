import React from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { useSession } from "../SessionContext";
import { API_ORIGIN } from "../services/api";
import { colors, fonts, radius, shadows } from "../theme";

export function ProfileScreen() {
  const { user, logout } = useSession();

  return (
    <ScrollView contentContainerStyle={styles.content} style={styles.page}>
      <View style={styles.avatar}>
        <Text style={styles.avatarText}>{user?.display_name.slice(0, 1).toUpperCase()}</Text>
      </View>
      <Text style={styles.name}>{user?.display_name}</Text>
      <Text style={styles.email}>{user?.email}</Text>

      <View style={styles.card}>
        <Row label="Onboarding" value={user?.onboarding_complete ? "Complete" : "Incomplete"} />
        <Row label="Location" value={user?.location_permission.replace(/_/g, " ") ?? "Unknown"} />
        <Row label="Backend" value={API_ORIGIN} />
      </View>

      <Text style={styles.sectionTitle}>Your interests</Text>
      <View style={styles.tags}>
        {user?.preferences.length ? (
          user.preferences.map((preference) => (
            <View key={preference} style={styles.tag}>
              <Text style={styles.tagText}>{preference.replace(/_/g, " ")}</Text>
            </View>
          ))
        ) : (
          <Text style={styles.empty}>No preferences selected.</Text>
        )}
      </View>

      <Pressable onPress={() => void logout()} style={styles.logoutButton}>
        <Text style={styles.logoutText}>Sign out</Text>
      </Pressable>
    </ScrollView>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.label}>{label}</Text>
      <Text numberOfLines={2} style={styles.value}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  page: { backgroundColor: colors.background },
  content: { alignItems: "center", padding: 20, paddingBottom: 40 },
  avatar: { alignItems: "center", backgroundColor: colors.secondary, borderRadius: 38, height: 76, justifyContent: "center", marginTop: 14, width: 76 },
  avatarText: { color: colors.onPrimary, fontFamily: fonts.display, fontSize: 30 },
  name: { color: colors.secondary, fontFamily: fonts.display, fontSize: 25, marginTop: 13 },
  email: { color: colors.muted, fontFamily: fonts.body, fontSize: 14, marginTop: 4 },
  card: { alignSelf: "stretch", backgroundColor: colors.surface, borderColor: colors.border, borderRadius: radius.lg, borderWidth: 1, marginTop: 25, paddingHorizontal: 16, ...shadows.card },
  row: { alignItems: "center", borderBottomColor: colors.border, borderBottomWidth: StyleSheet.hairlineWidth, flexDirection: "row", justifyContent: "space-between", minHeight: 58 },
  label: { color: colors.muted, fontFamily: fonts.body, fontSize: 13 },
  value: { color: colors.text, flex: 1, fontFamily: fonts.body, fontSize: 13, marginLeft: 16, textAlign: "right", textTransform: "capitalize" },
  sectionTitle: { alignSelf: "stretch", color: colors.text, fontFamily: fonts.display, fontSize: 18, marginTop: 24 },
  tags: { alignSelf: "stretch", flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 12 },
  tag: { backgroundColor: colors.primaryTint, borderRadius: radius.pill, paddingHorizontal: 12, paddingVertical: 7 },
  tagText: { color: colors.primary, fontFamily: fonts.body, fontSize: 12, textTransform: "capitalize" },
  empty: { color: colors.muted, fontFamily: fonts.body, fontSize: 14 },
  logoutButton: { alignItems: "center", alignSelf: "stretch", borderColor: colors.danger, borderRadius: radius.lg, borderWidth: 1, marginTop: 32, paddingVertical: 14 },
  logoutText: { color: colors.danger, fontFamily: fonts.display, fontSize: 14 },
});
