import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { getPaidAccessEnvironment } from "@/lib/paid-reading/env";

let cachedClient: SupabaseClient | undefined;

export function getPaidReadingDatabase() {
  if (!cachedClient) {
    const environment = getPaidAccessEnvironment();
    cachedClient = createClient(
      environment.VALLEY_SUPABASE_URL,
      environment.VALLEY_SUPABASE_SERVICE_ROLE_KEY,
      {
        auth: {
          autoRefreshToken: false,
          detectSessionInUrl: false,
          persistSession: false,
        },
        global: {
          headers: {
            "X-Client-Info": "valeoflight-paid-reading/1",
          },
        },
      }
    );
  }
  return cachedClient;
}

export function resetPaidReadingDatabaseForTests() {
  cachedClient = undefined;
}
