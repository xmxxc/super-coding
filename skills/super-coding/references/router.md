# router 派发

用 `wfc` 命令把 worker 和审查者派到各自宿主的 tmux 会话里，然后你去睡眠，等它们发来消息再醒。账本、交接、审查、验证和放行的规则见 [ai-coding 的 references](../../ai-coding/references/)。

## 前提

- **wfc 命令**：先运行 `wfc --version` 确认它在 PATH 上，并把版本号记进 `state.md`。如果没有，请用户从 xmxxc/workflow-core 的 Releases 下载 `wfc`，放进 PATH（例如 `~/.local/bin`）。本技能与 `wfc` 分开发布：技能（含 `scripts/ctl.py`）来自 xmxxc/super-coding。系统要求：Linux 或 macOS（Windows 请用 WSL2），装有 python3 和 tmux。
- **状态目录**：每个范围用一个独立的 `WFC_STATE`，例如 `~/.local/state/workflow-core/<仓库>-<范围>`。对这个范围执行的每条 router 命令都要带上它，并把它写进 `state.md`。
- **同一个 tmux 服务**：每个 worker 在名为 `wfc-<dispatch id>` 的 tmux 会话里运行。总控、worker，以及用户执行 `tmux attach` 时，都要连到同一个 tmux 服务（同一个用户、同一个 `TMUX_TMPDIR`）。看门狗找不到会话，就会报 `exited`。
- **信任**：
  - Codex 的信任作用于 git 仓库根。接管时请用户在仓库根运行一次 `codex` 并选择信任，之后该仓库的所有 worktree 都不会再问。
  - Claude Code 会对每个新路径单独询问。如果用户已经信任过某个上级目录，router 派发时会替这个 worktree 写入信任；派发结果里的 `trustedBy` 就是那个上级目录。
  - 除此之外，信任由用户亲自确认。worker 卡在信任提示上时，看门狗会报 `stalled`。

## 派发

```sh
WFC_STATE=<状态目录> wfc dispatch --host <codex|opencode|claude> [--model <模型>] [--effort <强度>] \
  [--network] [--git] [--label "<项目> | <票> | <角色>"] \
  --task <prompts/ 中任务文件的绝对路径> --cwd <工作树> --report <reports/<票>-<角色>/r<N>.md>
```

- **回报目录按会话划分**：同一个 dispatch 的各轮回报都放在一个目录里，例如 `reports/2-impl/r1.md`、`reports/2-impl/r2.md`。router 只在派发时把这个目录开放给 worker 写入，所以 `continue` 也只接受这个目录里的路径。
- **会话标签**：回报目录按 `reports/<票>-<角色>/` 命名。router 在目录名的最后一个 `-` 处切出票和角色，加上项目名，组成默认标签"项目 | 票 | 角色"，用作 tmux 窗口名和 Claude Code 的会话名，`status` 里也会显示。需要时用 `--label` 覆盖。
- **推理强度**：用 `--effort <强度>` 指定，router 把它映射到各宿主自己的参数，强度的取值也按宿主自己的。
- **派给 OpenCode 时必须带 `--model`**，因为它的默认模型可能是受限的免费模型。
- **无人值守下的权限**：
  - Codex：`workspace-write` 沙箱，不请求审批，默认不能联网，带 `--network` 时可以联网；
  - OpenCode：工作目录外的路径一律放行，没有目录限制，可以联网；
  - Claude Code：`auto` 模式，可以联网。
- **联网**：`--network` 只对 Codex 生效，其他宿主本来就能联网，`dispatch` 会把它列在 `ignored` 里。Codex worker 默认断网，用之前先想清楚为什么需要联网，并把理由记进账本。`--effort` 和 `--network` 都随 dispatch 记录，`resume` 时沿用，不需要在工作树里写 `.codex/config.toml`。
- **本地提交（`--git`）**：Codex 的沙箱默认不能在链接 worktree 里提交。Codex 实施者需要自己做本地提交时才带 `--git`，例如有多次提交的票。开启后，worker 能改主仓库 `.git` 下的所有内容，不只是自己的分支。Codex worker 没有凭据，沙箱默认也不联网，所以推送、开 PR 和发评论由你代做；带 `--git` 也只是允许本地提交。不带 `--git` 时，Codex 实施者的提交也由你代做。Claude Code 和 OpenCode 本来就能写 `.git`，会忽略这个参数。
- 需要推送分支、建 PR 或发评论的任务，派给能联网的宿主；或者在你的授权范围内由你代发。
- worker 完工用 `done` 报告，需要决定时用 `ask` 提问。这两条命令的用法由 router 写进 worker 的说明。

