# Adaptive PC: Adams predictor-corrector with a free local error estimate.
# Ported from https://github.com/YakovSava/adaptive-step-samplers (MIT)

import torch
from tqdm.auto import trange

import lib_es.const as consts
from lib_es.extra_samplers.utils.adams_pc.integrator import AdaptiveConfig, integrate_adaptive_pc
from lib_es.utils import sampler_metadata


@torch.no_grad()
@sampler_metadata("Adaptive PC", sampler_aliases=["apc"])
def sample_adaptive_pc(model, x, sigmas, extra_args=None, callback=None, disable=None):
    """Variable-step Adams predictor-corrector, one model call per step.

    The gap between the predicted and the corrected state is a local error estimate
    that needs no extra model call. In "fixed" mode the sampler follows the schedule
    as given; in "budget" mode it moves the same number of steps along the schedule
    to where the estimate says they are needed.
    """
    if len(sigmas) <= 1:
        return x

    p = getattr(model, "p", None)
    config = AdaptiveConfig(
        order=getattr(p, consts.APC_ORDER, consts.APC_DEFAULT_ORDER),
        mode=getattr(p, consts.APC_MODE, consts.APC_DEFAULT_MODE),
        use_corrector=getattr(p, consts.APC_USE_CORRECTOR, True),
        rtol=getattr(p, consts.APC_RTOL, consts.APC_DEFAULT_RTOL),
        atol=getattr(p, consts.APC_ATOL, consts.APC_DEFAULT_ATOL),
        damping=getattr(p, consts.APC_DAMPING, consts.APC_DEFAULT_DAMPING),
        min_ratio=getattr(p, consts.APC_MIN_RATIO, consts.APC_DEFAULT_MIN_RATIO),
        max_ratio=getattr(p, consts.APC_MAX_RATIO, consts.APC_DEFAULT_MAX_RATIO),
        spread=getattr(p, consts.APC_SPREAD, consts.APC_DEFAULT_SPREAD),
        smoothing=getattr(p, consts.APC_SMOOTHING, consts.APC_DEFAULT_SMOOTHING),
    )

    extra_args = {} if extra_args is None else extra_args
    s_in = x.new_ones([x.shape[0]])
    reference = sigmas[0]
    progress = trange(len(sigmas) - 1, disable=disable)

    def denoise_fn(state, sigma):
        return model(state, sigma * s_in, **extra_args)

    def on_step(record):
        progress.update(1)
        if callback is not None:
            sigma = reference.new_full((), record["sigma"])
            callback(
                {
                    "x": record["x"],
                    "i": record["index"],
                    "sigma": sigma,
                    "sigma_hat": sigma,
                    "denoised": record["denoised"],
                }
            )

    result = integrate_adaptive_pc(denoise_fn, x, [float(value) for value in sigmas], config, on_step=on_step)
    progress.close()
    return result
