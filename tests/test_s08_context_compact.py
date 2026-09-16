import runpy
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LESSON = ROOT / "s08_context_compact" / "code.py"


def load_lesson(monkeypatch, workdir: Path):
    fake_anthropic = types.ModuleType("anthropic")
    fake_dotenv = types.ModuleType("dotenv")

    class FakeAnthropic:
        def __init__(self, *args, **kwargs):
            self.messages = types.SimpleNamespace(create=None)

    fake_anthropic.Anthropic = FakeAnthropic
    fake_dotenv.load_dotenv = lambda override=True: None
    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)
    monkeypatch.setitem(sys.modules, "dotenv", fake_dotenv)
    monkeypatch.setenv("MODEL_ID", "test-model")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.chdir(workdir)
    return runpy.run_path(str(LESSON))


def test_glob_double_star_matches_files_at_any_depth(tmp_path, monkeypatch):
    (tmp_path / "root.py").write_text("")
    (tmp_path / "one").mkdir()
    (tmp_path / "one" / "one.py").write_text("")
    (tmp_path / "one" / "two").mkdir()
    (tmp_path / "one" / "two" / "deep.py").write_text("")
    lesson = load_lesson(monkeypatch, tmp_path)

    matches = set(lesson["run_glob"]("**/*.py").splitlines())

    assert matches == {"root.py", "one/one.py", "one/two/deep.py"}


def test_prepare_preserves_tool_results_while_context_is_within_limit(
        tmp_path, monkeypatch):
    lesson = load_lesson(monkeypatch, tmp_path)
    messages = []
    expected_results = []
    for index in range(5):
        tool_id = f"tool-{index}"
        result = f"result-{index}:" + "x" * 200
        expected_results.append(result)
        messages.extend([
            {"role": "assistant", "content": [
                {"type": "tool_use", "id": tool_id, "name": "bash", "input": {}}
            ]},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": tool_id, "content": result}
            ]},
        ])
    messages.append({"role": "assistant", "content": [
        {"type": "text", "text": "continue"}
    ]})

    prepared = lesson["COMPACTOR"].prepare(messages, "inspect the repository")
    actual_results = [
        block["content"]
        for message in prepared
        if message["role"] == "user"
        for block in message["content"]
        if block["type"] == "tool_result"
    ]

    assert actual_results == expected_results


def test_prepare_micro_compacts_tool_results_after_context_exceeds_limit(
        tmp_path, monkeypatch):
    lesson = load_lesson(monkeypatch, tmp_path)
    messages = []
    for index in range(5):
        tool_id = f"tool-{index}"
        messages.extend([
            {"role": "assistant", "content": [
                {"type": "tool_use", "id": tool_id, "name": "bash", "input": {}}
            ]},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": tool_id,
                 "content": f"result-{index}:" + "x" * 1000}
            ]},
        ])
    messages.append({"role": "assistant", "content": [
        {"type": "text", "text": "continue"}
    ]})
    compactor = lesson["COMPACTOR"]
    compactor.CONTEXT_CHAR_LIMIT = 4500

    prepared = compactor.prepare(messages, "inspect the repository")
    actual_results = [
        block["content"]
        for message in prepared
        if message["role"] == "user"
        for block in message["content"]
        if block["type"] == "tool_result"
    ]

    assert all(result.startswith("[Earlier tool result saved at ")
               for result in actual_results[:2])
    for index, result in enumerate(actual_results[:2]):
        saved_path = Path(result.removeprefix(
            "[Earlier tool result saved at ").removesuffix("]"))
        assert saved_path.read_text() == f"result-{index}:" + "x" * 1000
    assert all(result.startswith(f"result-{index}:")
               for index, result in enumerate(actual_results[2:], start=2))


