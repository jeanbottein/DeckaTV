import { ButtonItem, DialogButton, Focusable, ModalRoot, PanelSectionRow, showModal } from "@decky/ui";
import { useEffect, useState } from "react";
import { clearLogs, readLogs } from "../api";

function LogsModal({ closeModal }: { closeModal?: () => void }) {
  const [text, setText] = useState("Loading…");

  const load = async () => {
    try {
      setText((await readLogs()) || "No logs yet.");
    } catch {
      setText("Failed to load logs.");
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const clear = async () => {
    try {
      await clearLogs();
    } catch {
      /* best-effort — reload shows the real state either way */
    }
    await load();
  };

  return (
    <ModalRoot onCancel={closeModal} onEscKeypress={closeModal} bAllowFullSize>
      <div style={{ fontSize: "1.3em", fontWeight: "bold", paddingBottom: "8px" }}>DeckaTV logs</div>
      {/* A Focusable so the gamepad can reach and scroll it — a plain overflow div can't take
          focus, which is why the old inline viewer wouldn't scroll on the Deck. */}
      <Focusable
        style={{
          height: "58vh",
          overflowY: "scroll",
          padding: "8px 12px",
          background: "rgba(0, 0, 0, 0.2)",
          borderRadius: "4px",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          fontFamily: "monospace",
          fontSize: "12px",
          lineHeight: 1.4,
        }}
      >
        {text}
      </Focusable>
      <Focusable style={{ display: "flex", gap: "8px", paddingTop: "12px" }}>
        <DialogButton style={{ flex: 1 }} onClick={() => void load()}>
          Refresh
        </DialogButton>
        <DialogButton style={{ flex: 1 }} onClick={() => void clear()}>
          Clear
        </DialogButton>
        <DialogButton style={{ flex: 1 }} onClick={() => closeModal?.()}>
          Close
        </DialogButton>
      </Focusable>
    </ModalRoot>
  );
}

export function Logs() {
  return (
    <PanelSectionRow>
      <ButtonItem layout="below" bottomSeparator="none" onClick={() => showModal(<LogsModal />)}>
        View logs
      </ButtonItem>
    </PanelSectionRow>
  );
}
