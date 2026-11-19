"use client";

import { useEffect, useState } from "react";
import { api } from "./api";

export type Area = { id: number; name_bn: string; name_en: string; parent_id: number | null };

let cache: Area[] | null = null;

export function useAreas(): Area[] {
  const [areas, setAreas] = useState<Area[]>(cache || []);
  useEffect(() => {
    if (cache) return;
    api<Area[]>("/areas").then((a) => {
      cache = a;
      setAreas(a);
    }).catch(() => undefined);
  }, []);
  return areas;
}

/** Parents followed by their children, for <select> lists. */
export function areaOptions(areas: Area[], locale: string): { id: number; label: string }[] {
  const name = (a: Area) => (locale === "en" ? a.name_en : a.name_bn);
  const out: { id: number; label: string }[] = [];
  for (const p of areas.filter((a) => a.parent_id === null)) {
    out.push({ id: p.id, label: name(p) });
    for (const c of areas.filter((a) => a.parent_id === p.id)) out.push({ id: c.id, label: `— ${name(c)}` });
  }
  return out;
}