def test_prepare_persists_oversized_unseen_result_before_full_compact(
        tmp_path, monkeypatch):
    lesson = load_lesson(monkeypatch, tmp_path)
    output = "latest-result:" + "x" * 60000
    messages = [
        {"role": "assistant", "content": [
            {"type": "tool_use", "id": "latest", "name": "read_file", "input": {}}
        ]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "latest", "content": output}
        ]},
    ]
    compactor = lesson["COMPACTOR"]
    compactor.summarize_history = lambda _messages: (_ for _ in ()).throw(
        AssertionError("full compaction should not run"))

    prepared = compactor.prepare(messages, "inspect the result")
    content = prepared[-1]["content"][0]["content"]

    assert len(prepared) == 2
    assert content.startswith("<persisted-output>")
    saved_line = next(line for line in content.splitlines()
                      if line.startswith("Full output: "))
    assert Path(saved_line.removeprefix("Full output: ")).read_text() == output


def test_default_limit_keeps_a_debug_sized_history_uncompressed(
        tmp_path, monkeypatch):
    """防止临时教学阈值让约 6 KB 的普通历史自动进入微压缩。"""
    lesson = load_lesson(monkeypatch, tmp_path)
    messages = []
    expected_results = []
    for index in range(5):
        tool_id = f"tool-{index}"
        result = f"result-{index}:" + "x" * 1000
        expected_results.append(result)
        messages.extend([
            {"role": "assistant", "content": [
                {"type": "tool_use", "id": tool_id,
                 "name": "bash", "input": {}}
            ]},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": tool_id,
                 "content": result}
            ]},
        ])
    messages.append({"role": "assistant", "content": [
        {"type": "text", "text": "continue"}
    ]})

    prepared = lesson["COMPACTOR"].prepare(messages, "继续调试")
    actual_results = [
        block["content"]
        for message in prepared
        if message["role"] == "user"
        for block in message["content"]
        if block["type"] == "tool_result"
    ]

    assert actual_results == expected_results


def test_default_snip_limit_keeps_thirteen_messages(tmp_path, monkeypatch):
    """防止临时教学阈值让很短的会话提前归档。"""
    lesson = load_lesson(monkeypatch, tmp_path)
    messages = [
        {"role": "user" if index % 2 == 0 else "assistant",
         "content": f"message-{index}"}
        for index in range(13)
    ]

    compacted = lesson["COMPACTOR"].snip_compact(messages)

    assert compacted == messages


def test_default_summary_limit_keeps_nine_kb_input(tmp_path, monkeypatch):
    """防止临时教学阈值过早截断发送给摘要模型的历史。"""
    lesson = load_lesson(monkeypatch, tmp_path)
    messages = [{"role": "user", "content": "x" * 9000}]

    summary_input = lesson["COMPACTOR"].summary_input(messages)

    assert "[middle omitted; full transcript is on disk]" not in summary_input


def test_default_large_result_limit_keeps_five_kb_output(tmp_path, monkeypatch):
    """防止临时教学阈值把普通的 5 KB 工具结果判定为大结果。"""
    lesson = load_lesson(monkeypatch, tmp_path)
    output = "x" * 5000

    persisted = lesson["COMPACTOR"].persist_large_output("tool-1", output)

    assert persisted == output


def test_default_persisted_preview_keeps_two_thousand_characters(
        tmp_path, monkeypatch):
    """防止临时教学设置把大结果的默认预览缩得过短。"""
    lesson = load_lesson(monkeypatch, tmp_path)

    persisted = lesson["COMPACTOR"].persisted_preview("tool-1", "x" * 3000)
    preview = persisted.split("Preview:\n", 1)[1].removesuffix(
        "\n</persisted-output>")

    assert len(preview) == 2000


def test_fit_tool_results_keeps_one_thousand_character_preview(
        tmp_path, monkeypatch):
    """防止临时教学设置让再适配阶段丢失过多结果预览。"""
    lesson = load_lesson(monkeypatch, tmp_path)
    messages = [{"role": "user", "content": [{
        "type": "tool_result",
        "tool_use_id": "tool-1",
        "content": "x" * 2000,
    }]}]

    lesson["COMPACTOR"].fit_tool_results(messages, target_chars=100)
    persisted = messages[0]["content"][0]["content"]
    preview = persisted.split("Preview:\n", 1)[1].removesuffix(
        "\n</persisted-output>")

    assert len(preview) == 1000
