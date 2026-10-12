let lastCorrelationId: string | null = null;

export function setLastCorrelationId(correlationId: string | null): void {
  lastCorrelationId = correlationId;
}

export function getLastCorrelationId(): string | null {
  return lastCorrelationId;
}
