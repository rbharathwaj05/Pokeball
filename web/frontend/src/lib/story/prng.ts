/**
 * web/frontend/src/lib/story/prng.ts — Seeded PRNG for deterministic story generation.
 * Zero Math.random, zero Date dependencies.
 */

export function hashString(str: string): number {
  let hash = 0x811c9dc5;
  for (let i = 0; i < str.length; i++) {
    hash ^= str.charCodeAt(i);
    hash += (hash << 1) + (hash << 4) + (hash << 7) + (hash << 8) + (hash << 24);
  }
  return hash >>> 0;
}

export function mulberry32(seed: number): () => number {
  return function () {
    let t = (seed += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function seededChoice<T>(items: T[], seed: number): T {
  if (!items || items.length === 0) {
    throw new Error("Cannot select from empty array");
  }
  const rng = mulberry32(seed >>> 0);
  const idx = Math.floor(rng() * items.length);
  return items[idx];
}
