import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatMoney(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === "") return "";
  const amount = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(amount)) return String(value);
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(amount);
}

export function discountPercent(price: string, compare: string | null) {
  if (!compare) return null;
  const current = Number(price);
  const was = Number(compare);
  if (!was || was <= current) return null;
  return Math.round(((was - current) / was) * 100);
}
