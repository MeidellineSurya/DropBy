const { getDefaultConfig } = require("expo/metro-config");
const path = require("path");

const config = getDefaultConfig(__dirname);

// Bundle the browser demo as JavaScript text instead of an Expo asset. This
// avoids a file URL that Expo Go cannot serve from outside apps/mobile.
config.resolver.assetExts = config.resolver.assetExts.filter((extension) => extension !== "html");
if (!config.resolver.sourceExts.includes("html")) config.resolver.sourceExts.push("html");
config.watchFolders = [...(config.watchFolders || []), path.resolve(__dirname, "../..")];
config.transformer.babelTransformerPath = path.resolve(__dirname, "htmlTransformer.js");

module.exports = config;
