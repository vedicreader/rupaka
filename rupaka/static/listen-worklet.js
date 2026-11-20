/* listen-worklet: finds drum onsets in the microphone signal, on this device, and posts {t}: the time of each onset on the context clock.
   It keeps no audio. Each hop of about 5 ms gives the log energy of the high-passed, rectified signal. The flux is its rise over the
   running median of the hops before it. An onset is a flux over median + 4 MAD of the recent flux (and over a floor), then 60 ms of rest.
   The listen block loads this file with audioWorklet.addModule from the folder of rupaka.js. */
const median = a => {
  const s = Float64Array.from(a).sort(), n = s.length;
  return n ? (n % 2 ? s[n >> 1] : (s[n / 2 - 1] + s[n / 2]) / 2) : 0;
};

class RupakaListen extends AudioWorkletProcessor {
  constructor() {
    super();
    this.hop = Math.max(32, Math.round(sampleRate * 0.005));
    const rc = 1 / (2 * Math.PI * 150);
    this.a = rc / (rc + 1 / sampleRate);   // a one-pole high-pass at 150 Hz takes away hum and handling noise
    this.px = 0; this.py = 0;
    this.buf = new Float32Array(this.hop); this.n = 0; this.at = 0;   // `at`: the frame of the first sample of this hop
    this.logs = []; this.flux = []; this.rest = 0;
    this.LOGS = 10;     // 50 ms of log energy for the running median
    this.FLUX = 100;    // 0.5 s of flux for the threshold
    this.FLOOR = 0.3;   // a rise of at least 3 dB (log10 units), so a still room gives no onset
    this.REST = Math.round(0.06 * sampleRate / this.hop);
  }
  process(inputs) {
    const x = inputs[0] && inputs[0][0];
    if (!x) return true;
    for (let i = 0; i < x.length; i++) {
      const y = this.a * (this.py + x[i] - this.px);
      this.px = x[i]; this.py = y;
      if (this.n === 0) this.at = currentFrame + i;
      this.buf[this.n++] = y;
      if (this.n === this.hop) { this.step(); this.n = 0; }
    }
    return true;
  }
  step() {
    let e = 0, peak = 0;
    for (let i = 0; i < this.hop; i++) { const y = Math.abs(this.buf[i]); e += y * y; if (y > peak) peak = y; }
    e = Math.log10(e / this.hop + 1e-12);
    const f = this.logs.length >= this.LOGS ? Math.max(0, e - median(this.logs)) : 0;
    this.logs.push(e); if (this.logs.length > this.LOGS) this.logs.shift();
    const ready = this.flux.length >= 20, m = median(this.flux), mad = median(this.flux.map(v => Math.abs(v - m)));
    this.flux.push(f); if (this.flux.length > this.FLUX) this.flux.shift();
    if (this.rest > 0) { this.rest--; return; }
    if (!ready || e < -8 || f <= Math.max(m + 4 * mad, this.FLOOR)) return;
    let k = 0;   // the first sample of the hop at a quarter of its peak: a time finer than the hop
    while (k < this.hop - 1 && Math.abs(this.buf[k]) < 0.25 * peak) k++;
    this.port.postMessage({t: (this.at + k) / sampleRate});
    this.rest = this.REST;
  }
}

try { registerProcessor('rupaka-listen', RupakaListen); } catch (_) { /* this context has it already */ }
