import type { BottomTabScreenProps } from "@react-navigation/bottom-tabs";
import type { CompositeScreenProps } from "@react-navigation/native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import React, { useCallback, useEffect, useRef, useState } from "react";
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

import type { MainTabParamList, RootStackParamList } from "../navigation/RootNavigator";
import { api } from "../services/api";
import { colors, fonts, radius } from "../theme";
import type {
  ConnectionStatusView,
  ConnectionSummary,
  Conversation,
  RecentSquadmate,
  UserSearchResult,
} from "../types";

type Props = CompositeScreenProps<
  BottomTabScreenProps<MainTabParamList, "Squads">,
  NativeStackScreenProps<RootStackParamList>
>;
type Tab = "friends" | "chat";
type Person = UserSearchResult | RecentSquadmate;

export function ConnectionsScreen({ navigation }: Props) {
  const [tab, setTab] = useState<Tab>("friends");
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<UserSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [recent, setRecent] = useState<RecentSquadmate[]>([]);
  const [incoming, setIncoming] = useState<ConnectionSummary[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [pendingUserIds, setPendingUserIds] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const loadFriendsTab = useCallback(async () => {
    try {
      const [recentSquadmates, requests] = await Promise.all([
        api.getRecentSquadmates(),
        api.getIncomingRequests(),
      ]);
      setRecent(recentSquadmates);
      setIncoming(requests);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load connections");
    }
  }, []);

  const loadChatTab = useCallback(async () => {
    try {
      setConversations(await api.getConversations());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load chats");
    }
  }, []);

  useEffect(() => {
    void loadFriendsTab();
  }, [loadFriendsTab]);

  useEffect(() => {
    if (tab === "chat") void loadChatTab();
  }, [tab, loadChatTab]);

  useEffect(() => {
    if (searchTimer.current) clearTimeout(searchTimer.current);
    if (!query.trim()) {
      setSearchResults([]);
      return;
    }
    setSearching(true);
    searchTimer.current = setTimeout(async () => {
      try {
        setSearchResults(await api.searchUsers(query.trim()));
        setError(null);
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : "Search failed");
      } finally {
        setSearching(false);
      }
    }, 350);
    return () => {
      if (searchTimer.current) clearTimeout(searchTimer.current);
    };
  }, [query]);

  async function addFriend(userId: string) {
    setPendingUserIds((current) => new Set(current).add(userId));
    try {
      await api.sendConnectionRequest(userId);
      setSearchResults((current) =>
        current.map((person) =>
          person.user_id === userId ? { ...person, connection_status: "pending_outgoing" } : person,
        ),
      );
      setRecent((current) =>
        current.map((person) =>
          person.user_id === userId ? { ...person, connection_status: "pending_outgoing" } : person,
        ),
      );
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not send request");
    } finally {
      setPendingUserIds((current) => {
        const next = new Set(current);
        next.delete(userId);
        return next;
      });
    }
  }

  async function respond(connectionId: string, accept: boolean) {
    try {
      await api.respondToRequest(connectionId, accept);
      setIncoming((current) => current.filter((request) => request.id !== connectionId));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not respond to request");
    }
  }

  function actionLabel(status: ConnectionStatusView): string {
    switch (status) {
      case "connected":
        return "Friends";
      case "pending_outgoing":
        return "Requested";
      case "pending_incoming":
        return "Respond below";
      case "blocked":
        return "Blocked";
      default:
        return "Add";
    }
  }

  function PersonRow({ person }: { person: Person }) {
    const disabled = person.connection_status !== "none" || pendingUserIds.has(person.user_id);
    return (
      <View style={styles.row}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>{person.display_name.slice(0, 1).toUpperCase()}</Text>
        </View>
        <View style={styles.rowCopy}>
          <Text style={styles.rowName}>{person.display_name}</Text>
          {"met_via_drop_title" in person && person.met_via_drop_title ? (
            <Text style={styles.rowMeta}>Met at {person.met_via_drop_title}</Text>
          ) : null}
        </View>
        <Pressable
          disabled={disabled}
          onPress={() => void addFriend(person.user_id)}
          style={[styles.actionButton, disabled && styles.actionButtonDisabled]}
        >
          <Text style={[styles.actionButtonText, disabled && styles.actionButtonTextDisabled]}>
            {actionLabel(person.connection_status)}
          </Text>
        </Pressable>
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.page}>
      <View style={styles.tabRow}>
        <Pressable onPress={() => setTab("friends")} style={[styles.tabButton, tab === "friends" && styles.tabButtonActive]}>
          <Text style={[styles.tabButtonText, tab === "friends" && styles.tabButtonTextActive]}>Add Friends</Text>
        </Pressable>
        <Pressable onPress={() => setTab("chat")} style={[styles.tabButton, tab === "chat" && styles.tabButtonActive]}>
          <Text style={[styles.tabButtonText, tab === "chat" && styles.tabButtonTextActive]}>Chat</Text>
        </Pressable>
      </View>

      {tab === "friends" ? (
        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
          <TextInput
            autoCapitalize="none"
            onChangeText={setQuery}
            placeholder="Search by name"
            placeholderTextColor={colors.muted}
            style={styles.searchInput}
            value={query}
          />
          {searching && <ActivityIndicator color={colors.primary} style={styles.spinner} />}

          {query.trim().length > 0 && (
            <>
              <Text style={styles.sectionTitle}>Results</Text>
              {searchResults.length === 0 && !searching ? (
                <Text style={styles.empty}>No one found.</Text>
              ) : (
                searchResults.map((person) => <PersonRow key={person.user_id} person={person} />)
              )}
            </>
          )}

          {incoming.length > 0 && (
            <>
              <Text style={styles.sectionTitle}>Requests</Text>
              {incoming.map((request) => (
                <View key={request.id} style={styles.row}>
                  <View style={styles.avatar}>
                    <Text style={styles.avatarText}>{request.other_user.display_name.slice(0, 1).toUpperCase()}</Text>
                  </View>
                  <View style={styles.rowCopy}>
                    <Text style={styles.rowName}>{request.other_user.display_name}</Text>
                  </View>
                  <Pressable onPress={() => void respond(request.id, true)} style={styles.actionButton}>
                    <Text style={styles.actionButtonText}>Accept</Text>
                  </Pressable>
                  <Pressable onPress={() => void respond(request.id, false)} style={styles.declineButton}>
                    <Text style={styles.declineButtonText}>Decline</Text>
                  </Pressable>
                </View>
              ))}
            </>
          )}

          <Text style={styles.sectionTitle}>People you've met</Text>
          {recent.length === 0 ? (
            <Text style={styles.empty}>Join a squad to start meeting people.</Text>
          ) : (
            recent.map((person) => <PersonRow key={person.user_id} person={person} />)
          )}

          {error && <Text style={styles.error}>{error}</Text>}
        </ScrollView>
      ) : (
        <ScrollView contentContainerStyle={styles.content}>
          {conversations.length === 0 ? (
            <Text style={styles.empty}>No chats yet. Add a friend to start one.</Text>
          ) : (
            conversations.map((conversation) => (
              <Pressable
                key={conversation.connection_id}
                onPress={() =>
                  navigation.navigate("ChatThread", {
                    connectionId: conversation.connection_id,
                    displayName: conversation.other_user.display_name,
                  })
                }
                style={styles.row}
              >
                <View style={styles.avatar}>
                  <Text style={styles.avatarText}>{conversation.other_user.display_name.slice(0, 1).toUpperCase()}</Text>
                </View>
                <View style={styles.rowCopy}>
                  <Text style={styles.rowName}>{conversation.other_user.display_name}</Text>
                  <Text numberOfLines={1} style={styles.rowMeta}>
                    {conversation.last_message?.body ?? "Say hello"}
                  </Text>
                </View>
              </Pressable>
            ))
          )}
          {error && <Text style={styles.error}>{error}</Text>}
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  page: { backgroundColor: colors.background, flex: 1 },
  content: { padding: 20, paddingBottom: 40 },
  tabRow: { flexDirection: "row", gap: 10, paddingHorizontal: 20, paddingTop: 12 },
  tabButton: { alignItems: "center", borderColor: colors.border, borderRadius: radius.pill, borderWidth: 1, flex: 1, paddingVertical: 11 },
  tabButtonActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  tabButtonText: { color: colors.muted, fontFamily: fonts.display, fontSize: 14 },
  tabButtonTextActive: { color: colors.onPrimary },
  searchInput: { backgroundColor: colors.surface, borderColor: colors.border, borderRadius: radius.sm, borderWidth: 1, color: colors.text, fontFamily: fonts.body, fontSize: 15, paddingHorizontal: 14, paddingVertical: 12 },
  spinner: { marginTop: 12 },
  sectionTitle: { color: colors.text, fontFamily: fonts.display, fontSize: 16, marginTop: 22, marginBottom: 6 },
  empty: { color: colors.muted, fontFamily: fonts.body, fontSize: 14, marginTop: 6 },
  row: { alignItems: "center", borderBottomColor: colors.border, borderBottomWidth: StyleSheet.hairlineWidth, flexDirection: "row", minHeight: 62 },
  avatar: { alignItems: "center", backgroundColor: colors.info, borderRadius: 18, height: 36, justifyContent: "center", width: 36 },
  avatarText: { color: colors.onPrimary, fontFamily: fonts.display, fontSize: 14 },
  rowCopy: { flex: 1, marginLeft: 11 },
  rowName: { color: colors.text, fontFamily: fonts.body, fontSize: 15 },
  rowMeta: { color: colors.muted, fontFamily: fonts.body, fontSize: 12, marginTop: 2 },
  actionButton: { alignItems: "center", backgroundColor: colors.primary, borderRadius: radius.pill, marginLeft: 8, paddingHorizontal: 14, paddingVertical: 8 },
  actionButtonDisabled: { backgroundColor: colors.border },
  actionButtonText: { color: colors.onPrimary, fontFamily: fonts.display, fontSize: 12 },
  actionButtonTextDisabled: { color: colors.muted },
  declineButton: { alignItems: "center", borderColor: colors.border, borderRadius: radius.pill, borderWidth: 1, marginLeft: 8, paddingHorizontal: 14, paddingVertical: 8 },
  declineButtonText: { color: colors.muted, fontFamily: fonts.display, fontSize: 12 },
  error: { color: colors.danger, fontFamily: fonts.body, fontSize: 14, marginTop: 16 },
});
