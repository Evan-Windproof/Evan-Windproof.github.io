# HoofTTY project page

The static page lives at `projects/hooftty/index.html`. Preview it from the site root with `python -m http.server 8000` and open `/projects/hooftty/`. The desktop and Aelthoren Projects views use the same listing in `js/projects.js`.

When publishing another version, verify the release title, date, notes and case-sensitive ISO filename on [GitHub Releases](https://github.com/Evan-Windproof/HoofTTY/releases). Update the pinned download and source links, status, command reference and changelog in the page HTML. The primary download action follows GitHub’s latest-release redirect. The terminal preview intentionally shows the version string printed by the Beta 0.4.0 boot code.

`evan.png` is a 48×54 lossless export of the original [Evan sprite](https://github.com/Evan-Windproof/HoofTTY/blob/beta0.4.0/include/Pony/evan.h) using the tagged [framebuffer palette](https://github.com/Evan-Windproof/HoofTTY/blob/beta0.4.0/kernel/drivers/framebuffer.c) and transparent index 255. The corresponding source is under [GPL-3.0-or-later](https://github.com/Evan-Windproof/HoofTTY/blob/beta0.4.0/LICENSE). The locally hosted Silkscreen font is distributed under the [SIL Open Font License](../projects/hooftty/silkscreen-OFL.txt).
