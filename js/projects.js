'use strict';
window.Projects = (() => {
  // Repository descriptions, README files and visibility checked on 2026-11-22.
  const groups = ['systems', 'research', 'applications', 'web'];
  // name, repository slug, category, documented status, descriptions (简 / 繁 / EN), optional website
  const projects = [
    ['Orfreon', 'Orfreon', 'systems', 'planned', ['计划为多个操作系统提供共享内核基础的实验性外核。','規劃為多個作業系統提供共用核心基礎的實驗性外核心。','A planned experimental exokernel intended as a shared foundation for several operating systems.'], 'https://orfreon.meoy.top/'],
    ['Evavind OS', 'Evavind-OS', 'systems', 'planned', ['基于 Linux 内核的通用桌面操作系统规划，目前处于早期研究。','以 Linux 核心為基礎的通用桌面作業系統，目前處於早期規劃與研究階段。','A general-purpose Linux-based desktop OS in early planning and research.']],
    ['Liberpony OS', 'Liberpony-OS', 'systems', 'planned', ['计划基于 Orfreon 外核开发的开源小马主题操作系统。','規劃以 Orfreon 外核心為基礎的開源小馬主題作業系統。','A planned open-source pony-themed operating system based on Orfreon.']],
    ['Glivand OS', 'Glivand-OS', 'systems', null, ['仓库为私有，无法核验公开项目说明、许可证或开发进度。','儲存庫為私人，無法查證公開專案說明、授權條款或開發進度。','The repository is private. Its public description, license and development progress could not be verified.']],
    ['Liberums', 'Liberums', 'research', 'maintenance', ['用于研究与教学的 C11/i686 外核。v1.0.0 建立了教学基线，主要功能开发已结束。','用於研究與教學的 C11/i686 外核心。v1.0.0 建立教學基準，主要功能開發已結束。','A C11/i686 research and teaching exokernel. v1.0.0 establishes the educational baseline after major feature development.']],
    ['Kernseed OS', 'Kernseed_OS', 'research', 'archived', ['以 C 和汇编实现的 x86-64 教学单体操作系统。项目已完成，无定期维护计划。','以 C 與組合語言實作的 x86-64 教學單體作業系統。專案已完成，無定期維護計畫。','An educational x86-64 monolithic OS written in C and assembly. Completed, with no regular maintenance planned.']],
    ['HoofTTY', 'HoofTTY', 'research', 'beta', ['基于 Kernseed OS 的小马主题文本优先爱好者系统，有独立内核和 Shell。','源自 Kernseed OS 的小馬主題純文字優先同好作業系統，具備獨立核心與 Shell。','A pony-inspired, text-first hobby OS based on Kernseed OS, with its own kernel and shell.']],
    ['LinuxLibOS', 'LinuxLibOS', 'research', null, ['基于 Liberums 的独立 i686 Ring 3 库操作系统，研究受限执行静态 Linux i386 ELF32。','以 Liberums 為基礎的獨立 i686 Ring 3 函式庫作業系統，研究在受限環境中執行靜態 Linux i386 ELF32。','An independent i686 Ring 3 Library OS for Liberums that explores restricted execution of static Linux i386 ELF32 binaries.']],
    ['Aelthuvor', 'Aelthuvor', 'research', null, ['面向 Liberums 的独立 C11/i686 Ring 3 库操作系统及应用 SDK。','供 Liberums 使用的獨立 C11/i686 Ring 3 函式庫作業系統與應用程式 SDK。','An independent C11/i686 Ring 3 Library OS and application SDK for Liberums.']],
    ['Aelthoren', 'Aelthoren', 'applications', 'discontinued', ['基于 Gecko 的实验性浏览器，探索轻量、隐私和无账户设计。','以 Gecko 為基礎的實驗性瀏覽器，探索輕量化、隱私保護及免帳號設計。','An experimental Gecko-based browser exploring lightweight, private, account-free design.']],
    ['liberFPS', 'liberFPS', 'applications', null, ['使用 Godot 和 GDScript 开发的离线单人射击沙盒，已有可游玩的训练场。','以 Godot 與 GDScript 開發的離線單人射擊沙盒，已有可遊玩的訓練場。','An offline single-player FPS sandbox built with Godot and GDScript, with a playable training range.']],
    ['Evan Windproof Website', 'Evan-Windproof.github.io', 'web', null, ['个人技术博客、开源项目入口与 Evavind 模拟桌面。','個人技術部落格、開源專案入口與 Evavind 模擬桌面。','A personal technology blog, open source project index and the Evavind mock desktop.'], 'https://evanwindproof.top/'],
    ['Orfreon Website', 'Orfreon-Website', 'web', 'preview', ['介绍 Orfreon 规划的三语静态网站原型。','介紹 Orfreon 規劃的三語靜態網站原型。','A trilingual static website prototype introducing the plans for Orfreon.'], 'https://orfreon.meoy.top/']
  ];
  const languages = ['zh-CN', 'zh-TW', 'en'];
  const labels = {
    projectFilter: ['按分类筛选','依類別篩選','Filter by category'],
    projectAll: ['全部','全部','All'],
    systems: ['操作系统','作業系統','Operating Systems'],
    research: ['内核与研究','核心與研究','Kernel & Research'],
    applications: ['应用与工具','應用程式與工具','Applications & Tools'],
    web: ['网站项目','網站專案','Web Projects'],
    planned: ['规划中','規劃中','Planned'],
    maintenance: ['维护阶段','維護階段','Maintenance'],
    archived: ['已完成并归档','已完成並封存','Completed and archived'],
    beta: ['实验性测试版','實驗性測試版','Experimental beta'],
    discontinued: ['概念验证已完成，停止维护','概念驗證已完成，停止維護','Proof of concept complete · maintenance discontinued'],
    preview: ['原型预览','原型預覽','Prototype preview'],
    projectWebsite: ['项目网站','專案網站','Website']
  };
  for (const [key, values] of Object.entries(labels)) {
    languages.forEach((lang, index) => { window.EvavindLocales[lang][key] = values[index]; });
  }
  projects.forEach(([, repo, , , description]) => {
    languages.forEach((lang, index) => { window.EvavindLocales[lang][`projectDesc:${repo}`] = description[index]; });
  });

  const external = 'target="_blank" rel="noopener noreferrer"';
  function card([name, repo, group, status, , website]) {
    const {text} = I18n;
    return `<article class="card project-card">
      ${text(group, 'span', 'tag')}
      <h3>${name}</h3>
      ${text(`projectDesc:${repo}`, 'p')}
      ${status ? text(status, 'p', 'project-status') : ''}
      <div class="project-links">
        <a href="https://github.com/Evan-Windproof/${repo}" ${external}>GitHub ↗</a>
        ${website ? `<a href="${website}" ${external}>${text('projectWebsite')} ↗</a>` : ''}
      </div>
    </article>`;
  }

  function markup() {
    const {text, t} = I18n;
    return `<div class="project-showcase">
      ${text('projectsTitle', 'h2')}
      <label class="project-filter">${text('projectFilter')}
        <select data-project-filter>
          <option value="" data-i18n="projectAll">${t('projectAll')}</option>
          ${groups.map(group => `<option value="${group}" data-i18n="${group}">${t(group)}</option>`).join('')}
        </select>
      </label>
      <p><a href="https://github.com/Evan-Windproof?tab=repositories" ${external}>${text('repos')}</a></p>
      ${groups.map(group => `<section data-project-group="${group}">
        ${text(group, 'h3')}
        <div class="cards">${projects.filter(project => project[2] === group).map(card).join('')}</div>
      </section>`).join('')}
    </div>`;
  }

  document.addEventListener('change', event => {
    const filter = event.target.closest('[data-project-filter]');
    if (!filter) return;
    for (const section of filter.closest('.project-showcase').querySelectorAll('[data-project-group]')) {
      section.hidden = Boolean(filter.value && filter.value !== section.dataset.projectGroup);
    }
  });

  return { markup };
})();
