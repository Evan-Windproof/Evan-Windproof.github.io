# IndexNow 手动提交指南

IndexNow 用于向参与该协议的搜索引擎通知页面变更。HTTP 200 表示已收到通知，HTTP 202 表示已收到通知、密钥仍待校验。抓取和收录由各搜索引擎独立决定。Google 不参与 IndexNow，请继续使用现有的 Google Search Console、Sitemap 和 RSS。[IndexNow 官方文档](https://www.indexnow.org/documentation) · [参与者列表](https://www.indexnow.org/searchengines.json)

## 部署并验证公开密钥

站点根目录的 `{KEY}.txt` 是站点所有权验证文件。文件名和文件内容使用同一个密钥，内容为 UTF-8，且没有 BOM 或末尾换行。该文件随仓库发布，现有 GitHub Pages 工作流会将它复制到站点根目录。已有的有效密钥可直接沿用。如果需要初始化，可在仓库根目录运行：

```sh
python scripts/indexnow.py --init-key
```

将根目录的密钥文件纳入版本管理。部署完成后，在仓库根目录运行以下命令。验证成功时，脚本会确认 `https://evanwindproof.top/{KEY}.txt` 返回 HTTP 200，响应正文与本地密钥逐字节一致。

```sh
python scripts/indexnow.py --verify-key
```

## 预览并提交 URL

先用现有博客生成器刷新本地 `sitemap.xml`：

```sh
python -m pip install -r requirements-blog.txt
python -X utf8 scripts/build_blog.py
```

客户端以站点地图中的页面为准，要求 URL 使用 `https://evanwindproof.top/`，并保留生成器输出的末尾斜杠。草稿和静态资源不在站点地图中；带查询参数或片段的 URL 会被拒绝。正式提交前，客户端还会验证线上密钥和生产站点地图中的 URL。

先预览单页。预览会校验 URL、按首次出现的顺序去重，并显示端点和各批 URL。它不联网、不读取密钥，也不写提交日志。

```sh
python scripts/indexnow.py --url https://evanwindproof.top/blog/kernseed/ --dry-run
```

部署和密钥验证通过后，可手动提交单页、多页或文件列表。列表使用 UTF-8，每行填一个完整 URL，空行会跳过。

```sh
python scripts/indexnow.py --url https://evanwindproof.top/blog/kernseed/
python scripts/indexnow.py --url https://evanwindproof.top/blog/kernseed/ --url https://evanwindproof.top/blog/c-skeleton/
python scripts/indexnow.py --url-file urls.txt
```

如需批量提交站点地图里的全部页面，可先预览，再显式运行提交命令。`--batch-size` 可设为 1 至 10000，默认 10000。

```sh
python scripts/indexnow.py --sitemap --batch-size 1000 --dry-run
python scripts/indexnow.py --sitemap --batch-size 1000
```

## 查看日志和处理失败

每个已尝试提交的批次会在 `.indexnow/submissions.jsonl` 追加一行，内容包括 UTC 时间、URL 列表、批次大小、端点、最终 HTTP 状态、结果、重试次数和错误信息。日志仅存于本地，且不含密钥。

```sh
cat .indexnow/submissions.jsonl
```

在 PowerShell 中可运行 `Get-Content .indexnow/submissions.jsonl`。

| HTTP 状态 | 处理方式 |
| --- | --- |
| 200 | 通知已收到。 |
| 202 | 通知已收到，IndexNow 正在验证密钥。 |
| 400 | 检查请求格式。 |
| 403 | 运行 `--verify-key`，检查密钥文件是否已部署且内容一致。 |
| 422 | 检查 URL 是否与站点地图一致，以及请求内容是否符合协议。 |
| 429 | 根据 `Retry-After` 等待后重试；缺失或无效时采用退避。如果服务器要求等待超过 60 秒，本次运行结束，请按服务器要求稍后重试。 |
| 5xx | 按退避策略重试；如提供有效的 `Retry-After`，同样遵守等待上限。 |

429 和 5xx 每批最多重试三次。批次最终失败后，脚本会返回非零退出码，后续批次不会发送。重新提交前先看日志，确认哪些批次已收到回执。

## 运行测试

```sh
python -m unittest discover -s tests -p test_indexnow.py -v
```

运行完整 Python 回归测试前，请安装 `requirements-blog.txt` 中的依赖。IndexNow 测试使用模拟 HTTP 响应，状态并发测试使用本地临时 Git 仓库。

工作流也会运行现有浏览器回归。博客浏览器用例依赖可编辑的示例文章，失败时会发出警告，以免删除、转草稿或更改示例文章的 slug 时阻止部署。

## 第二阶段自动通知

在 `main` 创建、编辑、发布或删除 Markdown 后，原有 **Build and deploy technology blog** 工作流构建站点、执行回归测试、部署 GitHub Pages。部署成功后，通知作业核对生产版本标记、公开密钥和 Sitemap，再提交已变化且待发送的 URL。失败的构建、失败的部署、非 `main` 分支和预览不会触发通知。通知作业失败时，已完成的 Pages 部署继续提供服务。

生成器从实际发布的文章生成 `indexnow-manifest.json`。清单包含 `schema_version`、部署提交 `commit` 和以生产规范 URL 为键的 `articles`。每篇文章记录 Markdown 路径、SHA-256 指纹及标题、描述、日期、更新日期、标签、分类和语言。指纹使用清理后的正文和发布元数据，忽略普通 HTML 文本的换行与连续空白，保留代码中的空白。模板重建、文件移动、草稿和静态资源变更不会单独进入通知队列。公开站点只额外发布 `indexnow-deployment.txt`，内容为该次部署的 Git 提交 SHA。

以实际成功部署的清单为差异基线。新增和更新提交当前 URL，删除和转草稿提交旧 URL，slug 变更提交新旧两个 URL。当前 URL 必须出现在生产 Sitemap。删除和替换前的 URL 必须来自之前可信的发布清单，并等到生产 Sitemap 移除该 URL 后再发送。两者均须使用生产域名及规范的 HTTPS 文章路径。同一 URL 在队列中只保留较新的变更。手动命令仍要求 URL 出现在 Sitemap；如确需批量提交，使用前述显式的 `--sitemap` 命令。

## 状态、失败处理与暂停

同一仓库的 `indexnow-state` 分支通过 `state.json` 保存长期状态。部署部分存放已上线清单和将要部署的候选清单。通知部分分别存放待发事件和已接受回执。部署前保存候选清单，便于下次发布从生产版本标记找回已上线但因作业中断而未记录的部署。整个工作流串行执行，状态只允许普通快进推送，过期写入会被 Git 拒绝。仓库自带的 `GITHUB_TOKEN` 只在状态作业获得 `contents: write`。公开仓库的状态分支也可公开读取，保存的是发布元数据和回执，无密钥、令牌或文章正文。清单和 JSONL 日志在 Actions 中保留 30 天，均不进入 Pages 文件目录。

首次成功部署只建立基线，保留已有待发项，不回填现有文章。初始化以前的变更不在自动通知范围内。没有变更或待发项时不会调用 IndexNow API。中断发生在保存候选状态之前，或站点连续多次在无法读取生产标记时发布，中间版本可能无法自动补齐。遇到未登记的生产版本时，自动发送会暂停。先从对应部署的产物、Git 提交和状态历史恢复。

每批最多 100 个 URL。HTTP 200 和 202 的回执按批保存，后续批次失败时，已接受的批次在下次运行中跳过。HTTP 429、5xx 使用有上限的重试和退避。网络失败、密钥验证问题或暂时错误会保留待发项，在下次成功部署时重试。HTTP 400 和 422 会保留并暂停该批次；修复原因后在 Actions 手动运行 `main` 的工作流，勾选 `retry_blocked`。如果远端已接收而连接在回执之前中断，或收到回执后状态保存失败，下次可能重复发送该批，无法保证恰好一次。

在 Actions 打开相应运行的 **Summary**，查看部署前后提交、初始化状态、变更计数、待发数、HTTP 状态、重试和接受数。需要逐批排查时下载 `indexnow-submissions-*` 产物。要暂停实际发送，在仓库 **Settings → Secrets and variables → Actions → Variables** 把 `INDEXNOW_AUTOMATION` 设为 `off`。部署仍继续记录基线并积累待发事件。恢复时删除该变量或改为 `on`，然后运行 `main` 工作流。

## 恢复状态分支

在维护时段操作，先暂停发送并等待当前部署结束。优先找回最近一条已核对的状态提交，以保留待发项和已接受的回执。如果分支存在但文件损坏，核对已知良好提交的 `state.json` 后，将其树以当前损坏分支最新提交为父追加恢复。使用普通推送，保留状态历史：

```sh
git fetch origin refs/heads/indexnow-state
tip=$(git rev-parse FETCH_HEAD)
good=替换为已验证的状态提交SHA
git show "${good}:state.json"
restored=$(git commit-tree "${good}^{tree}" -p "$tip" -m "Restore verified IndexNow state")
git push origin "$restored:refs/heads/indexnow-state"
```

分支缺失但可信的状态提交还在本地时，可将它重新推送到 `refs/heads/indexnow-state`。恢复已有分支后，如果基线落后于线上版本，优先用该次成功部署的 Actions 清单，或在干净的独立工作副本中按生产版本标记重建清单。使用 `recover` 记录已核对的线上清单，并保留原有队列和回执。只有分支确实缺失且无法找回任何记录时，才改用 `initialize` 重新建立基线。两个子命令都验证生产版本，均不会发送通知。丢失的待发事件和回执无法自动重建。

```sh
live=$(curl --fail --silent --show-error https://evanwindproof.top/indexnow-deployment.txt)
git fetch origin main
git switch --detach "$live"
python -m pip install -r requirements-blog.txt
mkdir -p .indexnow
python -X utf8 scripts/build_blog.py --indexnow-manifest .indexnow/recovery.json --commit "$live"
python scripts/indexnow_deploy.py recover .indexnow/recovery.json --commit "$live"
```
