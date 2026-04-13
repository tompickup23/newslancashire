import type { APIRoute } from "astro";
import { SITE_URL, escapeXml } from "../lib/site";
import { getCollection } from "astro:content";
import { articleSlug } from "../lib/articles";

export const prerender = true;

export const GET: APIRoute = async () => {
  const articles = await getCollection("articles");

  const entries = articles
    .sort((a, b) => b.data.date.localeCompare(a.data.date))
    .map(
      (article) =>
        `  <url>
    <loc>${SITE_URL}/${article.data.borough}/${articleSlug(article)}/</loc>
    <news:news>
      <news:publication>
        <news:name>News Lancashire</news:name>
        <news:language>en</news:language>
      </news:publication>
      <news:publication_date>${article.data.date}</news:publication_date>
      <news:title>${escapeXml(article.data.headline)}</news:title>
    </news:news>
  </url>`
    );

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
${entries.join("\n")}
</urlset>`;

  return new Response(xml, {
    headers: { "Content-Type": "application/xml; charset=utf-8" },
  });
};
