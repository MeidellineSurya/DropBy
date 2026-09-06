import { Ionicons } from "@expo/vector-icons";
import type { BottomTabBarProps } from "@react-navigation/bottom-tabs";
import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { colors, fonts, radius } from "../theme";

/** Persistent bottom navigation matching the Figma DropBy tab bar:
 *  a dark rounded bar; the active tab is a filled pink pill. */
const ICONS: Record<string, keyof typeof Ionicons.glyphMap> = {
  Home: "home",
  Explore: "location",
  Squads: "people",
  Profile: "person",
};

export function BottomTabBar({ state, descriptors, navigation }: BottomTabBarProps) {
  const insets = useSafeAreaInsets();

  return (
    <View style={[styles.wrap, { paddingBottom: Math.max(insets.bottom, 12) }]}>
      <View style={styles.bar}>
        {state.routes.map((route, index) => {
          const focused = state.index === index;
          const { options } = descriptors[route.key];
          const label =
            typeof options.tabBarLabel === "string" ? options.tabBarLabel : route.name;

          function onPress() {
            const event = navigation.emit({
              type: "tabPress",
              target: route.key,
              canPreventDefault: true,
            });
            if (!focused && !event.defaultPrevented) {
              navigation.navigate(route.name);
            }
          }

          return (
            <Pressable
              accessibilityRole="button"
              accessibilityState={focused ? { selected: true } : {}}
              key={route.key}
              onPress={onPress}
              style={styles.item}
            >
              <View style={[styles.pill, focused && styles.pillActive]}>
                <Ionicons
                  color={focused ? colors.onPrimary : colors.textInverse}
                  name={ICONS[route.name] ?? "ellipse"}
                  size={20}
                />
                <Text style={[styles.label, focused && styles.labelActive]}>{label}</Text>
              </View>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { backgroundColor: "transparent", paddingHorizontal: 16, paddingTop: 6 },
  bar: {
    alignItems: "center",
    backgroundColor: colors.surfaceInverse,
    borderRadius: radius.xxl,
    flexDirection: "row",
    justifyContent: "space-between",
    paddingHorizontal: 10,
    paddingVertical: 10,
  },
  item: { flex: 1 },
  pill: {
    alignItems: "center",
    borderRadius: radius.xxl,
    gap: 2,
    paddingVertical: 6,
  },
  pillActive: { backgroundColor: colors.primary },
  label: { color: colors.textInverse, fontFamily: fonts.body, fontSize: 10 },
  labelActive: { color: colors.onPrimary },
});
