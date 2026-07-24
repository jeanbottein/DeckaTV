import { ButtonItem, PanelSection, PanelSectionRow } from "@decky/ui";
import { toaster } from "@decky/api";
import { volumeDown, volumeUp, type Tv } from "../api";

// Fire-and-forget so rapid taps aren't blocked by a disabled state; each press is one webOS
// volumeUp/Down step. Errors toast (e.g. "401" until the TV is re-paired with CONTROL_AUDIO).
export function VolumeControls({ tv }: { tv: Tv }) {
  const nudge = (dir: "up" | "down") => () => {
    (dir === "up" ? volumeUp : volumeDown)(tv.host).catch((error) =>
      toaster.toast({ title: "Volume failed", body: String(error) }),
    );
  };

  return (
    <PanelSection>
      <PanelSectionRow>
        <ButtonItem layout="below" bottomSeparator="none" onClick={nudge("up")}>
          Volume +
        </ButtonItem>
      </PanelSectionRow>
      <PanelSectionRow>
        <ButtonItem layout="below" bottomSeparator="none" onClick={nudge("down")}>
          Volume −
        </ButtonItem>
      </PanelSectionRow>
    </PanelSection>
  );
}
