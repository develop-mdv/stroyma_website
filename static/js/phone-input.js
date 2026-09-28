(function () {
  'use strict';

  const DEFAULT_HINT = 'Введите 10 цифр после +7. Полный номер можно вставить с 8 или +7.';
  const INCOMPLETE_HINT = 'Введите все 10 цифр номера после +7.';

  function digitsOnly(value) {
    return (value || '').replace(/\D/g, '');
  }

  function nationalDigits(value) {
    const digits = digitsOnly(value);
    const hasCountryPrefix = /^\s*\+7/.test(value) ||
      (digits.length === 11 && /^[78]/.test(digits)) ||
      (digits.length === 1 && /^[78]/.test(digits));
    return (hasCountryPrefix ? digits.slice(1) : digits).slice(0, 10);
  }

  function format(digits) {
    if (!digits) return '+7';
    let value = '+7 (' + digits.slice(0, 3);
    if (digits.length >= 3) value += ')';
    if (digits.length > 3) value += ' ' + digits.slice(3, 6);
    if (digits.length > 6) value += '-' + digits.slice(6, 8);
    if (digits.length > 8) value += '-' + digits.slice(8, 10);
    return value;
  }

  function indexAt(value, position) {
    return Math.max(0, digitsOnly(value.slice(0, position)).length - 1);
  }

  function positionAt(value, digitIndex) {
    const opening = value.indexOf('(');
    if (opening < 0) return value.length;
    const positions = [];
    for (let i = opening + 1; i < value.length; i++) {
      if (/\d/.test(value[i])) positions.push(i);
    }
    if (!positions.length) return value.length;
    return digitIndex >= positions.length ? value.length : positions[digitIndex];
  }

  function attach(input) {
    if (input.dataset.phoneMaskInit) return;
    input.dataset.phoneMaskInit = '1';
    input.inputMode = 'numeric';

    const hintId = input.getAttribute('aria-describedby');
    const hint = hintId ? document.getElementById(hintId.split(/\s+/)[0]) : null;
    const originalHint = hint ? hint.textContent : DEFAULT_HINT;

    function validate(showError) {
      const count = nationalDigits(input.value).length;
      const emptyRequired = input.required && count === 0;
      const incomplete = count > 0 && count < 10;
      const message = emptyRequired ? 'Введите номер телефона.' :
        (incomplete ? INCOMPLETE_HINT : '');
      input.setCustomValidity(message);
      const visibleError = showError && !!message;
      input.setAttribute('aria-invalid', visibleError ? 'true' : 'false');
      if (hint) {
        hint.textContent = visibleError ? message : originalHint;
        hint.classList.toggle('phone-mask-error', visibleError);
      }
    }

    function setValue(digits, caretIndex) {
      input.value = format(digits.slice(0, 10));
      const position = positionAt(input.value, caretIndex);
      input.setSelectionRange(position, position);
      validate(false);
    }

    function reformat() {
      const raw = input.value;
      const caret = input.selectionStart == null ? raw.length : input.selectionStart;
      const allDigits = digitsOnly(raw);
      const prefixed = /^\s*\+7/.test(raw) ||
        (allDigits.length === 11 && /^[78]/.test(allDigits)) ||
        (allDigits.length === 1 && /^[78]/.test(allDigits));
      const digitsBefore = digitsOnly(raw.slice(0, caret)).length - (prefixed ? 1 : 0);
      setValue(nationalDigits(raw), Math.max(0, digitsBefore));
    }

    input.addEventListener('beforeinput', function (event) {
      const start = input.selectionStart;
      const end = input.selectionEnd;
      if (start == null || end == null) return;

      const digits = nationalDigits(input.value);
      const from = indexAt(input.value, start);
      const to = indexAt(input.value, end);

      if (event.inputType === 'deleteContentBackward' || event.inputType === 'deleteContentForward') {
        event.preventDefault();
        if (to > from) {
          setValue(digits.slice(0, from) + digits.slice(to), from);
        } else if (event.inputType === 'deleteContentBackward' && from > 0) {
          setValue(digits.slice(0, from - 1) + digits.slice(from), from - 1);
        } else if (event.inputType === 'deleteContentForward' && from < digits.length) {
          setValue(digits.slice(0, from) + digits.slice(from + 1), from);
        }
        return;
      }

      if (event.inputType === 'insertText' && event.data) {
        event.preventDefault();
        if (!/^\d+$/.test(event.data)) return;
        if (digits.length === 10 && from === to) return;
        setValue(digits.slice(0, from) + event.data + digits.slice(to), from + event.data.length);
      }
    });

    input.addEventListener('input', reformat);
    input.addEventListener('change', function () {
      if (input.value && !/^\+7 \(/.test(input.value)) reformat();
    });

    input.addEventListener('paste', function (event) {
      const text = event.clipboardData && event.clipboardData.getData('text');
      if (!text) return;
      const pasted = digitsOnly(text);
      if (!pasted) return;
      event.preventDefault();

      const number = (/^\s*\+7/.test(text) || pasted.length === 11 && /^[78]/.test(pasted))
        ? pasted.slice(1) : pasted;
      if (number.length >= 10) {
        setValue(number.slice(0, 10), 10);
        return;
      }

      const current = nationalDigits(input.value);
      const from = indexAt(input.value, input.selectionStart || 0);
      const to = indexAt(input.value, input.selectionEnd || 0);
      setValue(current.slice(0, from) + number + current.slice(to), from + number.length);
    });

    input.addEventListener('blur', function () {
      validate(true);
    });

    if (input.form && !input.required) {
      input.form.addEventListener('submit', function () {
        if (!nationalDigits(input.value)) input.value = '';
      });
    }

    input.value = format(nationalDigits(input.value));
    validate(false);
  }

  function init() {
    document.querySelectorAll('input[type="tel"][name="phone"]').forEach(attach);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
