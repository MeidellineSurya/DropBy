import { Ionicons } from "@expo/vector-icons";
import type { BottomTabScreenProps } from "@react-navigation/bottom-tabs";
import type { CompositeScreenProps } from "@react-navigation/native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import React, { useEffect, useMemo, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import MapView, { Marker, type Region } from "react-native-maps";

import { useSession } from "../SessionContext";
import { api } from "../services/api";
import { colors, fonts, radius, shadows } from "../theme";
import type { DropSnapshot } from "../types";
import type { MainTabParamList, RootStackParamList } from "../navigation/RootNavigator";

type Props = CompositeScreenProps<
  BottomTabScreenProps<MainTabParamList, "Home">,
  NativeStackScreenProps<RootStackParamList>
>;

const MELBOURNE: Region = {
  latitude: -37.8119,
  longitude: 144.9674,
  latitudeDelta: 0.02,
  longitudeDelta: 0.02,
};

// TODO(api): streak + weekly challenge have no backend yet — mocked for the UI.
const MOCK_STREAK = 15;
const MOCK_CHALLENGE = { label: "Catch 3 Food Drops for bonus XP", done: 1, target: 3, reward: 50 };

export function HomeScreen({ navigation }: Props) {
  const { user } = useSession();
  const [drops, setDrops] = useState<DropSnapshot[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    void api
      .locationPing(MELBOURNE.latitude, MELBOURNE.longitude)
      .then((response) => {
        if (active) setDrops(response.drops);
      })
      .catch(() => undefined)
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const nearest = useMemo(
    () => [...drops].sort((a, b) => a.distance_m - b.distance_m)[0],
    [drops],
  );
  const mapped = useMemo(
    () => drops.filter((drop) => drop.latitude != null && drop.longitude != null),
    [drops],
  );
  const firstName = user?.display_name.split(" ")[0] ?? "there";
  const challengePct = `${Math.round((MOCK_CHALLENGE.done / MOCK_CHALLENGE.target) * 100)}%` as const;

  return (
    <ScrollView contentContainerStyle={styles.content} style={styles.page}>
      <View style={styles.topRow}>
        <View style={styles.wordmark}>
          <Text style={styles.wordmarkDrop}>DROP</Text>
          <Ionicons color={colors.primary} name="location" size={18} style={styles.wordmarkPin} />
          <Text style={styles.wordmarkBy}>BY</Text>
        </View>
        <View style={styles.streak}>
          <Ionicons color={colors.warning} name="flame" size={16} />
          <Text style={styles.streakText}>{MOCK_STREAK}</Text>
        </View>
      </View>

      <Text style={styles.greeting}>HEY {firstName.toUpperCase()},</Text>
      <Text style={styles.prompt}>What are you up to today?</Text>

      <View style={styles.challengeCard}>
        <Text style={styles.challengeLabel}>THIS WEEK&apos;S CHALLENGE</Text>
        <Text style={styles.challengeBody}>{MOCK_CHALLENGE.label}</Text>
        <View style={styles.progressTrack}>
          <View style={[styles.progressFill, { width: challengePct }]} />
        </View>
        <View style={styles.challengeFooter}>
          <Text style={styles.challengeCount}>
            {MOCK_CHALLENGE.done}/{MOCK_CHALLENGE.target} caught
          </Text>
          <Pressable disabled style={[styles.claimButton, styles.claimDisabled]}>
            <Text style={styles.claimText}>CLAIM +{MOCK_CHALLENGE.reward} XP</Text>
          </Pressable>
        </View>
      </View>

      <View style={styles.dropCard}>
        <View style={styles.mapWrap} pointerEvents="none">
          <MapView initialRegion={MELBOURNE} style={styles.map}>
            {mapped.map((drop) => (
              <Marker
                coordinate={{ latitude: drop.latitude!, longitude: drop.longitude! }}
                key={drop.id}
                pinColor={drop.stage === "reveal" ? colors.secondary : colors.primary}
              />
            ))}
          </MapView>
          {loading && (
            <View style={styles.mapLoading}>
              <ActivityIndicator color={colors.primary} />
            </View>
          )}
        </View>

        {nearest ? (
          <View style={styles.dropBody}>
            <Text style={styles.liveLabel}>LIVE NEAR YOU</Text>
            <Text style={styles.dropTitle}>DROP NEARBY</Text>
            <MetaRow icon="walk" text={`${nearest.distance_m}m away`} />
            <MetaRow
              icon="restaurant"
              text={(nearest.interest_tag ?? nearest.category ?? "surprise").replace(/_/g, " ")}
            />
            <MetaRow icon="people" text={`Min. squad of ${nearest.min_group_size ?? 1}`} />
            <Pressable
              onPress={() => navigation.navigate("DropDetail", { drop: nearest })}
              style={styles.huntButton}
            >
              <Text style={styles.huntText}>HUNT</Text>
            </Pressable>
          </View>
        ) : (
          <View style={styles.dropBody}>
            <Text style={styles.dropTitle}>NO DROPS NEARBY</Text>
            <Text style={styles.emptyText}>Head to Explore and move around to reveal Drops.</Text>
            <Pressable onPress={() => navigation.navigate("Explore")} style={styles.huntButton}>
              <Text style={styles.huntText}>OPEN MAP</Text>
            </Pressable>
          </View>
        )}
      </View>
    </ScrollView>
  );
}

function MetaRow({ icon, text }: { icon: keyof typeof Ionicons.glyphMap; text: string }) {
  return (
    <View style={styles.metaRow}>
      <Ionicons color={colors.subtle} name={icon} size={14} />
      <Text style={styles.metaText}>{text}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  page: { backgroundColor: colors.background },
  content: { padding: 20, paddingBottom: 32 },
  topRow: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", paddingTop: 8 },
  wordmark: { alignItems: "center", flexDirection: "row" },
  wordmarkDrop: { color: colors.primary, fontFamily: fonts.display, fontSize: 22 },
  wordmarkPin: { marginHorizontal: 1 },
  wordmarkBy: { color: colors.text, fontFamily: fonts.display, fontSize: 22 },
  streak: {
    alignItems: "center",
    backgroundColor: colors.warningTint,
    borderRadius: radius.pill,
    flexDirection: "row",
    gap: 4,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  streakText: { color: colors.warning, fontFamily: fonts.display, fontSize: 13 },
  greeting: { color: colors.secondary, fontFamily: fonts.display, fontSize: 30, marginTop: 22 },
  prompt: { color: colors.text, fontFamily: fonts.body, fontSize: 16, marginTop: 4 },
  challengeCard: {
    backgroundColor: colors.secondaryTint,
    borderRadius: radius.lg,
    marginTop: 22,
    padding: 16,
  },
  challengeLabel: { color: colors.secondary, fontFamily: fonts.display, fontSize: 11, letterSpacing: 0.5 },
  challengeBody: { color: colors.text, fontFamily: fonts.body, fontSize: 14, marginTop: 6 },
  progressTrack: {
    backgroundColor: colors.surface,
    borderRadius: 5,
    height: 10,
    marginTop: 12,
    overflow: "hidden",
  },
  progressFill: { backgroundColor: colors.secondary, borderRadius: 5, height: "100%" },
  challengeFooter: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: 12,
  },
  challengeCount: { color: colors.subtle, fontFamily: fonts.body, fontSize: 12 },
  claimButton: {
    backgroundColor: colors.primary,
    borderRadius: radius.pill,
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  claimDisabled: { opacity: 0.45 },
  claimText: { color: colors.onPrimary, fontFamily: fonts.display, fontSize: 12 },
  dropCard: {
    backgroundColor: colors.surface,
    borderRadius: radius.xl,
    marginTop: 18,
    overflow: "hidden",
    ...shadows.card,
  },
  mapWrap: { height: 200, position: "relative" },
  map: { bottom: 0, left: 0, position: "absolute", right: 0, top: 0 },
  mapLoading: {
    alignItems: "center",
    backgroundColor: colors.overlay,
    bottom: 0,
    justifyContent: "center",
    left: 0,
    position: "absolute",
    right: 0,
    top: 0,
  },
  dropBody: { padding: 18 },
  liveLabel: { color: colors.subtle, fontFamily: fonts.display, fontSize: 10, letterSpacing: 0.5 },
  dropTitle: { color: colors.text, fontFamily: fonts.display, fontSize: 24, marginTop: 4 },
  emptyText: { color: colors.subtle, fontFamily: fonts.body, fontSize: 13, lineHeight: 18, marginTop: 6 },
  metaRow: { alignItems: "center", flexDirection: "row", gap: 8, marginTop: 8 },
  metaText: { color: colors.subtle, fontFamily: fonts.body, fontSize: 12, textTransform: "capitalize" },
  huntButton: {
    alignItems: "center",
    alignSelf: "flex-start",
    backgroundColor: colors.primary,
    borderRadius: radius.xxl,
    marginTop: 16,
    paddingHorizontal: 32,
    paddingVertical: 12,
  },
  huntText: { color: colors.onPrimary, fontFamily: fonts.display, fontSize: 14 },
});
