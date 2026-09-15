#!/usr/bin/env python3
"""运行固定配置的 Qoder 主会话；只测行为，不启动子代理或真实检索。"""
import argparse
import hashlib
import json
import os
import signal
import subprocess
import time
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
TOOLS = {"Read", "Glob", "Grep", "Skill"}
SKILLS = {"bioinfo-db-search", "deep-search", "external-knowledge-search"}
MODEL = "Qwen3.8-Flash"


def parse_trace(raw, returncode):
    events = []
    for line in raw.splitlines():
        try:
            value = json.loads(line)
            if isinstance(value, dict):
                events.append(value)
        except json.JSONDecodeError:
            pass
    init = next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), {})
    finals = [e for e in events if e.get("type") == "result"]
    final = finals[-1] if finals else {}
    calls = []
    for event in events:
        content = event.get("message", {}).get("content", [])
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    calls.append({"name": block.get("name"), "input": block.get("input", {})})
    extra_tools = sorted(set(init.get("tools", [])) - TOOLS)
    extra_skills = sorted(set(init.get("skills", [])) - SKILLS)
    missing_skills = sorted(SKILLS - set(init.get("skills", [])))
    return {
        "completed": returncode == 0 and bool(finals) and not final.get("is_error", False),
        "answer": final.get("result", ""),
        "returncode": returncode,
        "tools": init.get("tools", []),
        "skills": init.get("skills", []),
        "model": init.get("model"),
        "cli_version": init.get("qodercli_version"),
        "unexpected_tools": extra_tools,
        "unexpected_skills": extra_skills,
        "environment_ok": bool(init) and not extra_tools and not extra_skills and not missing_skills,
        "tool_calls": calls,
        "credits": final.get("total_credits"),
        "usage": final.get("usage", {}),
        "error": final.get("is_error", False),
        "errors": final.get("errors", []),
        "permission_denials": final.get("permission_denials", []),
    }


def fingerprints():
    root = BASE / "runtime"
    files = [root / "AGENTS.md", root / "Expert-source.md"]
    files += [p for p in (root / ".qoder").rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}


def run_case(case, directory, timeout):
    prompt = case["question"]
    if case.get("fixture") is not None:
        prompt += "\n\n以下为明确标记的模拟检索返回；请依据你的专家规范处理，不进行真实联网。\n"
        prompt += json.dumps(case["fixture"], ensure_ascii=False, indent=2)
    (directory / "input.txt").write_text(prompt)
    cmd = [
        "qodercli", "--cwd", str(BASE / "runtime"),
        "--setting-sources", "project,local", "--agent", "helix-under-test",
        "--model", MODEL, "--tools", "Read", "Glob", "Grep", "Skill",
        "--allowed-tools", "Read,Glob,Grep,Skill",
        "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
        "--no-session-persistence", "--max-model-request-retries", "0",
        "--output-format", "stream-json", "-p", prompt,
    ]
    env = os.environ.copy()
    env["QODER_MEMORY"] = "0"
    started = time.monotonic()
    timed_out = False
    with (directory / "trace.jsonl").open("w") as out, (directory / "stderr.txt").open("w") as err:
        proc = subprocess.Popen(cmd, stdout=out, stderr=err, env=env, start_new_session=True)
        try:
            returncode = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
            returncode = 124
    result = parse_trace((directory / "trace.jsonl").read_text(), returncode)
    result.update(case_id=case["id"], title=case["title"],
                  duration_seconds=round(time.monotonic() - started, 2),
                  timed_out=timed_out, test_type="offline_behavior_with_synthetic_results")
    (directory / "answer.md").write_text(result["answer"] + "\n")
    (directory / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", help="仅运行给定用例 ID；默认全部")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    if args.repeat < 1 or args.timeout < 1:
        parser.error("repeat 和 timeout 必须大于 0")
    cases = json.loads((BASE / "cases.json").read_text())
    if args.case:
        cases = [case for case in cases if case["id"] == args.case]
        if not cases:
            parser.error("没有该用例")
    run = BASE / "runs" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    run.mkdir(parents=True)
    before = fingerprints()
    (run / "manifest.json").write_text(json.dumps({
        "model": MODEL, "cli_version": subprocess.check_output(["qodercli", "--version"], text=True).strip(),
        "hashes": before, "scope": "离线行为测试；Qoder模型推理联网，检索工具不联网",
        "account": "使用现有Qoder登录；未复制凭证", "new_session_per_case": True
    }, ensure_ascii=False, indent=2) + "\n")
    results = []
    print("RUN_DIR=" + str(run), flush=True)
    for repetition in range(1, args.repeat + 1):
        for case in cases:
            directory = run / (case["id"] + "-r" + str(repetition))
            directory.mkdir()
            result = run_case(case, directory, args.timeout)
            results.append(result)
            print(json.dumps({k: result[k] for k in ["case_id", "completed", "environment_ok", "duration_seconds", "credits"]}, ensure_ascii=False), flush=True)
            (run / "summary.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
            if not result["environment_ok"] or not result["completed"]:
                print("已停止：运行环境或模型响应未通过，未将其计为专家测试通过。", flush=True)
                return 1
    unchanged = before == fingerprints()
    (run / "integrity.json").write_text(json.dumps({"runtime_files_unchanged": unchanged}) + "\n")
    return 0 if unchanged else 1


if __name__ == "__main__":
    raise SystemExit(main())
