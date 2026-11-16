'use strict';
window.I18n = (() => {
  const supported = ['zh-CN', 'en'];
  let language = /^zh(?:-|$)/i.test(navigator.language) ? 'zh-CN' : 'en';
  try {
    const saved = JSON.parse(localStorage.getItem('evavind-settings') || '{}');
    if (supported.includes(saved.language)) language = saved.language;
  } catch {}
  function t(key, values = {}) {
    let text = window.EvavindLocales[language][key] ?? window.EvavindLocales.en[key] ?? key;
    return text.replace(/\{(\w+)\}/g, (_, name) => String(values[name] ?? ''));
  }
  function translate(root = document) {
    root.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
    for (const attr of ['aria-label', 'title', 'placeholder']) {
      root.querySelectorAll(`[data-i18n-${attr}]`).forEach(el => {
        el.setAttribute(attr, t(el.getAttribute(`data-i18n-${attr}`)));
      });
    }
  }
  function setLanguage(next) {
    language = supported.includes(next) ? next : 'en';
    document.documentElement.lang = language;
    translate();
    document.dispatchEvent(new CustomEvent('languagechange'));
  }
  const text = (key, tag = 'span', cls = '') => `<${tag} class="${cls}" data-i18n="${key}">${t(key)}</${tag}>`;
  return { t, text, translate, setLanguage, get language() { return language; } };
})();
