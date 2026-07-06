import { PanelSection, PanelSectionRow, staticClasses } from "@decky/ui";
import { addEventListener, definePlugin, removeEventListener } from "@decky/api";
import { useEffect, useState } from "react";
import { FaTv } from "react-icons/fa";
import {
  getInputs,
  getSelectedTv,
  listBrands,
  listDisplays,
  listRules,
  listTvs,
  getNotifications,
  reapplyRules,
  safeCall,
  setSelectedTv,
  type Brand,
  type Display,
  type Input,
  type Rule,
  type Tv,
} from "./api";
import { TvSection } from "./components/TvSection";
import { TvManage } from "./components/TvManage";
import { PairView } from "./components/PairView";
import { InputSwitcher } from "./components/InputSwitcher";
import { AutoSwitch } from "./components/AutoSwitch";
import { TriggerSettings } from "./components/TriggerSettings";
import { NotificationSettings } from "./components/NotificationSettings";
import { Logs } from "./components/Logs";
import { notify, setNotify } from "./notify";

const sameInputs = (a: Input[], b: Input[]) =>
  a.length === b.length && a.every((item, i) => item.id === b[i].id && item.label === b[i].label);
const exists = (tvs: Tv[], host: string) => tvs.some((tv) => tv.host === host);
function pickSelected(tvs: Tv[], saved: string, current: string) {
  if (exists(tvs, saved)) return saved;
  if (exists(tvs, current)) return current;
  return tvs[0]?.host ?? "";
}

// The panel's React tree unmounts every time the Quick Access menu closes, but this
// module stays loaded for the whole session. Stashing the last rendered state here lets
// a reopen paint the full UI instantly (no "Loading…" flash) while a fresh load runs in
// the background to correct anything stale.
type Snapshot = {
  tvs: Tv[];
  displays: Display[];
  rules: Rule[];
  selectedHost: string;
  inputs: Input[];
};
let snapshot: Snapshot | null = null;

