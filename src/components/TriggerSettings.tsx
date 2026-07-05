import { PanelSection, PanelSectionRow, ToggleField } from "@decky/ui";
import { useEffect, useState } from "react";
import { getTriggers, setTrigger, type Triggers } from "../api";

// Global (not per-TV) toggles for which events re-assert the TV input. Keys match the backend
// TRIGGERS; all default on, so an untouched install behaves exactly as before.
const ITEMS: { key: keyof Triggers; label: string; description: string }[] = [
  { key: "connect", label: "A screen connects", description: "You dock, or boot up already docked" },
  { key: "wake", label: "Waking from sleep", description: "The Deck resumes from suspend" },
  { key: "home", label: "Steam button", description: "Press the Steam/Guide button to re-assert" },
];

export function TriggerSettings() {
  const [triggers, setTriggers] = useState<Triggers | null>(null);

  // Leave the section hidden on a stale backend that lacks get_triggers (guarded like the
  // rest of the plugin's callable use, since a missing method can throw synchronously).
  useEffect(() => {
    try {
      getTriggers().then(setTriggers).catch(() => {});
    } catch {
      /* stale/mismatched backend — ignore */
    }
  }, []);

  if (!triggers) return null;

  const toggle = (key: keyof Triggers, on: boolean) => {
    setTriggers({ ...triggers, [key]: on });
    try {
      void setTrigger(key, on).catch(() => {});
    } catch {
      /* stale/mismatched backend — ignore */
    }
  };

  return (
    <PanelSection title="Auto-switch triggers">
      <PanelSectionRow>
        <div style={{ fontSize: "0.8em", opacity: 0.6, paddingBottom: "2px" }}>Switch the input when…</div>
      </PanelSectionRow>
      {ITEMS.map((item, index) => (
        <PanelSectionRow key={item.key}>
          <ToggleField
            label={item.label}
            description={item.description}
            checked={triggers[item.key]}
            bottomSeparator={index === ITEMS.length - 1 ? "none" : "standard"}
            onChange={(on) => toggle(item.key, on)}
          />
        </PanelSectionRow>
      ))}
    </PanelSection>
  );
}