### 断网的审查者（Codex）

派发之前，先准备两样东西，都放进它的回报目录：

- 在固定快照上执行项目的全量检查（安装、类型检查、lint、格式、测试），保存日志，并记录每条命令真实的退出码；
- 需求来源，也就是 Issue 和 spec 正文的本地副本。它的沙箱不能联网，读不到 GitHub，所以任务文件里要写明这些副本的路径。

审查结论写进报告，标为"待发布"。由你注明原作者后，转录到 PR 上。

断网审查者在报告里列出的"限制"（例如没法核实上游字段的业务含义），由你联网关闭：抓取真实上游数据，和权威来源交叉比对。发现缺陷时，以总控核验记录的形式发到 PR，再走修复和增量复核。修复任务里遇到故障分支，要事先定好原则（宁可不可用，不给错值），不要交给实施者自选。

### 总控例行检查

每一轮都要做的四件事，统一用本技能自带的脚本 `scripts/ctl.py` 执行（下面的 `<ctl>` 指 `python3 <本技能目录>/scripts/ctl.py`；本技能目录就是这份 SKILL.md 所在的目录），不要每次临时拼命令。每条命令都输出一份 JSON，任何一项检查不通过时退出码为 1。

```sh
# 1. 把审查快照切到新 head，跑全量检查，日志记录每条命令真实的退出码（用 pipefail）
<ctl> checks --cwd <审查快照> --head <sha> --log <reports/…/verification-rN.log> \
  --cmd "pnpm install --frozen-lockfile" --cmd "pnpm typecheck" --cmd "pnpm test" …
# 2. 回读候选：远端 head、tree、未 force-push、密钥没有提交、没有关闭关键词、留痕评论存在、端口已释放
<ctl> candidate --git <仓库克隆> --repo <owner/name> --branch <分支> --head <sha> \
  [--since <上次获审候选>] [--pr <N>] [--secret-file <.env> --secret-key PGPASSWORD] [--comment <id> …] [--port <端口>]
# 3. 把断网审查者的报告段落转录到 PR（带原作者说明，正文不改）
<ctl> transcribe --repo <owner/name> --pr <N> --report <r2.md> --start "## 独立复核记录" \
  [--end "## 最终完整审查状态"] --author 'Codex 审查者（router dispatch `d-…`）'
# 4. 切换生命周期标签并回读
<ctl> label --repo <owner/name> --issue <N> --from in-review --to changes-requested
```

`checks` 在快照有本地改动时会拒绝执行；检查命令执行完后，HEAD、tree 或工作树（含未跟踪文件）有变化的，判为失败，输出的 `changed` 写明哪里变了，现场和日志都保留，不会自动重置。`candidate` 不会打印密钥的值。`transcribe` 是幂等的：评论正文带隐藏标记 `<!-- ctl:transcribe <标记> -->`，标记由仓库、目标编号、来源报告路径和转录段落确定。发之前先在帖子里找这次转录自己发过的评论：作者是当前 gh 身份（`gh api user`），正文第一行就是标记行，整段正文与这次要发的完全相同（只统一行尾）。找到就直接返回它的 URL 并注明 `"existing": true`。发送报错（例如 GitHub 偶尔返回的 502 或 EOF）后按同样的条件再查一次，评论其实已经发出时同样按成功返回。只是引用了标记的评论（贴出的失败日志、别人复制的标记、改过的正文）不算已发布。所以失败后可以直接重跑，不会产生重复评论，也不会把没发出的转录误报为成功。

### 状态与证据

