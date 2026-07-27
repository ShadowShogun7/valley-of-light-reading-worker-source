export function addDays(date: Date, days: number) {
  return new Date(date.getTime() + days * 24 * 60 * 60 * 1000);
}

export function toWholeSecondIso(date: Date) {
  return new Date(Math.floor(date.getTime() / 1000) * 1000).toISOString();
}
