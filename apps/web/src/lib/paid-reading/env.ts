import { z } from "zod";

const rawEnvironmentSchema = z
  .object({
    NODE_ENV: z.enum(["development", "test", "production"]).default("development"),
    VALLEY_RUNTIME_ENV: z.enum(["development", "staging", "production"]).default("development"),
    VALEOFLIGHT_APP_BASE_URL: z.string().url(),
    VALLEY_SUPABASE_URL: z.string().url(),
    VALLEY_SUPABASE_SERVICE_ROLE_KEY: z.string().min(20),
    VALLEY_ACCESS_SIGNING_SECRET: z.string().min(32),
    VALLEY_ACCESS_GRANT_TTL_DAYS: z.coerce.number().int().min(2).max(90).default(30),
    VALLEY_INTAKE_VERSION: z.string().min(1).max(80).default("relationship-intake-v1"),
    VALLEY_GENERATION_CONSENT_VERSION: z.string().min(1).max(80),
    VALLEY_CHECKOUT_TERMS_VERSION: z
      .string()
      .regex(/^[A-Za-z0-9._:-]{1,80}$/),
    VALLEY_ACCEPTED_CHECKOUT_TERMS_VERSIONS: z.string().max(809).optional(),
    VALLEY_RETENTION_POLICY_VERSION: z.string().min(1).max(80).optional(),
    VALLEY_EMAIL_QUEUE_MAX_AGE_MINUTES: z.coerce
      .number()
      .int()
      .min(5)
      .max(1440)
      .default(15),
    CRON_SECRET: z.string().min(32).optional(),
    VALLEY_WOOCOMMERCE_RECONCILIATION_BATCH_SIZE: z.coerce
      .number()
      .int()
      .min(1)
      .max(25)
      .default(25),
    VALLEY_WOOCOMMERCE_RECONCILIATION_LOOKBACK_HOURS: z.coerce
      .number()
      .int()
      .min(1)
      .max(168)
      .default(48),
    VALLEY_WOOCOMMERCE_RECONCILIATION_MAX_AGE_MINUTES: z.coerce
      .number()
      .int()
      .min(5)
      .max(1440)
      .default(30),
    VALLEY_WOOCOMMERCE_RECONCILIATION_WINDOW_LAG_SECONDS: z.coerce
      .number()
      .int()
      .min(0)
      .max(300)
      .default(60),
    VALEOFLIGHT_WOOCOMMERCE_REST_API_URL: z.string().url().optional(),
    VALEOFLIGHT_WOOCOMMERCE_CONSUMER_KEY: z.string().min(8).optional(),
    VALEOFLIGHT_WOOCOMMERCE_CONSUMER_SECRET: z.string().min(8).optional(),
    VALEOFLIGHT_WOOCOMMERCE_WEBHOOK_SECRET: z.string().min(16).optional(),
    VALEOFLIGHT_WOOCOMMERCE_PRODUCT_ID: z.coerce.number().int().positive().optional(),
    VALEOFLIGHT_WORDPRESS_EMAIL_API_URL: z.string().url().optional(),
    VALEOFLIGHT_WORDPRESS_EMAIL_SIGNING_SECRET: z.string().min(32).optional(),
    VALEOFLIGHT_WOOCOMMERCE_EXPECTED_CURRENCY: z
      .string()
      .regex(/^[A-Z]{3}$/)
      .default("TWD"),
    VALEOFLIGHT_WOOCOMMERCE_EXPECTED_AMOUNT_MINOR: z.coerce.number().int().min(0).optional(),
    RESEND_API_KEY: z.string().min(8).optional(),
    RESEND_WEBHOOK_SECRET: z.string().min(16).optional(),
    VALEOFLIGHT_EMAIL_FROM: z.string().min(3).optional(),
    VALEOFLIGHT_EMAIL_REPLY_TO: z.string().email().optional(),
    VALEOFLIGHT_SUPPORT_EMAIL: z.string().email().optional(),
    VALLEY_AGPL_SOURCE_SHA256: z
      .string()
      .regex(/^[a-f0-9]{64}$/)
      .optional(),
    VALLEY_AGPL_SOURCE_URL: z.string().url().optional(),
    VALLEY_WORKER_URL: z.string().url().optional(),
    VALLEY_WORKER_SIGNING_SECRET: z.string().min(32).optional(),
  })
  .superRefine((value, context) => {
    if (value.NODE_ENV === "production") {
      for (const [path, candidate] of [
        ["VALEOFLIGHT_APP_BASE_URL", value.VALEOFLIGHT_APP_BASE_URL],
        ["VALLEY_SUPABASE_URL", value.VALLEY_SUPABASE_URL],
        ...(value.VALLEY_WORKER_URL
          ? ([["VALLEY_WORKER_URL", value.VALLEY_WORKER_URL]] as const)
          : []),
        ...(value.VALLEY_AGPL_SOURCE_URL
          ? ([["VALLEY_AGPL_SOURCE_URL", value.VALLEY_AGPL_SOURCE_URL]] as const)
          : []),
        ...(value.VALEOFLIGHT_WORDPRESS_EMAIL_API_URL
          ? ([
              [
                "VALEOFLIGHT_WORDPRESS_EMAIL_API_URL",
                value.VALEOFLIGHT_WORDPRESS_EMAIL_API_URL,
              ],
            ] as const)
          : []),
      ] as const) {
        if (!candidate.startsWith("https://")) {
          context.addIssue({
            code: "custom",
            message: "must use https in production",
            path: [path],
          });
        }
      }
    }

    if (Boolean(value.VALLEY_WORKER_URL) !== Boolean(value.VALLEY_WORKER_SIGNING_SECRET)) {
      context.addIssue({
        code: "custom",
        message: "VALLEY_WORKER_URL and VALLEY_WORKER_SIGNING_SECRET must be configured together",
        path: ["VALLEY_WORKER_URL"],
      });
    }
    if (
      value.VALLEY_WORKER_URL &&
      (!value.VALLEY_AGPL_SOURCE_URL || !value.VALLEY_AGPL_SOURCE_SHA256)
    ) {
      context.addIssue({
        code: "custom",
        message:
          "worker deployments require the matching public AGPL source URL and SHA-256",
        path: [
          !value.VALLEY_AGPL_SOURCE_URL
            ? "VALLEY_AGPL_SOURCE_URL"
            : "VALLEY_AGPL_SOURCE_SHA256",
        ],
      });
    }

    if (
      Boolean(value.VALEOFLIGHT_WORDPRESS_EMAIL_API_URL) !==
      Boolean(value.VALEOFLIGHT_WORDPRESS_EMAIL_SIGNING_SECRET)
    ) {
      context.addIssue({
        code: "custom",
        message:
          "VALEOFLIGHT_WORDPRESS_EMAIL_API_URL and VALEOFLIGHT_WORDPRESS_EMAIL_SIGNING_SECRET must be configured together",
        path: ["VALEOFLIGHT_WORDPRESS_EMAIL_API_URL"],
      });
    }
    if (
      value.VALEOFLIGHT_WORDPRESS_EMAIL_SIGNING_SECRET &&
      value.VALEOFLIGHT_WORDPRESS_EMAIL_SIGNING_SECRET ===
        value.VALLEY_ACCESS_SIGNING_SECRET
    ) {
      context.addIssue({
        code: "custom",
        message: "notification and access-token signing secrets must be distinct",
        path: ["VALEOFLIGHT_WORDPRESS_EMAIL_SIGNING_SECRET"],
      });
    }
    if (
      value.VALEOFLIGHT_WORDPRESS_EMAIL_API_URL &&
      !isSafeWordPressEmailApiUrl(
        value.VALEOFLIGHT_WORDPRESS_EMAIL_API_URL
      )
    ) {
      context.addIssue({
        code: "custom",
        message: "must target the fixed WordPress access-email endpoint",
        path: ["VALEOFLIGHT_WORDPRESS_EMAIL_API_URL"],
      });
    }

    const acceptedTermsVersions = parseAcceptedTermsVersions(
      value.VALLEY_ACCEPTED_CHECKOUT_TERMS_VERSIONS ??
        value.VALLEY_CHECKOUT_TERMS_VERSION
    );
    if (
      acceptedTermsVersions === null ||
      !acceptedTermsVersions.includes(value.VALLEY_CHECKOUT_TERMS_VERSION)
    ) {
      context.addIssue({
        code: "custom",
        message:
          "must be a unique comma-separated allowlist containing the current terms version",
        path: ["VALLEY_ACCEPTED_CHECKOUT_TERMS_VERSIONS"],
      });
    }
  })
  .transform((value) => ({
    ...value,
    VALLEY_ACCEPTED_CHECKOUT_TERMS_VERSIONS:
      parseAcceptedTermsVersions(
        value.VALLEY_ACCEPTED_CHECKOUT_TERMS_VERSIONS ??
          value.VALLEY_CHECKOUT_TERMS_VERSION
      ) ?? [],
  }));

