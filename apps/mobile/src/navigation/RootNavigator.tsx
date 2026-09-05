import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import React from "react";

import { DropDetailScreen } from "../screens/DropDetailScreen";
import { MapScreen } from "../screens/MapScreen";
import { ProfileScreen } from "../screens/ProfileScreen";
import { RedeemScreen } from "../screens/RedeemScreen";
import { SquadScreen } from "../screens/SquadScreen";

export type RootStackParamList = {
  Map: undefined;
  DropDetail: { dropId: string };
  Squad: { groupId: string };
  Redeem: { groupId: string };
  Profile: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();

export function RootNavigator() {
  return (
    <NavigationContainer>
      <Stack.Navigator initialRouteName="Map">
        <Stack.Screen name="Map" component={MapScreen} />
        <Stack.Screen name="DropDetail" component={DropDetailScreen} />
        <Stack.Screen name="Squad" component={SquadScreen} />
        <Stack.Screen name="Redeem" component={RedeemScreen} />
        <Stack.Screen name="Profile" component={ProfileScreen} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
