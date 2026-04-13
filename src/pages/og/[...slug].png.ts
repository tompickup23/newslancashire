import type { APIRoute, GetStaticPaths } from "astro";
import satori from "satori";
import sharp from "sharp";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { getCollection } from "astro:content";
import { BOROUGHS } from "../../data/boroughs";
import { getBoroughName } from "../../data/boroughs";
import { getCategoryName } from "../../data/categories";
import { articleSlug } from "../../lib/articles";

const COLORS = {
  bg: "#0a0a0a",
  surface: "#1c1c1e",
  accent: "#0a84ff",
  accentLight: "#5ac8fa",
  text: "#f5f5f7",
  muted: "#8e8e93",
  breaking: "#ff453a",
};

let manropeBold: ArrayBuffer | null = null;
let soraExtraBold: ArrayBuffer | null = null;

function loadFont(name: string): ArrayBuffer {
  const fontPath = join(process.cwd(), "src", "assets", "fonts", name);
  return readFileSync(fontPath).buffer as ArrayBuffer;
}

function ensureFonts() {
  if (!manropeBold) manropeBold = loadFont("Manrope-Bold.ttf");
  if (!soraExtraBold) soraExtraBold = loadFont("Sora-ExtraBold.ttf");
}

export const getStaticPaths: GetStaticPaths = async () => {
  const articles = await getCollection("articles");

  const articlePaths = articles.map((a) => ({
    params: { slug: `${a.data.borough}/${articleSlug(a)}` },
    props: {
      title: a.data.headline,
      subtitle: getBoroughName(a.data.borough),
      badge: getCategoryName(a.data.category),
    },
  }));

  const boroughPaths = BOROUGHS.map((b) => ({
    params: { slug: b.slug },
    props: {
      title: `${b.name} News`,
      subtitle: `Population ${b.population.toLocaleString("en-GB")}`,
      badge: "Borough",
    },
  }));

  return [
    {
      params: { slug: "home" },
      props: {
        title: "News Lancashire",
        subtitle: "Independent Local News",
        badge: "14 Boroughs",
      },
    },
    ...boroughPaths,
    ...articlePaths,
  ];
};

export const GET: APIRoute = async ({ props }) => {
  ensureFonts();

  const { title, subtitle, badge } = props as {
    title: string;
    subtitle: string;
    badge: string;
  };

  const svg = await satori(
    {
      type: "div",
      props: {
        style: {
          width: "1200px",
          height: "630px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "60px 70px",
          background: `linear-gradient(135deg, ${COLORS.bg} 0%, ${COLORS.surface} 100%)`,
          fontFamily: "Manrope",
        },
        children: [
          // Logo
          {
            type: "div",
            props: {
              style: {
                display: "flex",
                alignItems: "center",
                gap: "12px",
              },
              children: [
                {
                  type: "div",
                  props: {
                    style: {
                      width: "44px",
                      height: "44px",
                      borderRadius: "12px",
                      background: COLORS.accent,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: "#fff",
                      fontWeight: 800,
                      fontSize: "18px",
                    },
                    children: "NL",
                  },
                },
                {
                  type: "div",
                  props: {
                    style: { display: "flex", flexDirection: "column" },
                    children: [
                      {
                        type: "span",
                        props: {
                          style: { fontWeight: 700, fontSize: "16px", color: COLORS.text },
                          children: "News Lancashire",
                        },
                      },
                      {
                        type: "span",
                        props: {
                          style: { fontSize: "11px", color: COLORS.muted, letterSpacing: "0.05em" },
                          children: "newslancashire.co.uk",
                        },
                      },
                    ],
                  },
                },
              ],
            },
          },
          // Content
          {
            type: "div",
            props: {
              style: { display: "flex", flexDirection: "column", gap: "12px" },
              children: [
                {
                  type: "div",
                  props: {
                    style: {
                      display: "flex",
                      padding: "6px 16px",
                      background: "rgba(10, 132, 255, 0.15)",
                      borderRadius: "8px",
                      fontSize: "14px",
                      fontWeight: 700,
                      color: COLORS.accentLight,
                      textTransform: "uppercase",
                      letterSpacing: "0.04em",
                      alignSelf: "flex-start",
                    },
                    children: badge,
                  },
                },
                {
                  type: "div",
                  props: {
                    style: {
                      display: "flex",
                      fontSize: "42px",
                      fontWeight: 800,
                      fontFamily: "Sora",
                      color: COLORS.text,
                      lineHeight: "1.15",
                    },
                    children: title.length > 80 ? title.slice(0, 77) + "..." : title,
                  },
                },
                subtitle
                  ? {
                      type: "div",
                      props: {
                        style: { display: "flex", fontSize: "20px", color: COLORS.muted },
                        children: subtitle,
                      },
                    }
                  : null,
              ].filter(Boolean),
            },
          },
          // Bottom bar
          {
            type: "div",
            props: {
              style: { display: "flex", alignItems: "center", gap: "16px" },
              children: [
                {
                  type: "div",
                  props: {
                    style: {
                      display: "flex",
                      height: "4px",
                      flex: "1",
                      background: COLORS.accent,
                      borderRadius: "2px",
                    },
                    children: [],
                  },
                },
                {
                  type: "span",
                  props: {
                    style: { display: "flex", fontSize: "14px", color: COLORS.muted, letterSpacing: "0.04em" },
                    children: "Independent Local News",
                  },
                },
              ],
            },
          },
        ],
      },
    },
    {
      width: 1200,
      height: 630,
      fonts: [
        { name: "Manrope", data: manropeBold!, weight: 700, style: "normal" as const },
        { name: "Sora", data: soraExtraBold!, weight: 800, style: "normal" as const },
      ],
    }
  );

  const png = await sharp(Buffer.from(svg)).png({ quality: 90 }).toBuffer();

  return new Response(png, {
    headers: {
      "Content-Type": "image/png",
      "Cache-Control": "public, max-age=86400",
    },
  });
};
