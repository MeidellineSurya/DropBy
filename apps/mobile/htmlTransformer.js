const upstreamTransformer = require("expo/node_modules/@expo/metro-config/babel-transformer");

module.exports.transform = ({ src, filename, options }) => {
  if (filename.endsWith(".html")) {
    return upstreamTransformer.transform({
      src: `module.exports = ${JSON.stringify(src)};`,
      filename,
      options,
    });
  }

  return upstreamTransformer.transform({ src, filename, options });
};
