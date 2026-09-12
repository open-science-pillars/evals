"""How one trial is launched on each runtime.

The prompt, the tool allowance and the turn bound come from the manifest
and are the same on every runtime; what differs is the command that
runs them headlessly. Claude Code is the runtime the runner has driven
since the seed grades. The Codex command is written from the Codex CLI's
documented headless form (`codex exec`, prompt on stdin) and is marked
unexercised until the reference capability's Codex leg runs it; a
runtime with no headless command here is refused rather than guessed.
Cowork has no headless interface, so a Cowork result is produced by the
qualification checklist and carries the same record.
"""


def command_for(runtime: str, prompt: str, allowed_tools: str, max_turns: int, model: str,
                extra_args=()):
    """(argv, stdin_text, notes) for one headless trial on runtime."""
    extra = list(extra_args)
    if runtime == "claude-code":
        return (["claude", "-p", prompt, "--model", model, "--allowedTools", allowed_tools,
                 "--max-turns", str(max_turns), *extra], None, [])
    if runtime == "openai-codex":
        # Unexercised: the reference capability's Codex leg confirms these flags.
        notes = ["allowed_tools and max_turns are Claude Code allowances with no Codex "
                 "equivalent; the sandbox flag is the bound applied instead"]
        return (["codex", "exec", "--model", model, "--sandbox", "read-only",
                 "--skip-git-repo-check", *extra, "-"], prompt, notes)
    raise ValueError(f"no headless driver for runtime {runtime!r}; a result on it is recorded "
                     "from the qualification checklist with the same record fields")