function Content() {
  const [brands, setBrands] = useState<Brand[]>([]);
  const [tvs, setTvs] = useState<Tv[]>(snapshot?.tvs ?? []);
  const [displays, setDisplays] = useState<Display[]>(snapshot?.displays ?? []);
  const [rules, setRules] = useState<Rule[]>(snapshot?.rules ?? []);
  const [selectedHost, setSelectedHost] = useState(snapshot?.selectedHost ?? "");
  const [inputs, setInputs] = useState<Input[]>(snapshot?.inputs ?? []);
  const [adding, setAdding] = useState(false);
  // Reveal immediately when we have a cached snapshot to show; otherwise gate on first load.
  const [ready, setReady] = useState(snapshot !== null);

  // Mirror the rendered state into the module-level snapshot so the next reopen is instant.
  useEffect(() => {
    snapshot = { tvs, displays, rules, selectedHost, inputs };
  }, [tvs, displays, rules, selectedHost, inputs]);

  // Fetch the fast local-store state and apply the setters common to both loads; returns the
  // bits each caller resolves differently. No live TV round-trip, so the panel stays snappy.
  const loadCore = async () => {
    const [nextTvs, nextDisplays, nextRules, saved] = await Promise.all([
      listTvs(),
      listDisplays(),
      listRules(),
      getSelectedTv(),
    ]);
    setTvs(nextTvs);
    setDisplays(nextDisplays);
    setRules(nextRules);
    return { nextTvs, saved };
  };

  const refresh = async () => {
    const { nextTvs, saved } = await loadCore();
    setSelectedHost((current) => pickSelected(nextTvs, saved, current));
  };

  useEffect(() => {
    listBrands().then(setBrands);
    let active = true;
    // Initial load: gate only on the fast local store reads (see loadCore), so the panel
    // reveals immediately. Seed the Manual switch from the cached inputs that already travel
    // with each TV; the polling effect refreshes it from the TV in the background. Blocking
    // the whole UI on getInputs() here cost ~2s on every open.
    (async () => {
      try {
        const { nextTvs, saved } = await loadCore();
        if (!active) return;
        const host = pickSelected(nextTvs, saved, "");
        setSelectedHost(host);
        const cached = nextTvs.find((tv) => tv.host === host)?.inputs ?? [];
        if (cached.length) setInputs(cached);
      } catch {
        /* fall through to reveal the UI anyway */
      }
      if (active) setReady(true);
    })();
    return () => {
      active = false;
    };
  }, []);

  // Poll the selected TV's inputs: returns the cached list when offline, refreshes
  // (and repoints any stale rule server-side) once the TV is reachable again.
  useEffect(() => {
    if (!selectedHost) {
      setInputs([]);
      return;
    }
    let active = true;
    // Don't clear here: keep showing the current inputs until the fresh list arrives,
    // so switching TVs (and the initial load) doesn't flash an empty Manual switch.
    const load = async () => {
      try {
        const list = await getInputs(selectedHost);
        if (!active) {
          return;
        }
        // Keep the same array (and never overwrite a good list with a transient
        // empty one) so a routine refresh can't reset the user's dropdown pick.
        setInputs((prev) => (list.length === 0 || sameInputs(prev, list) ? prev : list));
        setRules(await listRules()); // pick up any rule repointed to an existing input
      } catch {
        /* keep the last known list */
      }
    };
    load();
    const timer = setInterval(load, 8000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [selectedHost]);

  const selectTv = (host: string) => {
    setSelectedHost(host);
    void setSelectedTv(host);
  };
  const onPaired = (host: string) => {
    setAdding(false);
    selectTv(host);
    refresh();
  };

  const selectedTv = tvs.find((tv) => tv.host === selectedHost);

  if (!ready) {
    return (
      <PanelSection>
        <PanelSectionRow>
          <div style={{ textAlign: "center", opacity: 0.6, padding: "12px 0" }}>Loading…</div>
        </PanelSectionRow>
      </PanelSection>
    );
  }

  if (adding || tvs.length === 0) {
    return <PairView brands={brands} tvs={tvs} onPaired={onPaired} onCancel={() => setAdding(false)} />;
  }

  return (
    <>
      <TvSection tvs={tvs} selectedHost={selectedHost} onSelect={selectTv} onAdd={() => setAdding(true)} />
      {selectedTv ? <InputSwitcher tv={selectedTv} inputs={inputs} /> : null}
      {selectedTv ? (
        <AutoSwitch tv={selectedTv} displays={displays} rules={rules} inputs={inputs} onChanged={refresh} />
      ) : null}
      {rules.some((rule) => rule.enabled) ? (
        <>
          <TriggerSettings />
          <NotificationSettings />
        </>
      ) : null}
      <PanelSection>
        <TvManage tvs={tvs} selectedHost={selectedHost} onChanged={refresh} />
        <Logs />
      </PanelSection>
    </>
  );
}

export default definePlugin(() => {
  const listener = addEventListener<[name: string, inputId: string]>(
    "auto_switch",
    (name, inputId) => {
      notify({ title: "TV input switched", body: `${name} → ${inputId}` });
    },
  );

  // Seed the toast flag once at session start so the listener above honours the setting even if
  // the panel is never opened. The in-panel toggle keeps this same module-level flag in sync.
  safeCall(() => getNotifications().then(setNotify));

  // "One Touch Play", like a console's home button: pressing the controller's central Steam/Guide
  // button re-asserts the docked TV's input. RegisterForSystemKeyEvents reports that button as
  // eKey=0 (eKey=1 is the "…" Quick Access button). Unlike focus-change events — which fire every
  // 5s on their own, and which a switch's own toast/HDMI-flap re-emits (the old hook's infinite
  // loop) — a system-key event fires only on the physical press, on the home screen and in games
  // alike, and is never a side effect of switching, so it can't self-trigger a loop. The backend
  // no-ops when the TV is already on that input, so firing often is cheap; the debounce just
  // coalesces the press/release pair and rapid re-presses. Registered here (not in the panel,
  // which only exists while the QAM is open) so it lives for the whole session.
  const steamClient = (window as unknown as { SteamClient?: any }).SteamClient;
  // reapplyRules is fully guarded via safeCall: a stale backend missing it must NEVER break
  // plugin load. A callable can surface "unknown method" synchronously, so safeCall wraps the
  // call itself — not just the returned promise — or the throw escapes definePlugin and the
  // whole plugin fails to import (Error: unknown method … in PluginLoader.importReactPlugin).
  const STEAM_BUTTON_KEY = 0; // eKey for the central Steam/Guide button (eKey=1 is Quick Access)
  let lastReapply = 0;
  const onSystemKey = (event: { eKey?: number }) => {
    if (event?.eKey !== STEAM_BUTTON_KEY) return;
    const now = Date.now();
    if (now - lastReapply < 3000) return;
    lastReapply = now;
    safeCall(() => reapplyRules());
  };
  let keyReg: { unregister?: () => void } | undefined;
  try {
    keyReg = steamClient?.System?.UI?.RegisterForSystemKeyEvents?.(onSystemKey);
  } catch (error) {
    console.error("[deckatv] system-key hook setup failed", error);
  }

  return {
    // Identity must match plugin.json's name (Decky keys the install/settings/log dirs off
    // it) — kept space-free so the plugin folder has no spaces. The panel title below is the
    // separate, human-readable display string.
    name: "DeckaTV",
    titleView: <div className={staticClasses.Title}>DeckaTV</div>,
    content: <Content />,
    icon: <FaTv />,
    onDismount() {
      removeEventListener("auto_switch", listener);
      keyReg?.unregister?.();
    },
  };
});
