# Evan Windproof — Personal Technology Blog

技术博客是核心内容；Evavind 桌面保留为视觉特色和兼容入口。以下历史功能继续保留。

## 博客架构与本次变更

原站使用 HTML/CSS/原生 JavaScript、DOM 窗口管理器和纯静态 GitHub Pages，旧 Articles 只在 Aelthoren 窗口内读取 Markdown。本次追加 Python 静态生成器，不替换窗口系统；保留 Articles 旧地址、C-Skeleton、Orfreon、GitHub/GitLab/X 和联系方式。原有界面实际仅有简体中文和英文，本次补齐繁体中文资源及语言选择；文章不自动翻译。

- `content/blog/YYYY/*.md`：正式博客唯一内容源，YAML front matter + Markdown。
- `scripts/build_blog.py`：生成独立 `/blog/<slug>/index.html`、列表、首页最新文章、`rss.xml`、`sitemap.xml` 和 `robots.txt`。
- `blog/blog.css`、`blog/blog.js`：阅读主题、本地搜索、三语言界面，沿用原设置存储。
- `requirements-blog.txt`：固定生成依赖（Markdown/Pygments/PyYAML/Bleach）；运行站点不需要 Python。
- `.github/workflows/blog.yml`：推送 main 后构建静态产物并通过官方 Pages Actions 发布，复用现有 Pages 站点并保留 CNAME；如仍有原生分支构建，先等待同一提交的旧构建结束，再发布新产物以防覆盖。

每篇 Markdown 必须填写 `title`、`description`、`date`、`updated`、`tags`（数组）、`category`、`slug`（全站唯一小写英文短横线）、`draft`（布尔值）、`language`。日期为 YYYY-MM-DD，正文从二级标题开始；slug 发布后保持不变。`draft: true` 不进入页面、搜索、RSS、首页或 sitemap。文章按日期降序排列，相邻文章导航在有相邻文章时显示。当前仅一篇明确标注的简体中文示例，无虚构成果或翻译。

```sh
python3 -m venv work/venv
work/venv/bin/pip install -r requirements-blog.txt
work/venv/bin/python scripts/build_blog.py
python3 -m http.server 8000
```

直接访问 `/blog/` 和 `/blog/example-systems-note/`，刷新无需桌面路由。支持 fenced code（c/cpp/rust/python/bash）、表格、图片、链接、目录和锚点；原始 HTML 经白名单清理。图片放 assets，正文路径建议从 `/assets/` 开始。本地搜索覆盖标题、摘要、分类与标签，不发送网络请求。切换界面语言不会翻译文章。

生成文件一并提交便于普通静态预览；CI 每次从 Markdown 重新生成。不要手改生成文章 HTML、RSS、sitemap、highlight.css 或首页 latest 标记区域。删除文章后重新构建会依据 `blog/.generated.json` 清除旧生成页面。旧 `articles/` 内容继续按旧发布方式维护，不自动迁移或删除。

## 验证与部署

`python scripts/build_blog.py`、`node tests/blog.cjs`（需本地 8000 HTTP 服务）、以及下方原桌面回归测试。博客测试覆盖无 JS 独立阅读/刷新、Markdown 表格/高亮/图片/目录、搜索、RSS/sitemap、主题/繁体界面、手机排版与旧项目入口。部署使用 GitHub Pages 官方 artifact/deploy 流程，无商业服务或数据库。若仓库策略拒绝 Actions 更新 Pages source，需要管理员在 Settings → Pages → Build and deployment 选择 GitHub Actions；不要删除 CNAME 或其他项目仓库。

# Evavind — Concept Version · Phase 3.1

Evan Windproof 的个人网站，基于 Phase 1 桌面架构增量开发。HTML、CSS、原生 JavaScript；桌面无构建依赖，正式博客使用上方静态生成流程。

## 本地预览

```sh
python3 -m http.server 8000
```

打开 http://localhost:8000 。桌面也可直接打开 `index.html`，但文章正文通过 fetch 加载，需使用 HTTP 服务器预览。所有资源使用相对路径，兼容现有 GitHub Pages 托管。

## 联系方式

现有 About / 关于页面包含 Contact / 联系方式区域，支持即时切换中英文，沿用深浅主题。Aelthoren 的关于页复用该内容。

- Email：[evan.windproof@tutanota.de](mailto:evan.windproof@tutanota.de)，点击调用设备默认邮件应用。
- GitHub：https://github.com/Evan-Windproof

## Phase 3.1：Dock 显示控制与阶段性收尾

在 Settings 的 **Dock Visibility / Dock 显示方式** 中选择：