| 状态 | router 证据 |
| --- | --- |
| `pending-handoff` | `dispatch` 或 `continue` 已经成功返回 |
| `accepted` | 收到该 dispatch 的消息，或者 `tmux capture-pane -p -t wfc-<id>` 显示它已经开始处理本轮任务 |
| `returned` | 收到本轮的 `done`，并且按 [账本](../../ai-coding/references/ledger.md) 完成了回读核对，包括 `done` 消息里的 `head` 和 `dirty` |

**独立性**：实施和审查分别派发。dispatch id 不同，就是不同的宿主会话、各自的上下文。各个 worker 能读到同一个状态库，OpenCode 还能写任意路径，所以文件隔离不能作为独立性的证据。审查者的 `--cwd` 用固定快照或独立的工作树。

## 续派：修复与增量复核

```sh
WFC_STATE=<状态目录> wfc continue <dispatch> --task <下一轮任务文件> --report <同一回报目录中的 r<N+1>.md>
```

- **修复**：审查有阻塞时，用 `continue` 把修复任务交给原来的实施者。任务文件里写明审查记录的链接、要修的各项、当前 head，以及"在现有提交上追加，不要 force-push"。
- **增量复核**：修复报告 `returned` 之后，把审查快照移到新的 head，在快照上执行全量检查，然后用 `continue` 让原来的审查者复核"上次获审候选 → 新 head"。
- **何时可以续派**：只有在该 dispatch 已经对当前任务报告 `done` 之后才行。`continue` 发现上一轮还没有 `done`，会直接报错。
- **会话已经结束**（`exited`、误关或被 Ctrl-C）：用 `resume` 把 worker 重新拉回它原来的宿主会话，上下文都还在。会话结束时，`continue` 会直接报错，不会把任务打进去。
- **会话只读**：宿主切换了服务商或账号后，旧会话变成只读或不可用。`continue` 遇到这种会话会报错，带上画面原文，本轮记录回滚，任务没有送出。这时按消息处理表里 `session_read_only` 的办法，在同一宿主上新开会话。
- **原会话不再合适**（例如宿主配置已经改了，或者会话已经只读）：新派一个会话，在任务文件里写明真实的起点。
- **改派**：任务从一个宿主改派给另一个宿主时（例如 Codex 额度耗尽或认证失败，按角色表改给备用的 Claude），新任务文件必须写明：
  - 原任务文件；
  - 当前分支和 head；
  - 已有的 diff，未提交的部分是保留还是丢弃；
  - 已有报告所在的目录；
  - 旧 dispatch 记为 `stale` 的原因。
- **最后一轮增量复核**：预计能通过时，可以在同一个任务里写两步，先增量复核，无阻塞时紧接着做最终完整审查，两份记录分开写。有阻塞就只做第一步。

## 恢复会话：resume

```sh
WFC_STATE=<状态目录> wfc resume <dispatch> [--task <下一轮任务文件> --report <同一回报目录中的 r<N+1>.md>]
```

- 不带 `--task`：worker 回到原会话，接着做没做完的当前任务。
- 带 `--task`：worker 已经报告了 `done`，回到原会话做下一轮，效果等同于 `continue`。
- router 按 brief 里的 `(dispatch <id>)` 找到宿主会话：Codex 查 rollout 文件，OpenCode 查它的会话库；Claude Code 在派发时就指定了会话 id。找不到时报错，这时新派一个会话。
- tmux 会话还在时，`resume` 会拒绝执行；这种情况用 `continue`，或者 attach 上去看。
- `resume` 之后画面显示会话只读的，`resume` 会报错并提示新派：任务没有送出，会话只能看不能用。按消息处理表里 `session_read_only` 的办法处理。

## 会话的生命周期

