import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function resolveImageUrl(path: string | null | undefined): string {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  // Django serves media at /media/. Use that path directly — nginx proxies
  // /media/* → backend, regardless of NEXT_PUBLIC_API_URL.
  const cleanPath = path.replace(/^\//, "");
  if (cleanPath.startsWith("media/")) {
    return `/${cleanPath}`;
  }
  return `/media/${cleanPath}`;
}
