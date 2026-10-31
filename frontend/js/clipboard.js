(function () {
  async function writeText(text) {
    try { await navigator.clipboard.writeText(text); return { ok: true }; }
    catch (error) {
      if (error?.name === 'AbortError') return { ok: false, cancelled: true };
      try {
        const area = document.createElement('textarea'); area.value = text; area.setAttribute('readonly', '');
        area.style.position = 'fixed'; area.style.opacity = '0'; document.body.appendChild(area); area.select();
        const copied = document.execCommand('copy') === true; area.remove(); if (copied) return { ok: true, fallback: true };
      } catch (_) { /* Report a clear message below. */ }
      return { ok: false, message: 'Copy was blocked by browser permissions. Select and copy the text manually.' };
    }
  }
  async function readText() {
    try { return { ok: true, text: await navigator.clipboard.readText() }; }
    catch (error) { return error?.name === 'AbortError' ? { ok: false, cancelled: true } : { ok: false, message: 'Clipboard access was blocked. Paste directly into the log area.' }; }
  }
  window.clipboardService = { readText, writeText };
})();
