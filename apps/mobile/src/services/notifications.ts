import { Platform } from "react-native";
import * as Notifications from "expo-notifications";

const DROP_ALERT_CHANNEL = "drop-alerts";

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldPlaySound: true,
    shouldSetBadge: false,
    shouldShowBanner: true,
    shouldShowList: true,
  }),
});

/**
 * Sets up on-device alerts for the demo. This intentionally uses local
 * notifications only: no FCM credentials, device token, or API call needed.
 */
export async function enableLocalNotifications(): Promise<boolean> {
  if (Platform.OS === "android") {
    await Notifications.setNotificationChannelAsync(DROP_ALERT_CHANNEL, {
      name: "Drop alerts",
      description: "Alerts when a nearby Drop becomes revealable",
      importance: Notifications.AndroidImportance.HIGH,
      vibrationPattern: [0, 250, 150, 250],
    });
  }

  const existing = await Notifications.getPermissionsAsync();
  if (existing.granted) return true;

  const requested = await Notifications.requestPermissionsAsync({
    ios: { allowAlert: true, allowBadge: false, allowSound: true },
  });
  return requested.granted;
}

export async function notifyDropRevealed(drop: { id: string; title: string }): Promise<void> {
  await Notifications.scheduleNotificationAsync({
    content: {
      title: "Deal unlocked nearby \uD83D\uDC40",
      body: `${drop.title} is close enough to reveal.`,
      data: { dropId: drop.id },
      sound: "default",
    },
    trigger: null,
  });
}

export async function notifyDemoAlert(): Promise<void> {
  await Notifications.scheduleNotificationAsync({
    content: {
      title: "DropBy notifications are on \uD83D\uDD14",
      body: "When you get close enough, nearby deals will appear here.",
      sound: "default",
    },
    trigger: null,
  });
}
