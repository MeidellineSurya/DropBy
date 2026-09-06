import { Ionicons } from "@expo/vector-icons";
import type { BottomTabScreenProps } from "@react-navigation/bottom-tabs";
import type { CompositeScreenProps } from "@react-navigation/native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import * as Location from "expo-location";
import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import MapView, { Circle, Marker, type Region } from "react-native-maps";

import { useSession } from "../SessionContext";
import type { MainTabParamList, RootStackParamList } from "../navigation/RootNavigator";
import { api } from "../services/api";
import { connectLiveSocket } from "../services/ws";
import { colors, fonts, radius, shadows } from "../theme";
import type { DropSnapshot, DropStageEvent } from "../types";

type Props = CompositeScreenProps<
  BottomTabScreenProps<MainTabParamList, "Explore">,
  NativeStackScreenProps<RootStackParamList>
>;
type Coordinate = { latitude: number; longitude: number };
type LocationMode = "off" | "live" | "demo";

const MELBOURNE: Region = {
  latitude: -37.8119,
  longitude: 144.9674,
  latitudeDelta: 0.018,
  longitudeDelta: 0.018,
};

const TEST_POSITIONS = [
  ["Detect", -37.8074, 144.9674],
  ["Reveal", -37.81105, 144.9674],
] as const;

const stageColor = {
  detect: colors.info,
  reveal: colors.secondary,
};

