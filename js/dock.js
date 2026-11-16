'use strict';
window.DockVisibility = {
  mount(dock, changeMode) {
    const settings = document.querySelector('.status [data-app="settings"]');
    const trigger = document.createElement('button');
    trigger.type = 'button'; trigger.className = 'dock-trigger';
    trigger.setAttribute('data-i18n-aria-label', 'dockReveal');
    trigger.setAttribute('data-i18n-title', 'dockReveal');
    trigger.setAttribute('aria-controls', 'application-dock');
    dock.id = 'application-dock'; dock.before(trigger);
    const desktop = document.querySelector('#desktop');
    let mode = 'always', expanded = false, timer;
    function cancel() { clearTimeout(timer); }
    function display(show) {
      expanded = show; desktop.classList.toggle('dock-expanded', show);
      dock.inert = !show; dock.setAttribute('aria-hidden', String(!show));
      trigger.setAttribute('aria-expanded', String(show));
    }
    function reveal() { cancel(); if (mode !== 'hidden') display(true); }
    function schedule() {
      cancel();
      if (mode === 'auto') timer = setTimeout(() => {
        if (!dock.matches(':hover') && !dock.contains(document.activeElement) && document.activeElement !== trigger) display(false);
      }, 350);
    }
    function apply(next) {
      const normalized = ['always', 'auto', 'hidden'].includes(next) ? next : 'always';
      if (mode === normalized && desktop.dataset.dockMode) return;
      cancel(); mode = normalized;
      if (mode !== 'always' && dock.contains(document.activeElement)) settings.focus();
      if (mode !== 'auto' && document.activeElement === trigger) settings.focus();
      desktop.dataset.dockMode = mode;
      dock.hidden = mode === 'hidden'; trigger.hidden = mode !== 'auto';
      display(mode === 'always');
    }
    trigger.addEventListener('pointerenter', e => { if (e.pointerType === 'mouse') reveal(); });
    trigger.addEventListener('pointerleave', schedule);
    trigger.addEventListener('focus', reveal);
    trigger.addEventListener('blur', schedule);
    trigger.addEventListener('click', reveal);
    dock.addEventListener('pointerenter', reveal);
    dock.addEventListener('pointerleave', schedule);
    dock.addEventListener('focusin', reveal);
    dock.addEventListener('focusout', schedule);
    document.addEventListener('pointerdown', e => {
      if (mode === 'auto' && !dock.contains(e.target) && !trigger.contains(e.target)) {
        if (dock.contains(document.activeElement) || document.activeElement === trigger) settings.focus();
        cancel(); display(false);
      }
    });
    document.addEventListener('keydown', e => {
      if (e.ctrlKey && e.altKey && !e.metaKey && (e.code === 'KeyD' || e.key.toLowerCase() === 'd')) {
        e.preventDefault(); changeMode(mode === 'hidden' ? 'always' : 'hidden');
        if (mode === 'always') dock.querySelector('button')?.focus();
      }
    });
    return { apply, reveal, focusApp(id) {
      if (mode === 'hidden') settings.focus();
      else { reveal(); dock.querySelector(`[data-app="${id}"]`)?.focus(); }
    } };
  }
};
