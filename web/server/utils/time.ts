export function now(): string {
  return new Date().toISOString()
}

export function addMinutes(minutes: number): string {
  const date = new Date()
  date.setMinutes(date.getMinutes() + minutes)
  return date.toISOString()
}

export function isExpired(isoString: string): boolean {
  return new Date(isoString) < new Date()
}
