from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_sitecustomize_module():
    module_path = PROJECT_ROOT / "src" / "sitecustomize.py"
    spec = importlib.util.spec_from_file_location(
        "task_router_sitecustomize_under_test", module_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _install_fake_transformers(monkeypatch):
    class FakeBatchEncoding(dict):
        pass

    class FakePreTrainedTokenizerBase:
        def apply_chat_template(self, *args, **kwargs):
            raise NotImplementedError

    transformers_module = types.ModuleType("transformers")
    transformers_module.PreTrainedTokenizerBase = FakePreTrainedTokenizerBase

    tokenization_module = types.ModuleType("transformers.tokenization_utils_base")
    tokenization_module.BatchEncoding = FakeBatchEncoding

    monkeypatch.setitem(sys.modules, "transformers", transformers_module)
    monkeypatch.setitem(
        sys.modules, "transformers.tokenization_utils_base", tokenization_module
    )
    return FakePreTrainedTokenizerBase, FakeBatchEncoding


def test_sglang_chat_template_patch_unwraps_batch_encoding(monkeypatch) -> None:
    monkeypatch.delenv("TASK_ROUTER_SGLANG_CHAT_TEMPLATE_FIX", raising=False)
    tokenizer_base, batch_encoding = _install_fake_transformers(monkeypatch)
    module = _load_sitecustomize_module()

    def fake_apply_chat_template(self, *args, **kwargs):
        return batch_encoding({"input_ids": [1, 2, 3], "attention_mask": [1, 1, 1]})

    monkeypatch.setattr(tokenizer_base, "apply_chat_template", fake_apply_chat_template)

    assert module._patch_sglang_chat_template_batch_encoding()
    assert tokenizer_base.apply_chat_template(object(), []) == [1, 2, 3]


def test_sglang_chat_template_patch_keeps_tensor_outputs(monkeypatch) -> None:
    monkeypatch.delenv("TASK_ROUTER_SGLANG_CHAT_TEMPLATE_FIX", raising=False)
    tokenizer_base, batch_encoding = _install_fake_transformers(monkeypatch)
    module = _load_sitecustomize_module()

    def fake_apply_chat_template(self, *args, **kwargs):
        return batch_encoding({"input_ids": [1, 2, 3]})

    monkeypatch.setattr(tokenizer_base, "apply_chat_template", fake_apply_chat_template)

    assert module._patch_sglang_chat_template_batch_encoding()
    result = tokenizer_base.apply_chat_template(object(), [], return_tensors="pt")
    assert isinstance(result, batch_encoding)


def test_sglang_chat_template_patch_keeps_explicit_dict_outputs(monkeypatch) -> None:
    monkeypatch.delenv("TASK_ROUTER_SGLANG_CHAT_TEMPLATE_FIX", raising=False)
    tokenizer_base, batch_encoding = _install_fake_transformers(monkeypatch)
    module = _load_sitecustomize_module()

    def fake_apply_chat_template(self, *args, **kwargs):
        return batch_encoding({"input_ids": [1, 2, 3]})

    monkeypatch.setattr(tokenizer_base, "apply_chat_template", fake_apply_chat_template)

    assert module._patch_sglang_chat_template_batch_encoding()
    result = tokenizer_base.apply_chat_template(object(), [], return_dict=True)
    assert isinstance(result, batch_encoding)
