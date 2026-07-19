import { ButtonItem, DialogButton, DropdownItem, PanelSectionRow, TextField } from "@decky/ui";
import { toaster } from "@decky/api";
import { useEffect, useRef, useState } from "react";
import { discoverTvs, pairTv, type Brand, type DiscoveredTv } from "../api";

// A discovered TV name prefills the editable Name field; cap its length so a long name
// can't overflow the panel here (or anywhere the name is later shown).
const MAX_NAME = 20;

// Decky remounts the Quick Access content whenever a dropdown overlay opens and closes —
// which is exactly how you pick a discovered TV. Without persistence that remount would
// reset the form (host back to "") and re-fire the auto-scan, so the selection vanished
// and Pair never became reachable. Stash the form here and write to it *synchronously*
// from each onChange (an effect can be torn down before it flushes, losing the pick).
// `discoveredBrand` records which brand `discovered` belongs to so we only auto-scan when
// the brand actually changed, not on every remount. `pin`/`pinRequired` survive the same
// remount: opening the on-screen keyboard to type a Sony PIN itself remounts the panel, so
// the PIN step must persist here or it would vanish mid-entry.
type FormCache = {
  host: string;
  name: string;
  brand: string;
  discovered: DiscoveredTv[];
  discoveredBrand: string;
  pin: string;
  pinRequired: boolean;
};
let formCache: FormCache = {
  host: "",
  name: "",
  brand: "",
  discovered: [],
  discoveredBrand: "",
  pin: "",
  pinRequired: false,
};

