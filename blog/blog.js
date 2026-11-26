'use strict';
let settings={};try{settings=JSON.parse(localStorage.getItem('evavind-settings')||'{}')}catch{}
function theme(){document.body.classList.toggle('light',settings.theme==='light')}
function save(){try{localStorage.setItem('evavind-settings',JSON.stringify(settings))}catch{}}
theme();I18n.setLanguage(I18n.language);
const language=document.querySelector('#blog-language');language.value=I18n.language;
language.addEventListener('change',()=>{settings.language=language.value;save();I18n.setLanguage(language.value)});
document.querySelector('#blog-theme').addEventListener('click',()=>{settings.theme=settings.theme==='light'?'dark':'light';save();theme()});

const list = document.querySelector('#article-list');
function translateCounts() {
  document.querySelectorAll('[data-post-count]').forEach(node => {
    node.textContent = I18n.t('blogPostCount', {count: node.dataset.postCount});
  });
}
document.addEventListener('languagechange', translateCounts);
translateCounts();
if (list) setupSearch(list);

function setupSearch(list) {
  const search = document.querySelector('#blog-search');
  const cards = document.querySelector('#article-cards');
  const pagination = document.querySelector('#article-pagination');
  const empty = document.querySelector('#search-empty');
  const error = document.querySelector('#search-error');
  const base = list.dataset.listBase;
  const size = Number(list.dataset.pageSize);
  const staticPath = location.pathname;
  const staticCards = [...cards.children];
  const staticNav = [...pagination.children];
  let index;
  let renderId = 0;

  function element(tag, text = '', className = '') {
    const node = document.createElement(tag);
    node.textContent = text;
    if (className) node.className = className;
    return node;
  }
  function link(text, url, className) {
    const node = element('a', text, className);
    node.href = url;
    return node;
  }
  function resultCard(post) {
    const article = element('article', '', 'post-card');
    const date = element('time', post.date);
    date.dateTime = post.date;
    const title = element('h2');
    title.append(link(post.title, post.url));
    const tags = element('div', '', 'tag-list');
    post.tags.forEach((tag, i) => tags.append(link(tag.trim(), post.tagUrls[i], 'tag-link')));
    article.append(date, title, element('p', post.description), element('p', post.category, 'muted'));
    if (tags.childElementCount) article.append(tags);
    return article;
  }
  function searchUrl(query, page) {
    const params = new URLSearchParams({q: query});
    if (page > 1) params.set('page', page);
    return base + '?' + params;
  }
  function searchNav(query, current, pages, count) {
    if (pages <= 1) return;
    const nav = element('nav', '', 'blog-pagination');
    nav.dataset.i18nAriaLabel = 'blogPagination';
    function pageLink(number, label, key) {
      const anchor = link(label, searchUrl(query, number));
      anchor.dataset.searchPage = number;
      if (key) anchor.dataset.i18n = key;
      return anchor;
    }
    if (current > 1) nav.append(pageLink(current - 1, '', 'blogPrevPage'));
    const numbers = [...new Set([1, pages, current - 1, current, current + 1])]
      .filter(n => n >= 1 && n <= pages).sort((a, b) => a - b);
    let previous = 0;
    for (const number of numbers) {
      if (number - previous === 2) nav.append(pageLink(previous + 1, previous + 1));
      if (number - previous > 2) {
        const dots = element('span', '…');
        dots.setAttribute('aria-hidden', 'true');
        nav.append(dots);
      }
      if (number === current) {
        const active = element('span', number);
        active.setAttribute('aria-current', 'page');
        nav.append(active);
      } else nav.append(pageLink(number, number));
      previous = number;
    }
    if (current < pages) nav.append(pageLink(current + 1, '', 'blogNextPage'));
    const total = element('span', '', 'pagination-count');
    total.dataset.postCount = count;
    nav.append(total);
    pagination.append(nav);
    I18n.translate(pagination);
    translateCounts();
  }
  function getIndex() {
    index ??= fetch('/blog/articles.json').then(response => {
      if (!response.ok) throw new Error('Article index unavailable');
      return response.json();
    }).catch(cause => {
      index = null;
      throw cause;
    });
    return index;
  }
  async function render(scroll = false, syncInput = true) {
    const id = ++renderId;
    const params = new URLSearchParams(location.search);
    const query = (params.get('q') || '').trim();
    if (syncInput) search.value = query;
    error.hidden = empty.hidden = true;
    if (!query) {
      if (location.pathname !== staticPath) {
        location.reload();
        return;
      }
      cards.replaceChildren(...staticCards);
      pagination.replaceChildren(...staticNav);
      I18n.translate(pagination);
      translateCounts();
      return;
    }
    cards.replaceChildren();
    pagination.replaceChildren();
    try {
      const posts = await getIndex();
      if (id !== renderId) return;
      const needle = query.toLocaleLowerCase();
      const results = posts.filter(post =>
        (base === '/blog/' || post.tagUrls.includes(base))
        && [post.title, post.description, post.category, ...post.tags].join(' ').toLocaleLowerCase().includes(needle));
      const pages = Math.max(1, Math.ceil(results.length / size));
      const value = params.get('page') || '1';
      const current = /^[1-9]\d*$/.test(value) ? Math.min(Number(value), pages) : 1;
      history.replaceState(history.state, '', searchUrl(query, current));
      cards.replaceChildren(...results.slice((current - 1) * size, current * size).map(resultCard));
      empty.hidden = results.length !== 0;
      searchNav(query, current, pages, results.length);
      if (scroll) {
        list.focus({preventScroll: true});
        list.scrollIntoView();
      }
    } catch {
      if (id === renderId) error.hidden = false;
    }
  }
  search.addEventListener('input', () => {
    const query = search.value.trim();
    if (!query && !new URLSearchParams(location.search).has('q')) return;
    const hadQuery = new URLSearchParams(location.search).has('q');
    if (!query && staticPath !== base) {
      location.assign(base);
      return;
    }
    const method = hadQuery && !history.state?.searchPage ? 'replaceState' : 'pushState';
    history[method]({searchPage: false}, '', query ? searchUrl(query, 1) : base);
    void render(false, false);
  });
  pagination.addEventListener('click', event => {
    const anchor = event.target.closest('[data-search-page]');
    if (!anchor || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    history.pushState({searchPage: true}, '', anchor.href);
    void render(true);
  });
  window.addEventListener('popstate', () => void render());
  void render(location.search.includes('page='));
}
