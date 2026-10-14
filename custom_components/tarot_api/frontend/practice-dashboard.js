/* Native dashboard creation through HA's own authenticated WebSocket APIs. */
export const PRACTICE_VIEWS = [
  ["affirmation", "Affirmations"], ["tarot", "Tarot"], ["oracle", "Oracle"],
  ["deity", "Gods"], ["rune", "Runes"], ["horoscope", "Horoscopes"],
];
export function dashboardConfig(config) {
  return {
    title: "Daily Practice", tarot_api_entry_id: config.tarot_api_entry_id,
    views: PRACTICE_VIEWS.map(([section, title]) => ({
      title, path: section, type: "sections", max_columns: 3,
      sections: [{type: "grid", column_span: 3, cards: [{
        type: "custom:moon-practice-card", section,
        entry_id: config.tarot_api_entry_id, unique_prefix: config.unique_prefix,
        ...config.card, grid_options: {columns: "full", rows: "auto"},
      }]}],
    })),
  };
}
export async function ensureDashboard(hass, config, progress = () => {}) {
  const path = config.dashboard_path;
  const run = async () => {
    if (!hass.user?.is_admin) {
      try {
        await hass.callWS({type: "lovelace/config", url_path: path});
        return path;
      } catch {
        throw new Error("An administrator needs to open Daily Practice once to create the dashboard. After that, everyone can use it.");
      }
    }
    const dashboards = await hass.callWS({type: "lovelace/dashboards/list"});
    let existing = dashboards.find(item => item.url_path === path);
    if (existing) {
      await hass.callWS({type: "lovelace/config", url_path: path});
      return path;
    }
    progress("Creating your Daily Practice dashboard…");
    try {
      await hass.callWS({type: "lovelace/dashboards/create", url_path: path,
        title: "Daily Practice", icon: "mdi:moon-waning-crescent",
        show_in_sidebar: true, require_admin: false});
    } catch (error) {
      existing = (await hass.callWS({type: "lovelace/dashboards/list"})).find(item => item.url_path === path);
      if (!existing) throw error;
      await hass.callWS({type: "lovelace/config", url_path: path});
      return path;
    }
    try {
      await hass.callWS({type: "lovelace/config/save", url_path: path, config: dashboardConfig(config)});
    } catch (error) {
      throw new Error(`The dashboard was created but its starting layout could not be saved. Open Settings → Dashboards and use the bundled YAML example, or delete the empty dashboard and retry. ${error?.message || ""}`);
    }
    return path;
  };
  return globalThis.navigator?.locks ? navigator.locks.request(`tarot-api-dashboard-${path}`, run) : run();
}
