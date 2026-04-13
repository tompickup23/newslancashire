export interface Borough {
  name: string;
  slug: string;
  council_url: string;
  population: number;
  colour: string;
  mp: string;
  constituency: string;
}

export const BOROUGHS: Borough[] = [
  { name: "Burnley", slug: "burnley", council_url: "https://www.burnley.gov.uk", population: 87_600, colour: "#0a84ff", mp: "Oliver Ryan", constituency: "Burnley" },
  { name: "Pendle", slug: "pendle", council_url: "https://www.pendle.gov.uk", population: 92_000, colour: "#30d158", mp: "Jonathan Hinder", constituency: "Pendle and Clitheroe" },
  { name: "Hyndburn", slug: "hyndburn", council_url: "https://www.hyndburnbc.gov.uk", population: 81_000, colour: "#ff9f0a", mp: "Sarah Smith", constituency: "Hyndburn" },
  { name: "Rossendale", slug: "rossendale", council_url: "https://www.rossendale.gov.uk", population: 70_000, colour: "#bf5af2", mp: "Andy MacNae", constituency: "Rossendale and Darwen" },
  { name: "Ribble Valley", slug: "ribble-valley", council_url: "https://www.ribblevalley.gov.uk", population: 61_000, colour: "#64d2ff", mp: "Maya Ellis", constituency: "Pendle and Clitheroe" },
  { name: "Lancaster", slug: "lancaster", council_url: "https://www.lancaster.gov.uk", population: 144_000, colour: "#ff453a", mp: "Cat Smith", constituency: "Lancaster and Wyre" },
  { name: "Wyre", slug: "wyre", council_url: "https://www.wyre.gov.uk", population: 111_000, colour: "#ffd60a", mp: "Cat Smith", constituency: "Lancaster and Wyre" },
  { name: "Fylde", slug: "fylde", council_url: "https://new.fylde.gov.uk", population: 80_000, colour: "#ac8e68", mp: "Bill Esterson", constituency: "Fylde" },
  { name: "Chorley", slug: "chorley", council_url: "https://www.chorley.gov.uk", population: 117_000, colour: "#ff6482", mp: "Sir Lindsay Hoyle", constituency: "Chorley" },
  { name: "South Ribble", slug: "south-ribble", council_url: "https://www.southribble.gov.uk", population: 111_000, colour: "#5e5ce6", mp: "Paul Foster", constituency: "South Ribble" },
  { name: "Preston", slug: "preston", council_url: "https://www.preston.gov.uk", population: 144_000, colour: "#ff375f", mp: "Sir Mark Hendrick", constituency: "Preston" },
  { name: "West Lancashire", slug: "west-lancashire", council_url: "https://www.westlancs.gov.uk", population: 114_000, colour: "#30b0c7", mp: "Ashley Sherborne-Maycock", constituency: "West Lancashire" },
  { name: "Blackpool", slug: "blackpool", council_url: "https://www.blackpool.gov.uk", population: 141_000, colour: "#ff9500", mp: "Chris Webb", constituency: "Blackpool South" },
  { name: "Blackburn", slug: "blackburn", council_url: "https://www.blackburn.gov.uk", population: 149_000, colour: "#32ade6", mp: "Adnan Hussain", constituency: "Blackburn" },
];

export const LANCASHIRE_WIDE = {
  name: "Lancashire",
  slug: "lancashire-wide",
  colour: "#0a84ff",
};

export function getBoroughBySlug(slug: string): Borough | undefined {
  return BOROUGHS.find((b) => b.slug === slug);
}

export function getBoroughName(slug: string): string {
  if (slug === "lancashire-wide") return "Lancashire";
  return getBoroughBySlug(slug)?.name ?? slug;
}
