import { toaster } from "@decky/api";

// Whether an auto-switch should surface a toast. Mirrors the backend "notifications" setting.
// Kept at module scope so the session-scoped auto_switch listener (which outlives the panel)
// and the in-panel toggle read and write the same flag without a round-trip on every event.
let enabled = true;

export const setNotify = (on: boolean) => {
  enabled = on;
};

export const notify = (options: Parameters<typeof toaster.toast>[0]) => {
  if (enabled) toaster.toast(options);
};
