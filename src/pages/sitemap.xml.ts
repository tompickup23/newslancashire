import type { APIRoute } from "astro";
import { SITE_URL } from "../lib/site";
import { getCollection } from "astro:content";
import { BOROUGHS } from "../data/boroughs";
import { CATEGORIES } from "../data/categories";
import { articleSlug } from "../lib/articles";

export const prerender = true;

export const GET: APIRoute = async () => {
  const articles = await getCollection("articles");
  const today = new Date().toISOString().split("T")[0];

  const staticPages = [
    { path: "/", priority: "1.0", changefreq: "daily" },
    { path: "/latest/", priority: "0.9", changefreq: "daily" },
    { path: "/investigations/", priority: "0.8", changefreq: "weekly" },
    { path: "/about/", priority: "0.5", changefreq: "monthly" },
    { path: "/newsletter/", priority: "0.5", changefreq: "monthly" },
    { path: "/privacy/", priority: "0.3", changefreq: "yearly" },
    { path: "/cookies/", priority: "0.3", changefreq: "yearly" },
    { path: "/accessibility/", priority: "0.3", changefreq: "yearly" },
  ];

  const urls = [
    ...staticPages.map(
      (p) =>
        `  <url>\n    <loc>${SITE_URL}${p.path}</loc>\n    <lastmod>${today}</lastmod>\n    <changefreq>${p.changefreq}</changefreq>\n    <priority>${p.priority}</priority>\n  </url>`
    ),
    // Borough pages
    ...BOROUGHS.map(
      (b) =>
        `  <url>\n    <loc>${SITE_URL}/${b.slug}/</loc>\n    <lastmod>${today}</lastmod>\n    <changefreq>daily</changefreq>\n    <priority>0.8</priority>\n  </url>`
    ),
    // Lancashire-wide
    `  <url>\n    <loc>${SITE_URL}/lancashire-wide/</loc>\n    <lastmod>${today}</lastmod>\n    <changefreq>daily</changefreq>\n    <priority>0.7</priority>\n  </url>`,
    // Category pages
    ...CATEGORIES.map(
      (c) =>
        `  <url>\n    <loc>${SITE_URL}/${c.slug}/</loc>\n    <lastmod>${today}</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>0.6</priority>\n  </url>`
    ),
    // Articles
    ...articles.map(
      (a) =>
        `  <url>\n    <loc>${SITE_URL}/${a.data.borough}/${articleSlug(a)}/</loc>\n    <lastmod>${a.data.updated || a.data.date}</lastmod>\n    <changefreq>monthly</changefreq>\n    <priority>0.7</priority>\n  </url>`
    ),
  ];

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.join("\n")}
</urlset>`;

  return new Response(xml, {
    headers: { "Content-Type": "application/xml; charset=utf-8" },
  });
};
