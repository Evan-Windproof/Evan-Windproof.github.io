'use strict';
window.Aelthoren = (() => {
  const HOME = 'aelthoren://home';
  const INTERNAL = [HOME, 'aelthoren://about', 'aelthoren://projects', 'aelthoren://articles'];
  // Explicit schemes are never treated as search terms. Only validated HTTP(S)
  // addresses reach external links; user input is never inserted as HTML.
  function resolve(raw) {
    const value = raw.trim();
    if (!value) return { type: 'internal', url: HOME };
    if (/^aelthoren:/i.test(value)) {
      const url = value.toLowerCase().replace(/\/$/, '');
      return (INTERNAL.includes(url) || /^aelthoren:\/\/articles\/[a-z0-9]+(?:-[a-z0-9]+)*$/.test(url)) ? { type: 'internal', url } : { type: 'error', key: 'notFound' };
    }
    if (/^[a-z][a-z\d+.-]*:/i.test(value)) {
      try {
        const url = new URL(value);
        if (!['https:', 'http:'].includes(url.protocol) || !url.hostname || url.username || url.password || /[\u0000-\u0020<>"\\]/.test(value)) throw Error();
        return { type: 'external', url: url.href };
      } catch { return { type: 'error', key: 'badUrl' }; }
    }
    if (/[\u0000-\u001f]/.test(value) || /^[^\s]*:/.test(value)) return { type: 'error', key: 'badUrl' };
    if (/^(?:localhost|(?:[a-z\d-]+\.)+[a-z\d-]+)(?:[/:?#]|$)/i.test(value) && !/\s/.test(value)) return resolve('https://' + value);
    return { type: 'search', url: 'https://duckduckgo.com/?q=' + encodeURIComponent(value) };
  }
  function mount(win, { projectMarkup, aboutMarkup }) {
    const { t, text: tx } = I18n;
    const root = win.querySelector('.window-content');root.classList.add('browser-content');
    root.innerHTML = `<div class="browser-toolbar"><div class="browser-actions">${[['back','←'],['forward','→'],['reload','↻'],['home','⌂']].map(([id,glyph])=>`<button type="button" data-browser="${id}" data-i18n-aria-label="${id}" data-i18n-title="${id}" aria-label="${t(id)}" title="${t(id)}">${glyph}</button>`).join('')}</div><form class="address-form"><input class="address" aria-label="${t('address')}" data-i18n-aria-label="address" spellcheck="false" autocomplete="off" autocapitalize="off"><button data-i18n="go">${t('go')}</button></form><button type="button" data-browser="bookmarks" data-i18n-aria-label="bookmarks" data-i18n-title="bookmarks" aria-label="${t('bookmarks')}" title="${t('bookmarks')}" aria-expanded="false">☆</button></div><div class="browser-bookmarks" hidden></div><p class="browser-feedback" role="status" hidden></p><div class="browser-page"></div>`;
    const page=root.querySelector('.browser-page'),address=root.querySelector('.address'),feedback=root.querySelector('.browser-feedback');
    const history=[{type:'internal',url:HOME}];let index=0, renderVersion=0;
    const shortcuts=()=>`<div class="browser-shortcuts"><button data-navigate="https://github.com/Evan-Windproof">GitHub ↗</button><button data-navigate="https://github.com/Evan-Windproof/Evan-Windproof.github.io" data-i18n="evavindProject">${t('evavindProject')}</button><button data-navigate="aelthoren://projects" data-i18n="projects">${t('projects')}</button><button data-navigate="aelthoren://articles" data-i18n="articles">${t('articles')}</button><button data-navigate="aelthoren://about" data-i18n="browserAbout">${t('browserAbout')}</button></div>`;
    root.querySelector('.browser-bookmarks').innerHTML=shortcuts();
    function showFeedback(key) { feedback.hidden=false;feedback.dataset.i18n=key;feedback.textContent=t(key); }
    function render() {
      const version=++renderVersion;const current=history[index];address.value=current.url;
      root.querySelector('[data-browser="back"]').disabled=index===0;
      root.querySelector('[data-browser="forward"]').disabled=index===history.length-1;
      if(current.type==='external') {
        page.innerHTML=`${tx('externalTitle','h2')}${tx('externalNote','p','muted')}<p class="external-url"></p><a class="external-link" target="_blank" rel="noopener noreferrer" data-i18n="openExternal">${t('openExternal')}</a>`;
        page.querySelector('.external-url').textContent=current.url;
        page.querySelector('.external-link').href=current.url;
      } else if(current.url==='aelthoren://articles') { Articles.list(page);
      } else if(current.url.startsWith('aelthoren://articles/')) { Articles.read(page,current.url.slice('aelthoren://articles/'.length),()=>version===renderVersion && win.isConnected);
      } else if(current.url===HOME) {
        page.innerHTML=`<div class="browser-home"><img class="aelthoren-logo" src="assets/aelthoren.svg" alt="Aelthoren"><h2>Aelthoren</h2><form class="home-search"><input data-i18n-placeholder="search" data-i18n-aria-label="address" placeholder="${t('search')}" aria-label="${t('address')}" autocomplete="off" autocapitalize="off"><button data-i18n="go">${t('go')}</button></form>${tx('searchNote','p','muted')}${tx('shortcuts','h3')}${shortcuts()}</div>`;
        page.querySelector('form').addEventListener('submit',e=>{e.preventDefault();navigate(e.currentTarget.querySelector('input').value)});
      } else if(current.url==='aelthoren://projects') page.innerHTML=projectMarkup();
      else page.innerHTML=`<img class="aelthoren-logo small" src="assets/aelthoren.svg" alt="Aelthoren">${tx('browserAbout','h2')}${tx('browserNotice','p','muted')}<hr>${aboutMarkup()}`;
      I18n.translate(root);
    }
    function navigate(raw) {
      const target=resolve(raw);
      if(target.type==='error'){showFeedback(target.key);return}
      if(target.type==='search') {
        // Called synchronously from a user gesture; noopener prevents opener access.
        window.open(target.url,'_blank','noopener,noreferrer');showFeedback('searchNote');return;
      }
      feedback.hidden=true;
      if(history[index].url!==target.url){history.splice(index+1);history.push(target);index++}
      render();page.scrollTop=0;
    }
    root.querySelector('.address-form').addEventListener('submit',e=>{e.preventDefault();navigate(address.value)});
    root.addEventListener('click',e=>{
      const link=e.target.closest('[data-navigate]');if(link){navigate(link.dataset.navigate);return}
      const control=e.target.closest('[data-browser]');if(!control)return;
      const action=control.dataset.browser;
      if(action==='bookmarks'){const panel=root.querySelector('.browser-bookmarks');panel.hidden=!panel.hidden;control.setAttribute('aria-expanded',String(!panel.hidden));return}
      if(action==='home'){navigate(HOME);return}
      if(action==='back'&&index>0)index--;
      if(action==='forward'&&index<history.length-1)index++;
      feedback.hidden=true;render();
    });
    // Translate existing nodes rather than remounting: preserve drafts, selection,
    // scroll, current address, bookmark visibility and instance-only history.
    win.translateBrowser=()=>{I18n.translate(root);if(history[index].url.startsWith('aelthoren://articles')){const draft=address.value,scroll=page.scrollTop;render();address.value=draft;page.scrollTop=scroll}};
    render();
  }
  return { mount, resolve };
})();
