import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import * as Location from "expo-location";
import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  Share,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { useSession } from "../SessionContext";
import type { RootStackParamList } from "../navigation/RootNavigator";
import { api } from "../services/api";
import { connectLiveSocket } from "../services/ws";
import { colors } from "../theme";
import type { GroupEvent, GroupSnapshot, RedemptionEvent } from "../types";

type Props = NativeStackScreenProps<RootStackParamList, "Squad">;

export function SquadScreen({ navigation, route }: Props) {
  const { token } = useSession();
  const { groupId } = route.params;
  const [group, setGroup] = useState<GroupSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [leaving, setLeaving] = useState(false);
  const [claiming, setClaiming] = useState(false);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setGroup(await api.getGroup(groupId));
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load this squad");
    } finally {
      setLoading(false);
    }
  }, [groupId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (!token) return;
    const socket = connectLiveSocket(
      token,
      (event) => {
        // redemption.* covers check-in/confirm — check-in auto-confirms now
        // (see api/app/services/redemption.py), so this is what tells other
        // squad members the Drop was redeemed without them tapping anything.
        if (!event.type.startsWith("group.") && !event.type.startsWith("redemption.")) return;
        if ((event as GroupEvent | RedemptionEvent).group_id === groupId) void refresh();
      },
      setConnected,
    );
    return () => socket.close();
  }, [groupId, refresh, token]);

  async function shareSquad() {
    await Share.share({
      message: `Join my DropBy squad. Open DropBy and paste this squad ID: ${groupId}`,
      title: "Join my DropBy squad",
    });
  }

  async function claimDrop() {
    setClaiming(true);
    setError(null);
    try {
      // Check-in is a location claim, not a QR scan — freshen the server's
      // record of where we are right before claiming, so a stale location
      // from minutes ago (or from before this screen was even opened)
      // doesn't fail the venue-proximity check.
      const permission = await Location.requestForegroundPermissionsAsync();
      if (permission.status !== "granted") {
        setError("Location permission is required to check in.");
        return;
      }
      const location = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.High,
      });
      await api.locationPing(location.coords.latitude, location.coords.longitude);
      await api.checkIn(groupId);
      await refresh();
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Could not check in — move closer to the venue and try again.",
      );
    } finally {
      setClaiming(false);
    }
  }

  async function leaveSquad() {
    setLeaving(true);
    setError(null);
    try {
      await api.leaveGroup(groupId);
      navigation.popTo("Discover");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not leave this squad");
      setLeaving(false);
    }
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.lime} size="large" />
      </View>
    );
  }

  const count = group?.current_count ?? 0;
  const maximum = group?.max_allowed ?? 4;
  const progress = `${Math.min(100, Math.round((count / maximum) * 100))}%` as const;
  const ready = group?.status === "ready";
  const completed = group?.status === "completed";

  const eyebrow = completed ? "REDEEMED" : ready ? "SQUAD READY" : "ASSEMBLING";
  const subtitle = completed
    ? "Checked in and redeemed — XP is on its way to everyone in the squad."
    : ready
      ? "Your minimum squad is ready. You can still fill the remaining spaces."
      : `${Math.max(0, (group?.min_required ?? 2) - count)} more needed to unlock the Drop.`;

  return (
    <ScrollView contentContainerStyle={styles.content} style={styles.page}>
      <View style={styles.liveRow}>
        <View style={[styles.dot, connected && styles.dotLive]} />
        <Text style={styles.liveText}>{connected ? "Live squad updates" : "Reconnecting"}</Text>
      </View>

      <Text style={styles.eyebrow}>{eyebrow}</Text>
      <Text style={styles.title}>{count}/{maximum} explorers</Text>
      <Text style={styles.subtitle}>{subtitle}</Text>

      <View style={styles.progressTrack}>
        <View style={[styles.progressFill, { width: progress }]} />
      </View>

      {ready && (
        <View style={styles.claimCard}>
          <Text style={styles.claimTitle}>At the venue?</Text>
          <Text style={styles.claimSubtitle}>
            Check in once you've arrived — we'll confirm you're close enough, no
            code to scan.
          </Text>
          <Pressable
            disabled={claiming}
            onPress={() => void claimDrop()}
            style={styles.claimButton}
          >
            {claiming ? (
              <ActivityIndicator color={colors.black} />
            ) : (
              <Text style={styles.claimButtonText}>Check in now</Text>
            )}
          </Pressable>
        </View>
      )}

      {completed && (
        <View style={styles.successCard}>
          <Text style={styles.successText}>
            ✓ Redeemed! Everyone in the squad earns XP for this one.
          </Text>
        </View>
      )}

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Members</Text>
        {group?.members.map((member) => (
          <View key={member.user_id} style={styles.memberRow}>
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>{member.display_name.slice(0, 1).toUpperCase()}</Text>
            </View>
            <View style={styles.memberCopy}>
              <Text style={styles.memberName}>{member.display_name}</Text>
              <Text style={styles.memberRole}>{member.role}</Text>
            </View>
            <Text style={styles.joined}>Joined</Text>
          </View>
        ))}
        {Array.from({ length: Math.max(0, maximum - count) }).map((_, index) => (
          <View key={`open-${index}`} style={styles.memberRow}>
            <View style={styles.emptyAvatar}><Text style={styles.emptyAvatarText}>+</Text></View>
            <Text style={styles.openSlot}>Open spot</Text>
          </View>
        ))}
      </View>

      {!completed && (
        <View style={styles.codeCard}>
          <Text style={styles.codeLabel}>SQUAD ID</Text>
          <Text selectable style={styles.code}>{groupId}</Text>
          <Pressable onPress={() => void shareSquad()} style={styles.primaryButton}>
            <Text style={styles.primaryButtonText}>Share squad invite</Text>
          </Pressable>
        </View>
      )}

      <Pressable onPress={() => void refresh()} style={styles.secondaryButton}>
        <Text style={styles.secondaryButtonText}>Refresh now</Text>
      </Pressable>
      {!completed && (
        <Pressable disabled={leaving} onPress={() => void leaveSquad()} style={styles.leaveButton}>
          {leaving ? (
            <ActivityIndicator color={colors.danger} />
          ) : (
            <Text style={styles.leaveText}>Leave squad</Text>
          )}
        </Pressable>
      )}
      {error && <Text style={styles.error}>{error}</Text>}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { backgroundColor: colors.background },
  content: { padding: 20, paddingBottom: 40 },
  center: { alignItems: "center", backgroundColor: colors.background, flex: 1, justifyContent: "center" },
  liveRow: { alignItems: "center", flexDirection: "row" },
  dot: { backgroundColor: colors.muted, borderRadius: 4, height: 8, marginRight: 7, width: 8 },
  dotLive: { backgroundColor: colors.cyan },
  liveText: { color: colors.muted, fontSize: 13 },
  eyebrow: { color: colors.lime, fontSize: 12, fontWeight: "900", letterSpacing: 1.4, marginTop: 24 },
  title: { color: colors.text, fontSize: 38, fontWeight: "900", letterSpacing: -1, marginTop: 4 },
  subtitle: { color: colors.muted, fontSize: 15, lineHeight: 22, marginTop: 8 },
  progressTrack: { backgroundColor: colors.surfaceRaised, borderRadius: 5, height: 10, marginTop: 22, overflow: "hidden" },
  progressFill: { backgroundColor: colors.lime, borderRadius: 5, height: "100%" },
  claimCard: { backgroundColor: colors.surfaceRaised, borderColor: colors.lime, borderRadius: 18, borderWidth: 1, marginTop: 18, padding: 16 },
  claimTitle: { color: colors.text, fontSize: 17, fontWeight: "900" },
  claimSubtitle: { color: colors.muted, fontSize: 13, lineHeight: 19, marginTop: 6 },
  claimButton: { alignItems: "center", backgroundColor: colors.lime, borderRadius: 11, marginTop: 14, paddingVertical: 14 },
  claimButtonText: { color: colors.black, fontSize: 14, fontWeight: "900" },
  successCard: { backgroundColor: colors.surfaceRaised, borderColor: colors.lime, borderRadius: 18, borderWidth: 1, marginTop: 18, padding: 16 },
  successText: { color: colors.text, fontSize: 14, lineHeight: 20, fontWeight: "700" },
  card: { backgroundColor: colors.surface, borderColor: colors.border, borderRadius: 18, borderWidth: 1, marginTop: 22, padding: 16 },
  cardTitle: { color: colors.text, fontSize: 18, fontWeight: "900", marginBottom: 8 },
  memberRow: { alignItems: "center", borderBottomColor: colors.border, borderBottomWidth: StyleSheet.hairlineWidth, flexDirection: "row", minHeight: 60 },
  avatar: { alignItems: "center", backgroundColor: colors.violet, borderRadius: 18, height: 36, justifyContent: "center", width: 36 },
  avatarText: { color: colors.black, fontSize: 14, fontWeight: "900" },
  emptyAvatar: { alignItems: "center", borderColor: colors.border, borderRadius: 18, borderStyle: "dashed", borderWidth: 1, height: 36, justifyContent: "center", width: 36 },
  emptyAvatarText: { color: colors.muted, fontSize: 20 },
  memberCopy: { flex: 1, marginLeft: 11 },
  memberName: { color: colors.text, fontSize: 15, fontWeight: "700" },
  memberRole: { color: colors.muted, fontSize: 12, marginTop: 2, textTransform: "capitalize" },
  joined: { color: colors.cyan, fontSize: 12, fontWeight: "700" },
  openSlot: { color: colors.muted, fontSize: 14, marginLeft: 11 },
  codeCard: { backgroundColor: colors.surfaceRaised, borderRadius: 16, marginTop: 16, padding: 16 },
  codeLabel: { color: colors.muted, fontSize: 11, fontWeight: "900", letterSpacing: 1 },
  code: { color: colors.text, fontSize: 13, marginTop: 7 },
  primaryButton: { alignItems: "center", backgroundColor: colors.lime, borderRadius: 11, marginTop: 15, paddingVertical: 14 },
  primaryButtonText: { color: colors.black, fontSize: 14, fontWeight: "900" },
  secondaryButton: { alignItems: "center", borderColor: colors.border, borderRadius: 11, borderWidth: 1, marginTop: 15, paddingVertical: 13 },
  secondaryButtonText: { color: colors.text, fontSize: 14, fontWeight: "700" },
  leaveButton: { alignItems: "center", minHeight: 46, justifyContent: "center", marginTop: 7 },
  leaveText: { color: colors.danger, fontSize: 14, fontWeight: "700" },
  error: { color: colors.danger, fontSize: 14, marginTop: 12 },
});
