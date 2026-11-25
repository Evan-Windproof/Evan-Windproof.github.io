# HoofTTY project page

The authoritative page is `Evan-Windproof.github.io:main/projects/hooftty/`. The existing GitHub Pages workflow publishes it at [evanwindproof.top/projects/hooftty/](https://evanwindproof.top/projects/hooftty/). Preview it from the site root with `python -m http.server 8000` and open `/projects/hooftty/`. The desktop and Aelthoren Projects views use the same listing in `js/projects.js`.

## Release updates

Verify the latest release title, date, notes and case-sensitive ISO filename on [GitHub Releases](https://github.com/Evan-Windproof/HoofTTY/releases). Update the terminal preview, status version and download heading together. The browser test checks that those labels agree. Update the pinned download and source links, command reference and changelog based on the release. The primary download action follows GitHub’s latest-release redirect.

`evan.png` is a 48×54 lossless export of the original [Evan sprite](https://github.com/Evan-Windproof/HoofTTY/blob/beta0.4.0/include/Pony/evan.h) using the tagged [framebuffer palette](https://github.com/Evan-Windproof/HoofTTY/blob/beta0.4.0/kernel/drivers/framebuffer.c) and transparent index 255. `social-card.png` uses the same sprite at integer scale. The corresponding source is under [GPL-3.0-or-later](https://github.com/Evan-Windproof/HoofTTY/blob/beta0.4.0/LICENSE). The locally hosted Silkscreen font is distributed under the [SIL Open Font License](../projects/hooftty/silkscreen-OFL.txt).

## Mirror synchronization

[HoofTTY-Website](https://github.com/Evan-Windproof/HoofTTY-Website) mirrors the page directory and contains its own README and license. Keep GitHub Pages disabled in the mirror’s **Settings → Pages**. The main website’s Pages workflow, domain and canonical URL remain authoritative.

The **Sync HoofTTY website mirror** workflow runs on relevant pushes to the main website’s `main` branch. It can also be run manually on `main`. It compares the mirror’s committed page tree against the last authoritative commit recorded in the mirror’s `.hooftty-source` file. A mismatch stops the job for review. A match permits a one-way update of the page directory and provenance file. The push is a normal fast-forward push, so concurrent mirror edits cause a rejection if the branch advanced after checkout.

### Enable the workflow

1. Create a [fine-grained GitHub personal access token](https://github.com/settings/personal-access-tokens/new). Select **Evan-Windproof** as resource owner, limit repository access to **HoofTTY-Website**, and grant **Contents: Read and write**. GitHub also includes **Metadata: Read**. Use a finite expiration.
2. In **Evan-Windproof.github.io → Settings → Secrets and variables → Actions**, create the repository secret `HOOFTTY_MIRROR_TOKEN` with the token value. The default workflow token is scoped to the main website repository. With the secret unset, the synchronization steps are skipped and the run reports a warning.
3. Run **Actions → Sync HoofTTY website mirror → Run workflow** on `main`. Check that the job succeeds and that the mirror’s `.hooftty-source` identifies the authoritative commit for its page tree. If the mirror requires pull requests, use the manual procedure below and submit the sync commit through that review process. Keep the branch protection rules in place.

### Manual sync and divergence recovery

Use separate, clean checkouts of the source and mirror with full source history. Check out the desired authoritative `main` commit and start from the current mirror `main` tip. From the main site checkout, run:

```sh
bash scripts/sync_hooftty.sh . /path/to/HoofTTY-Website
git -C /path/to/HoofTTY-Website diff --cached --stat
```

If changes were staged, review and commit them, then push a fast-forward update or submit a pull request according to the mirror’s branch rules. If the script detects drift, inspect the mirror changes and incorporate any intended page changes in the authoritative repository first. Restore the mirror page tree to the revision recorded in `.hooftty-source` with a reviewed commit, then rerun synchronization. Keep the recorded commit and page tree paired.
