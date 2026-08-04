import { useEffect, useState } from "react";

import { api } from "../api/client";

export interface Stats {
  companies: number;
  filings: number;
}

/** Loads top-line counts for the header stat tiles. Best-effort (silent on error). */
export function useStats(refreshKey: number): Stats | null {
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.listCompanies(), api.listFilings()])
      .then(([companies, filings]) => {
        if (!cancelled) setStats({ companies: companies.length, filings: filings.length });
      })
      .catch(() => {
        if (!cancelled) setStats(null);
      });
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  return stats;
}
