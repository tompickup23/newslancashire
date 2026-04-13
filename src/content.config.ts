import { defineCollection, z } from "astro:content";

export const BOROUGHS = [
  "burnley",
  "pendle",
  "hyndburn",
  "rossendale",
  "ribble-valley",
  "lancaster",
  "wyre",
  "fylde",
  "chorley",
  "south-ribble",
  "preston",
  "west-lancashire",
  "blackpool",
  "blackburn",
  "lancashire-wide",
] as const;

export const CATEGORIES = [
  "local",
  "crime",
  "politics",
  "health",
  "education",
  "transport",
  "planning",
  "environment",
  "business",
  "sport",
  "council",
  "investigation",
  "data-driven",
] as const;

export const CONTENT_TIERS = [
  "summary",
  "analysis",
  "investigation",
  "cross-publish",
  "data-driven",
] as const;

const articles = defineCollection({
  type: "content",
  schema: z.object({
    headline: z.string(),
    date: z.string(),
    updated: z.string().optional(),
    category: z.enum(CATEGORIES),
    borough: z.enum(BOROUGHS),
    source: z.string(),
    source_url: z.string().url(),
    interest_score: z.number().min(0).max(100).default(50),
    content_tier: z.enum(CONTENT_TIERS).default("summary"),
    cross_project: z.string().optional(),
    summary: z.string(),
    fact_check_score: z.number().min(0).max(100).optional(),
    image_alt: z.string().optional(),
  }),
});

export const collections = { articles };
