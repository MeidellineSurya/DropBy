import React from "react";
import { StatusBar } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { SessionProvider } from "./src/SessionContext";
import { RootNavigator } from "./src/navigation/RootNavigator";

export default function App() {
  return (
    <SafeAreaProvider>
      <SessionProvider>
        <StatusBar barStyle="light-content" />
        <RootNavigator />
      </SessionProvider>
    </SafeAreaProvider>
  );
}