- 每个 worker 和审查者的 tmux 会话，都保留到整个范围放行或关闭为止。worker 报告 `done` 之后也不要关掉它，后面的修复和复核还要用 `continue` 续派。
- 范围结束后，把 tmux 会话、worktree、已合并 PR 的实施分支（本地和远端）、router 状态目录和端口占用都列进回收清单，由用户决定什么时候回收。分支只列已合并、并且核实过当前 head 就是 PR 合并时的 head 的。用户没有同意之前，总控不要自己去关会话、删分支、停服务。
- 会话用 `wfc reclaim` 回收：
  1. 先运行 `WFC_STATE=<状态目录> wfc reclaim`，列出已经 `done`、tmux 会话还在的 dispatch（`dispatch`、`label`、`tmux`，`result: listed`）。它默认只列出，不会关闭。拿这份清单问用户。
  2. 用户同意后，运行 `WFC_STATE=<状态目录> wfc reclaim --yes`。用户只同意其中一部分时，用 `WFC_STATE=<状态目录> wfc reclaim --dispatch <id> --yes`（`--dispatch` 可重复）点名。
  3. 没有完成的会话（例如已记为 `stale` 的只读会话）不在默认清单里，只有用户逐个点名同意后，才用 `WFC_STATE=<状态目录> wfc reclaim --dispatch <id> --yes` 关闭。
  4. 关闭后回读每一项的 `result`：`reclaimed` 和 `gone`（会话本来就不在）算完成；`refused`（会话不属于本状态目录）、`failed`、`changed`（列出之后又被 `continue` 或 `resume` 派了新任务，没有关）写进账本，再问用户。有 `refused` 或 `failed` 时命令退出码为 1。然后用 `WFC_STATE=<状态目录> wfc status --active` 核对关掉的 dispatch 已不在 `reclaimable` 里。这几条命令的状态目录和预览时是同一个，也写进回收清单。

  reclaim 只关本状态目录里 router 开的 tmux 会话；router.db 的记录、账本、宿主的聊天记录都保留。关掉之后看门狗不再报 `exited`，之后仍然可以 `resume`。worktree、分支、端口和状态目录不归它管，仍然列进回收清单，由用户决定。
- 每张票分配不同的端口，并写进任务文件。router 的 brief 会要求 worker 在报告完工前停掉自己启动的服务。

## 等待与唤醒

**Claude Code 总控**：每次派发、续派或回复之后，在后台挂上

```sh
WFC_STATE=<状态目录> wfc wait --timeout <秒> [--stall-after <秒>]
```

然后结束当前回复。同一时刻只保留一个 `wait`。用户在窗口里发言也会唤醒你；回应完用户后，确认后台的 `wait` 还在。`wait` 以退出码 3 返回，表示超时：先用 `wfc status --active` 查看，再回读各任务的现场，有进展就重新挂 `wait`，没有进展的任务记为 `blocked`。

**Codex 总控**：总控会话用 `danger-full-access` 启动。接管后执行一次

```sh
WFC_STATE=<状态目录> wfc relay --codex --detach [--stall-after <秒>]
```

`--codex` 从 Codex 为命令设置的 `CODEX_THREAD_ID` 取本会话的线程，并在启动前核对对应的 rollout，所以必须在总控会话自己的命令里运行。它会输出进程号和日志路径，把它们写进 `state.md`。每次派发或回复之后结束当前回复，worker 的消息会作为一条以 `[router] Messages for the controller:` 开头的新消息送到你这里。全程不要运行 `wait`：`wait` 和 relay 同时运行，会抢同一批消息。relay 启动后，要确认它投递的第一条消息确实到了你这里。relay 报 `no rollout found` 并退出（启动时拒绝，或投递时 `codex queue` 找不到会话）时，说明线程不对：回头检查是不是在总控会话里运行的，不要换个 ID 硬试。如果派发后迟迟没有动静，先用 `wfc status --active` 和 `relay.log` 看消息是否已经标为送达。

**OpenCode 总控**：总控会话必须用固定端口启动，例如 `opencode <工作目录> --port 4096`（默认端口是随机的，relay 找不到）。接管后执行一次

```sh
WFC_STATE=<状态目录> wfc relay --opencode-url http://127.0.0.1:<端口> --opencode-session <你的会话 id> --detach [--stall-after <秒>]
```

