import { safeCall, setStreaming } from "./api";

// Watches for a Remote Play session streaming *from* this machine and pushes that state to the
// backend, which pauses auto-switch while one is live: the player is elsewhere in the house, so
// grabbing the docked TV's input would take it from whoever is actually watching it.
//
// Pushed on change only — no polling and no heartbeat, so an idle machine sends nothing at all.
// The cost of that is a missed "stopped" event leaving the pause stuck on, which three cheap
// things undo: `resyncStreaming` on every panel open, the backend clearing the flag on resume,
// and the panel's indicator making a stuck pause visible instead of silent.

interface RemotePlaySettings {
  unStreamingSessionID?: number;
}

interface Registration {
  unregister?: () => void;
}

// One watcher exists per session (registered in definePlugin), so its state lives at module
// scope — that is what lets the panel re-push it on open without owning the subscriptions.
const sessions = new Set<string>();
let streamingSessionId = 0;
let pushed: boolean | null = null;

const sessionKey = (steamId: string, guestId: number) => `${steamId}:${guestId}`;
const isStreaming = () => sessions.size > 0 || streamingSessionId !== 0;

/** Push the backend's copy of the flag, unconditionally. */
export function resyncStreaming() {
  const active = isStreaming();
  pushed = active;
  safeCall(() => setStreaming(active));
}

// RegisterForSettingsChanges fires for *any* Remote Play setting, not just a session starting or
// stopping, so handlers push through here: one RPC per real transition, however chatty the
// callbacks are. resyncStreaming stays unconditional — it repairs a backend whose view has
// drifted, which this cache would otherwise suppress.
const pushIfChanged = () => isStreaming() !== pushed && resyncStreaming();

// Two independent signals, OR'd, because neither alone is trustworthy. SessionStarted/Stopped is
// the symmetric, purpose-built pair but leaks an entry if a stop is ever missed; the settings'
// unStreamingSessionID is level state, but only clears the set on an observed non-zero → zero
// transition, so a settings stream that never populates the field can't cancel the pause.
export function watchStreaming(): () => void {
  const remotePlay = (window as unknown as { SteamClient?: any }).SteamClient?.RemotePlay;

  const onSessionStarted = (steamId: string, _gameId: string, guestId: number) => {
    sessions.add(sessionKey(steamId, guestId));
    pushIfChanged();
  };

  const onSessionStopped = (steamId: string, guestId: number) => {
    sessions.delete(sessionKey(steamId, guestId));
    pushIfChanged();
  };

  const onSettingsChanged = (settings: RemotePlaySettings) => {
    const current = settings?.unStreamingSessionID ?? 0;
    if (streamingSessionId !== 0 && current === 0) sessions.clear();
    streamingSessionId = current;
    pushIfChanged();
  };

  const registrations: (Registration | undefined)[] = [];
  try {
    registrations.push(
      remotePlay?.RegisterForSessionStarted?.(onSessionStarted),
      remotePlay?.RegisterForSessionStopped?.(onSessionStopped),
      remotePlay?.RegisterForSettingsChanges?.(onSettingsChanged),
    );
  } catch (error) {
    console.error("[deckatv] remote-play hook setup failed", error);
  }

  return () => {
    registrations.forEach((registration) => registration?.unregister?.());
    sessions.clear();
    streamingSessionId = 0;
    resyncStreaming();
  };
}
