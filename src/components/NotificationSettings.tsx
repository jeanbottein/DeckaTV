import { PanelSection, PanelSectionRow, ToggleField } from "@decky/ui";
import { useEffect, useState } from "react";
import { getNotifications, setNotifications } from "../api";
import { setNotify } from "../notify";

// Global toggle for the auto-switch toast. Defaults on, so an untouched install behaves as
// before. Stays hidden on a stale backend that lacks get_notifications (a missing callable can
// throw synchronously), like the rest of the plugin's guarded callable use.
export function NotificationSettings() {
  const [on, setOn] = useState<boolean | null>(null);

  useEffect(() => {
    try {
      getNotifications()
        .then((value) => {
          setOn(value);
          setNotify(value);
        })
        .catch(() => {});
    } catch {
      /* stale/mismatched backend — ignore */
    }
  }, []);

  if (on === null) return null;

  const toggle = (value: boolean) => {
    setOn(value);
    setNotify(value);
    try {
      void setNotifications(value).catch(() => {});
    } catch {
      /* stale/mismatched backend — ignore */
    }
  };

  return (
    <PanelSection title="Notifications">
      <PanelSectionRow>
        <ToggleField
          label="Auto-switch toast"
          description="Show a notification when the input auto-switches"
          checked={on}
          bottomSeparator="none"
          onChange={toggle}
        />
      </PanelSectionRow>
    </PanelSection>
  );
}
