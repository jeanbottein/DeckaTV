import { ButtonItem, PanelSection, PanelSectionRow } from "@decky/ui";
import { toaster } from "@decky/api";
import { useState } from "react";
import { powerOffTv, tvLabel, type Tv } from "../api";

// Powering the TV off has to happen while the Deck is awake and on the network — doing it during
// OS suspend loses the race with Wi-Fi teardown. So these are explicit buttons: "Suspend TV"
// powers the TV down now; "Suspend computer + TV" powers it down first, then suspends the Deck
// once the TV is confirmed off (so the order is guaranteed and the command actually lands).
export function PowerControls({ tv }: { tv: Tv }) {
  const [busy, setBusy] = useState(false);

  const turnOff = async (): Promise<boolean> => {
    try {
      await powerOffTv(tv.host);
      return true;
    } catch (error) {
      toaster.toast({ title: "Turn off failed", body: String(error) });
      return false;
    }
  };

  const onTurnOff = async () => {
    setBusy(true);
    if (await turnOff()) toaster.toast({ title: "TV turned off", body: tvLabel(tv) });
    setBusy(false);
  };

  const onSleepBoth = async () => {
    setBusy(true);
    const off = await turnOff();
    setBusy(false);
    if (!off) return; // don't suspend if the TV never went off — surfaces the failure to the user
    // Suspend through Steam's own flow, the same as the menu's Sleep. Must be called as a method
    // (sc.System.SuspendPC()) — pulling it off System into a bare variable loses `this` and fails.
    const sc = (window as unknown as { SteamClient?: any }).SteamClient;
    if (typeof sc?.System?.SuspendPC !== "function") {
      // TV is off but we can't drive suspend — say so rather than silently stopping half-done.
      toaster.toast({ title: "TV off — suspend unavailable", body: "SuspendPC not found" });
      return;
    }
    try {
      sc.System.SuspendPC();
    } catch (error) {
      toaster.toast({ title: "Suspend failed", body: String(error) });
    }
  };

  return (
    <PanelSection>
      <PanelSectionRow>
        <ButtonItem layout="below" bottomSeparator="none" disabled={busy} onClick={onTurnOff}>
          Suspend TV
        </ButtonItem>
      </PanelSectionRow>
      <PanelSectionRow>
        <ButtonItem layout="below" bottomSeparator="none" disabled={busy} onClick={onSleepBoth}>
          Suspend computer + TV
        </ButtonItem>
      </PanelSectionRow>
    </PanelSection>
  );
}
