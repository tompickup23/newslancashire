import { useEffect, useRef, useState } from "preact/hooks";

interface SearchEntry {
  href: string;
  title: string;
  kind: string;
  kicker: string;
  description: string;
  priority: number;
  searchText: string;
}

export default function SearchDialog() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchEntry[]>([]);
  const [selected, setSelected] = useState(0);
  const [index, setIndex] = useState<SearchEntry[] | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Load search index on first open
  useEffect(() => {
    if (!open || index) return;
    fetch("/search-index.json")
      .then((r) => r.json())
      .then((data) => setIndex(data))
      .catch(() => setIndex([]));
  }, [open]);

  // Keyboard shortcut: Cmd+K / Ctrl+K
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", onKey);

    // Listen for search trigger button
    const btn = document.getElementById("search-trigger");
    const handler = () => setOpen(true);
    btn?.addEventListener("click", handler);

    return () => {
      document.removeEventListener("keydown", onKey);
      btn?.removeEventListener("click", handler);
    };
  }, []);

  // Focus input when opening
  useEffect(() => {
    if (open) {
      setQuery("");
      setResults([]);
      setSelected(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  // Fuzzy search
  useEffect(() => {
    if (!index || !query.trim()) {
      setResults([]);
      setSelected(0);
      return;
    }
    const q = query.toLowerCase().trim();
    const tokens = q.split(/\s+/);
    const scored = index
      .map((entry) => {
        const text = entry.searchText;
        let score = 0;
        for (const t of tokens) {
          if (!text.includes(t)) return null;
          // Title match scores higher
          if (entry.title.toLowerCase().includes(t)) score += 10;
          else score += 1;
        }
        score += entry.priority / 20; // Boost high-interest articles
        return { entry, score };
      })
      .filter(Boolean) as { entry: SearchEntry; score: number }[];

    scored.sort((a, b) => b.score - a.score);
    setResults(scored.slice(0, 12).map((s) => s.entry));
    setSelected(0);
  }, [query, index]);

  // Arrow key navigation
  function onKeyDown(e: KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelected((s) => Math.min(s + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelected((s) => Math.max(s - 1, 0));
    } else if (e.key === "Enter" && results[selected]) {
      e.preventDefault();
      window.location.href = results[selected].href;
    }
  }

  if (!open) return null;

  return (
    <div
      class="search-overlay"
      onClick={(e) => {
        if ((e.target as HTMLElement).classList.contains("search-overlay"))
          setOpen(false);
      }}
    >
      <div class="search-dialog">
        <div class="search-input-wrap">
          <svg
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            viewBox="0 0 24 24"
            style={{ opacity: 0.4, flexShrink: 0 }}
          >
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.35-4.35" />
          </svg>
          <input
            ref={inputRef}
            type="text"
            class="search-input"
            placeholder="Search articles..."
            value={query}
            onInput={(e) => setQuery((e.target as HTMLInputElement).value)}
            onKeyDown={onKeyDown}
            aria-label="Search articles"
          />
          <kbd class="search-kbd">ESC</kbd>
        </div>

        {query.trim() && (
          <div class="search-results">
            {results.length === 0 && index && (
              <div class="search-empty">No articles match "{query}"</div>
            )}
            {!index && (
              <div class="search-empty">Loading search index...</div>
            )}
            {results.map((r, i) => (
              <a
                href={r.href}
                class={`search-result ${i === selected ? "search-result--active" : ""}`}
                onMouseEnter={() => setSelected(i)}
              >
                <div class="search-result-title">{r.title}</div>
                <div class="search-result-meta">
                  <span class="search-result-kicker">{r.kicker}</span>
                  {r.kind === "investigation" && (
                    <span class="search-result-badge">Investigation</span>
                  )}
                </div>
              </a>
            ))}
          </div>
        )}

        {!query.trim() && (
          <div class="search-hint">
            Type to search across all articles, boroughs, and categories
          </div>
        )}
      </div>
    </div>
  );
}
