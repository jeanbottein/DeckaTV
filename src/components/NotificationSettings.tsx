import { PanelSection, PanelSectionRow, ToggleField } from "@decky/ui";
import { useEffect, useState } from "react";
import { getNotifications, safeCall, setNotifications } from "../api";
import { setNotify } from "../notify";

// Global toggle for the auto-switch toast. Defaults on, so an untouched install behaves as
// before. Stays hidden on a stale backend that lacks get_notifications (a missing callable can
// throw synchronously), like the rest of the plugin's guarded callable use.
export function NotificationSettings() {
  const [on, setOn] = useState<boolean | null>(null);

  useEffect(() => {
    safeCall(() =>
      getNotifications().then((value) => {
        setOn(value);
        setNotify(value);
      }),
    );
  }, []);

  if (on === null) return null;

  const toggle = (value: boolean) => {
    setOn(value);
    setNotify(value);
    safeCall(() => setNotifications(value));
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