export type PaidAccessEnvironment = z.infer<typeof rawEnvironmentSchema>;

export type CommerceEnvironment = PaidAccessEnvironment & {
  VALEOFLIGHT_WOOCOMMERCE_EXPECTED_AMOUNT_MINOR: number;
  VALEOFLIGHT_WOOCOMMERCE_CONSUMER_KEY: string;
  VALEOFLIGHT_WOOCOMMERCE_CONSUMER_SECRET: string;
  VALEOFLIGHT_WOOCOMMERCE_PRODUCT_ID: number;
  VALEOFLIGHT_WOOCOMMERCE_REST_API_URL: string;
  VALEOFLIGHT_WOOCOMMERCE_WEBHOOK_SECRET: string;
  VALEOFLIGHT_WORDPRESS_EMAIL_API_URL: string;
  VALEOFLIGHT_WORDPRESS_EMAIL_SIGNING_SECRET: string;
};

export type ResendEnvironment = PaidAccessEnvironment & {
  RESEND_API_KEY: string;
  RESEND_WEBHOOK_SECRET: string;
};

let cachedEnvironment: PaidAccessEnvironment | undefined;

export class ServerConfigurationError extends Error {
  readonly code = "SERVER_CONFIGURATION_ERROR";

  constructor(readonly missingOrInvalidKeys: string[]) {
    super(`Paid-reading server configuration is invalid: ${missingOrInvalidKeys.join(", ")}`);
    this.name = "ServerConfigurationError";
  }
}

