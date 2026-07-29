import { type CSSProperties } from "react";

// Shared look for the panel's footer rows — the small, dimmed "label + value + status dot" lines
// (address/reachability, streaming pause). Kept here so the rows stay visually identical as more
// of them appear, rather than drifting apart one inline object at a time.
export const statusLine: CSSProperties = {
  display: "flex",
  alignItems: "center",
  fontSize: "0.8em",
  opacity: 0.6,
  paddingBottom: "8px",
};

export const statusLabel: CSSProperties = { fontWeight: "bold", marginRight: "6px" };

export const statusDot = (color: string): CSSProperties => ({
  width: "10px",
  height: "10px",
  borderRadius: "50%",
  background: color,
  marginLeft: "8px",
  flexShrink: 0,
  display: "inline-block",
});
