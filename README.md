# Evavind — Concept Version

Evan Windproof 的个人网站，Phase 1 桌面概念版本。使用 HTML、CSS 和原生 JavaScript，无框架、无构建步骤、无外部运行依赖。

## 本地预览

```sh
python3 -m http.server 8000
```

在浏览器中打开 http://localhost:8000 。也可直接打开 `index.html`。

## 功能

- 深色极简桌面：中央绿色 Evavind 标题、Concept Version 副标题、右上状态栏和设备本地时间。
- 五应用 Dock：应用启动器、模拟终端、项目、关于、设置。
- 多窗口支持拖动、置顶、最小化、恢复、最大化及关闭；双击标题栏最大化，Escape 关闭最上层窗口。
- 模拟终端：`help`、`about`、`projects`、`open <app>`、`date`、`whoami`、`echo <text>`、`clear`，方向键浏览历史。不会执行系统命令。
- 设置：深色/浅色、12/24 小时制、减少动画，使用 localStorage 保存；禁用存储时仍可使用。
- 响应式布局、键盘焦点、按钮名称及系统减少动画偏好支持。

状态栏网络图标反映浏览器的在线状态，不代表实际互联网连通性；音量按钮仅为模拟状态，不控制设备音量。项目页仅展示当前网站及真实 GitHub 仓库入口。

## 文件

- `index.html`：静态页面入口、状态栏、桌面与 Dock 容器。
- `styles.css`：主题、布局、窗口和响应式样式。
- `app.js`：窗口管理、终端、时钟与设置。
- `tests/desktop.cjs`：Playwright 浏览器交互回归测试。

## 测试

需要 Node.js、Playwright 和 Chromium（仅用于开发测试，网站本身无需安装依赖）。

```sh
npm install --no-save --package-lock=false playwright
python3 -m http.server 8000
# 在另一终端执行；可通过 CHROMIUM_PATH 指定浏览器路径
node tests/desktop.cjs
```

## GitHub Pages 兼容性

所有资源使用相对路径，纯静态文件可由 GitHub Pages 托管。本阶段**未配置或启用 GitHub Pages**，也未添加发布工作流。

## License

保留仓库原有 [LICENSE](LICENSE)，GNU GPL v3。
