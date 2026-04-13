/**
 * Smart article image selection.
 *
 * Priority order:
 *   1. Keyword match (death → memorial, roadworks → roadworks photo, football club → ground)
 *   2. Borough + category combo (council story in Burnley → Burnley Town Hall)
 *   3. Borough-specific landmark (any story in Blackpool → Tower)
 *   4. Category fallback (crime → police photo)
 *
 * All images are CC BY-SA 2.0 (Geograph/Wikimedia) or free (Unsplash/Pexels).
 * Attribution shown on article pages via imageCredit().
 */

// ── Borough civic buildings (for council/politics stories) ──
const BOROUGH_CIVIC: Record<string, string> = {
  burnley: "/images/boroughs/burnley-town-hall.jpg",
  pendle: "/images/boroughs/pendle-town-hall.jpg",
  hyndburn: "/images/boroughs/hyndburn-town-hall.jpg",
  rossendale: "/images/boroughs/rossendale-town.jpg",
  "ribble-valley": "/images/boroughs/ribble-valley-castle.jpg",
  lancaster: "/images/boroughs/lancaster-ashton-memorial.jpg",
  blackburn: "/images/boroughs/blackburn-town-hall.jpg",
  blackpool: "/images/boroughs/blackpool-tower.jpg",
  preston: "/images/boroughs/preston-harris-museum.jpg",
  chorley: "/images/boroughs/chorley-town-hall.jpg",
  "south-ribble": "/images/boroughs/south-ribble-civic.jpg",
  "west-lancashire": "/images/boroughs/west-lancashire-ormskirk.jpg",
  wyre: "/images/boroughs/wyre-poulton.jpg",
  fylde: "/images/boroughs/fylde-lytham-hall.jpg",
  "lancashire-wide": "/images/boroughs/lancashire-county-hall.jpg",
};

// ── Football grounds (for sport stories mentioning clubs) ──
const FOOTBALL_GROUNDS: Record<string, { image: string; keywords: string[] }> = {
  burnley: { image: "/images/sport/turf-moor-burnley.jpg", keywords: ["burnley fc", "turf moor", "clarets"] },
  blackburn: { image: "/images/sport/ewood-park-blackburn.jpg", keywords: ["blackburn rovers", "ewood park", "rovers"] },
  preston: { image: "/images/sport/deepdale-preston.jpg", keywords: ["preston north end", "deepdale", "pne"] },
  blackpool: { image: "/images/sport/bloomfield-road-blackpool.jpg", keywords: ["blackpool fc", "bloomfield road", "seasiders"] },
  hyndburn: { image: "/images/sport/wham-stadium-accrington.jpg", keywords: ["accrington stanley", "wham stadium"] },
};

// ── Sensitive topic keywords → memorial images ──
const SENSITIVE_KEYWORDS = [
  "death", "died", "killed", "fatal", "murder", "manslaughter",
  "funeral", "tribute", "memorial", "tragedy", "tragic", "passed away",
  "lost life", "lost lives", "inquest", "coroner",
];

const SENSITIVE_IMAGES = [
  "/images/sensitive/memorial-flowers.jpg",
  "/images/sensitive/candles-memorial.jpg",
  "/images/sensitive/church-memorial.jpg",
];

// ── Transport keywords → specific images ──
const TRANSPORT_KEYWORDS: { keywords: string[]; image: string }[] = [
  { keywords: ["roadworks", "road closure", "road closed", "resurfacing", "pothole"], image: "/images/transport/roadworks.jpg" },
  { keywords: ["m6", "m65", "m55", "motorway", "a59", "a56"], image: "/images/transport/motorway.jpg" },
  { keywords: ["m6 lancaster", "m6 north"], image: "/images/transport/m6-lancaster.jpg" },
];

// ── Category fallbacks ──
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

// ── Credits ──
const GEOGRAPH_CREDIT = "Geograph (CC BY-SA 2.0)";
const WIKIMEDIA_CREDIT = "Wikimedia Commons (CC BY-SA 2.0)";
const UNSPLASH_CREDIT = "Unsplash";
const PEXELS_CREDIT = "Pexels";

/**
 * Select the best image for an article.
 * @param category - Article category (crime, politics, etc.)
 * @param borough - Borough slug (burnley, preston, lancashire-wide, etc.)
 * @param headline - Article headline for keyword matching
 * @param summary - Article summary for keyword matching
 */
export function selectImage(
  category: string,
  borough: string,
  headline: string = "",
  summary: string = ""
): string {
  const text = `${headline} ${summary}`.toLowerCase();

  // 1. Sensitive content check (highest priority — respectful imagery)
  if (SENSITIVE_KEYWORDS.some((kw) => text.includes(kw))) {
    // Deterministic selection based on headline hash
    const idx = Math.abs(simpleHash(headline)) % SENSITIVE_IMAGES.length;
    return SENSITIVE_IMAGES[idx];
  }

  // 2. Sport: check for specific football club mentions
  if (category === "sport") {
    for (const [, club] of Object.entries(FOOTBALL_GROUNDS)) {
      if (club.keywords.some((kw) => text.includes(kw))) {
        return club.image;
      }
    }
    // Fallback: if borough has a football ground, use it
    if (FOOTBALL_GROUNDS[borough]) {
      return FOOTBALL_GROUNDS[borough].image;
    }
  }

  // 3. Transport: keyword-specific images
  if (category === "transport") {
    for (const rule of TRANSPORT_KEYWORDS) {
      if (rule.keywords.some((kw) => text.includes(kw))) {
        return rule.image;
      }
    }
  }

  // 4. Council/politics: use borough civic building
  if (category === "council" || category === "politics") {
    if (BOROUGH_CIVIC[borough]) {
      return BOROUGH_CIVIC[borough];
    }
  }

  // 5. Category fallback
  return CATEGORY_IMAGES[category] || DEFAULT_IMAGE;
}

/**
 * Get image credit text for attribution.
 */
export function imageCredit(imagePath: string): string {
  if (imagePath.includes("/boroughs/") || imagePath.includes("/sport/turf") || imagePath.includes("/sport/ewood") || imagePath.includes("/sport/deepdale") || imagePath.includes("/sport/bloomfield") || imagePath.includes("/sport/wham") || imagePath.includes("/transport/m6")) {
    return GEOGRAPH_CREDIT;
  }
  if (imagePath.includes("/sensitive/")) {
    return PEXELS_CREDIT;
  }
  return UNSPLASH_CREDIT;
}

/** Simple string hash for deterministic image selection */
function simpleHash(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = ((h << 5) - h + s.charCodeAt(i)) | 0;
  }
  return h;
}

/** Legacy function — use selectImage() for new code */
export function categoryImage(category: string): string {
  return CATEGORY_IMAGES[category] || DEFAULT_IMAGE;
}
