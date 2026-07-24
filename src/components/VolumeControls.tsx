import { DialogButton, Focusable } from "@decky/ui";
import { toaster } from "@decky/api";
import { volumeDown, volumeUp, type Tv } from "../api";

// One row of two buttons rather than two stacked full-width rows — the labels are short enough
// to sit side by side, and the Quick Access menu is tight on vertical space. Returns bare
// buttons; the panel stacks them with the power buttons at a single uniform gap.
//
// Fire-and-forget so rapid taps aren't blocked by a disabled state; each press is one webOS
// volumeUp/Down step. Errors toast (e.g. "401" until the TV is re-paired with CONTROL_AUDIO).
export function VolumeControls({ tv }: { tv: Tv }) {
  const nudge = (step: typeof volumeUp) => () => {
    step(tv.host).catch((error) => toaster.toast({ title: "Volume failed", body: String(error) }));
  };

  return (
    <Focusable style={{ display: "flex", gap: "8px" }}>
      <DialogButton style={{ flex: 1, minWidth: 0 }} onClick={nudge(volumeDown)}>
        Volume −
      </DialogButton>
      <DialogButton style={{ flex: 1, minWidth: 0 }} onClick={nudge(volumeUp)}>
        Volume +
      </DialogButton>
    </Focusable>
  );
}
