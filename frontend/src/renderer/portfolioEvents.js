export function notifyPortfolioDataUpdated() {
  window.dispatchEvent(new CustomEvent("portfolio:data-updated"));
}
