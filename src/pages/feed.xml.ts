import type { APIRoute } from "astro";
import { SITE_NAME, SITE_URL, escapeXml } from "../lib/site";
import { getCollection } from "astro:content";
import { getBoroughName } from "../data/boroughs";
import { articleSlug } from "../lib/articles";

export const prerender = true;

export const GET: APIRoute = async () => {
  const articles = (await getCollection("articles"))
    .sort((a, b) => b.data.date.localeCompare(a.data.date))
    .slice(0, 50);

  const lastBuild = articles[0]?.data.date ?? new Date().toISOString().split("T")[0];

  const items = articles.map(
    (a) => `    <item>
      <title>${escapeXml(a.data.headline)}</title>
      <link>${SITE_URL}/${a.data.borough}/${articleSlug(a)}/</link>
      <guid isPermaLink="true">${SITE_URL}/${a.data.borough}/${articleSlug(a)}/</guid>
      <pubDate>${new Date(a.data.date).toUTCString()}</pubDate>
      <description>${escapeXml(a.data.summary)}</description>
      <category>${escapeXml(getBoroughName(a.data.borough))}</category>
      <category>${escapeXml(a.data.category)}</category>
      <source url="${SITE_URL}/feed.xml">${escapeXml(SITE_NAME)}</source>
    </item>`
  );

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>${escapeXml(SITE_NAME)}</title>
    <link>${SITE_URL}</link>
    <description>Independent local news for Lancashire. Quality journalism covering all 14 boroughs.</description>
    <language>en-gb</language>
    <lastBuildDate>${new Date(lastBuild).toUTCString()}</lastBuildDate>
    <ttl>60</ttl>
    <atom:link href="${SITE_URL}/feed.xml" rel="self" type="application/rss+xml" />
${items.join("\n")}
  </channel>
</rss>`;

  return new Response(xml, {
    headers: { "Content-Type": "application/rss+xml; charset=utf-8" },
  });
};