export function parsePaidAccessEnvironment(
  source: Record<string, string | undefined>
): PaidAccessEnvironment {
  const parsed = rawEnvironmentSchema.safeParse({
    NODE_ENV: source.NODE_ENV,
    VALLEY_RUNTIME_ENV: source.VALLEY_RUNTIME_ENV,
    VALEOFLIGHT_APP_BASE_URL: source.VALEOFLIGHT_APP_BASE_URL,
    VALLEY_SUPABASE_URL: source.VALLEY_SUPABASE_URL,
    VALLEY_SUPABASE_SERVICE_ROLE_KEY: source.VALLEY_SUPABASE_SERVICE_ROLE_KEY,
    VALLEY_ACCESS_SIGNING_SECRET: source.VALLEY_ACCESS_SIGNING_SECRET,
    VALLEY_ACCESS_GRANT_TTL_DAYS: source.VALLEY_ACCESS_GRANT_TTL_DAYS,
    VALLEY_INTAKE_VERSION: source.VALLEY_INTAKE_VERSION,
    VALLEY_GENERATION_CONSENT_VERSION: source.VALLEY_GENERATION_CONSENT_VERSION,
    VALLEY_CHECKOUT_TERMS_VERSION: source.VALLEY_CHECKOUT_TERMS_VERSION,
    VALLEY_ACCEPTED_CHECKOUT_TERMS_VERSIONS:
      source.VALLEY_ACCEPTED_CHECKOUT_TERMS_VERSIONS,
    VALLEY_RETENTION_POLICY_VERSION: source.VALLEY_RETENTION_POLICY_VERSION,
    VALLEY_EMAIL_QUEUE_MAX_AGE_MINUTES:
      source.VALLEY_EMAIL_QUEUE_MAX_AGE_MINUTES,
    CRON_SECRET: source.CRON_SECRET,
    VALLEY_WOOCOMMERCE_RECONCILIATION_BATCH_SIZE:
      source.VALLEY_WOOCOMMERCE_RECONCILIATION_BATCH_SIZE,
    VALLEY_WOOCOMMERCE_RECONCILIATION_LOOKBACK_HOURS:
      source.VALLEY_WOOCOMMERCE_RECONCILIATION_LOOKBACK_HOURS,
    VALLEY_WOOCOMMERCE_RECONCILIATION_MAX_AGE_MINUTES:
      source.VALLEY_WOOCOMMERCE_RECONCILIATION_MAX_AGE_MINUTES,
    VALLEY_WOOCOMMERCE_RECONCILIATION_WINDOW_LAG_SECONDS:
      source.VALLEY_WOOCOMMERCE_RECONCILIATION_WINDOW_LAG_SECONDS,
    VALEOFLIGHT_WOOCOMMERCE_REST_API_URL: source.VALEOFLIGHT_WOOCOMMERCE_REST_API_URL,
    VALEOFLIGHT_WOOCOMMERCE_CONSUMER_KEY: source.VALEOFLIGHT_WOOCOMMERCE_CONSUMER_KEY,
    VALEOFLIGHT_WOOCOMMERCE_CONSUMER_SECRET: source.VALEOFLIGHT_WOOCOMMERCE_CONSUMER_SECRET,
    VALEOFLIGHT_WOOCOMMERCE_WEBHOOK_SECRET: source.VALEOFLIGHT_WOOCOMMERCE_WEBHOOK_SECRET,
    VALEOFLIGHT_WOOCOMMERCE_PRODUCT_ID: source.VALEOFLIGHT_WOOCOMMERCE_PRODUCT_ID,
    VALEOFLIGHT_WORDPRESS_EMAIL_API_URL:
      source.VALEOFLIGHT_WORDPRESS_EMAIL_API_URL,
    VALEOFLIGHT_WORDPRESS_EMAIL_SIGNING_SECRET:
      source.VALEOFLIGHT_WORDPRESS_EMAIL_SIGNING_SECRET,
    VALEOFLIGHT_WOOCOMMERCE_EXPECTED_CURRENCY:
      source.VALEOFLIGHT_WOOCOMMERCE_EXPECTED_CURRENCY,
    VALEOFLIGHT_WOOCOMMERCE_EXPECTED_AMOUNT_MINOR:
      source.VALEOFLIGHT_WOOCOMMERCE_EXPECTED_AMOUNT_MINOR,
    RESEND_API_KEY: source.RESEND_API_KEY,
    RESEND_WEBHOOK_SECRET: source.RESEND_WEBHOOK_SECRET,
    VALEOFLIGHT_EMAIL_FROM: source.VALEOFLIGHT_EMAIL_FROM,
    VALEOFLIGHT_EMAIL_REPLY_TO: source.VALEOFLIGHT_EMAIL_REPLY_TO,
    VALEOFLIGHT_SUPPORT_EMAIL: source.VALEOFLIGHT_SUPPORT_EMAIL,
    VALLEY_AGPL_SOURCE_SHA256: source.VALLEY_AGPL_SOURCE_SHA256,
    VALLEY_AGPL_SOURCE_URL: source.VALLEY_AGPL_SOURCE_URL,
    VALLEY_WORKER_URL: source.VALLEY_WORKER_URL,
    VALLEY_WORKER_SIGNING_SECRET: source.VALLEY_WORKER_SIGNING_SECRET,
  });

  if (!parsed.success) {
    const keys = [...new Set(parsed.error.issues.map((issue) => String(issue.path[0] ?? "environment")))];
    throw new ServerConfigurationError(keys);
  }
  return parsed.data;
}

