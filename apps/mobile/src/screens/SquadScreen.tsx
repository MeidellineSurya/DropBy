import React from "react";
import { Text, View } from "react-native";

// TODO: live squad-fill progress (e.g. "2/4 ready"), driven by
// group.state_update / group.member_joined / group.ready WS events.
export function SquadScreen() {
  return (
    <View>
      <Text>Squad</Text>
    </View>
  );
}
