import react from "@vitejs/plugin-react";
import { copyFileSync, readFileSync } from "node:fs";
import { defineConfig, splitVendorChunkPlugin } from "vite";
import svgr from "vite-plugin-svgr";
import { visualizer } from "rollup-plugin-visualizer";
import tsconfigPaths from "vite-tsconfig-paths";

const buildVersion = readFileSync("../../VERSION", "utf8").trim();

// https://vitejs.dev/config/
export default defineConfig({
  build: {
    assetsDir: "statics",
    emptyOutDir: true,
    outDir: "build",
  },
  define: {
    __LOCALE_BUILD_ID__: JSON.stringify(buildVersion),
  },
  plugins: [
    tsconfigPaths(),
    react({
      include: "**/*.tsx",
    }),
    svgr(),
    visualizer(),
    splitVendorChunkPlugin(),
    (() => {
      let outDir = "build";
      return {
      name: "write-dashboard-404-fallback",
      configResolved(config) {
        outDir = config.build.outDir;
      },
      closeBundle() {
        copyFileSync(`${outDir}/index.html`, `${outDir}/404.html`);
      },
      };
    })(),
  ],
});