- **Always Show / 始终显示**：默认，保持原有 Dock 行为。
- **Auto Hide / 自动隐藏**：闲置时收起至桌面外，鼠标移至底部窄触发区显示，离开后延迟 350ms 收起；移入 Dock 或焦点位于 Dock 内时保持展开。触屏点击底部短线区域展开，点击其他区域收起。
- **Always Hide / 始终隐藏**：Dock 及触发区域完全隐藏，但不关闭或重建运行中的应用。右上角设置按钮始终可用，可随时恢复模式。

自动隐藏时，键盘用户可用 Tab 聚焦底部展开区域，再 Tab 进入 Dock。**Ctrl + Alt + D** 将当前模式切换为始终隐藏；再次按下切换为始终显示并聚焦第一个应用。快捷键切换也会同步设置选项并保存。隐藏 Dock 后关闭或最小化窗口，焦点返回右上角设置按钮，避免焦点落入隐藏控件。

模式存入原有 `evavind-settings.dockVisibility`，不影响主题、语言、时钟等字段；存储不可用时仍可切换，只是不跨刷新保存。新增选项、提示、触发区标签均即时切换中英文。普通窗口的尺寸和位置保持不变；最大化窗口在 Dock 始终隐藏时扩展至底部 12px 边距，在自动隐藏收起时仅保留 18px 触发区，展开 Dock 后恢复预留空间；收起后的 Dock 不拦截窗口点击，只有底部 18px 窄触发区保留交互。

至此进入阶段性稳定维护：后续以 Bug 修复、体验优化和文章内容更新为主，不主动增加大型功能。

## Phase 3：紧凑工具栏与静态文章

Aelthoren 保留窗口标题栏，将返回、前进、刷新、主页、地址栏和书签整合到同一行。手机端缩小按钮和间距，地址栏弹性占用剩余空间。桌面与六应用 Dock 不变，文章不增加 Dock 图标。

首页快捷栏及书签入口新增 **Articles / 文章**：

- `aelthoren://articles`：按发布日期降序展示标题、日期、分类和摘要。
- `aelthoren://articles/<id>`：在当前浏览器窗口内阅读 Markdown 正文。
- 使用原有返回、前进、刷新及主页按钮；刷新重新读取正文文件。
- 切换语言更新列表、元信息和正文，保留窗口位置、导航历史及地址栏草稿。缺少当前语言版本时回退英语。
- 附带一篇明确标注为“示例”的双语文章，不代表真实技术研究或成果。

### 发布与维护文章

1. 在 `articles/<id>/` 中添加 UTF-8 的 `zh-CN.md` 和 `en.md`。
2. 在 `articles/index.js` 数组中登记文章。ID 使用小写字母、数字和单连字符，如 `my-first-note`；日期为 `YYYY-MM-DD`，是手动指定的发布日期。
3. 每个语言版本填写 `title`、`category`、`summary`、`file`。路径相对网站根目录，建议使用 `articles/<id>/<language>.md`。至少提供 `en` 版本。
4. 本地启动 HTTP 服务，检查中英文列表、正文和前后导航，再提交文件。无需数据库、服务器程序或构建步骤。

索引结构示例（说明用途，不是额外文章）：

```javascript
{
  id: 'my-first-note',
  date: '2026-11-17',
  translations: {
    'zh-CN': { title: '标题', category: '笔记', summary: '摘要', file: 'articles/my-first-note/zh-CN.md' },
    en: { title: 'Title', category: 'Notes', summary: 'Summary', file: 'articles/my-first-note/en.md' }
  }
}
```

正文支持标题、段落、粗体、斜体、行内代码、三反引号代码块、引用、简单有序/无序列表、分隔线及 HTTP/HTTPS 链接。这是精简 Markdown 子集，不支持表格、嵌套列表、图片、原始 HTML 或完整 CommonMark 扩展。代码不执行，也没有语法高亮依赖。

`js/articles.js` 将正文和元信息作为不可信文本处理，通过 DOM/textContent 创建内容，禁止原始 HTML 执行；链接仅允许 HTTP/HTTPS，使用 `noopener noreferrer`。不要将不可信 JavaScript 放入文章索引：索引本身是受代码审查的站点配置，正文才是 Markdown 数据。加载失败可使用刷新重试，过期的异步加载结果不会覆盖后续导航页面。

## Phase 2

### 中文 / English

在设置窗口的 **Language / 语言** 中选择简体中文或 English，立即切换，无需刷新。首次访问根据浏览器语言选择：中文语言映射至 `zh-CN`，其他语言回退至 `en`。手动选择保存在原有 `evavind-settings` localStorage 对象中，保留主题、时钟及动画设置。

Dock、应用名、已打开和最小化窗口、页面、终端帮助与反馈、Aelthoren 界面及可访问性标签均支持切换。更新文本节点和属性，保留窗口位置、层级、输入、终端命令历史及浏览导航历史。终端历史中的系统反馈随语言变化，用户输入和 echo 内容保持原样。HTML `lang` 同步更新。存储不可用时仍可切换，但不跨刷新保存。

