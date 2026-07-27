import type { NextRequest } from "next/server";

const PRODUCTION_COOKIE = "__Host-vol_reading_access";
const DEVELOPMENT_COOKIE = "vol_reading_access";

export function paidReadingCookieName() {
  return process.env.NODE_ENV === "production"
    ? PRODUCTION_COOKIE
    : DEVELOPMENT_COOKIE;
}

export function paidReadingTokenFromRequest(request: NextRequest) {
  return request.cookies.get(paidReadingCookieName())?.value ?? null;
}

export function paidReadingCookieOptions(expiresAt: string) {
  return {
    expires: new Date(expiresAt),
    httpOnly: true,
    path: "/",
    priority: "high" as const,
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production",
  };
}
