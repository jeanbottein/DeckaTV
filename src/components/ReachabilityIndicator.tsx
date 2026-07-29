import { useEffect, useState } from "react";
import { isReachable } from "../api";
import { statusDot } from "./styles";

export function ReachabilityIndicator({ host }: { host: string }) {
  const [online, setOnline] = useState(false);

  useEffect(() => {
    let active = true;
    const check = async () => {
      try {
        const ok = await isReachable(host);
        if (active) setOnline(ok);
      } catch {
        if (active) setOnline(false);
      }
    };
    setOnline(false);
    check();
    const timer = setInterval(check, 5000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [host]);

  const color = online ? "#2ecc71" : "#e74c3c";
  const title = online ? "Reachable" : "Unreachable";
  return <span title={title} style={statusDot(color)} />;
}
