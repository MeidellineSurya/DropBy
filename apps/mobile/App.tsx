import React from "react";
import { StatusBar } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { BrowserDemoApp } from "./src/BrowserDemoApp";

export default function App() {
  return (
    <SafeAreaProvider>
      <StatusBar barStyle="light-content" />
      <BrowserDemoApp />
    </SafeAreaProvider>
  );
}
