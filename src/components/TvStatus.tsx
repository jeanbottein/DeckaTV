import { PanelSection, PanelSectionRow } from "@decky/ui";
import { type Tv } from "../api";
import { ReachabilityIndicator } from "./ReachabilityIndicator";
import { StreamingIndicator } from "./StreamingIndicator";

// The panel's footer: which TV is selected, whether it answers, and whether anything is holding
// auto-switch back. Sits last because it is reference, not control — every button the user came
// for is above it.
export function TvStatus({ tv }: { tv: Tv }) {
  return (
    <PanelSection>
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
          <span style={{ fontWeight: "bold", marginRight: "6px" }}>Address</span>
          <span>{tv.host}</span>
          <ReachabilityIndicator host={tv.host} />
        </div>
      </PanelSectionRow>
      <StreamingIndicator />
    </PanelSection>
  );
}