export function MapScreen({ navigation }: Props) {
  const { token } = useSession();
  const insets = useSafeAreaInsets();
  const [coordinate, setCoordinate] = useState<Coordinate | null>(null);
  const [drops, setDrops] = useState<DropSnapshot[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [socketConnected, setSocketConnected] = useState(false);
  const [groupId, setGroupId] = useState("");
  const [joining, setJoining] = useState(false);
  const [locationMode, setLocationMode] = useState<LocationMode>("off");
  const [countdown, setCountdown] = useState(28 * 60 + 19);
  const watchPingRunning = useRef(false);
  const pingSequence = useRef(0);
  const loadingSequence = useRef(0);

  const revealedDrops = useMemo(
    () => drops.filter((drop) => drop.latitude != null && drop.longitude != null),
    [drops],
  );
  const nearest = useMemo(() => [...drops].sort((a, b) => a.distance_m - b.distance_m)[0], [drops]);

  // TODO(api): drive this from nearest.ends_at once the backend returns it consistently.
  useEffect(() => {
    const timer = setInterval(() => setCountdown((value) => (value > 0 ? value - 1 : 0)), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!token) return;
    const socket = connectLiveSocket(
      token,
      (event) => {
        if (event.type !== "drop.stage_update") return;
        const update = event as DropStageEvent;
        setDrops((current) => {
          const next = current.filter((drop) => drop.id !== update.drop_id);
          return [...next, update.data].sort((a, b) => a.distance_m - b.distance_m);
        });
      },
      setSocketConnected,
    );
    return () => socket.close();
  }, [token]);

  useEffect(() => {
    let mounted = true;
    void Location.getForegroundPermissionsAsync().then((permission) => {
      if (mounted && permission.status === "granted") setLocationMode("live");
    });
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (locationMode !== "live") return;
    let mounted = true;
    let subscription: Location.LocationSubscription | null = null;

    void (async () => {
      const permission = await Location.getForegroundPermissionsAsync();
      if (!mounted) return;
      if (permission.status !== "granted") {
        setLocationMode("off");
        setError("Location permission is required to discover nearby Drops.");
        return;
      }
      subscription = await Location.watchPositionAsync(
        {
          accuracy: Location.Accuracy.High,
          distanceInterval: 10,
          timeInterval: 5000,
          mayShowUserSettingsDialog: true,
        },
        (location) => {
          if (!mounted || watchPingRunning.current) return;
          watchPingRunning.current = true;
          void ping(
            {
              latitude: location.coords.latitude,
              longitude: location.coords.longitude,
            },
            false,
          ).finally(() => {
            watchPingRunning.current = false;
          });
        },
        (message) => {
          if (mounted) setError(message);
        },
      );
    })();

    return () => {
      mounted = false;
      subscription?.remove();
      watchPingRunning.current = false;
    };
  }, [locationMode]);

  async function ping(position: Coordinate, showLoading = true) {
    const sequence = ++pingSequence.current;
    if (showLoading) {
      loadingSequence.current = sequence;
      setLoading(true);
    }
    setError(null);
    setCoordinate(position);
    try {
      const response = await api.locationPing(position.latitude, position.longitude);
      if (sequence !== pingSequence.current) return;
      setDrops(response.drops);
    } catch (reason) {
      if (sequence !== pingSequence.current) return;
      setError(reason instanceof Error ? reason.message : "Could not load nearby Drops");
    } finally {
      if (showLoading && sequence === loadingSequence.current) setLoading(false);
    }
  }

  async function enableLiveTracking() {
    const permission = await Location.requestForegroundPermissionsAsync();
    if (permission.status !== "granted") {
      setError("Location permission is required to discover nearby Drops.");
      return;
    }
    const location = await Location.getCurrentPositionAsync({
      accuracy: Location.Accuracy.High,
    });
    await ping({
      latitude: location.coords.latitude,
      longitude: location.coords.longitude,
    });
    setLocationMode("live");
  }

  async function joinSquad() {
    if (!groupId.trim()) return;
    setJoining(true);
    setError(null);
    try {
      const group = await api.joinGroup(groupId.trim());
      setGroupId("");
      navigation.navigate("Squad", { groupId: group.id });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not join that squad");
    } finally {
      setJoining(false);
    }
  }

  const clock = `${String(Math.floor(countdown / 60)).padStart(2, "0")}:${String(countdown % 60).padStart(2, "0")}`;

  return (
    <View style={styles.root}>
      <MapView
        initialRegion={MELBOURNE}
        region={
          coordinate ? { ...coordinate, latitudeDelta: 0.012, longitudeDelta: 0.012 } : undefined
        }
        style={styles.map}
      >
        {coordinate && <Marker coordinate={coordinate} pinColor={colors.secondary} title="You" />}
        {coordinate && (
          <Circle
            center={coordinate}
            fillColor="rgba(224,82,110,0.10)"
            radius={700}
            strokeColor="rgba(224,82,110,0.60)"
          />
        )}
        {revealedDrops.map((drop) => (
          <Marker
            coordinate={{ latitude: drop.latitude!, longitude: drop.longitude! }}
            description={drop.business_name}
            key={drop.id}
            pinColor={colors.primary}
            title={drop.title}
          />
        ))}
      </MapView>

      <View style={[styles.livePill, { top: insets.top + 12 }]}>
        <View style={[styles.liveDot, socketConnected && styles.liveDotOn]} />
        <Text style={styles.livePillText}>
          {drops.length} drop{drops.length === 1 ? "" : "s"} live
        </Text>
        {loading && <ActivityIndicator color={colors.secondary} size="small" />}
      </View>

      <View style={styles.sheet}>
        <View style={styles.handle} />
        <ScrollView
          contentContainerStyle={styles.sheetContent}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          {nearest ? (
            <View style={styles.hero}>
              <View style={styles.heroTop}>
                <Text style={styles.eyebrow}>LIVE NEAR YOU</Text>
                <Text style={styles.clock}>{clock}</Text>
              </View>
              <Text style={styles.heroTitle}>DROP NEARBY</Text>
              <MetaRow
                icon="walk"
                text={`${nearest.distance_m}m (${Math.max(1, Math.round(nearest.distance_m / 80))} min walk)`}
              />
              <MetaRow
                icon="pricetag"
                text={(nearest.interest_tag ?? nearest.category ?? "surprise").replace(/_/g, " ")}
              />
              <MetaRow icon="people" text={`Min. squad of ${nearest.min_group_size ?? 1}`} />
              <Pressable
                onPress={() => navigation.navigate("DropDetail", { drop: nearest })}
                style={styles.hunt}
              >
                <Text style={styles.huntText}>HUNT</Text>
              </Pressable>
            </View>
          ) : (
            <View style={styles.hero}>
              <Text style={styles.heroTitle}>NO DROPS YET</Text>
              <Text style={styles.emptyText}>
                Turn on location or tap a demo position to reveal nearby Drops.
              </Text>
            </View>
          )}

          {error && <Text style={styles.error}>{error}</Text>}

          {drops.length > 0 && (
            <>
              <Text style={styles.sectionTitle}>
                {drops.length} signal{drops.length === 1 ? "" : "s"}
              </Text>
              {drops.map((drop) => {
                const title =
                  drop.title ?? drop.interest_tag?.replace(/_/g, " ") ?? "Mystery Drop";
                return (
                  <Pressable
                    key={drop.id}
                    onPress={() => navigation.navigate("DropDetail", { drop })}
                    style={styles.dropCard}
                  >
                    <View style={[styles.signal, { backgroundColor: stageColor[drop.stage] }]}>
                      <Ionicons
                        color={colors.onPrimary}
                        name={drop.stage === "reveal" ? "checkmark" : "help"}
                        size={18}
                      />
                    </View>
                    <View style={styles.dropCopy}>
                      <Text style={styles.dropStage}>
                        {drop.stage.toUpperCase()} · {drop.distance_m} M
                      </Text>
                      <Text style={styles.dropTitle}>{title}</Text>
                      <Text style={styles.dropMeta}>
                        {drop.business_name ??
                          `${drop.rarity ?? "common"} · min ${drop.min_group_size ?? 1}`}
                      </Text>
                    </View>
                    <Ionicons color={colors.muted} name="chevron-forward" size={20} />
                  </Pressable>
                );
              })}
            </>
          )}

          <Text style={styles.sectionTitle}>Location</Text>
          <Pressable
            onPress={() => {
              if (locationMode === "live") setLocationMode("off");
              else void enableLiveTracking();
            }}
            style={[styles.controlButton, locationMode === "live" && styles.controlButtonActive]}
          >
            <Ionicons
              color={locationMode === "live" ? colors.primary : colors.onPrimary}
              name={locationMode === "live" ? "pause" : "navigate"}
              size={16}
            />
            <Text
              style={[
                styles.controlButtonText,
                locationMode === "live" && styles.controlButtonTextActive,
              ]}
            >
              {locationMode === "live" ? "Pause continuous tracking" : "Enable continuous location"}
            </Text>
          </Pressable>

          <View style={styles.demoRow}>
            {TEST_POSITIONS.map(([label, latitude, longitude]) => (
              <Pressable
                key={label}
                onPress={() => {
                  setLocationMode("demo");
                  void ping({ latitude, longitude });
                }}
                style={styles.demoButton}
              >
                <Text style={styles.demoButtonText}>{label}</Text>
              </Pressable>
            ))}
          </View>

          <View style={styles.joinRow}>
            <TextInput
              autoCapitalize="none"
              autoCorrect={false}
              onChangeText={setGroupId}
              placeholder="Paste a squad ID"
              placeholderTextColor={colors.muted}
              style={styles.joinInput}
              value={groupId}
            />
            <Pressable
              disabled={!groupId.trim() || joining}
              onPress={() => void joinSquad()}
              style={[styles.joinButton, (!groupId.trim() || joining) && styles.disabled]}
            >
              {joining ? (
                <ActivityIndicator color={colors.onPrimary} />
              ) : (
                <Text style={styles.joinButtonText}>Join</Text>
              )}
            </Pressable>
          </View>
        </ScrollView>
      </View>
    </View>
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
  root: { backgroundColor: colors.surfaceInverse, flex: 1 },
  map: { bottom: 0, left: 0, position: "absolute", right: 0, top: 0 },
  livePill: {
    alignItems: "center",
    alignSelf: "center",
    backgroundColor: colors.secondaryTint,
    borderRadius: radius.pill,
    flexDirection: "row",
    gap: 8,
    paddingHorizontal: 16,
    paddingVertical: 10,
    position: "absolute",
    ...shadows.card,
  },
  liveDot: { backgroundColor: colors.muted, borderRadius: 4, height: 8, width: 8 },
  liveDotOn: { backgroundColor: colors.secondary },
  livePillText: { color: colors.secondary, fontFamily: fonts.display, fontSize: 13 },
  sheet: {
    backgroundColor: colors.background,
    borderTopLeftRadius: radius.xl,
    borderTopRightRadius: radius.xl,
    bottom: 0,
    left: 0,
    maxHeight: "64%",
    position: "absolute",
    right: 0,
    ...shadows.card,
  },
  handle: {
    alignSelf: "center",
    backgroundColor: colors.border,
    borderRadius: 3,
    height: 5,
    marginTop: 10,
    width: 44,
  },
  sheetContent: { padding: 20, paddingBottom: 120 },
  hero: { marginBottom: 8 },
  heroTop: { alignItems: "center", flexDirection: "row", justifyContent: "space-between" },
  eyebrow: { color: colors.subtle, fontFamily: fonts.display, fontSize: 10, letterSpacing: 0.5 },
  clock: { color: colors.subtle, fontFamily: fonts.body, fontSize: 12 },
  heroTitle: { color: colors.text, fontFamily: fonts.display, fontSize: 24, marginTop: 4 },
  metaRow: { alignItems: "center", flexDirection: "row", gap: 8, marginTop: 8 },
  metaText: { color: colors.subtle, fontFamily: fonts.body, fontSize: 12, textTransform: "capitalize" },
  emptyText: { color: colors.subtle, fontFamily: fonts.body, fontSize: 13, lineHeight: 18, marginTop: 6 },
  hunt: {
    alignItems: "center",
    alignSelf: "flex-start",
    backgroundColor: colors.primary,
    borderRadius: radius.xxl,
    marginTop: 16,
    paddingHorizontal: 32,
    paddingVertical: 12,
  },
  huntText: { color: colors.onPrimary, fontFamily: fonts.display, fontSize: 14 },
  error: { color: colors.danger, fontFamily: fonts.body, fontSize: 13, marginTop: 12 },
  sectionTitle: { color: colors.text, fontFamily: fonts.display, fontSize: 16, marginBottom: 8, marginTop: 22 },
  dropCard: {
    alignItems: "center",
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexDirection: "row",
    marginBottom: 10,
    padding: 14,
    ...shadows.card,
  },
  signal: { alignItems: "center", borderRadius: radius.pill, height: 44, justifyContent: "center", width: 44 },
  dropCopy: { flex: 1, marginLeft: 12 },
  dropStage: { color: colors.muted, fontFamily: fonts.display, fontSize: 11, letterSpacing: 0.8 },
  dropTitle: { color: colors.text, fontFamily: fonts.display, fontSize: 17, marginTop: 3, textTransform: "capitalize" },
  dropMeta: { color: colors.muted, fontFamily: fonts.body, fontSize: 13, marginTop: 3, textTransform: "capitalize" },
  controlButton: {
    alignItems: "center",
    backgroundColor: colors.primary,
    borderRadius: radius.lg,
    flexDirection: "row",
    gap: 8,
    justifyContent: "center",
    paddingVertical: 14,
  },
  controlButtonActive: { backgroundColor: colors.surface, borderColor: colors.primary, borderWidth: 1 },
  controlButtonText: { color: colors.onPrimary, fontFamily: fonts.display, fontSize: 14 },
  controlButtonTextActive: { color: colors.primary },
  demoRow: { flexDirection: "row", gap: 8, marginTop: 10 },
  demoButton: {
    alignItems: "center",
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.sm,
    borderWidth: 1,
    flex: 1,
    paddingVertical: 11,
  },
  demoButtonText: { color: colors.text, fontFamily: fonts.body, fontSize: 13 },
  joinRow: {
    alignItems: "center",
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexDirection: "row",
    gap: 8,
    marginTop: 10,
    padding: 10,
    ...shadows.card,
  },
  joinInput: {
    backgroundColor: colors.background,
    borderColor: colors.border,
    borderRadius: radius.sm,
    borderWidth: 1,
    color: colors.text,
    flex: 1,
    fontFamily: fonts.body,
    fontSize: 13,
    minWidth: 0,
    paddingHorizontal: 11,
    paddingVertical: 10,
  },
  joinButton: {
    alignItems: "center",
    backgroundColor: colors.primary,
    borderRadius: radius.sm,
    justifyContent: "center",
    minHeight: 40,
    minWidth: 70,
    paddingHorizontal: 12,
  },
  joinButtonText: { color: colors.onPrimary, fontFamily: fonts.display, fontSize: 13 },
  disabled: { opacity: 0.45 },
});
