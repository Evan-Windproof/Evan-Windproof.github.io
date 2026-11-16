# Evavind — Concept Version · Phase 2

Evan Windproof 的个人网站，基于 Phase 1 桌面架构增量开发。HTML、CSS、原生 JavaScript，无构建步骤，无外部运行依赖。

## 本地预览

```sh
python3 -m http.server 8000
```

打开 http://localhost:8000 ，也支持直接打开 `index.html`。所有资源使用相对路径，兼容现有 GitHub Pages 托管。

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
```

`desktop.cjs` 保留 Phase 1 回归检查，仅更新 Dock 数量并固定中文测试环境。`phase2.cjs` 检查语言默认值/回退、切换与持久化、动态翻译和草稿保留、内部导航、历史分支、刷新、危险 URL、外部/搜索新标签页、opener 隔离、移动尺寸及存储不可用场景。外部/搜索目标通过 Playwright 拦截，验证请求地址和窗口行为，不依赖第三方页面内容。

手动验收可检查：切换语言后拖动窗口、最小化恢复；在浏览器内访问三个内部地址并前后导航；输入关键词打开 DuckDuckGo；切换主题及手机尺寸。

## 文件

- `index.html`、`styles.css`：保留桌面入口及主题，追加 Phase 2 资源与样式。
- `app.js`：原有窗口管理器、应用、终端、时钟和设置。
- `js/i18n.js`、`locales/`：双语资源和文本更新。
- `js/aelthoren.js`、`assets/aelthoren.svg`：概念浏览器及标志。
- `tests/`：Phase 1 回归和 Phase 2 自动化测试。

## 部署与许可证

网址：https://evan-windproof.github.io/ 。沿用已有 GitHub Pages 配置，本次不新增发布工作流或更改 Pages 设置。

保留原有 [LICENSE](LICENSE)：GNU GPL v3（GPL-3.0）。
