/**
 * Category-based article image selection.
 * Maps article categories to placeholder images in /images/categories/.
 */

const CATEGORY_IMAGES: Record<string, string> = {
  crime: "/images/categories/crime.jpg",
  politics: "/images/categories/politics.jpg",
  health: "/images/categories/health.jpg",
  education: "/images/categories/education.jpg",
  transport: "/images/categories/transport.jpg",
  sport: "/images/categories/sport.jpg",
  environment: "/images/categories/environment.jpg",
  planning: "/images/categories/planning.jpg",
  business: "/images/categories/business.jpg",
  council: "/images/categories/council.jpg",
  local: "/images/categories/local.jpg",
  investigation: "/images/categories/magnifying-glass.jpg",
  "data-driven": "/images/categories/data-driven.jpg",
};

const DEFAULT_IMAGE = "/images/categories/local.jpg";

export function categoryImage(category: string): string {
  return CATEGORY_IMAGES[category] || DEFAULT_IMAGE;
}
