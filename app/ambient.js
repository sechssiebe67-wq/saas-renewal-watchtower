/**
 * Focus Flow ambient sound.
 *
 * Pure, dependency-free helpers for the optional background sound layer. This
 * module has no access to the page, the storage layer, the network, or any
 * global: it takes plain data and a caller-supplied audio `context` and returns
 * plain data, so the DOM layer (main.js) owns every side effect and the logic
 * here can be reasoned about and tested on its own.
 *
 * Everything is synthesised in the browser from a deterministic seeded PRNG —
 * no audio files are downloaded, shipped, or requested. The stored shape is
 * `{ type, volume }`; `normalizeAmbient` coerces arbitrary input into that
 * canonical shape without ever throwing.
 */

/** The supported ambient sound ids, in display order. `"off"` disables the
 * layer entirely. */
export const AMBIENT_TYPES = Object.freeze(["off", "brown", "pink", "rain"]);

/** Human-readable names for each ambient id, used by the UI. */
export const AMBIENT_LABELS = Object.freeze({
  off: "Off",
  brown: "Brown noise",
  pink: "Pink noise",
  rain: "Soft rain",
});

/** The default ambient setting: silent, with a comfortable volume ready for
 * when the user picks a sound. */
export const DEFAULT_AMBIENT = Object.freeze({ type: "off", volume: 0.3 });

const MIN_VOLUME = 0;
const MAX_VOLUME = 1;
const DEFAULT_SECONDS = 4;
const DEFAULT_SAMPLE_RATE = 44100;

/** Fixed per-type PRNG seeds so generated buffers are byte-for-byte identical
 * across runs and machines — tests never depend on `Math.random`. */
const NOISE_SEEDS = Object.freeze({
  brown: 0x1a2b3c4d,
  pink: 0x2b3c4d5e,
  rain: 0x3c4d5e6f,
});

/** Mulberry32: a tiny, fast, deterministic 32-bit PRNG. */
function createRandom(seed) {
  let state = seed >>> 0;
  return function next() {
    state = (state + 0x6d2b79f5) | 0;
    let t = Math.imul(state ^ (state >>> 15), 1 | state);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function clampVolume(value) {
  const parsed =
    typeof value === "number" ? value : Number.parseFloat(value);
  if (!Number.isFinite(parsed)) {
    return DEFAULT_AMBIENT.volume;
  }
  if (parsed < MIN_VOLUME) {
    return MIN_VOLUME;
  }
  if (parsed > MAX_VOLUME) {
    return MAX_VOLUME;
  }
  return parsed;
}

/**
 * Coerce arbitrary stored input into the canonical `{ type, volume }` shape.
 *
 * Accepts an object, a bare type string, or anything else. Unknown types fall
 * back to `"off"`, `volume` is clamped to `0..1`, and a missing or malformed
 * volume falls back to the default. Never throws.
 */
export function normalizeAmbient(raw) {
  let source = raw;
  if (typeof raw === "string") {
    source = { type: raw };
  } else if (raw === null || typeof raw !== "object") {
    source = {};
  }

  const type = AMBIENT_TYPES.includes(source.type)
    ? source.type
    : DEFAULT_AMBIENT.type;

  return {
    type,
    volume: clampVolume(source.volume),
  };
}

function fillBrown(data, random) {
  let last = 0;
  for (let i = 0; i < data.length; i += 1) {
    const white = random() * 2 - 1;
    last = (last + 0.02 * white) / 1.02;
    data[i] = last * 3.5;
  }
}

function fillPink(data, random) {
  let b0 = 0;
  let b1 = 0;
  let b2 = 0;
  let b3 = 0;
  let b4 = 0;
  let b5 = 0;
  let b6 = 0;
  for (let i = 0; i < data.length; i += 1) {
    const white = random() * 2 - 1;
    b0 = 0.99886 * b0 + white * 0.0555179;
    b1 = 0.99332 * b1 + white * 0.0750759;
    b2 = 0.969 * b2 + white * 0.153852;
    b3 = 0.8665 * b3 + white * 0.3104856;
    b4 = 0.55 * b4 + white * 0.5329522;
    b5 = -0.7616 * b5 - white * 0.016898;
    data[i] =
      (b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * 0.5362) * 0.11;
    b6 = white * 0.115926;
  }
}

/** Rain is modelled as filtered noise: a one-pole low-pass for the steady
 * hiss plus a sparse, decaying impulse layer for individual droplets. */
function fillRain(data, random) {
  const alpha = 0.12;
  let lowPass = 0;
  let droplet = 0;
  for (let i = 0; i < data.length; i += 1) {
    const white = random() * 2 - 1;
    lowPass += alpha * (white - lowPass);
    if (random() < 0.0015) {
      droplet = 0.5 + random() * 0.5;
    }
    droplet *= 0.9995;
    const sample = lowPass * 0.85 + droplet * (random() * 2 - 1) * 0.35;
    data[i] = Math.max(-1, Math.min(1, sample));
  }
}

/**
 * Build one buffer of the requested noise colour.
 *
 * Returns a `Float32Array` when no audio `context` is available, or an
 * `AudioBuffer` created from `context` when one is supplied. `"off"` (or any
 * unknown type) returns `null`. The generation is deterministic: the same type
 * and options always yield the same samples.
 */
export function createNoiseBuffer(
  context,
  type,
  { seconds = DEFAULT_SECONDS, sampleRate } = {},
) {
  const normalized = normalizeAmbient({ type }).type;
  if (normalized === "off") {
    return null;
  }

  const rate =
    (Number.isFinite(sampleRate) && sampleRate > 0 && sampleRate) ||
    (context && Number.isFinite(context.sampleRate) && context.sampleRate > 0
      ? context.sampleRate
      : DEFAULT_SAMPLE_RATE);
  const safeSeconds =
    Number.isFinite(seconds) && seconds > 0 ? seconds : DEFAULT_SECONDS;
  const length = Math.max(1, Math.round(safeSeconds * rate));
  const data = new Float32Array(length);
  const random = createRandom(NOISE_SEEDS[normalized]);

  if (normalized === "brown") {
    fillBrown(data, random);
  } else if (normalized === "pink") {
    fillPink(data, random);
  } else {
    fillRain(data, random);
  }

  if (context && typeof context.createBuffer === "function") {
    const buffer = context.createBuffer(1, length, rate);
    if (buffer && typeof buffer.copyToChannel === "function") {
      buffer.copyToChannel(data, 0);
    } else if (buffer && typeof buffer.getChannelData === "function") {
      buffer.getChannelData(0).set(data);
    }
    return buffer;
  }

  return data;
}

/**
 * Pure decision helper: should ambient sound currently be playing for the
 * given timer phase?
 *
 * Ambient plays throughout work sessions, and — only when breaks are set to
 * auto-start — keeps playing through the breaks too. `"off"` is always silent.
 * This says nothing about whether the timer is paused; the DOM layer combines
 * it with the running flag so pausing always silences the loop.
 */
export function shouldPlay({ phase, type, autoStartBreaks = false } = {}) {
  const normalized = normalizeAmbient({ type }).type;
  if (normalized === "off") {
    return false;
  }
  if (phase === "work") {
    return true;
  }
  if (phase === "shortBreak" || phase === "longBreak") {
    return Boolean(autoStartBreaks);
  }
  return false;
}
