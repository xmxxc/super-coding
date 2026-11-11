# Pinned and maintained copies

These two skills started as byte-for-byte copies of the user's skills repository (`/path/to/skills-repo`, commit `9d38b84`). This repository keeps them so that `super-coding` and its shared rules can be used on their own: `super-coding` follows the ledger, review, release and label rules of `ai-coding`, and hands formal merge and live acceptance to `live-verify`.

- `ai-coding` is a pinned copy. Do not edit it here. Workflow changes go into `super-coding` (or `router.py`). Changes to the prototype go to the skills repository first, and then get re-copied here with a new pin.
- `live-verify` is maintained here. It was forked from the skills repository at `9d38b84` and is no longer a pinned copy: edit it in this repository. The skills repository's copy is not updated from here.
- `install.py` always installs `super-coding`, and installs `ai-coding`, `live-verify` and `setup-matt-pocock-skills` only where the user has none of their own, so a user's own copies are never replaced and two copies never compete for the same skill name.
- Other skills the workers use (`code-review`, `implement`, `tdd` and so on) are not bundled; they are recommended and installed separately.

SHA-256 of `ai-coding` at pin time:

```
5b5e5d8c950a9c9bc1ebd89fcdcc05914ed08d6bf8cb48349f6ae325492c2d9b  ai-coding/agents/openai.yaml
07e73619495e7d1b3f550f2610c150db2ff755624f02841760450b3af607c417  ai-coding/dispatch/codex.md
723b4ee9b5b1991721f119026323f25dfd80f4b1af30a544359524dbd1913cb9  ai-coding/dispatch/host.md
80b3ea72fe20d646912e4450a001a2972b1f34d210416337784a8c3dd41d0126  ai-coding/dispatch/manual.md
de11888127dd9f60f915201d16a74ec53fe6c0c4ed27ff235a411f5fe9a5ac4f  ai-coding/references/handoff.md
5f3d511897433257242a3e1e8936b4397cb4db74eaef4d5385c7c3f1b1fc462a  ai-coding/references/labels.md
70fcb891313447018296741d685ddc732856ca819725cde205e71cbcff170399  ai-coding/references/ledger.md
edd1d291710d75168273d523f2d13d3a5f46933b5b74ba6457420cd25346e197  ai-coding/references/release.md
ed2851c8c371d0d22015c67fe14d9cab4e1b96a967382b0fc5b68633b86299ac  ai-coding/references/review.md
59b81ec716ff15b8142c9211c948edc8d3bc5995b28d9641b891b8280ad11c40  ai-coding/references/verification.md
26cf6187d0c44f5c87b8611d04f1f0963a18c8a20db5471c97dcb155918f9693  ai-coding/SKILL.md
```

## setup-matt-pocock-skills (third-party, pinned)

`skills/setup-matt-pocock-skills/` is a pinned, unmodified copy of `skills/engineering/setup-matt-pocock-skills/` from [mattpocock/skills](https://github.com/mattpocock/skills) at commit `4ae2317ddb22b046e26455e4f9c9b3aaaf62212d`. `ai-coding` and `live-verify` call it when a project is not yet initialized.

- Do not edit it here. To update it, copy the directory again from upstream at a new commit, replace the pin and the checksums below, and keep the upstream `LICENSE` beside it.
- `skills/setup-matt-pocock-skills/LICENSE` is the upstream repository's `LICENSE` at the same commit, unmodified. It sits in the skill's directory so that the copyright notice is installed together with the files.

SHA-256 of the upstream files at pin time:

```
9527de0110541c45712319025155aeab8dc7d77c6ed6e5e83271bab1851ab939  setup-matt-pocock-skills/agents/openai.yaml
593a7042218689f1d24df89df14eaf0a20e19e0d0a7d479a01947ac78f0784b9  setup-matt-pocock-skills/domain.md
6fdb3e9b00b7b0b115ecac3b1c00e3790f637f190abf598815368722c0a94692  setup-matt-pocock-skills/issue-tracker-github.md
947602d33a80f98f939fb990995b8f95a3459b114b919c4221d08bd75d7cffe0  setup-matt-pocock-skills/issue-tracker-gitlab.md
7dcda20a2eb4bdc89b95d1143423c0691309921cadae3132e6424f371030506e  setup-matt-pocock-skills/issue-tracker-local.md
b01e05bfe8c323171275c6ceec78b12f1bd4c62dfd26c2cfe8be806d3883f1ed  setup-matt-pocock-skills/SKILL.md
ae512af838c78b8750471c42cd2b20fa32319553e61d84c9a23d171b40ce14aa  setup-matt-pocock-skills/triage-labels.md
0e7ac423bf2c6e223b7c5b156f8cf72da49d748e56a1641402c31f22ad07dbb5  setup-matt-pocock-skills/LICENSE
```

Upstream copyright and license notice:

```
MIT License

Copyright (c) 2026 Matt Pocock

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
