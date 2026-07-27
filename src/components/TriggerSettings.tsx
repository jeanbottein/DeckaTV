import { PanelSection, PanelSectionRow, ToggleField } from "@decky/ui";
import { useEffect, useState } from "react";
import { getTriggers, safeCall, setTrigger, type Triggers } from "../api";
import { StreamingSettings } from "./StreamingSettings";

// Global (not per-TV) toggles for which events re-assert the TV input. Keys match the backend
// TRIGGERS; all default on, so an untouched install behaves exactly as before.
const ITEMS: { key: keyof Triggers; label: string; description: string }[] = [
  { key: "connect", label: "A screen connects", description: "You dock, or boot up already docked" },
  { key: "wake", label: "Waking from sleep", description: "The machine resumes from suspend" },
  { key: "home", label: "Steam button", description: "Press the Steam/Guide button to re-assert" },
];

export function TriggerSettings() {
  const [triggers, setTriggers] = useState<Triggers | null>(null);

  // Leave the section hidden on a stale backend that lacks get_triggers (guarded like the
  // rest of the plugin's callable use, since a missing method can throw synchronously).
  useEffect(() => {
    safeCall(() => getTriggers().then(setTriggers));
  }, []);

  if (!triggers) return null;

  const toggle = (key: keyof Triggers, on: boolean) => {
    setTriggers({ ...triggers, [key]: on });
    safeCall(() => setTrigger(key, on));
  };

  return (
    <PanelSection title="Auto-switch triggers">
      <PanelSectionRow>
        <div style={{ fontSize: "0.8em", opacity: 0.6, paddingBottom: "2px" }}>Switch the input when…</div>
      </PanelSectionRow>
      {ITEMS.map((item) => (
        <PanelSectionRow key={item.key}>
          <ToggleField
            label={item.label}
            description={item.description}
            checked={triggers[item.key]}
            onChange={(on) => toggle(item.key, on)}
          />
        </PanelSectionRow>
      ))}
      {/* The pause lives here, not in its own section: it suppresses exactly the triggers above,
          and shares their "no rules enabled" visibility. It owns its own fetch and state. */}
      <StreamingSettings />
    </PanelSection>
  );
}
