export function shouldRequireLoginForTab(tabKey, user) {
  return ["customization"].includes(tabKey) && !user;
}

export function shouldRequireLoginForSettingsTab(settingsTab, user) {
  return ["general", "account", "security"].includes(settingsTab) && !user;
}
