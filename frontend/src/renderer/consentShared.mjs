export function shouldShowConsentBanner(state) {
  return !Boolean(state?.local_consent);
}

export function formatConsentSummary(state) {
  const local = state?.local_consent ? "Granted" : "Not granted";
  const external = state?.external_consent ? "Granted" : "Not granted";
  return `Local processing: ${local} • External AI: ${external}`;
}
