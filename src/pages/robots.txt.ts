import type { APIRoute } from "astro";
import { SITE_URL } from "../lib/site";

export const prerender = true;

export const GET: APIRoute = async () => {
  const body = `User-agent: *
Allow: /

Sitemap: ${SITE_URL}/sitemap.xml
Sitemap: ${SITE_URL}/news-sitemap.xml
`;

  return new Response(body, {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
};
