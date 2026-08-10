export type Kind = "independent" | "chain";
export type Coverage = "allocine" | "operator" | "none";
export type Version = "VO" | "VOST" | "VF" | "UNKNOWN";

export interface Venue {
  id: string;
  name: string;
  arrondissement: number;
  kind: Kind;
  chain: string | null;
  coverage: Coverage;
  accessibility: Record<string, unknown> | null;
}

export interface Film {
  tmdb_id: number | null;
  title_en: string | null;
  overview: string | null;
  poster_path: string | null;
  backdrop_path: string | null;
  runtime: number | null;
  year: number | null;
}

export interface Screening {
  venue_id: string;
  start_utc: string;
  title_marquee: string;
  film_key: string | null;
  version: Version;
  booking_url: string | null;
  source: string;
  is_event: boolean;
  fetched_at: string;
}

export interface SourceStatus {
  slug: string;
  ok: boolean;
  ok_venues: number;
  failed_venues: Record<string, string>;
}

export interface Payload {
  generated_at: string;
  sources: SourceStatus[];
  venues: Venue[];
  films: Record<string, Film>;
  screenings: Screening[];
}