export function getPaidAccessEnvironment() {
  cachedEnvironment ??= parsePaidAccessEnvironment(process.env);
  return cachedEnvironment;
}

export function getCommerceEnvironment(): CommerceEnvironment {
  const environment = getPaidAccessEnvironment();
  const requiredKeys = [
    "VALEOFLIGHT_WOOCOMMERCE_REST_API_URL",
    "VALEOFLIGHT_WOOCOMMERCE_CONSUMER_KEY",
    "VALEOFLIGHT_WOOCOMMERCE_CONSUMER_SECRET",
    "VALEOFLIGHT_WOOCOMMERCE_WEBHOOK_SECRET",
    "VALEOFLIGHT_WOOCOMMERCE_PRODUCT_ID",
    "VALEOFLIGHT_WOOCOMMERCE_EXPECTED_AMOUNT_MINOR",
    "VALEOFLIGHT_WORDPRESS_EMAIL_API_URL",
    "VALEOFLIGHT_WORDPRESS_EMAIL_SIGNING_SECRET",
  ] as const;
  const missing = requiredKeys.filter((key) => environment[key] === undefined);
  if (missing.length > 0) throw new ServerConfigurationError([...missing]);
  return environment as CommerceEnvironment;
}

export function getResendEnvironment(): ResendEnvironment {
  const environment = getPaidAccessEnvironment();
  const requiredKeys = ["RESEND_API_KEY", "RESEND_WEBHOOK_SECRET"] as const;
  const missing = requiredKeys.filter(
    (key) => environment[key] === undefined
  );
  if (missing.length > 0) throw new ServerConfigurationError([...missing]);
  return environment as ResendEnvironment;
}

