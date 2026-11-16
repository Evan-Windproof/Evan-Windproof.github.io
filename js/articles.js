'use strict';
window.Articles = (() => {
  function safeLink(raw) {
    try {
      const url = new URL(raw);
      return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password ? url.href : null;
    } catch { return null; }
  }
  // A deliberately small Markdown subset. All untrusted text enters text nodes,
  // never innerHTML. Raw HTML/images are not interpreted; links are allowlisted.
  function inline(parent, source, depth = 0) {
    if (depth > 8) { parent.append(document.createTextNode(source)); return; }
    const pattern = /`([^`]+)`|\[([^\]\n]+)\]\(([^\s)]+)\)|\*\*([^*]+)\*\*|\*([^*]+)\*/g;
    let match, offset = 0;
    while ((match = pattern.exec(source))) {
      parent.append(document.createTextNode(source.slice(offset, match.index)));
      let node;
      if (match[1] !== undefined) { node = document.createElement('code'); node.textContent = match[1]; }
      else if (match[2] !== undefined) {
        const href = safeLink(match[3]);
        if (href) {
          node = document.createElement('a'); node.href = href;
          node.target = '_blank'; node.rel = 'noopener noreferrer'; inline(node, match[2], depth + 1);
        } else node = document.createTextNode(match[0]);
      } else {
        node = document.createElement(match[4] !== undefined ? 'strong' : 'em');
        inline(node, match[4] ?? match[5], depth + 1);
      }
      parent.append(node); offset = pattern.lastIndex;
    }
    parent.append(document.createTextNode(source.slice(offset)));
  }
  function markdown(source) {
    const fragment = document.createDocumentFragment();
    const lines = source.replace(/\r\n?/g, '\n').split('\n');
    const special = line => /^(?:\s*$|```|#{1,6}\s|>\s?|[-*]\s|\d+\.\s|---+$)/.test(line);
    for (let i = 0; i < lines.length;) {
      const line = lines[i]; let node, match;
      if (!line.trim()) { i++; continue; }
      if (line.startsWith('```')) {
        node = document.createElement('pre'); const code = document.createElement('code'); const body = [];
        i++; while (i < lines.length && !lines[i].startsWith('```')) body.push(lines[i++]);
        if (i < lines.length) i++;
        code.textContent = body.join('\n'); node.append(code);
      } else if ((match = /^(#{1,6})\s+(.+)$/.exec(line))) {
        node = document.createElement('h' + match[1].length); inline(node, match[2]); i++;
      } else if (/^---+$/.test(line)) { node = document.createElement('hr'); i++; }
      else if (/^>\s?/.test(line)) {
        node = document.createElement('blockquote'); const body = [];
        while (i < lines.length && /^>\s?/.test(lines[i])) body.push(lines[i++].replace(/^>\s?/, ''));
        inline(node, body.join('\n'));
      } else if (/^(?:[-*]|\d+\.)\s+/.test(line)) {
        const ordered = /^\d+\./.test(line); node = document.createElement(ordered ? 'ol' : 'ul');
        const pattern = ordered ? /^\d+\.\s+(.*)$/ : /^[-*]\s+(.*)$/;
        while (i < lines.length && (match = pattern.exec(lines[i]))) {
          const item = document.createElement('li'); inline(item, match[1]); node.append(item); i++;
        }
      } else {
        node = document.createElement('p'); const body = [line]; i++;
        while (i < lines.length && !special(lines[i])) body.push(lines[i++]);
        inline(node, body.join('\n'));
      }
      fragment.append(node);
    }
    return fragment;
  }
  const find = id => window.EvavindArticles.find(article => article.id === id);
  const localized = article => article.translations[I18n.language] || article.translations.en;
  function metadata(parent, article, data) {
    const meta = document.createElement('p'); meta.className = 'article-meta';
    const date = document.createElement('time'); date.dateTime = article.date;
    date.textContent = new Date(article.date + 'T00:00:00Z').toLocaleDateString(I18n.language, { timeZone: 'UTC', year: 'numeric', month: 'long', day: 'numeric' });
    meta.append(date, document.createTextNode(' · ' + data.category)); parent.append(meta);
  }
  function list(page) {
    page.replaceChildren();
    const heading = document.createElement('h2'); heading.textContent = I18n.t('articles'); page.append(heading);
    const intro = document.createElement('p'); intro.className = 'muted'; intro.textContent = I18n.t('articlesIntro'); page.append(intro);
    const items = document.createElement('div'); items.className = 'article-list';
    [...window.EvavindArticles].sort((a,b) => b.date.localeCompare(a.date)).forEach(article => {
      const data = localized(article); const entry = document.createElement('article'); entry.className = 'article-card';
      const button = document.createElement('button'); button.dataset.navigate = 'aelthoren://articles/' + article.id; button.textContent = data.title;
      const title = document.createElement('h3'); title.append(button); entry.append(title);
      metadata(entry, article, data);
      const summary = document.createElement('p'); summary.textContent = data.summary; entry.append(summary); items.append(entry);
    });
    page.append(items);
  }
  async function read(page, id, isCurrent) {
    const article = find(id); page.replaceChildren();
    if (!article) { const p = document.createElement('p'); p.textContent = I18n.t('articleMissing'); page.append(p); return; }
    const data = localized(article);
    const header = document.createElement('header');
    const back = document.createElement('button'); back.className = 'article-back'; back.dataset.navigate = 'aelthoren://articles'; back.textContent = '← ' + I18n.t('articles'); header.append(back);
    const heading = document.createElement('h2'); heading.textContent = data.title; header.append(heading); metadata(header, article, data);
    const summary = document.createElement('p'); summary.className = 'muted'; summary.textContent = data.summary; header.append(summary);
    const body = document.createElement('div'); body.className = 'markdown-body'; body.setAttribute('aria-busy', 'true'); body.textContent = I18n.t('articleLoading');
    page.append(header, body);
    try {
      const response = await fetch(data.file, { cache: 'no-store' });
      if (!response.ok) throw Error('Article unavailable');
      const source = await response.text();
      if (!isCurrent()) return;
      body.replaceChildren(markdown(source));
    } catch {
      if (isCurrent()) { body.setAttribute('role', 'status'); body.textContent = I18n.t('articleError'); }
    } finally { if (isCurrent()) body.setAttribute('aria-busy', 'false'); }
  }
  return { list, read, markdown };
})();
