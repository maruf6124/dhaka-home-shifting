"use client";

import { useEffect } from "react";
import { CloseIcon } from "./icons";

export const btn = {
  primary:
    "inline-flex items-center justify-center gap-2 rounded-xl bg-teal-700 px-5 min-h-[48px] font-bold text-white hover:bg-teal-800 disabled:opacity-50 disabled:cursor-not-allowed",
  outline:
    "inline-flex items-center justify-center gap-2 rounded-xl border-[1.5px] border-teal-700 bg-white px-4 min-h-[44px] font-bold text-teal-700 hover:bg-teal-50 disabled:opacity-50",
  ghost:
    "inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-4 min-h-[44px] font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50",
  danger:
    "inline-flex items-center justify-center gap-2 rounded-xl bg-red-700 px-4 min-h-[44px] font-bold text-white hover:bg-red-800 disabled:opacity-50",
};

export const input =
  "w-full min-h-[48px] rounded-xl border border-slate-300 bg-white px-3.5 text-[15px] font-normal text-slate-900 placeholder:text-slate-400 focus:border-teal-700 focus:outline-none focus:ring-2 focus:ring-teal-700/20";

export const card = "rounded-2xl border border-slate-200 bg-white";

export function Field({ label, hint, error, children }: { label: string; hint?: string; error?: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5 text-sm font-semibold text-slate-800">
      {label}
      {children}
      {hint && !error && <span className="text-xs font-normal text-slate-500">{hint}</span>}
      {error && <span className="text-xs font-semibold text-red-700">{error}</span>}
    </label>
  );
}

export function Alert({ kind = "error", children }: { kind?: "error" | "ok" | "info" | "warn"; children: React.ReactNode }) {
  const styles = {
    error: "bg-red-50 border-red-200 text-red-800",
    ok: "bg-green-50 border-green-200 text-green-800",
    info: "bg-teal-50 border-teal-200 text-teal-900",
    warn: "bg-amber-50 border-amber-200 text-amber-900",
  }[kind];
  return (
    <div role={kind === "error" ? "alert" : "status"} className={`rounded-xl border px-3.5 py-2.5 text-sm leading-relaxed ${styles}`}>
      {children}
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div role="status" className="flex items-center justify-center gap-2 py-10 text-slate-500">
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-teal-700" />
      {label && <span className="text-sm">{label}</span>}
    </div>
  );
}

export function Empty({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className={`${card} flex flex-col items-center gap-2 px-6 py-12 text-center`}>
      <p className="text-base font-bold text-slate-800">{title}</p>
      {children}
    </div>
  );
}

export function Modal({ open, onClose, title, children, label }: { open: boolean; onClose: () => void; title: string; label: string; children: React.ReactNode }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/55 sm:items-center sm:p-4" onClick={onClose}>
      <div role="dialog" aria-modal="true" aria-label={title}
        className="w-full max-w-md rounded-t-3xl bg-white p-6 shadow-2xl sm:rounded-3xl" onClick={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-start justify-between gap-4">
          <h2 className="text-xl font-bold">{title}</h2>
          <button onClick={onClose} aria-label={label} className="-m-2 flex h-11 w-11 items-center justify-center rounded-full text-slate-500 hover:bg-slate-100">
            <CloseIcon />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Badge({ tone = "slate", children }: { tone?: "slate" | "green" | "amber" | "red" | "teal" | "pink"; children: React.ReactNode }) {
  const t = {
    slate: "bg-slate-100 text-slate-700",
    green: "bg-green-100 text-green-800",
    amber: "bg-amber-100 text-amber-900",
    red: "bg-red-100 text-red-800",
    teal: "bg-teal-100 text-teal-900",
    pink: "bg-pink-100 text-pink-900",
  }[tone];
  return <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-bold ${t}`}>{children}</span>;
}
