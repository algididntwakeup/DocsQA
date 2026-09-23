/** Join conditional class names without pulling in clsx/tailwind-merge. */
export function cn(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}
