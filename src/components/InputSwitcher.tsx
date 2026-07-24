import { ButtonItem, DropdownItem, Field, PanelSection, PanelSectionRow } from "@decky/ui";
import { toaster } from "@decky/api";
import { useCallback, useEffect, useState } from "react";
import { switchInput, type Input, type Tv } from "../api";

// Decky remounts the Quick Access content whenever a dropdown overlay closes, which would reset
// this component's picked input back to the first one the moment you choose. Persist the pick
// per-TV in a module-level cache (written synchronously on select) so it survives the remount —
// the same trick the Add-TV form uses.
const lastPick: Record<string, string> = {};

export function InputSwitcher({ tv, inputs }: { tv: Tv; inputs: Input[] }) {
  const [selected, setSelected] = useState(lastPick[tv.host] ?? "");
  const [busy, setBusy] = useState(false);

  const choose = useCallback(
    (id: string) => {
      lastPick[tv.host] = id;
      setSelected(id);
    },
    [tv.host],
  );

  // Keep the current pick if it still exists, else fall back to the first input.
  // Ignore an empty list so a transient refresh can't wipe the selection.
  useEffect(() => {
    if (inputs.length === 0) {
      return;
    }
    if (!inputs.some((input) => input.id === selected)) {
      choose(inputs[0]?.id ?? "");
    }
  }, [inputs, selected, choose]);

  const send = async () => {
    if (!selected) {
      return;
    }
    setBusy(true);
    try {
      await switchInput(tv.host, selected);
      const label = inputs.find((input) => input.id === selected)?.label ?? selected;
      toaster.toast({ title: "Input switched", body: label });
    } catch (error) {
      toaster.toast({ title: "Switch failed", body: String(error) });
    } finally {
      setBusy(false);
    }
  };

  if (inputs.length === 0) {
    return (
      <PanelSection>
        <PanelSectionRow>
          <Field label="INPUT SWITCH" bottomSeparator="none" />
        </PanelSectionRow>
        <PanelSectionRow>No inputs found — make sure the TV is on.</PanelSectionRow>
      </PanelSection>
    );
  }

  return (
    <PanelSection>
      <PanelSectionRow>
        <Field label="MANUAL SWITCH" bottomSeparator="none" />
      </PanelSectionRow>
      <PanelSectionRow>
        <DropdownItem
          menuLabel="Select an input"
          rgOptions={inputs.map((input) => ({ data: input.id, label: input.label }))}
          selectedOption={selected}
          bottomSeparator="none"
          childrenContainerWidth="max"
          onChange={(option) => choose(option.data)}
        />
      </PanelSectionRow>
      <PanelSectionRow>
        <ButtonItem
          layout="below"
          bottomSeparator="none"
          disabled={busy || !selected}
          onClick={send}
        >
          {busy ? "Switching…" : "Switch input"}
        </ButtonItem>
      </PanelSectionRow>
    </PanelSection>
  );
}
