export interface Category {
  name: string;
  slug: string;
  colour: string;
  icon: string;
}

export const CATEGORIES: Category[] = [
  { name: "Local News", slug: "local", colour: "#0a84ff", icon: "newspaper" },
  { name: "Crime", slug: "crime", colour: "#ff453a", icon: "shield" },
  { name: "Politics", slug: "politics", colour: "#bf5af2", icon: "landmark" },
  { name: "Health", slug: "health", colour: "#30d158", icon: "heart-pulse" },
  { name: "Education", slug: "education", colour: "#ffd60a", icon: "graduation-cap" },
  { name: "Transport", slug: "transport", colour: "#ff9f0a", icon: "bus" },
  { name: "Planning", slug: "planning", colour: "#64d2ff", icon: "map-pin" },
  { name: "Environment", slug: "environment", colour: "#34c759", icon: "leaf" },
  { name: "Business", slug: "business", colour: "#ac8e68", icon: "briefcase" },
  { name: "Sport", slug: "sport", colour: "#ff6482", icon: "trophy" },
  { name: "Council", slug: "council", colour: "#5e5ce6", icon: "building-2" },
  { name: "Investigation", slug: "investigation", colour: "#ff375f", icon: "search" },
  { name: "Data", slug: "data-driven", colour: "#32ade6", icon: "bar-chart-3" },
];

export function getCategoryBySlug(slug: string): Category | undefined {
  return CATEGORIES.find((c) => c.slug === slug);
}

export function getCategoryName(slug: string): string {
  return getCategoryBySlug(slug)?.name ?? slug;
}

export function getCategoryColour(slug: string): string {
  return getCategoryBySlug(slug)?.colour ?? "#0a84ff";
}
