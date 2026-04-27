from __future__ import annotations

import os

_TRANSFORMERS_APPLY_CHAT_TEMPLATE_ORIGINAL = None


def _env_enabled(name: str, *, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"", "0", "false", "no", "off"}


def _set_multiprocessing_authkey() -> bool:
    authkey = os.getenv("TASK_ROUTER_MP_AUTHKEY", "").strip()
    if not authkey:
        return False
    try:
        import multiprocessing

        multiprocessing.current_process().authkey = authkey.encode("utf-8")
        return True
    except Exception:
        return False


def _safe_modify_tuple(values: tuple[object, ...], index: int, modifier):
    if not isinstance(values, tuple) or index < 0 or len(values) <= index:
        return values
    return (*values[:index], modifier(values[index]), *values[index + 1 :])


def _sglang_reduce_tensor_modified(*args, **kwargs):
    import torch
    from torch.multiprocessing import reductions
    from sglang.srt.utils import patch_torch

    output_fn, output_args = reductions._reduce_tensor_original(*args, **kwargs)
    tensor = args[0] if args else None
    if not isinstance(tensor, torch.Tensor) or tensor.device.type != "cuda":
        return output_fn, output_args

    device_index = getattr(patch_torch, "_REDUCE_TENSOR_ARG_DEVICE_INDEX", 6)
    return output_fn, _safe_modify_tuple(output_args, device_index, patch_torch._device_to_uuid)


def _sglang_rebuild_cuda_tensor_modified(*args):
    from torch.multiprocessing import reductions
    from sglang.srt.utils import patch_torch

    device_index = getattr(patch_torch, "_REDUCE_TENSOR_ARG_DEVICE_INDEX", 6)
    return reductions._rebuild_cuda_tensor_original(
        *_safe_modify_tuple(args, device_index, patch_torch._device_from_maybe_uuid)
    )


def _patch_sglang_torch_reductions() -> bool:
    try:
        from torch.multiprocessing import reductions
        from sglang.srt.utils import patch_torch
    except Exception:
        return False

    if not hasattr(patch_torch, "_device_to_uuid") or not hasattr(patch_torch, "_device_from_maybe_uuid"):
        return False

    _sglang_reduce_tensor_modified.__module__ = patch_torch.__name__
    _sglang_reduce_tensor_modified.__name__ = "_reduce_tensor_modified"
    _sglang_reduce_tensor_modified.__qualname__ = "_reduce_tensor_modified"
    _sglang_rebuild_cuda_tensor_modified.__module__ = patch_torch.__name__
    _sglang_rebuild_cuda_tensor_modified.__name__ = "_rebuild_cuda_tensor_modified"
    _sglang_rebuild_cuda_tensor_modified.__qualname__ = "_rebuild_cuda_tensor_modified"

    patch_torch._modify_tuple = _safe_modify_tuple
    patch_torch._reduce_tensor_modified = _sglang_reduce_tensor_modified
    patch_torch._rebuild_cuda_tensor_modified = _sglang_rebuild_cuda_tensor_modified

    if hasattr(reductions, "_reduce_tensor_original"):
        reductions.reduce_tensor = _sglang_reduce_tensor_modified
    if hasattr(reductions, "_rebuild_cuda_tensor_original"):
        reductions.rebuild_cuda_tensor = _sglang_rebuild_cuda_tensor_modified
    return True


def _transformers_apply_chat_template_unwrap_batch_encoding(self, *args, **kwargs):
    result = _TRANSFORMERS_APPLY_CHAT_TEMPLATE_ORIGINAL(self, *args, **kwargs)
    batch_encoding_type = getattr(
        _transformers_apply_chat_template_unwrap_batch_encoding,
        "_task_router_batch_encoding_type",
        None,
    )
    if batch_encoding_type is None:
        return result
    if (
        isinstance(result, batch_encoding_type)
        and kwargs.get("return_tensors") is None
        and not kwargs.get("return_dict")
    ):
        input_ids = result.get("input_ids")
        if isinstance(input_ids, list):
            return input_ids
    return result


def _patch_sglang_chat_template_batch_encoding() -> bool:
    global _TRANSFORMERS_APPLY_CHAT_TEMPLATE_ORIGINAL

    try:
        from transformers import PreTrainedTokenizerBase
        from transformers.tokenization_utils_base import BatchEncoding
    except Exception:
        return False

    original = PreTrainedTokenizerBase.apply_chat_template
    if getattr(original, "_task_router_unwrap_batch_encoding", False):
        return True

    _TRANSFORMERS_APPLY_CHAT_TEMPLATE_ORIGINAL = original
    _transformers_apply_chat_template_unwrap_batch_encoding._task_router_unwrap_batch_encoding = True
    _transformers_apply_chat_template_unwrap_batch_encoding._task_router_original = original
    _transformers_apply_chat_template_unwrap_batch_encoding._task_router_batch_encoding_type = BatchEncoding
    PreTrainedTokenizerBase.apply_chat_template = _transformers_apply_chat_template_unwrap_batch_encoding
    return True


if _env_enabled("TASK_ROUTER_SGLANG_CHAT_TEMPLATE_FIX"):
    _patch_sglang_chat_template_batch_encoding()

if _set_multiprocessing_authkey():
    _patch_sglang_torch_reductions()
