import type { Venue } from "./types";

// Approximate arrondissement centroids (from OpenStreetMap).
const CENTROIDS: Record<number, { lat: number; lng: number }> = {
  1: { lat: 48.863, lng: 2.335 },
  2: { lat: 48.868, lng: 2.344 },
  3: { lat: 48.864, lng: 2.360 },
  4: { lat: 48.856, lng: 2.357 },
  5: { lat: 48.843, lng: 2.350 },
  6: { lat: 48.851, lng: 2.334 },
  7: { lat: 48.856, lng: 2.312 },
  8: { lat: 48.873, lng: 2.308 },
  9: { lat: 48.878, lng: 2.339 },
  10: { lat: 48.876, lng: 2.361 },
  11: { lat: 48.859, lng: 2.378 },
  12: { lat: 48.840, lng: 2.389 },
  13: { lat: 48.832, lng: 2.356 },
  14: { lat: 48.833, lng: 2.327 },
  15: { lat: 48.841, lng: 2.299 },
  16: { lat: 48.864, lng: 2.273 },
  17: { lat: 48.884, lng: 2.317 },
  18: { lat: 48.892, lng: 2.347 },
  19: { lat: 48.882, lng: 2.381 },
  20: { lat: 48.862, lng: 2.399 },
};

export const MAP_WIDTH = 360;
export const MAP_HEIGHT = 320;

// Paris bounds for the SVG projection.
const B = { north: 48.902, south: 48.808, west: 2.244, east: 2.424 };

function project(lat: number, lng: number): { x: number; y: number } {
  return {
    x: ((lng - B.west) / (B.east - B.west)) * MAP_WIDTH,
    y: ((B.north - lat) / (B.north - B.south)) * MAP_HEIGHT,
  };
}

/** Deterministic hash of a string to a 0..1 float. */
function hashFloat(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return ((h >>> 0) % 10000) / 10000;
}

/** SVG position for a venue: arrondissement centroid + deterministic jitter. */
export function venuePosition(venue: Venue): { x: number; y: number } {
  const c = CENTROIDS[venue.arrondissement] ?? { lat: 48.856, lng: 2.335 };
  const lat = c.lat + (hashFloat(venue.id + "y") - 0.5) * 0.008;
  const lng = c.lng + (hashFloat(venue.id) - 0.5) * 0.008;
  return project(lat, lng);
}

/** Hand-drawn Seine path (rough S-curve through central Paris). */
export const SEINE_PATH =
  "M 312 252 Q 280 230 252 194 Q 230 170 202 160 Q 190 155 172 143 Q 130 135 92 143 Q 60 155 32 190 Q 18 215 12 245";

/** Arrondissement number labels, precomputed in SVG coordinates. */
export const ARRONDISSEMENT_LABELS: { num: number; x: number; y: number }[] =
  Object.entries(CENTROIDS).map(([num, c]) => ({
    num: Number(num),
    ...project(c.lat, c.lng),
  }));
