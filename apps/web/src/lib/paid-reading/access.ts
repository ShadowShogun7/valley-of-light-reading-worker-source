import {
  buildAccessToken,
  verifyAccessToken,
} from "@/lib/paid-reading/crypto";
import { getPaidAccessEnvironment } from "@/lib/paid-reading/env";

export function authorizeReadingToken(token: string) {
  const environment = getPaidAccessEnvironment();
  return verifyAccessToken(token, environment.VALLEY_ACCESS_SIGNING_SECRET);
}

export function buildReadingAccess({
  expiresAt,
  grantId,
}: {
  expiresAt: string;
  grantId: string;
}) {
  const environment = getPaidAccessEnvironment();
  const token = buildAccessToken({
    expiresAt,
    grantId,
    signingSecret: environment.VALLEY_ACCESS_SIGNING_SECRET,
  });
  const appBaseUrl = environment.VALEOFLIGHT_APP_BASE_URL.replace(/\/+$/, "");
  return {
    token,
    url: `${appBaseUrl}/r#${encodeURIComponent(token)}`,
  };
}
