---
name: super-coding
description: "多票据开发总控（router 版）：用 workflow-core router 把实施与独立审查派发到 Codex、OpenCode 或 Claude Code 会话，总控睡眠、由 worker 消息唤醒；修复复用原会话并增量复核，放行前最终完整审查。"
disable-model-invocation: true
---

# 开发总控（router 版）

你是本范围唯一的总控。范围、依赖、候选、证据、留痕、标签和放行都按原型 [ai-coding](../ai-coding/SKILL.md) 的规则执行，包括它的"按场景读取"、完成标准和全部 reference。本技能只替换派发方式：所有实施者和审查者都通过 `wfc`（workflow-core 的调度器）派发，你在它们工作时睡眠，由它们的消息唤醒。

用户手动调用并指定仓库和范围，授权范围与 ai-coding 相同，worker 的授权见 [router 派发](references/router.md)。正式合并、部署和真实验收另行授权，交给 `live-verify`。

## 你在哪个宿主

你的宿主就是你自己运行的这个。例如在 Codex 里，你执行的命令能读到有值的 `CODEX_THREAD_ID`。机器上其他总控进程和 relay 属于别的范围，不能拿来推断自己是谁。接管时，用 `wfc status --active` 输出里的 `waiters` 确认本状态目录有没有旧的 `wait` 或 relay。

- **Claude Code**：每次派发或回复之后，后台挂一个 `wfc wait`，然后结束当前回复。
- **Codex**：在总控会话里启动一次 `wfc relay --codex --detach`，消息会作为新的一轮送到你这里。总控会话用 `danger-full-access` 启动。
- **OpenCode**：总控会话要用固定端口启动（`opencode <目录> --port <端口>`）。接管后启动一次 `wfc relay --opencode-url … --opencode-session … --detach`，消息会作为新的一轮送到你这里。

需要 `wfc` 0.4.4 及以上版本。把 `wfc --version` 记进账本；之后版本与记录不一致或用户说已经升级时，先停掉旧的 `wait` 或 relay，再按宿主重新启动唯一的一个，并记下新的进程号和版本。各宿主的具体命令和恢复步骤，都在 [router 派发](references/router.md)。

每次被唤醒，处理完消息都要对账一次：有就绪的票、实施或审查有空位，就继续派发；只剩需要用户授权的事项（合并、真机验收、生产操作、回收）时，结束这一轮，并列出在等用户做什么。对账每次唤醒只做一次，没有新动作就结束，不要空转。做法见 [router 派发](references/router.md) 的"唤醒后对账"。

## 派给谁

接管时先读项目的角色表 `docs/agents/roles.md`，按任务的角色（实施、前端实施、审查等）取宿主、模型、推理强度、是否联网，以及备用宿主和模型。格式和示例见 [角色表模板](references/roles.md)。

- 表不存在时，先问用户，再按模板把用户的回答写进这张表，以后接管直接用。
- 用户在对话里临时另行指定的，以对话为准，并记入账本。

## 审查节奏

每张票按下面的顺序推进：

1. **首次完整审查**：实施者第一次报告 `done` 之后，派发一个独立审查者，审查从 PR 基线到候选的全部净变化。
2. **修复与增量复核**：审查有阻塞时，用 `continue` 把修复任务交给原来的实施者，让它在原会话里接着做。修复完成后，同样用 `continue` 让原来的审查者复核本轮补丁（上次获审候选 → 新 head）以及它影响到的调用和契约。原会话保留着上下文，所以修复和复核都只针对这次的补丁。补丁影响不清、做过 rebase 或 force-push 时，扩大为完整审查。
3. **最终完整审查**：放行之前，对 PR 基线到最终候选做一次完整审查。这一步可以继续用原审查者，也可以另派一个新的审查者。

三种审查的定义、独立性要求和记录格式，以 [ai-coding 的独立审查](../ai-coding/references/review.md) 为准。

## 完成标准

与 ai-coding 相同，另外加两条：

- 每个 dispatch 的最终状态都记入账本：`returned`、`stale` 或 `blocked`，并写明原因。已记为 `stale` 的会话再发来通知时，记一笔，并在回收清单里提议用 `wfc reclaim --dispatch <id>` 回收，用户同意后再加 `--yes` 执行，不要只记"已忽略"。
- 范围完成时，停掉 relay，列出 tmux 会话、worktree、已合并 PR 的实施分支（本地和远端）、router 状态目录和端口占用，作为回收清单交给用户；会话用 `wfc reclaim` 列出、用户同意后再加 `--yes` 关闭，做法见 [router 派发](references/router.md) 的“会话的生命周期”。回收是否执行由用户决定。在此之前，worker 的会话一律保留。
