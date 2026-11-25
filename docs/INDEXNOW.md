# IndexNow 手动提交指南

IndexNow 用于向参与该协议的搜索引擎通知页面变更。HTTP 200 表示已收到通知，HTTP 202 表示已收到通知、密钥仍待校验。两种状态都无法保证页面会被抓取或收录。[IndexNow 官方文档](https://www.indexnow.org/documentation)

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

测试使用模拟 HTTP 响应。GitHub Pages 构建和部署流程只发布验证文件，提交命令由站点维护者手动运行。

## 第二阶段的 URL 变更要求

第二阶段须在 GitHub Pages 部署成功后，根据 Git 变更和发布元数据判断哪些 URL 需要通知。删除已发布页面时，应提交被删除的规范 URL。更改已发布文章的 slug 时，应提交旧的规范 URL，并提交已上线的新规范 URL。

新增或更新的 URL 仍须通过生产站点地图校验。删除页面的 URL 和 slug 变更前的旧 URL 可能已从生产站点地图移除。第二阶段应依据变更前的发布记录确认这些 URL 曾公开发布，并继续校验其 HTTPS 格式和生产域名，使当前的站点地图成员校验不会拦截合法的删除通知。
