import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import React from "react";
import { ActivityIndicator, StyleSheet, View } from "react-native";

import { useSession } from "../SessionContext";
import { colors } from "../theme";
import type { DropSnapshot } from "../types";
import { AuthScreen } from "../screens/AuthScreen";
import { ChatThreadScreen } from "../screens/ChatThreadScreen";
import { ConnectionsScreen } from "../screens/ConnectionsScreen";
import { DropDetailScreen } from "../screens/DropDetailScreen";
import { MapScreen } from "../screens/MapScreen";
import { OnboardingScreen } from "../screens/OnboardingScreen";
import { ProfileScreen } from "../screens/ProfileScreen";
import { SquadScreen } from "../screens/SquadScreen";

export type RootStackParamList = {
  Discover: undefined;
  DropDetail: { drop: DropSnapshot };
  Squad: { groupId: string };
  Profile: undefined;
  Connections: undefined;
  ChatThread: { connectionId: string; displayName: string };
};

const Stack = createNativeStackNavigator<RootStackParamList>();

export function RootNavigator() {
  const { initializing, user } = useSession();

  if (initializing) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator color={colors.lime} size="large" />
      </View>
    );
  }
  if (!user) return <AuthScreen />;
  if (!user.onboarding_complete) return <OnboardingScreen />;

  return (
    <NavigationContainer
      theme={{
        dark: true,
        colors: {
          primary: colors.lime,
          background: colors.background,
          card: colors.surface,
          text: colors.text,
          border: colors.border,
          notification: colors.violet,
        },
        fonts: {
          regular: { fontFamily: "System", fontWeight: "400" },
          medium: { fontFamily: "System", fontWeight: "600" },
          bold: { fontFamily: "System", fontWeight: "700" },
          heavy: { fontFamily: "System", fontWeight: "900" },
        },
      }}
    >
      <Stack.Navigator
        initialRouteName="Discover"
        screenOptions={{
          contentStyle: { backgroundColor: colors.background },
          headerBackButtonDisplayMode: "minimal",
          headerTintColor: colors.text,
          headerStyle: { backgroundColor: colors.surface },
        }}
      >
        <Stack.Screen name="Discover" component={MapScreen} options={{ headerShown: false }} />
        <Stack.Screen name="DropDetail" component={DropDetailScreen} options={{ title: "Drop" }} />
        <Stack.Screen name="Squad" component={SquadScreen} />
        <Stack.Screen name="Profile" component={ProfileScreen} />
        <Stack.Screen
          name="Connections"
          component={ConnectionsScreen}
          options={{ presentation: "modal", title: "Connections" }}
        />
        <Stack.Screen name="ChatThread" component={ChatThreadScreen} options={{ title: "Chat" }} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  loading: { alignItems: "center", backgroundColor: colors.background, flex: 1, justifyContent: "center" },
});
