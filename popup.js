const RULESETS = ['custom', 'easylist', 'easyprivacy'];
const status = document.getElementById('status');

async function refresh() {
  const enabled = await chrome.declarativeNetRequest.getEnabledRulesets();
  for (const id of RULESETS) {
    document.getElementById(id).checked = enabled.includes(id);
  }
  status.textContent = enabled.length
    ? `Blocking with ${enabled.length}/${RULESETS.length} rulesets`
    : 'Paused';
}

for (const id of RULESETS) {
  document.getElementById(id).addEventListener('change', async (e) => {
    await chrome.declarativeNetRequest.updateEnabledRulesets(
      e.target.checked
        ? { enableRulesetIds: [id] }
        : { disableRulesetIds: [id] }
    );
    refresh();
  });
}

refresh();
