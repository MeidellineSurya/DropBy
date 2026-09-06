/**
 * Design tokens extracted from the DropBy Figma file
 * https://www.figma.com/design/hRuRdZOdURH15HCCuVnsBq/DropBy
 *
 * The Figma design is a light "paper" theme with dark accent screens
 * (the Drop screen background and the bottom nav bar use the dark ink).
 * This inverts the app's previous dark-only palette.
 *
 * `apps/dashboard/src/theme.css` mirrors this file as CSS custom
 * properties so the two front-ends read as one product.
 */

/** Raw values, named literally. Prefer the semantic `colors` map below. */
export const palette = {
  // Brand
  pink: "#E0526E", // primary — CTAs, active nav, headings
  green: "#6D9C42", // secondary — headings, positive/"live" state

  // Surfaces
  paper: "#FFFAF0", // light screen background
  card: "#FFFFFF", // list/detail cards on paper
  ink: "#2B2527", // dark screen background + bottom nav bar
  black: "#000000",

  // Text
  muted: "#B1B1B1", // labels next to stats ("connections", "catches")
  subtle: "#5F5F5F", // secondary metadata
  onDark: "#FFFAF0", // text/icons on ink surfaces

  // Tints (badge / chip backgrounds)
  pinkTint: "#FFE1E7",
  greenTint: "#EFF2D8",
  goldTint: "#FFEBCE",
  purpleTint: "#FEE6FF",

  // Accent text used on the tints
  gold: "#FF9601", // "RARE"
  purple: "#8F5DA6", // "LEGENDARY"

  // Derived
  hairline: "#EAE3D6", // subtle divider/border on paper (not a raw Figma value)
} as const;

export const colors = {
  // Surfaces
  background: palette.paper,
  surface: palette.card,
  surfaceInverse: palette.ink, // dark screens (Drop) + bottom nav
  border: palette.hairline,

  // Text
  text: palette.ink,
  textInverse: palette.onDark,
  muted: palette.muted,
  subtle: palette.subtle,

  // Brand
  primary: palette.pink,
  primaryTint: palette.pinkTint,
  onPrimary: palette.onDark,
  secondary: palette.green,
  secondaryTint: palette.greenTint,

  // Semantic / rarity system (bg tint + text pairs)
  success: palette.green,
  successTint: palette.greenTint,
  warning: palette.gold,
  warningTint: palette.goldTint,
  info: palette.purple,
  infoTint: palette.purpleTint,
  danger: palette.pink, // design has no distinct danger colour; alias to pink

  // Utility
  shadow: "rgba(0, 0, 0, 0.25)",
  overlay: "rgba(0, 0, 0, 0.10)",

  black: palette.black,
} as const;

/**
 * Font families. Loaded in App.tsx.
 *   display -> BBH Bartle  (the real face, apps/mobile/assets/fonts/BBHBartle-Regular.ttf)
 *   body    -> Candal      (Figma's body face, via @expo-google-fonts/candal)
 * Both are single-weight (400) display faces — emphasis comes from the
 * typeface, not the weight.
 */
export const fonts = {
  display: "BBHBartle",
  body: "Candal_400Regular",
} as const;

/**
 * Named text styles from the design. Spread directly into a StyleSheet
 * entry, then add `color`:
 *   title: { ...typography.heading, color: colors.text }
 * Tracking is a consistent ~+0.03em on display text.
 */
export const typography = {
  display: { fontFamily: fonts.display, fontSize: 33, lineHeight: 35, letterSpacing: 1.0 },
  title: { fontFamily: fonts.display, fontSize: 22, lineHeight: 25, letterSpacing: 0.66 },
  heading: { fontFamily: fonts.display, fontSize: 18, lineHeight: 20, letterSpacing: 0.54 },
  button: { fontFamily: fonts.display, fontSize: 16, lineHeight: 25, letterSpacing: 0.48 },
  tab: { fontFamily: fonts.display, fontSize: 12, lineHeight: 25, letterSpacing: 0.36 },

  name: { fontFamily: fonts.body, fontSize: 36, lineHeight: 40, letterSpacing: 1.08 },
  stat: { fontFamily: fonts.body, fontSize: 28, lineHeight: 32, letterSpacing: 0.84 },
  body: { fontFamily: fonts.body, fontSize: 14, lineHeight: 18, letterSpacing: 0.42 },
  label: { fontFamily: fonts.body, fontSize: 12, lineHeight: 18, letterSpacing: 0.36 },
  caption: { fontFamily: fonts.body, fontSize: 10, lineHeight: 18, letterSpacing: 0.3 },
  micro: { fontFamily: fonts.body, fontSize: 6, lineHeight: 18, letterSpacing: 0.18 },
} as const;

/** Raw size ramp for one-off cases not covered by `typography`. */
export const fontSize = {
  micro: 6,
  xxs: 8,
  xs: 10,
  sm: 12,
  base: 14,
  md: 16,
  lg: 18,
  xl: 20,
  xxl: 22,
  xxxl: 26,
  huge: 33,
  display: 36,
  mega: 50,
} as const;

/** 4-based spacing scale. Screen inset ≈ `xxl`, gap between cards ≈ `lg`. */
export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
  xxxl: 32,
} as const;

/** Corner radii. chips=`md`, cards/buttons=`lg`, hero containers=`xl`,
 *  CTA / nav pill / map markers=`xxl`, fully-round (avatars, dots)=`pill`. */
export const radius = {
  sm: 13,
  md: 20,
  lg: 25,
  xl: 30,
  xxl: 35,
  pill: 999,
} as const;

/** The design uses a single card elevation. */
export const shadows = {
  card: {
    shadowColor: palette.black,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
    elevation: 4,
  },
} as const;

export const theme = {
  palette,
  colors,
  fonts,
  typography,
  fontSize,
  spacing,
  radius,
  shadows,
} as const;
