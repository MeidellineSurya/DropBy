import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import { useSession } from "../SessionContext";
import type { RootStackParamList } from "../navigation/RootNavigator";
import { api } from "../services/api";
import { connectLiveSocket } from "../services/ws";
import { colors } from "../theme";
import type { Message } from "../types";

type Props = NativeStackScreenProps<RootStackParamList, "ChatThread">;

export function ChatThreadScreen({ navigation, route }: Props) {
  const { token, user } = useSession();
  const { connectionId, displayName } = route.params;
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<ScrollView>(null);

  useLayoutEffect(() => {
    navigation.setOptions({ title: displayName });
  }, [navigation, displayName]);

  const refresh = useCallback(async () => {
    try {
      setMessages(await api.getMessages(connectionId));
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load messages");
    } finally {
      setLoading(false);
    }
  }, [connectionId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (!token) return;
    const socket = connectLiveSocket(token, (event) => {
      if (event.type !== "chat.message_sent") return;
      if (event.connection_id !== connectionId) return;
      const received = event;
      setMessages((current) => {
        if (current.some((message) => message.id === received.message_id)) return current;
        return [
          ...current,
          {
            id: received.message_id,
            connection_id: received.connection_id,
            sender_id: received.sender_id,
            body: received.body,
            created_at: received.created_at,
          },
        ];
      });
    });
    return () => socket.close();
  }, [connectionId, token]);

  async function send() {
    const body = draft.trim();
    if (!body) return;
    setSending(true);
    setDraft("");
    try {
      const message = await api.sendMessage(connectionId, body);
      setMessages((current) => [...current, message]);
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not send message");
    } finally {
      setSending(false);
    }
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.lime} size="large" />
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      style={styles.page}
    >
      <ScrollView
        contentContainerStyle={styles.content}
        onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: true })}
        ref={scrollRef}
      >
        {messages.map((message) => {
          const mine = message.sender_id === user?.id;
          return (
            <View key={message.id} style={[styles.bubbleRow, mine && styles.bubbleRowMine]}>
              <View style={[styles.bubble, mine && styles.bubbleMine]}>
                <Text style={[styles.bubbleText, mine && styles.bubbleTextMine]}>{message.body}</Text>
              </View>
            </View>
          );
        })}
        {error && <Text style={styles.error}>{error}</Text>}
      </ScrollView>
      <View style={styles.composer}>
        <TextInput
          onChangeText={setDraft}
          placeholder="Message"
          placeholderTextColor={colors.muted}
          style={styles.input}
          value={draft}
        />
        <Pressable disabled={sending || !draft.trim()} onPress={() => void send()} style={styles.sendButton}>
          <Text style={styles.sendButtonText}>Send</Text>
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  page: { backgroundColor: colors.background, flex: 1 },
  center: { alignItems: "center", backgroundColor: colors.background, flex: 1, justifyContent: "center" },
  content: { padding: 16, paddingBottom: 24 },
  bubbleRow: { flexDirection: "row", marginBottom: 8 },
  bubbleRowMine: { justifyContent: "flex-end" },
  bubble: { backgroundColor: colors.surface, borderRadius: 16, maxWidth: "78%", paddingHorizontal: 14, paddingVertical: 10 },
  bubbleMine: { backgroundColor: colors.lime },
  bubbleText: { color: colors.text, fontSize: 15 },
  bubbleTextMine: { color: colors.black },
  composer: { alignItems: "center", borderTopColor: colors.border, borderTopWidth: StyleSheet.hairlineWidth, flexDirection: "row", gap: 10, padding: 12 },
  input: { backgroundColor: colors.surface, borderColor: colors.border, borderRadius: 20, borderWidth: 1, color: colors.text, flex: 1, fontSize: 15, paddingHorizontal: 16, paddingVertical: 10 },
  sendButton: { alignItems: "center", backgroundColor: colors.lime, borderRadius: 20, justifyContent: "center", paddingHorizontal: 16, paddingVertical: 11 },
  sendButtonText: { color: colors.black, fontSize: 14, fontWeight: "900" },
  error: { color: colors.danger, fontSize: 13, marginTop: 8, textAlign: "center" },
});
