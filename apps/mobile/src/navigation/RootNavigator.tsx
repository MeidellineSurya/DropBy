import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { NavigationContainer, type NavigatorScreenParams } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import React from "react";
import { ActivityIndicator, StyleSheet, View } from "react-native";

import { useSession } from "../SessionContext";
import { colors, fonts } from "../theme";
import type { DropSnapshot } from "../types";
import { AuthScreen } from "../screens/AuthScreen";
import { ChatThreadScreen } from "../screens/ChatThreadScreen";
import { ConnectionsScreen } from "../screens/ConnectionsScreen";
import { DropDetailScreen } from "../screens/DropDetailScreen";
import { HomeScreen } from "../screens/HomeScreen";
import { MapScreen } from "../screens/MapScreen";
import { OnboardingScreen } from "../screens/OnboardingScreen";
import { ProfileScreen } from "../screens/ProfileScreen";
import { SquadScreen } from "../screens/SquadScreen";
import { BottomTabBar } from "./BottomTabBar";

export type MainTabParamList = {
  Home: undefined;
  Explore: undefined;
  Squads: undefined;
  Profile: undefined;
};

export type RootStackParamList = {
  Main: NavigatorScreenParams<MainTabParamList> | undefined;
  DropDetail: { drop: DropSnapshot };
  Squad: { groupId: string };
  ChatThread: { connectionId: string; displayName: string };
};

const Tab = createBottomTabNavigator<MainTabParamList>();
const Stack = createNativeStackNavigator<RootStackParamList>();

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={{ headerShown: false }}
      tabBar={(props) => <BottomTabBar {...props} />}
    >
      <Tab.Screen name="Home" component={HomeScreen} />
      <Tab.Screen name="Explore" component={MapScreen} />
      <Tab.Screen name="Squads" component={ConnectionsScreen} options={{ tabBarLabel: "Squads" }} />
      <Tab.Screen name="Profile" component={ProfileScreen} />
    </Tab.Navigator>
  );
}

export function RootNavigator() {
  const { initializing, user } = useSession();

  if (initializing) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator color={colors.primary} size="large" />
      </View>
    );
  }
  if (!user) return <AuthScreen />;
  if (!user.onboarding_complete) return <OnboardingScreen />;

  return (
    <NavigationContainer
      theme={{
        dark: false,
        colors: {
          primary: colors.primary,
          background: colors.background,
          card: colors.surface,
          text: colors.text,
          border: colors.border,
          notification: colors.info,
        },
        fonts: {
          regular: { fontFamily: fonts.body, fontWeight: "400" },
          medium: { fontFamily: fonts.body, fontWeight: "400" },
          bold: { fontFamily: fonts.display, fontWeight: "400" },
          heavy: { fontFamily: fonts.display, fontWeight: "400" },
        },
      }}
    >
      <Stack.Navigator
        screenOptions={{
          contentStyle: { backgroundColor: colors.background },
          headerBackButtonDisplayMode: "minimal",
          headerTintColor: colors.text,
          headerTitleStyle: { fontFamily: fonts.display },
          headerStyle: { backgroundColor: colors.background },
          headerShadowVisible: false,
        }}
      >
        <Stack.Screen name="Main" component={MainTabs} options={{ headerShown: false }} />
        <Stack.Screen name="DropDetail" component={DropDetailScreen} options={{ title: "Drop" }} />
        <Stack.Screen name="Squad" component={SquadScreen} />
        <Stack.Screen name="ChatThread" component={ChatThreadScreen} options={{ title: "Chat" }} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  loading: { alignItems: "center", backgroundColor: colors.background, flex: 1, justifyContent: "center" },
});
