import type { CollectionEntry } from "astro:content";

/** Strip .md extension from article ID for clean URLs */
export function articleSlug(article: CollectionEntry<"articles">): string {
  return article.id.replace(/\.md$/, "");
}

/** Build article URL path */
export function articlePath(article: CollectionEntry<"articles">): string {
  return `/${article.data.borough}/${articleSlug(article)}/`;
}
