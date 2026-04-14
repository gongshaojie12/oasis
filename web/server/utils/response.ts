interface ApiResponse<T = any> {
  code: number
  data: T | null
  message: string
}

export function success<T>(data: T, message = 'ok'): ApiResponse<T> {
  return { code: 0, data, message }
}

export function error(code: number, message: string): ApiResponse<null> {
  return { code, data: null, message }
}

export const ErrorCodes = {
  SMS_RATE_LIMIT: 40001,
  SMS_CODE_EXPIRED: 40002,
  SMS_CODE_INVALID: 40003,
  PHONE_NOT_FOUND: 40004,
  TOKEN_INVALID: 40101,
  TOKEN_EXPIRED: 40102,
  ENTERPRISE_SUSPENDED: 40103,
  QUOTA_EXCEEDED: 40201,
  QUOTA_EXPIRED: 40202,
  NOT_FOUND: 40401,
  FORBIDDEN: 40301,
  VALIDATION_ERROR: 40001,
  ENGINE_DISPATCH_FAILED: 50002,
  ENGINE_UNAVAILABLE: 50003,
  SERVER_ERROR: 50001,
} as const
