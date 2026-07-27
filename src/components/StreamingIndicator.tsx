import { PanelSectionRow } from "@decky/ui";
import { useEffect, useState } from "react";
import { autoSwitchPaused, safeCall } from "../api";

const POLL_MS = 5000;

// Shown under the TV address while a Remote Play session is holding auto-switch back, so a
// pause is never silent — the one failure mode of pushing the session state on change is a
// missed "stopped" event, and this is what makes that visible. Renders nothing otherwise.
// Polls only while the Quick Access panel is mounted, so it costs nothing in the background.
export function StreamingIndicator() {
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    let active = true;
    const apply = (value: boolean) => {
      if (active) setPaused(value);
    };
    // Clear on failure rather than holding the last answer: a backend that stopped responding
    // must not leave a "paused" claim on screen indefinitely.
    const check = () => safeCall(() => autoSwitchPaused().then(apply, () => apply(false)));
    check();
    const timer = setInterval(check, POLL_MS);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);

  if (!paused) return null;

  // Owns its own row so nothing renders — not even an empty padded row — when idle.
  return (
    <PanelSectionRow>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          fontSize: "0.8em",
          opacity: 0.6,
          paddingBottom: "8px",
        }}
      >
        <span style={{ fontWeight: "bold", marginRight: "6px" }}>Remote Play</span>
        <span>auto-switch paused</span>
        <span
          title="A Remote Play session is streaming from this machine"
          style={{
            width: "10px",
            height: "10px",
            borderRadius: "50%",
            background: "#f39c12",
            marginLeft: "8px",
            flexShrink: 0,
            display: "inline-block",
          }}
        />
      </div>
    </PanelSectionRow>
  );
}
