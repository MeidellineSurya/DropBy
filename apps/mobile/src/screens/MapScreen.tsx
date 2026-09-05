import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import * as Location from "expo-location";
import React, { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import MapView, { Circle, Marker, type Region } from "react-native-maps";

import { useSession } from "../SessionContext";
import type { RootStackParamList } from "../navigation/RootNavigator";
import { api, API_ORIGIN } from "../services/api";
import { connectLiveSocket } from "../services/ws";
import { colors } from "../theme";
import type { DropSnapshot, DropStageEvent } from "../types";

type Props = NativeStackScreenProps<RootStackParamList, "Discover">;
type Coordinate = { latitude: number; longitude: number };

const MELBOURNE: Region = {
  latitude: -37.8119,
  longitude: 144.9674,
  latitudeDelta: 0.018,
  longitudeDelta: 0.018,
};

const TEST_POSITIONS = [
  ["Detect", -37.8074, 144.9674],
  ["Reveal", -37.81055, 144.9674],
  ["Discover", -37.81145, 144.9674],
] as const;

const stageColor = {
  detect: colors.violet,
  reveal: colors.cyan,
  discover: colors.lime,
};

export function MapScreen({ navigation }: Props) {
  const { token, user } = useSession();
  const [coordinate, setCoordinate] = useState<Coordinate | null>(null);
  const [drops, setDrops] = useState<DropSnapshot[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [socketConnected, setSocketConnected] = useState(false);
  const [groupId, setGroupId] = useState("");
  const [joining, setJoining] = useState(false);

  const discoveredDrops = useMemo(
    () => drops.filter((drop) => drop.latitude != null && drop.longitude != null),
    [drops],
  );

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

  async function ping(position: Coordinate) {
    setLoading(true);
    setError(null);
    setCoordinate(position);
    try {
      const response = await api.locationPing(position.latitude, position.longitude);
      setDrops(response.drops);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load nearby Drops");
    } finally {
      setLoading(false);
    }
  }

  async function useCurrentLocation() {
    const permission = await Location.requestForegroundPermissionsAsync();
    if (permission.status !== "granted") {
      setError("Location permission is required to discover nearby Drops.");
      return;
    }
    const location = await Location.getCurrentPositionAsync({
      accuracy: Location.Accuracy.Balanced,
    });
    await ping({
      latitude: location.coords.latitude,
      longitude: location.coords.longitude,
    });
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

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <View style={styles.header}>
          <View>
            <Text style={styles.eyebrow}>LIVE DISCOVERY</Text>
            <Text style={styles.title}>Nearby Drops</Text>
            <Text style={styles.greeting}>Hey {user?.display_name.split(" ")[0]}</Text>
          </View>
          <Pressable onPress={() => navigation.navigate("Profile")} style={styles.avatar}>
            <Text style={styles.avatarText}>{user?.display_name.slice(0, 1).toUpperCase()}</Text>
          </Pressable>
        </View>

        <View style={styles.connectionRow}>
          <View style={[styles.dot, socketConnected && styles.dotLive]} />
          <Text style={styles.connectionText}>
            {socketConnected ? "Live updates connected" : "Connecting live updates"}
          </Text>
          <Text numberOfLines={1} style={styles.host}>
            {API_ORIGIN.replace(/^https?:\/\//, "")}
          </Text>
        </View>

        <View style={styles.mapFrame}>
          <MapView
            initialRegion={MELBOURNE}
            region={
              coordinate
                ? { ...coordinate, latitudeDelta: 0.012, longitudeDelta: 0.012 }
                : undefined
            }
            style={styles.map}
          >
            {coordinate && <Marker coordinate={coordinate} pinColor="#367DFF" title="You" />}
            {coordinate && (
              <Circle
                center={coordinate}
                fillColor="#9B87FF12"
                radius={700}
                strokeColor="#9B87FF99"
              />
            )}
            {discoveredDrops.map((drop) => (
              <Marker
                coordinate={{ latitude: drop.latitude!, longitude: drop.longitude! }}
                description={drop.business_name}
                key={drop.id}
                pinColor={colors.lime}
                title={drop.title}
              />
            ))}
          </MapView>
          {loading && (
            <View style={styles.mapLoading}>
              <ActivityIndicator color={colors.lime} />
            </View>
          )}
        </View>

        <Pressable onPress={() => void useCurrentLocation()} style={styles.locationButton}>
          <Text style={styles.locationButtonText}>Use my current location</Text>
        </Pressable>

        <Text style={styles.testLabel}>MELBOURNE DEMO POSITIONS</Text>
        <View style={styles.testRow}>
          {TEST_POSITIONS.map(([label, latitude, longitude]) => (
            <Pressable
              key={label}
              onPress={() => void ping({ latitude, longitude })}
              style={styles.testButton}
            >
              <Text style={styles.testButtonText}>{label}</Text>
            </Pressable>
          ))}
        </View>

        <View style={styles.joinCard}>
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
              <ActivityIndicator color={colors.black} />
            ) : (
              <Text style={styles.joinButtonText}>Join squad</Text>
            )}
          </Pressable>
        </View>

        {error && <Text style={styles.error}>{error}</Text>}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>
            {drops.length
              ? `${drops.length} signal${drops.length === 1 ? "" : "s"}`
              : "No signals yet"}
          </Text>
          <Text style={styles.sectionHint}>Move closer to reveal more</Text>
        </View>

        {drops.map((drop) => {
          const title = drop.title ?? (drop.category ? drop.category.replace(/_/g, " ") : "Mystery Drop");
          return (
            <Pressable
              key={drop.id}
              onPress={() => navigation.navigate("DropDetail", { drop })}
              style={styles.dropCard}
            >
              <View style={[styles.signal, { backgroundColor: stageColor[drop.stage] }]}>
                <Text style={styles.signalText}>{drop.stage === "discover" ? "OK" : "?"}</Text>
              </View>
              <View style={styles.dropCopy}>
                <Text style={styles.dropStage}>
                  {drop.stage.toUpperCase()} · {drop.distance_m} M
                </Text>
                <Text style={styles.dropTitle}>{title}</Text>
                <Text style={styles.dropMeta}>
                  {drop.business_name ?? drop.rarity ?? "Details hidden"}
                </Text>
              </View>
              <Text style={styles.chevron}>›</Text>
            </Pressable>
          );
        })}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { backgroundColor: colors.background, flex: 1 },
  content: { paddingBottom: 36 },
  header: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", paddingHorizontal: 20, paddingTop: 18 },
  eyebrow: { color: colors.violet, fontSize: 12, fontWeight: "900", letterSpacing: 1.6 },
  title: { color: colors.text, fontSize: 32, fontWeight: "900", letterSpacing: -1, marginTop: 3 },
  greeting: { color: colors.muted, fontSize: 14, marginTop: 3 },
  avatar: { alignItems: "center", backgroundColor: colors.lime, borderRadius: 20, height: 40, justifyContent: "center", width: 40 },
  avatarText: { color: colors.black, fontSize: 17, fontWeight: "900" },
  connectionRow: { alignItems: "center", flexDirection: "row", marginHorizontal: 20, marginVertical: 14 },
  dot: { backgroundColor: colors.muted, borderRadius: 4, height: 8, marginRight: 7, width: 8 },
  dotLive: { backgroundColor: colors.cyan },
  connectionText: { color: colors.muted, fontSize: 13 },
  host: { color: colors.muted, flex: 1, fontSize: 11, marginLeft: 8, textAlign: "right" },
  mapFrame: { borderColor: colors.border, borderRadius: 22, borderWidth: 1, marginHorizontal: 14, overflow: "hidden" },
  map: { height: 300, width: "100%" },
  mapLoading: { alignItems: "center", backgroundColor: "#090B0FAA", bottom: 0, justifyContent: "center", left: 0, position: "absolute", right: 0, top: 0 },
  locationButton: { alignItems: "center", backgroundColor: colors.lime, borderRadius: 13, marginHorizontal: 20, marginTop: 14, paddingVertical: 14 },
  locationButtonText: { color: colors.black, fontSize: 15, fontWeight: "900" },
  testLabel: { color: colors.muted, fontSize: 11, fontWeight: "800", letterSpacing: 1.2, marginHorizontal: 20, marginTop: 20 },
  testRow: { flexDirection: "row", gap: 8, marginHorizontal: 20, marginTop: 9 },
  testButton: { alignItems: "center", backgroundColor: colors.surface, borderColor: colors.border, borderRadius: 10, borderWidth: 1, flex: 1, paddingVertical: 11 },
  testButtonText: { color: colors.text, fontSize: 13, fontWeight: "700" },
  joinCard: { alignItems: "center", backgroundColor: colors.surface, borderColor: colors.border, borderRadius: 14, borderWidth: 1, flexDirection: "row", gap: 8, marginHorizontal: 20, marginTop: 14, padding: 10 },
  joinInput: { backgroundColor: colors.background, borderColor: colors.border, borderRadius: 9, borderWidth: 1, color: colors.text, flex: 1, fontSize: 13, minWidth: 0, paddingHorizontal: 11, paddingVertical: 10 },
  joinButton: { alignItems: "center", backgroundColor: colors.lime, borderRadius: 9, justifyContent: "center", minHeight: 40, minWidth: 94, paddingHorizontal: 12 },
  joinButtonText: { color: colors.black, fontSize: 13, fontWeight: "900" },
  disabled: { opacity: 0.45 },
  error: { color: colors.danger, fontSize: 14, marginHorizontal: 20, marginTop: 14 },
  sectionHeader: { alignItems: "flex-end", flexDirection: "row", justifyContent: "space-between", marginHorizontal: 20, marginBottom: 10, marginTop: 24 },
  sectionTitle: { color: colors.text, fontSize: 20, fontWeight: "900" },
  sectionHint: { color: colors.muted, fontSize: 12 },
  dropCard: { alignItems: "center", backgroundColor: colors.surface, borderColor: colors.border, borderRadius: 16, borderWidth: 1, flexDirection: "row", marginBottom: 10, marginHorizontal: 20, padding: 14 },
  signal: { alignItems: "center", borderRadius: 22, height: 44, justifyContent: "center", width: 44 },
  signalText: { color: colors.black, fontSize: 14, fontWeight: "900" },
  dropCopy: { flex: 1, marginLeft: 12 },
  dropStage: { color: colors.muted, fontSize: 11, fontWeight: "800", letterSpacing: 0.8 },
  dropTitle: { color: colors.text, fontSize: 17, fontWeight: "800", marginTop: 3, textTransform: "capitalize" },
  dropMeta: { color: colors.muted, fontSize: 13, marginTop: 3, textTransform: "capitalize" },
  chevron: { color: colors.muted, fontSize: 30, marginLeft: 8 },
});
