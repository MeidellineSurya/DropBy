import React from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { useSession } from "../SessionContext";
import { API_ORIGIN } from "../services/api";
import { colors } from "../theme";

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
  avatar: { alignItems: "center", backgroundColor: colors.lime, borderRadius: 38, height: 76, justifyContent: "center", marginTop: 14, width: 76 },
  avatarText: { color: colors.black, fontSize: 30, fontWeight: "900" },
  name: { color: colors.text, fontSize: 25, fontWeight: "900", marginTop: 13 },
  email: { color: colors.muted, fontSize: 14, marginTop: 4 },
  card: { alignSelf: "stretch", backgroundColor: colors.surface, borderColor: colors.border, borderRadius: 17, borderWidth: 1, marginTop: 25, paddingHorizontal: 16 },
  row: { alignItems: "center", borderBottomColor: colors.border, borderBottomWidth: StyleSheet.hairlineWidth, flexDirection: "row", justifyContent: "space-between", minHeight: 58 },
  label: { color: colors.muted, fontSize: 13 },
  value: { color: colors.text, flex: 1, fontSize: 13, fontWeight: "700", marginLeft: 16, textAlign: "right", textTransform: "capitalize" },
  sectionTitle: { alignSelf: "stretch", color: colors.text, fontSize: 18, fontWeight: "900", marginTop: 24 },
  tags: { alignSelf: "stretch", flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 12 },
  tag: { backgroundColor: colors.surfaceRaised, borderColor: colors.violet, borderRadius: 99, borderWidth: 1, paddingHorizontal: 12, paddingVertical: 7 },
  tagText: { color: colors.text, fontSize: 12, textTransform: "capitalize" },
  empty: { color: colors.muted, fontSize: 14 },
  logoutButton: { alignItems: "center", alignSelf: "stretch", borderColor: colors.danger, borderRadius: 12, borderWidth: 1, marginTop: 32, paddingVertical: 14 },
  logoutText: { color: colors.danger, fontSize: 14, fontWeight: "800" },
});
