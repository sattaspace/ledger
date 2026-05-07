/**
 * Typed exception hierarchy for Sattabase SDK.
 *
 * Mirrors the Python SDK's exception module exactly.
 * Error mapping priority:
 *   1. Match by `code` field (e.g. `account_deleted`)
 *   2. Fall back to HTTP status code
 *   3. Final fallback: `ApiServerError`
 */

/** Base exception for all Sattabase SDK errors. */
export class SattabaseError extends Error {
  /** HTTP status code from the Sattabase API (0 for network errors). */
  readonly status: number;
  /** Optional structured error detail from the API response. */
  readonly detail: unknown;

  constructor(message = "", status = 0, detail?: unknown) {
    super(message);
    this.name = "SattabaseError";
    this.status = status;
    this.detail = detail;
  }
}

/** 401 — Invalid, expired, or missing token / API key. */
export class AuthenticationError extends SattabaseError {
  constructor(message = "Authentication failed", detail?: unknown) {
    super(message, 401, detail);
    this.name = "AuthenticationError";
  }
}

/** 401 — User account is deactivated by admin (code: `account_inactive`). */
export class AccountInactiveError extends AuthenticationError {
  constructor(message = "Account is inactive", detail?: unknown) {
    super(message, detail);
    this.name = "AccountInactiveError";
  }
}

/** 401 — User account has been soft-deleted (code: `account_deleted`). */
export class AccountDeletedError extends AuthenticationError {
  constructor(message = "Account has been deleted", detail?: unknown) {
    super(message, detail);
    this.name = "AccountDeletedError";
  }
}

/** 403 — Insufficient permissions. */
export class ForbiddenError extends SattabaseError {
  constructor(message = "Forbidden", detail?: unknown) {
    super(message, 403, detail);
    this.name = "ForbiddenError";
  }
}

/** 403 — Email not verified (code: `account_not_active`). */
export class AccountNotActiveError extends ForbiddenError {
  constructor(message = "Account not active — verify email", detail?: unknown) {
    super(message, detail);
    this.name = "AccountNotActiveError";
  }
}

/** 404 — Resource not found. */
export class NotFoundError extends SattabaseError {
  constructor(message = "Not found", detail?: unknown) {
    super(message, 404, detail);
    this.name = "NotFoundError";
  }
}

/** 409 — State conflict (e.g. duplicate resource). */
export class ConflictError extends SattabaseError {
  constructor(message = "Conflict", detail?: unknown) {
    super(message, 409, detail);
    this.name = "ConflictError";
  }
}

/** 429 — Too many requests. */
export class RateLimitError extends SattabaseError {
  /** Seconds to wait before retrying (from Retry-After header or response body). */
  readonly retryAfter: number | null;

  constructor(
    message = "Rate limit exceeded",
    detail?: unknown,
    retryAfter?: number | null,
  ) {
    super(message, 429, detail);
    this.name = "RateLimitError";
    this.retryAfter = retryAfter ?? null;
  }
}

/** 422 — Invalid request body / parameters. */
export class ValidationError extends SattabaseError {
  constructor(message = "Validation error", detail?: unknown) {
    super(message, 422, detail);
    this.name = "ValidationError";
  }
}

/** 400 — Malformed or invalid request. */
export class BadRequestError extends SattabaseError {
  constructor(message = "Bad request", detail?: unknown) {
    super(message, 400, detail);
    this.name = "BadRequestError";
  }
}

/** 5xx — Sattabase server error or network failure. */
export class ApiServerError extends SattabaseError {
  constructor(message = "Sattabase server error", detail?: unknown) {
    super(message, 500, detail);
    this.name = "ApiServerError";
  }
}

/** Map HTTP status codes to SDK exception classes. */
const STATUS_MAP: Record<
  number,
  new (msg: string, detail?: unknown) => SattabaseError
> = {
  400: BadRequestError,
  401: AuthenticationError,
  403: ForbiddenError,
  404: NotFoundError,
  409: ConflictError,
  422: ValidationError,
  429: RateLimitError,
};

/** Map error codes to SDK exception classes (higher priority than status). */
const ERROR_CODE_MAP: Record<
  string,
  new (msg: string, detail?: unknown) => SattabaseError
> = {
  account_inactive: AccountInactiveError,
  account_deleted: AccountDeletedError,
  account_not_active: AccountNotActiveError,
  unauthorized: AuthenticationError,
  forbidden: ForbiddenError,
  not_found: NotFoundError,
  conflict: ConflictError,
  too_many_requests: RateLimitError,
  bad_request: BadRequestError,
};

/**
 * Build the appropriate SDK exception from an HTTP response.
 *
 * Priority:
 *   1. Match by `code` field (e.g. `account_deleted`)
 *   2. Match by HTTP status code
 *   3. Fallback to `ApiServerError`
 */
export function buildError(
  status: number,
  body: Record<string, unknown> | null,
  code?: string | null,
): SattabaseError {
  const detail = body ?? undefined;
  let message = "Unknown error";

  if (body && typeof body === "object") {
    message = String(body["detail"] ?? body["message"] ?? message);
  }

  // Check error code first (more specific)
  if (code) {
    const Cls = ERROR_CODE_MAP[code];
    if (Cls) {
      if (Cls === RateLimitError) {
        const retryAfter = body?.["retry_after"];
        return new RateLimitError(
          message,
          detail,
          typeof retryAfter === "number" ? retryAfter : null,
        );
      }
      return new Cls(message, detail);
    }
  }

  // Fall back to status code
  const Cls = STATUS_MAP[status] ?? ApiServerError;
  if (Cls === RateLimitError) {
    const retryAfter = body?.["retry_after"];
    return new RateLimitError(
      message,
      detail,
      typeof retryAfter === "number" ? retryAfter : null,
    );
  }
  return new Cls(message, detail);
}
