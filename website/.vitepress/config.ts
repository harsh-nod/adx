import { defineConfig } from "vitepress";
import { resolve } from "node:path";

export default defineConfig({
  srcDir: resolve(__dirname, "../../docs"),
  vite: {
    resolve: {
      alias: {
        vue: resolve(__dirname, "../node_modules/vue"),
      },
    },
  },
  base: "/adx/",
  title: "ADX",
  description: "Agent-native document intelligence layer.",
  lang: "en-US",
  appearance: true,
  themeConfig: {
    logo: {
      text: "ADX"
    },
    nav: [
      { text: "Quickstart", link: "/quickstart/" },
      { text: "Agent Tools", link: "/guides/agent-tools" },
      { text: "PDF Guide", link: "/guides/pdf-processing" },
      { text: "Excel Guide", link: "/guides/excel-processing" },
      { text: "API Reference", link: "/reference/api" },
      { text: "Examples", link: "/examples/" },
    ],
    sidebar: {
      "/": [
        {
          text: "Getting Started",
          items: [
            { text: "Overview", link: "/" },
            { text: "Quickstart", link: "/quickstart/" },
          ]
        },
        {
          text: "Guides",
          items: [
            { text: "Agent Tools", link: "/guides/agent-tools" },
            { text: "PDF Processing", link: "/guides/pdf-processing" },
            { text: "Excel Processing", link: "/guides/excel-processing" },
            { text: "Extraction", link: "/guides/extraction" },
            { text: "Validation", link: "/guides/validation" },
            { text: "Citations", link: "/guides/citations" },
          ]
        },
        {
          text: "Examples",
          collapsed: false,
          items: [
            { text: "Catalog", link: "/examples/" },
            { text: "Invoice Extraction", link: "/examples/invoice" },
            { text: "Contract Review", link: "/examples/contract" },
            { text: "Financial Model", link: "/examples/financial-model" },
          ]
        },
        {
          text: "Reference",
          items: [
            { text: "REST API", link: "/reference/api" },
            { text: "Python SDK", link: "/reference/python-sdk" },
            { text: "CLI", link: "/reference/cli" },
            { text: "MCP Tools", link: "/reference/mcp" },
            { text: "Document Model", link: "/reference/document-model" },
          ]
        },
        {
          text: "Community",
          items: [
            { text: "Contributing", link: "/community/contributing" },
            { text: "Roadmap", link: "/community/roadmap" },
          ]
        }
      ]
    },
    socialLinks: [
      { icon: "github", link: "https://github.com/harsh-nod/adx" }
    ],
    footer: {
      message: "Documents are not text blobs. Give your agents document tools.",
      copyright: "© " + new Date().getFullYear() + " ADX contributors."
    }
  },
  head: [
    [
      "meta",
      { name: "theme-color", content: "#0f172a" }
    ]
  ]
});
