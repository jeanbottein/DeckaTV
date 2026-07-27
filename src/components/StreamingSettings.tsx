import { PanelSectionRow, ToggleField } from "@decky/ui";
import { useEffect, useState } from "react";
import { getPauseWhenStreaming, safeCall, setPauseWhenStreaming } from "../api";

// The inverse of a trigger, so it renders as the tail of the trigger section rather than its own:
// it suppresses the switches listed above while someone streams from this machine over Remote
// Play. Only auto-switch is held — the manual input, volume, and power buttons still work.
// Defaults on. Stays hidden on a stale backend that lacks get_pause_when_streaming, like the rest
// of the plugin's guarded callable use.
export function StreamingSettings() {
  const [on, setOn] = useState<boolean | null>(null);

  useEffect(() => {
    safeCall(() => getPauseWhenStreaming().then(setOn));
  }, []);

  if (on === null) return null;

  const toggle = (value: boolean) => {
    setOn(value);
    safeCall(() => setPauseWhenStreaming(value));
  };

  return (
    <>
      <PanelSectionRow>
        <div style={{ fontSize: "0.8em", opacity: 0.6, padding: "6px 0 2px" }}>…except while…</div>
      </PanelSectionRow>
      <PanelSectionRow>
        <ToggleField
          label="Streaming to another machine"
          description="A Remote Play session is running, so the TV is left to whoever is watching it"
          checked={on}
          bottomSeparator="none"
          onChange={toggle}
        />
      </PanelSectionRow>
    </>
  );
}
