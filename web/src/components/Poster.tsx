import type { Film } from "../types";
import { posterUrl } from "../data";

export function Poster({ film, size = "w185", alt }: {
  film: Film | null; size?: "w185" | "w500"; alt: string;
}) {
  const url = posterUrl(film, size);
  if (!url) return null;
  return (
    <img
      className={`poster poster-${size}`}
      src={url}
      alt={alt}
      loading="lazy"
      decoding="async"
    />
  );
}