会话 id 的确认：目录和更新时间只能用来缩小范围，不能证明哪个会话是你，因为同一目录下可能还有别的会话。做法如下：
1. 启动总控时，在第一条提示里放一个唯一标记，例如 `wfc-controller-<范围>-<随机串>`，并把这个标记写进 `state.md`。
2. 用 `curl -s http://127.0.0.1:<端口>/session` 列出 `directory` 等于本工作目录的候选会话，再逐个读取 `GET /session/<id>/message`，找出用户消息中含有这个标记的会话。必须恰好命中一个；命中零个或多个时，不要启动 relay，先把身份问题弄清楚。
3. relay 启动后，核对它投递的第一条消息确实进入了当前会话（这一点和 Codex 一样），然后把确认过的 `ses_…` 写进 `state.md`。和 Codex 一样，把进程号和日志路径写进 `state.md`，全程不要运行 `wait`。每次派发或回复之后结束当前回复，worker 的消息会以 `[router] Messages for the controller:` 开头的新一轮送达。连接被拒（OpenCode 没在监听）时，消息留着下次再送；OpenCode 返回错误或超时时，消息不会重发，`relay.log` 会记成 uncertain，这时去会话里核对是否收到。

**查看状态**：`wait` 超时，或者怀疑丢了消息时，先运行

```sh
WFC_STATE=<状态目录> wfc status --active
```

它只读不取消息，只列出还没完成的 dispatch（`working`、`asking`、`exited`；没完成就被点名回收的显示为 `reclaimed`，并附 `reclaimed` 回收时间）及其最后一条消息、画面静止的秒数，照常列出还没送达的消息（`undelivered`）和正在运行的 `wait` 或 relay（`waiters`）；已经 `done`、tmux 会话还在的 dispatch 列在 `reclaimable` 里。要看某个 dispatch 的全部消息，改用 `wfc status --dispatch <id>`（不能和 `--active` 一起用）。不带参数的 `wfc status` 列出全部 dispatch。不要直接查 `router.db`。

## 消息处理

| 消息 | 处理 |
| --- | --- |
| `done` | 完成 `returned` 的回读核对。拿消息里的 `head` 和报告里写的 head 比对，再看 `dirty` 是否符合预期（例如由你代提交时，工作树应当有未提交的改动）；对不上就按不一致处理，记进账本。两者为 `null` 表示 router 没读到 git 状态，这时到工作树里自己回读。缺留痕的，按账本补发转录，或者交回 worker 补发 |
| `question`（由 `ask` 发出） | 在已固定的范围、验收条件和授权内能回答的，直接执行 `wfc reply <消息 id> "<答案>"`。需要用户决定的，把原问题和选项原样转给用户。问题和答案都记入账本 |
| `stalled` | 先读附带的画面。<br>停在信任或权限提示上：请用户执行 `tmux attach -t wfc-<id>` 处理，该任务记为 `blocked`。同时告诉用户怎么离开：按 Ctrl-b 再按 d；如果终端截获了 Ctrl-b（例如 VS Code 的终端），就在另一个终端执行 `tmux detach-client -s wfc-<id>`，或者让总控代为执行。千万不要按 Ctrl-C，那会直接退出 worker。<br>停下了，但没报告也没提问（例如模型调用遇到网络错误）：回读现场，然后用 `WFC_STATE=<状态目录> wfc nudge <dispatch> --text "<提醒>"` 打一行提醒，并把这次介入记入账本。提醒之后再次报 `stalled` 的，记为 `blocked` |
| `blocked` | worker 的本轮因宿主报错而结束。消息附带宿主的错误类型 `kind` 和原文 `message`。先读原文，再按类型处理：<br>额度耗尽（`usage_limit_exceeded`、`rate_limit`）或认证失败（401、`token expired` 之类）：角色表里该角色配了备用、备用宿主不是当前失败的这个、而且这一轮还没有因为账号问题试过它时，按上面的改派换到备用宿主和模型，旧 dispatch 记为 `stale`，并把已经试过的宿主记进账本；没配备用的，或者备用也已失败的，该任务记为 `blocked`，请用户修复认证或者处理额度，问题解决前不要再为同一个宿主新开会话：额度耗尽的，由用户决定是等到原文里的恢复时间再 `nudge` 一次，还是另换宿主；认证失败的，请用户重新登录 worker 用的命令行，登录后再 `nudge` 一次。不要对同一个宿主反复 `nudge`，也不要新开会话硬试。总控和 worker 可能用不同的认证（例如总控是 VS Code 扩展，worker 是经本地网关的命令行），总控能正常对话，不代表 worker 能用。<br>会话只读（`session_read_only`）：宿主切换了服务商或账号，旧会话变成只读或不可用，`resume` 也只能看到只读界面；`message` 是画面原文，例如 Codex 的 `… so this chat is read-only.`。把旧 dispatch 记为 `stale`，保留现场，然后按角色表在**同一宿主上新开会话**（新会话用的是新服务商，可以正常工作），用下一轮编号，按上面改派的要求在新任务文件里写明真实起点。`continue`、`nudge`、`reply` 报会话只读时（本次记录已回滚，没有送出），也这样处理；`reply` 没送出的答案写进新任务文件。<br>认证失败和会话只读的区别：认证失败是账号本身不能用，同一宿主的新会话一样会失败，所以不要新开会话硬试，按角色表改派或者请用户处理；会话只读是旧会话不能用，账号没有问题，同一宿主的新会话可以用。按 `kind` 和原文区分：`session_read_only`、原文说会话只读或不可用的，是会话只读；401、`token expired` 之类的，是认证失败。<br>短暂故障（`server_overloaded`、5xx）：过一会儿再 `nudge`。<br>内容策略（`cyber_policy`）：调整任务措辞后再发给它。<br>每次处理都记入账本 |
| `exited` | 先检查 worker 退出前是否已经提交或推送，再用 `resume <dispatch>` 让它回到原会话，接着做当前任务，并记入账本。`resume` 报会话只读时，按上面 `blocked` 行里会话只读的办法处理。`resume` 找不到会话或者再次 `exited` 时，按账本的失效规则处理：记为 `stale`，保留现场，用下一轮编号新派，在新任务文件里写明真实起点，以及旧现场是续用还是放弃 |