export function getLaunchEnvironment(): CommerceEnvironment &
  Required<
    Pick<
      PaidAccessEnvironment,
      | "CRON_SECRET"
      | "VALLEY_AGPL_SOURCE_SHA256"
      | "VALLEY_AGPL_SOURCE_URL"
      | "VALLEY_RETENTION_POLICY_VERSION"
      | "VALLEY_WORKER_SIGNING_SECRET"
      | "VALLEY_WORKER_URL"
    >
  > {
  const environment = getCommerceEnvironment();
  const missing = (
    [
      "VALLEY_RETENTION_POLICY_VERSION",
      "CRON_SECRET",
      "VALLEY_AGPL_SOURCE_SHA256",
      "VALLEY_AGPL_SOURCE_URL",
      "VALLEY_WORKER_URL",
      "VALLEY_WORKER_SIGNING_SECRET",
    ] as const
  ).filter((key) => environment[key] === undefined);
  if (missing.length > 0) throw new ServerConfigurationError([...missing]);
  return environment as CommerceEnvironment &
    Required<
      Pick<
        PaidAccessEnvironment,
        | "CRON_SECRET"
        | "VALLEY_AGPL_SOURCE_SHA256"
        | "VALLEY_AGPL_SOURCE_URL"
        | "VALLEY_RETENTION_POLICY_VERSION"
        | "VALLEY_WORKER_SIGNING_SECRET"
        | "VALLEY_WORKER_URL"
      >
    >;
}

export function resetPaidAccessEnvironmentForTests() {
  cachedEnvironment = undefined;
}

function parseAcceptedTermsVersions(value: string) {
  const versions = value.split(",").map((candidate) => candidate.trim());
  if (
    versions.length < 1 ||
    versions.length > 10 ||
    versions.some(
      (candidate) => !/^[A-Za-z0-9._:-]{1,80}$/.test(candidate)
    ) ||
    new Set(versions).size !== versions.length
  ) {
    return null;
  }
  return versions;
}

function isSafeWordPressEmailApiUrl(value: string) {
  try {
    const url = new URL(value);
    return (
      (url.protocol === "https:" || url.protocol === "http:") &&
      url.username === "" &&
      url.password === "" &&
      url.search === "" &&
      url.hash === "" &&
      url.pathname === "/wp-json/vale-of-light/v1/access-email"
    );
  } catch {
    return false;
  }
}
