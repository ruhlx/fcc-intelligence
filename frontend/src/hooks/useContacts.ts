import { useEffect, useState } from "react";

import { ApiError, api } from "../api/client";
import type { Contact, ContactFilters } from "../api/types";

interface ContactsState {
  contacts: Contact[];
  loading: boolean;
  error: string | null;
}

/**
 * Fetches contacts whenever the (already-debounced) filters change, or when
 * ``refreshToken`` is bumped (e.g. after an ingestion run completes).
 */
export function useContacts(filters: ContactFilters, refreshToken = 0): ContactsState {
  const [state, setState] = useState<ContactsState>({
    contacts: [],
    loading: true,
    error: null,
  });

  const key = `${JSON.stringify(filters)}::${refreshToken}`;

  useEffect(() => {
    let cancelled = false;
    setState((s) => ({ ...s, loading: true, error: null }));

    api
      .listContacts(filters)
      .then((contacts) => {
        if (!cancelled) setState({ contacts, loading: false, error: null });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const message = err instanceof ApiError ? err.message : "Unexpected error";
        setState({ contacts: [], loading: false, error: message });
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  return state;
}

/** Debounces a rapidly-changing value (e.g. text-input filters). */
export function useDebounced<T>(value: T, delayMs = 300): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);
  return debounced;
}