每条消息都带 dispatch id，对照账本找到它所属的票和任务。记为 `blocked` 的任务，在 `state.md` 写清楚在等谁、要做什么、结果交回哪里。

## worker 的授权

用户以本技能调用并指定仓库和范围，即授权 worker 提交自有任务分支、推送、创建或更新 PR，以及在 Issue 和 PR 上发必要的评论。生产操作、正式合并和其他仓库的操作，仍按已有授权处理。

## 恢复

`wait` 和 relay 都是先把消息标为"已送达"，再交给你。所以换会话、上下文压缩或意外中断之后：

1. 按[账本](../../ai-coding/references/ledger.md)回读 `state.md`，并读角色表 `docs/agents/roles.md`。
2. 找回上次已经取走的消息：
   - Claude Code：读上一次后台 `wait` 的输出；
   - Codex：用 `wfc status --active` 的 `waiters` 和记录的进程号确认旧 relay 的状态，仍在运行但指向旧会话的，停掉它。
   - OpenCode：用 `wfc status --active` 的 `waiters` 和记录的进程号找到本状态目录里的旧 relay，用 `ps -o args= -p <进程号>` 核对它的 `--opencode-url` 和 `--opencode-session`；指向旧端口或旧会话的，停掉它。
3. 把账本与 `wfc status --active` 的输出、`relay.log`、`tmux ls` 列出的 `wfc-*` 会话逐一对照。账本里还在进行、却出现在 `reclaimable` 里的 dispatch，说明 worker 已报告 `done`：用 `wfc status --dispatch <id>` 读它的全部消息，看那条 `done` 的 `delivered` 字段，结合账本判断要不要补做处理。已经送达但账本里还没处理的消息，按上面的消息处理表补做。
4. 恢复唤醒：
   - Claude Code：重新挂 `wait`；
   - Codex：在当前会话里用 `wfc relay --codex --detach` 重新启动唯一的一个 relay；
   - OpenCode：按上面 OpenCode 总控的唯一标记流程，确认当前的 URL 和会话 ID，再运行 `wfc relay --opencode-url … --opencode-session … --detach`。然后用 `wfc status --active` 的 `waiters` 确认只有这一个 relay，并核对它投递的第一条消息确实进入了当前会话。全程不要运行 `wait`。
