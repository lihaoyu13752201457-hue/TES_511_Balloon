import { readFileSync } from "node:fs";
import { createRequire } from "node:module";


const require = createRequire(import.meta.url);
const server = require(
  "/home/ubuntu/.codex/plugins/cache/openai-curated-remote/data-analytics/0.2.8-13ceeea1f599/mcp/server.cjs",
);


export function validateArtifact(path) {
  const payload = JSON.parse(readFileSync(path, "utf8"));
  return server.callTool("validate_artifact", payload);
}


export function artifactChartSchema() {
  const tool = server.toolDefinitions().find((entry) => entry.name === "validate_artifact");
  return tool.inputSchema.properties.manifest.properties.charts.items;
}