翻译资源位于 `locales/zh-CN.js` 和 `locales/en.js`，由 `js/i18n.js` 统一处理。

### Aelthoren Web Concept / Mock Browser

通过 Dock、Applications 或终端 `open aelthoren` 启动，使用原有窗口管理器。主页标志为根据提供图形制作的本地 SVG。

- `aelthoren://home`：标志、搜索/地址框、常用站点和 GitHub / Evavind 项目入口。
- `aelthoren://about`：概念浏览器说明和个人介绍。
- `aelthoren://projects`：复用现有项目内容。
- 支持返回、前进、刷新、主页、书签入口。历史仅保存在当前实例，关闭后重置。
- 输入 HTTP / HTTPS URL 显示外部访问页面，提供“在新标签页中打开”。常见裸域名补全 HTTPS。
- 输入搜索词通过外部新标签页访问 DuckDuckGo，不抓取、不代理搜索结果。新标签页打开受宿主浏览器弹窗策略影响。
- 拒绝 `javascript:`、`data:`、`file:` 等协议、未知内部地址以及含凭据的 URL。用户地址通过 DOM 属性和 textContent 写入，不插入 HTML。

本实现**不内嵌外部网页**，因为网站可能通过 CSP / X-Frame-Options 禁止嵌入；不会绕过这些限制，也不声称所有网页可在窗口内访问。外部入口使用 `noopener noreferrer`。

Aelthoren 是 Evan Windproof 的实验性浏览器项目名，此处仅为 Web Concept。**不包含 Gecko 引擎，不是真正的独立浏览器，不具备完整浏览器安全隔离**。未移植 C++ 代码，未修改独立 Aelthoren 仓库。

## 保留的 Phase 1 功能

- 深色/浅色桌面、绿色 Evavind 标题、Concept Version 副标题和设备本地时间。
- 原有五应用及新增 Aelthoren，共六个 Dock 入口。
- 多窗口拖动、置顶、最小化、恢复、最大化和关闭；双击标题栏最大化，Escape 关闭最上层窗口。
- 终端 `help`、`about`、`projects`、`open <app>`、`date`、`whoami`、`echo <text>`、`clear`，方向键浏览命令历史。仅为模拟终端。
- 12/24 小时制、减少动画、本地保存设置、移动布局及键盘操作。

网络图标只反映浏览器在线状态，不代表实际互联网连通性；音量按钮仅模拟状态。

## 测试

需要 Node.js、Playwright 和 Chromium，仅供开发测试。

```sh
npm install --no-save --package-lock=false playwright
python3 -m http.server 8000
# 另一终端；可通过 CHROMIUM_PATH 指定 Chromium
node tests/desktop.cjs
node tests/phase2.cjs
node tests/phase3.cjs
node tests/phase31.cjs
node tests/dock-window.cjs
```

`desktop.cjs` 保留 Phase 1 回归检查，仅更新 Dock 数量并固定中文测试环境。`phase2.cjs` 检查语言默认值/回退、切换与持久化、动态翻译和草稿保留、内部导航、历史分支、刷新、危险 URL、外部/搜索新标签页、opener 隔离、移动尺寸及存储不可用场景。外部/搜索目标通过 Playwright 拦截，验证请求地址和窗口行为，不依赖第三方页面内容。

`phase3.cjs` 额外检查单行工具栏及按钮互不遮挡、文章入口/元信息/正文、返回/前进/刷新、中英文列表与正文、找不到文章/加载失败/过期异步结果、Markdown XSS 防护，以及 320/390/768 像素布局。

`phase31.cjs` 检查三种 Dock 模式、鼠标隐藏/恢复、焦点访问、设置恢复入口、快捷键、运行中应用保留、三模式刷新持久化、中英文选项、手机触控及禁用存储。

手动验收可检查：切换语言后拖动窗口、最小化恢复；在浏览器内访问内部地址与文章并前后导航；输入关键词打开 DuckDuckGo；切换主题及手机尺寸。

## 文件

- `index.html`、`styles.css`：保留桌面入口及主题，追加浏览器和文章资源与样式。
- `app.js`：原有窗口管理器、应用、终端、时钟和设置。
- `js/i18n.js`、`locales/`：双语资源和文本更新。
- `js/aelthoren.js`、`assets/aelthoren.svg`：概念浏览器及标志。
- `js/articles.js`、`articles/index.js`、`articles/*/*.md`：安全 Markdown 阅读器、静态索引和双语正文。
- `js/dock.js`：独立的 Dock 显示控制，复用原有设置系统。
- `tests/`：Phase 1–3 回归及 Phase 3.1 自动化测试。

## 部署与许可证

网址：https://evan-windproof.github.io/ 。沿用已有 GitHub Pages 配置，正式博客发布使用上方 GitHub Actions 流程。

保留原有 [LICENSE](LICENSE)：GNU GPL v3（GPL-3.0）。
