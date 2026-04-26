(function () {
  function countDigits(str) {
    let n = 0;
    for (let i = 0; i < str.length; i++) if (str[i] >= '0' && str[i] <= '9') n++;
    return n;
  }

  function digitsOnly(str) {
    return (str || '').replace(/\D/g, '');
  }

  function normalizeDigits(d) {
    if (!d) return '';

    // If user types 10 digits (without 7/8), assume Russia.
    if (d.length === 10 && d[0] !== '7' && d[0] !== '8') return '7' + d;

    // If starts with 8 (common "8..." format) -> immediately convert to 7.
    // Do it early (not only on full length), otherwise input feels "broken"
    // while user types and when they delete characters.
    if (d[0] === '8') d = '7' + d.slice(1);

    // If starts with 9 and user continues (common case) — prepend 7.
    if (d.length > 0 && d[0] === '9') d = '7' + d;

    // Limit to 11 digits (7 + 10).
    return d.slice(0, 11);
  }

  function formatRuPhone(d) {
    const nd = normalizeDigits(d);
    if (!nd) return '';

    const a = nd.slice(0, 1); // 7
    const b = nd.slice(1, 4);
    const c = nd.slice(4, 7);
    const e = nd.slice(7, 9);
    const f = nd.slice(9, 11);

    let out = '+' + a;
    if (b) out += ' (' + b;
    if (b.length === 3) out += ')';
    if (c) out += ' ' + c;
    if (e) out += '-' + e;
    if (f) out += '-' + f;
    return out;
  }

  function caretPosForDigitIndex(formatted, digitIndex) {
    // digitIndex: how many digits should be before caret
    if (digitIndex <= 0) return 0;
    let seen = 0;
    for (let i = 0; i < formatted.length; i++) {
      const ch = formatted[i];
      if (ch >= '0' && ch <= '9') {
        seen++;
        if (seen >= digitIndex) return i + 1;
      }
    }
    return formatted.length;
  }

  function attach(input) {
    if (!input || input.dataset.phoneMaskInit === '1') return;
    input.dataset.phoneMaskInit = '1';

    input.setAttribute('inputmode', 'tel');
    if (!input.getAttribute('autocomplete')) input.setAttribute('autocomplete', 'tel');

    let lastValue = input.value || '';

    function reformat() {
      const raw = input.value || '';
      const selStart = input.selectionStart ?? raw.length;
      const digitsBefore = countDigits(raw.slice(0, selStart));

      const formatted = formatRuPhone(digitsOnly(raw));
      input.value = formatted;

      const newPos = caretPosForDigitIndex(formatted, digitsBefore);
      try {
        input.setSelectionRange(newPos, newPos);
      } catch (_e) {
        // Some inputs/browsers may block selection range.
      }

      lastValue = formatted;
    }

    function deleteDigitAt(digits, idx) {
      if (idx < 0 || idx >= digits.length) return digits;
      return digits.slice(0, idx) + digits.slice(idx + 1);
    }

    input.addEventListener('keydown', function (e) {
      if (e.key !== 'Backspace' && e.key !== 'Delete') return;

      const raw = input.value || '';
      const start = input.selectionStart ?? raw.length;
      const end = input.selectionEnd ?? start;

      const digitsRaw = normalizeDigits(digitsOnly(raw));
      if (!digitsRaw) return; // allow default behavior on empty

      const startDigit = countDigits(raw.slice(0, start));
      const endDigit = countDigits(raw.slice(0, end));

      let digits = digitsRaw;
      let newDigitCaret = startDigit;

      // If selection exists: remove selected digits range
      if (endDigit > startDigit) {
        digits = digits.slice(0, startDigit) + digits.slice(endDigit);
        newDigitCaret = startDigit;
      } else if (e.key === 'Backspace') {
        // Remove previous digit
        const removeAt = startDigit - 1;
        if (removeAt >= 0) {
          digits = deleteDigitAt(digits, removeAt);
          newDigitCaret = Math.max(0, startDigit - 1);
        } else {
          return; // nothing to delete
        }
      } else {
        // Delete: remove next digit
        const removeAt = startDigit;
        if (removeAt < digits.length) {
          digits = deleteDigitAt(digits, removeAt);
          newDigitCaret = startDigit;
        } else {
          return; // nothing to delete
        }
      }

      // If user deletes down to just "7" (country code) — clear completely.
      if (!digits || digits === '7') {
        e.preventDefault();
        input.value = '';
        lastValue = '';
        try {
          input.setSelectionRange(0, 0);
        } catch (_e) {}
        return;
      }

      e.preventDefault();
      const formatted = formatRuPhone(digits);
      input.value = formatted;
      lastValue = formatted;

      const newPos = caretPosForDigitIndex(formatted, newDigitCaret);
      try {
        input.setSelectionRange(newPos, newPos);
      } catch (_e) {}
    });

    input.addEventListener('input', reformat);
    input.addEventListener('blur', function () {
      // Cleanup: if only "+7" or "+7 (" left — clear to avoid confusing partial values.
      const d = normalizeDigits(digitsOnly(input.value));
      if (!d || d === '7') {
        input.value = '';
        lastValue = '';
        return;
      }
      input.value = formatRuPhone(d);
      lastValue = input.value;
    });

    // Init formatting for prefilled values.
    if (input.value) {
      const formatted = formatRuPhone(digitsOnly(input.value));
      input.value = formatted;
      lastValue = formatted;
    }

    // If browser auto-fills later, keep it formatted (cheap polling for a short time).
    let checks = 0;
    const t = window.setInterval(function () {
      checks++;
      if (input.value !== lastValue) reformat();
      if (checks > 20) window.clearInterval(t);
    }, 250);
  }

  function init() {
    const inputs = document.querySelectorAll(
      'input[type="tel"], input[name*="phone" i], input[id*="phone" i]'
    );
    inputs.forEach(attach);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

