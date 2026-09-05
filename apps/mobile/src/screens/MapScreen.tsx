import React from "react";
import { Text, View } from "react-native";

// TODO: live map of unidentified Drops (react-native-maps), fed by
// src/services/api.ts locationPing() + src/services/ws.ts drop.stage_update events.
export function MapScreen() {
  return (
    <View>
      <Text>Map — nearby Drops</Text>
    </View>
  );
}
