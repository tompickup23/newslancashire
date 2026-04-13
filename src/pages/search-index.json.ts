import type { APIRoute } from "astro";
import { getCollection } from "astro:content";
import { getBoroughName } from "../data/boroughs";
import { getCategoryName } from "../data/categories";
import { articlePath } from "../lib/articles";

export const prerender = true;

export const GET: APIRoute = async () => {
  const articles = await getCollection("articles");

  const entries = articles.map((a) => ({
    href: articlePath(a),
    title: a.data.headline,
    kind: a.data.content_tier === "investigation" ? "investigation" : "article",
    kicker: getBoroughName(a.data.borough),
    description: a.data.summary,
    priority: a.data.interest_score,
    searchText: `${a.data.headline} ${a.data.summary} ${getBoroughName(a.data.borough)} ${getCategoryName(a.data.category)}`.toLowerCase(),
  }));

  return new Response(JSON.stringify(entries), {
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
};
