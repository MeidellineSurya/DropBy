import { Candal_400Regular, useFonts } from "@expo-google-fonts/candal";
import React from "react";
import { StatusBar } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { SessionProvider } from "./src/SessionContext";
import { RootNavigator } from "./src/navigation/RootNavigator";

export default function App() {
  const [fontsLoaded] = useFonts({
    Candal_400Regular,
    // Real "BBH Bartle" display face (apps/fonts/BBHBartle-Regular.ttf).
    BBHBartle: require("./assets/fonts/BBHBartle-Regular.ttf"),
  });

  if (!fontsLoaded) return null;

  return (
    <SafeAreaProvider>
      <SessionProvider>
        <StatusBar barStyle="dark-content" />
        <RootNavigator />
      </SessionProvider>
    </SafeAreaProvider>
  );
}
