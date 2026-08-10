import type { Film, Payload, Screening, Venue } from "./types";

export async function loadPayload(): Promise<Payload> {
  const res = await fetch("/data/screenings.json", { cache: "no-cache" });
  if (!res.ok) throw new Error(`Failed to load showtimes (HTTP ${res.status})`);
  return (await res.json()) as Payload;
}

/** Film lookup that never throws and never assumes `films` is populated. */
export function filmFor(payload: Payload, s: Screening): Film | null {
  if (!s.film_key) return null;
  return payload.films[s.film_key] ?? null;
}

/** Display title: English when TMDB matched, otherwise the marquee title. */
export function displayTitle(payload: Payload, s: Screening): string {
  return filmFor(payload, s)?.title_en || s.title_marquee;
}

/** Secondary title, shown only when it differs from the headline. */
export function secondaryTitle(payload: Payload, s: Screening): string | null {
  const en = filmFor(payload, s)?.title_en;
  return en && en !== s.title_marquee ? s.title_marquee : null;
}

export function posterUrl(film: Film | null, size: "w185" | "w500"): string | null {
  if (!film?.poster_path) return null;
  return `https://image.tmdb.org/t/p/${size}${film.poster_path}`;
}

export function venueMap(payload: Payload): Map<string, Venue> {
  return new Map(payload.venues.map((v) => [v.id, v]));
}
