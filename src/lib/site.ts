export const SITE_NAME = "News Lancashire";
export const SITE_URL = "https://newslancashire.co.uk";
export const DEFAULT_DESCRIPTION =
  "Independent local news for Lancashire. Quality journalism covering Burnley, Pendle, Hyndburn, Preston, Lancaster, and all 14 boroughs. No ads. No clickbait. Just news.";
export const DEFAULT_SOCIAL_IMAGE_PATH = "/og/home.png";

export type StructuredDataNode = Record<string, unknown>;

export function normalisePageTitle(title: string): string {
  if (/news\s*lancashire/i.test(title)) return title;
  return `${title} | ${SITE_NAME}`;
}

export function buildAbsoluteUrl(pathname: string): string {
  const normalizedPath = pathname.startsWith("/") ? pathname : `/${pathname}`;
  return new URL(normalizedPath, SITE_URL).toString();
}

export function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export function formatDateShort(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
  });
}

export function readingTime(text: string): string {
  const words = text.split(/\s+/).length;
  const mins = Math.max(1, Math.ceil(words / 230));
  return `${mins} min read`;
}

export function escapeXml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}
