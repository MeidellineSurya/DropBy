import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import React, { useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

import type { RootStackParamList } from "../navigation/RootNavigator";
import { api } from "../services/api";
import { colors } from "../theme";

type Props = NativeStackScreenProps<RootStackParamList, "DropDetail">;

const stageCopy = {
  detect: "This signal is always visible. Its type, rarity, and group requirement are known; move closer to reveal the venue.",
  reveal: "You found it. The location, full offer, and squad details are now unlocked.",
};

export function DropDetailScreen({ navigation, route }: Props) {
  const { drop } = route.params;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isRevealed = drop.stage === "reveal";
  const title = drop.title ?? drop.interest_tag?.replace(/_/g, " ") ?? "Mystery Drop";
  const groupSize = drop.min_group_size
    ? `${drop.min_group_size} needed${drop.max_group_size && drop.max_group_size !== drop.min_group_size ? ` · up to ${drop.max_group_size}` : ""}`
    : undefined;

  async function assembleSquad() {
    setLoading(true);
    setError(null);
    try {
      const group = await api.createGroup(drop.id);
      navigation.replace("Squad", { groupId: group.id });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not create the squad");
    } finally {
      setLoading(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.content} style={styles.page}>
      <View style={[styles.stageBadge, isRevealed && styles.stageBadgeRevealed]}>
        <Text style={styles.stageText}>{drop.stage.toUpperCase()}</Text>
      </View>
      <Text style={styles.distance}>{drop.distance_m} metres away</Text>
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.explanation}>{stageCopy[drop.stage]}</Text>

      <View style={styles.card}>
        <Detail label="Rarity" value={drop.rarity} />
        <Detail label="Type" value={drop.interest_tag?.replace(/_/g, " ")} />
        <Detail label="People needed" value={groupSize} />
        <Detail label="Business" value={drop.business_name} hidden={!isRevealed} />
        <Detail label="Address" value={drop.address} hidden={!isRevealed} />
        <Detail label="Offer" value={drop.description} hidden={!isRevealed} />
        {drop.ends_at && <Detail label="Ends" value={new Date(drop.ends_at).toLocaleString()} />}
      </View>

      {isRevealed && drop.drop_type !== "solo" && (
        <View style={styles.squadCard}>
          <Text style={styles.squadEyebrow}>ASSEMBLE</Text>
          <Text style={styles.squadTitle}>
            Build a squad of {drop.min_group_size ?? 2}–{drop.max_group_size ?? 4}
          </Text>
          <Text style={styles.squadBody}>
            Create a live squad, then share its ID so friends can join from their phones.
          </Text>
          <Pressable
            disabled={!drop.can_assemble || loading}
            onPress={() => void assembleSquad()}
            style={[styles.primaryButton, (!drop.can_assemble || loading) && styles.disabled]}
          >
            {loading ? (
              <ActivityIndicator color={colors.black} />
            ) : (
              <Text style={styles.primaryButtonText}>
                {drop.can_assemble ? "Create squad" : "Capacity reached"}
              </Text>
            )}
          </Pressable>
        </View>
      )}

      {!isRevealed && (
        <Pressable onPress={() => navigation.popTo("Discover")} style={styles.primaryButton}>
          <Text style={styles.primaryButtonText}>Return to the map</Text>
        </Pressable>
      )}
      {error && <Text style={styles.error}>{error}</Text>}
    </ScrollView>
  );
}

function Detail({
  label,
  value,
  hidden = false,
}: {
  label: string;
  value?: string;
  hidden?: boolean;
}) {
  return (
    <View style={styles.detailRow}>
      <Text style={styles.detailLabel}>{label}</Text>
      <Text style={[styles.detailValue, hidden && styles.hidden]}>
        {hidden ? "Move closer to unlock" : value ?? "Not provided"}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  page: { backgroundColor: colors.background },
  content: { padding: 20, paddingBottom: 40 },
  stageBadge: { alignSelf: "flex-start", backgroundColor: colors.violet, borderRadius: 99, paddingHorizontal: 13, paddingVertical: 7 },
  stageBadgeRevealed: { backgroundColor: colors.lime },
  stageText: { color: colors.black, fontSize: 11, fontWeight: "900", letterSpacing: 1 },
  distance: { color: colors.muted, fontSize: 13, marginTop: 18 },
  title: { color: colors.text, fontSize: 32, fontWeight: "900", marginTop: 5, textTransform: "capitalize" },
  explanation: { color: colors.muted, fontSize: 16, lineHeight: 24, marginTop: 10 },
  card: { backgroundColor: colors.surface, borderColor: colors.border, borderRadius: 18, borderWidth: 1, marginTop: 24, paddingHorizontal: 16 },
  detailRow: { borderBottomColor: colors.border, borderBottomWidth: StyleSheet.hairlineWidth, paddingVertical: 14 },
  detailLabel: { color: colors.muted, fontSize: 11, fontWeight: "800", letterSpacing: 0.9, textTransform: "uppercase" },
  detailValue: { color: colors.text, fontSize: 15, lineHeight: 21, marginTop: 5, textTransform: "capitalize" },
  hidden: { color: colors.violet, fontStyle: "italic" },
  squadCard: { backgroundColor: colors.surfaceRaised, borderColor: colors.lime, borderRadius: 18, borderWidth: 1, marginTop: 18, padding: 18 },
  squadEyebrow: { color: colors.lime, fontSize: 11, fontWeight: "900", letterSpacing: 1.2 },
  squadTitle: { color: colors.text, fontSize: 21, fontWeight: "900", marginTop: 6 },
  squadBody: { color: colors.muted, fontSize: 14, lineHeight: 20, marginTop: 7 },
  primaryButton: { alignItems: "center", backgroundColor: colors.lime, borderRadius: 12, marginTop: 18, minHeight: 50, justifyContent: "center", paddingHorizontal: 18 },
  primaryButtonText: { color: colors.black, fontSize: 15, fontWeight: "900" },
  disabled: { opacity: 0.45 },
  error: { color: colors.danger, fontSize: 14, marginTop: 14 },
});
