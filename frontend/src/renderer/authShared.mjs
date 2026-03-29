export function shouldRequireLoginForTab(tabKey, user) {
  return ["settings", "customization"].includes(tabKey) && !user;
}
