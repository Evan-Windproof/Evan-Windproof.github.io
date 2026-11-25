---
title: 'HoofTTY-一个My Little Pony主题的纯文本操作系统'
description: '基于Kernseed OS开发'
date: 2026-11-25
updated: 2026-11-25
tags: [技术, 开源, 项目, 操作系统]
category: 项目介绍
slug: hooftty
draft: false
language: zh-CN
---

## 介绍

名称：HoofTTY

类型：操作系统

CPU架构：x86_64

是否为Linux发行版：否

性质：受《My Little Pony》（小马宝莉）启发的 x86-64 纯文本操作系统。

开源协议：GPL-3.0

是否使用AI开发：Kernseed是，但HoofTTY是半AI半人工。

目前状态：已更新至Beta 0.4.0，并且会持续更新。

HoofTTY在测试中成功在QEMU和VMware虚拟机中运行。相较于Kernseed OS，已支持中文和小写英文字母，并且支持输入光标。

## 截图

![HoofTTY](https://ik.imagekit.io/lp7vr9041i/blog/OS/hoofTTY1.webp)

## 未来

### 后续方向（尚未承诺实现）

- 改善像素头像的布局、分辨率适配与绘图测试。
- 让颜色继承行为可控，逐步研究背景颜色与 ANSI 支持。
- 丰富原创小马资源和互动指令；`pony` 等需实际实现后再列入功能。
- 在终端基础完善之后，再考虑 Unicode 与简繁中文显示。

# 杂谈

HoofTTY在我这里更多的也只是学习中的一个兴趣项目，终究有一天会完结或者超低频

维护。但是我确实规划了另一个My Little Pony主题的操作系统——[Liberpony](https://github.com/Evan-Windproof/Liberpony-OS)。

## 许可证与同人声明

本仓库自有代码（包括继承的 Kernseed 代码）采用 **GNU GPL 第 3 版或由您选择的任何后续版本（`GPL-3.0-or-later`）**。允许商业与非商业使用、修改和再分发，但必须遵守 GPL；正式 GPLv3 全文见 [LICENSE](LICENSE)。HoofTTY 是基于 [Kernseed OS](https://github.com/Evan-Windproof/Kernseed_OS) 的派生项目。第三方组件保留原许可证，详情见 [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)。本次变更不会撤销历史 Release 已授予的许可，历史版本仍应按其原有声明和条款使用；旧 PolyForm 文本保留为[历史记录](docs/licenses/PolyForm-Noncommercial-1.0.0.md)。仓库许可不自动授权第三方角色、美术、商标和媒体素材。

《My Little Pony》及相关知识产权归各自权利人所有。HoofTTY 是非官方同人项

目，未受到官方授权或赞助。

## 链接

GitHub：<https://github.com/Evan-Windproof/HoofTTY> （最新）

GitLab：<https://gitlab.com/Evan-Windproof/HoofTTY>

Codeberq：<https://codeberg.org/Evan_Windproof/HoofTTY>