export function AddTv({ brands, onPaired }: { brands: Brand[]; onPaired: (host: string) => void }) {
  const [host, setHost] = useState(formCache.host);
  const [name, setName] = useState(formCache.name);
  const [brand, setBrand] = useState(formCache.brand);
  const [busy, setBusy] = useState(false);
  // Sony's PIN pairing is two-phase: the first Pair press makes the TV show a code, the
  // backend reports SONY_PIN_REQUIRED, and we reveal this field to enter it and re-pair.
  const [pin, setPin] = useState(formCache.pin);
  const [pinRequired, setPinRequired] = useState(formCache.pinRequired);
  const [discovered, setDiscovered] = useState<DiscoveredTv[]>(formCache.discovered);
  const [scanning, setScanning] = useState(false);
  // Bumped on every new scan and on cleanup, so a stale/cancelled scan's result is dropped.
  const scanToken = useRef(0);

  // Any pending PIN belongs to one specific TV, so drop it whenever the target (host or
  // brand) changes — otherwise a stale code would be submitted against the wrong set.
  const resetPin = () => {
    formCache.pin = "";
    formCache.pinRequired = false;
    setPin("");
    setPinRequired(false);
  };

  const setPinField = (next: string) => {
    const digits = next.replace(/\D/g, "").slice(0, 8);
    formCache.pin = digits;
    setPin(digits);
  };

  const pickHost = (next: string) => {
    formCache.host = next;
    setHost(next);
    resetPin();
  };

  const setNameField = (next: string) => {
    const capped = next.slice(0, MAX_NAME);
    formCache.name = capped;
    setName(capped);
  };

  // Picking a discovered TV also prefills the optional name with its reported name.
  const pickDiscovered = (selectedHost: string) => {
    pickHost(selectedHost);
    const found = discovered.find((tv) => tv.host === selectedHost);
    if (found?.name) {
      setNameField(found.name);
    }
  };

  // brands load async, so adopt the first one once it arrives (and keep any user choice).
  useEffect(() => {
    if (!brand && brands.length > 0) {
      formCache.brand = brands[0].id;
      setBrand(brands[0].id);
    }
  }, [brands, brand]);

  const scan = async () => {
    if (!brand) {
      return;
    }
    const token = ++scanToken.current;
    setScanning(true);
    try {
      const found = await discoverTvs(brand);
      if (token === scanToken.current) {
        formCache.discovered = found;
        formCache.discoveredBrand = brand;
        setDiscovered(found);
      }
    } catch {
      if (token === scanToken.current) {
        formCache.discovered = [];
        formCache.discoveredBrand = brand;
        setDiscovered([]);
      }
    } finally {
      if (token === scanToken.current) {
        setScanning(false);
      }
    }
  };

  // Scan automatically when the brand changes — but not on the remounts Decky triggers
  // when a dropdown overlay closes (we'd otherwise re-scan and clobber the selection).
  // `discoveredBrand` already matching `brand` means we've scanned it, so we skip.
  // The cleanup bumps the token so an in-flight scan is abandoned when the brand switches
  // or this view unmounts, so no background scan ever outlives the Add form.
  useEffect(() => {
    if (!brand || formCache.discoveredBrand === brand) {
      return;
    }
    pickHost("");
    formCache.discovered = [];
    setDiscovered([]);
    void scan();
    return () => {
      scanToken.current++;
      setScanning(false);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [brand]);

  const canPair = Boolean(host && brand) && !busy && (!pinRequired || pin.length > 0);

  const pair = async () => {
    if (!canPair) {
      return;
    }
    setBusy(true);
    try {
      // Send the PIN only once the TV has asked for it; other brands (and Sony's first
      // press) pair with an empty secret.
      const tv = await pairTv(host, name, brand, pinRequired ? pin : "");
      toaster.toast({ title: "TV paired", body: tv.name || tv.host });
      // Clear the cached form (keep the brand) so re-opening Add starts a fresh scan.
      formCache = {
        host: "",
        name: "",
        brand,
        discovered: [],
        discoveredBrand: "",
        pin: "",
        pinRequired: false,
      };
      setHost("");
      setName("");
      resetPin();
      onPaired(tv.host);
    } catch (error) {
      // The backend's sentinel means "the TV is now showing a PIN" — reveal the field and
      // wait for the user to enter it, rather than reporting a failure.
      if (String(error).includes("SONY_PIN_REQUIRED")) {
        formCache.pinRequired = true;
        setPinRequired(true);
        toaster.toast({
          title: "Enter the PIN",
          body: "A code is showing on your TV — type it below, then press Pair.",
        });
      } else {
        toaster.toast({ title: "Pairing failed", body: String(error) });
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PanelSectionRow>
        <DropdownItem
          label="Brand"
          layout="below"
          bottomSeparator="none"
          rgOptions={brands.map((item) => ({ data: item.id, label: item.label }))}
          selectedOption={brand}
          onChange={(option) => {
            formCache.brand = option.data;
            setBrand(option.data);
            resetPin();
          }}
        />
      </PanelSectionRow>
      <PanelSectionRow>
        <DropdownItem
          label="Discovered TVs"
          layout="below"
          bottomSeparator="none"
          disabled={scanning || discovered.length === 0}
          strDefaultLabel={
            scanning ? "Scanning…" : discovered.length === 0 ? "No TVs found" : "Select a TV"
          }
          rgOptions={discovered.map((tv) => ({ data: tv.host, label: tv.name || tv.host }))}
          selectedOption={host}
          onChange={(option) => pickDiscovered(option.data)}
        />
      </PanelSectionRow>
      <PanelSectionRow>
        <ButtonItem layout="below" bottomSeparator="none" disabled={scanning} onClick={scan}>
          {scanning ? "Scanning…" : "Scan Network"}
        </ButtonItem>
      </PanelSectionRow>
      <PanelSectionRow>
        <TextField
          label="IP or hostname"
          value={host}
          onChange={(event) => pickHost(event.target.value.trim())}
        />
      </PanelSectionRow>
      <PanelSectionRow>
        <TextField
          label="Name (optional)"
          value={name}
          onChange={(event) => setNameField(event.target.value)}
        />
      </PanelSectionRow>
      {pinRequired ? (
        <PanelSectionRow>
          <TextField
            label="PIN shown on TV"
            value={pin}
            onChange={(event) => setPinField(event.target.value)}
          />
        </PanelSectionRow>
      ) : null}
      <PanelSectionRow>
        <DialogButton
          disabled={!canPair}
          onClick={pair}
          // Green while it's an actionable (or in-progress) Pair; an explicit grey when
          // there's nothing to pair yet — DialogButton renders no background in its disabled
          // state, which left just the floating word "Pair", so force a visible button.
          style={
            host && brand
              ? { width: "100%", backgroundColor: "#4caf50", color: "#0e141b" }
              : { width: "100%", backgroundColor: "#3d4450", color: "#9aa0a6" }
          }
        >
          {busy
            ? pinRequired
              ? "Pairing…"
              : "Accept the prompt on your TV…"
            : pinRequired
              ? "Submit PIN"
              : "Pair"}
        </DialogButton>
      </PanelSectionRow>
    </>
  );
}
