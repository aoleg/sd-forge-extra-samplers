from typing import Any

import gradio as gr

import modules.scripts as scripts
from modules.processing import StableDiffusionProcessing
from modules.script_callbacks import on_ui_settings
from modules.shared import OptionInfo, opts

import lib_es.const as consts
from lib_es.xyz import xyz_support
from lib_es.samplers import add_extra_samplers
from lib_es.schedulers import add_schedulers


add_extra_samplers()
add_schedulers()


def from_setting_or_default(key: str, default: None | Any) -> None | Any:
    return opts.data.get(key, default)


def on_change_update_setting(key: str, value: Any) -> None:
    opts.set(key, value)


class ExtraSamplerExtension(scripts.Script):
    def __init__(self):
        super().__init__()
        self.xyz_cache = {}
        xyz_support(self.xyz_cache)

    def title(self):
        return "Extra Samplers"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, is_img2img):
        with gr.Accordion(label="Extra Samplers", open=False):
            with gr.Accordion(label="Adaptive Progressive", open=False):
                gr.Markdown("Adaptive progressive sampler that automatically adjusts to different step counts. ")
                gr.Markdown(
                    "Phase ends are automatically adjusted based on the total number of steps. These are approximations"
                )
                with gr.Row():
                    euler_a_end = gr.Slider(
                        minimum=0.0,
                        maximum=1.0,
                        step=0.05,
                        value=from_setting_or_default(consts.AP_EULER_A_END, 0.35),
                        label="Euler A end",
                    )
                    dpm_2m_end = gr.Slider(
                        minimum=0.0,
                        maximum=1.0,
                        step=0.05,
                        value=from_setting_or_default(consts.AP_DPM_2M_END, 0.75),
                        label="DPM++ 2M end",
                    )
                with gr.Row():
                    ancestral_eta = gr.Slider(
                        minimum=0.0,
                        maximum=1.0,
                        step=0.05,
                        value=from_setting_or_default(consts.AP_ANCESTRAL_ETA, 0.4),
                        label="Ancestral Eta",
                    )
                    detail_strength = gr.Slider(
                        minimum=0.0,
                        maximum=10.0,
                        step=0.1,
                        value=from_setting_or_default(consts.AP_DETAIL_STRENGTH, 1.5),
                        label="Detail Strength",
                    )

                euler_a_end.change(
                    fn=lambda value: on_change_update_setting(consts.AP_EULER_A_END, value), inputs=[euler_a_end]
                )
                dpm_2m_end.change(
                    fn=lambda value: on_change_update_setting(consts.AP_DPM_2M_END, value), inputs=[dpm_2m_end]
                )
                ancestral_eta.change(
                    fn=lambda value: on_change_update_setting(consts.AP_ANCESTRAL_ETA, value),
                    inputs=[ancestral_eta],
                )
                detail_strength.change(
                    fn=lambda value: on_change_update_setting(consts.AP_DETAIL_STRENGTH, value),
                    inputs=[detail_strength],
                )

            with gr.Accordion(label="Langevin Euler", open=False):
                langevin_strength = gr.Slider(
                    minimum=0.0,
                    maximum=0.5,
                    step=0.01,
                    value=from_setting_or_default(consts.LANGEVIN_STRENGTH, 0.1),
                    label="Langevin Strength",
                    info="Langevin strength for Langevin Euler sampler. Adjust to control the amount of noise.",
                )
                langevin_strength.change(
                    fn=lambda value: on_change_update_setting(consts.LANGEVIN_STRENGTH, value),
                    inputs=[langevin_strength],
                )

            with gr.Accordion(label="Gradient Estimation", open=False):
                use_adaptive_steps = from_setting_or_default(consts.GE_USE_ADAPTIVE_STEPS, False)

                adaptive_steps = gr.Checkbox(
                    label="Use Adaptive Steps",
                    value=use_adaptive_steps,
                    info="Modify the number of steps based on the noise schedule.",
                )
                use_timestep_adaptive_gamma = gr.Checkbox(
                    label="Timestep-Based Adaptive Gamma",
                    value=from_setting_or_default(consts.GE_USE_TIMESTEP_ADAPTIVE_GAMMA, False),
                    info="Adjust gamma during generation.",
                )
                gamma = gr.Slider(
                    minimum=consts.GE_MIN_GAMMA,
                    maximum=consts.GE_MAX_GAMMA,
                    step=0.05,
                    value=from_setting_or_default(consts.GE_GAMMA, consts.GE_DEFAULT_GAMMA),
                    label="Gamma",
                    info="Gamma value for gradient estimation. Higher values increase the amount of noise.",
                    interactive=not use_adaptive_steps,
                )
                gamma_offset = gr.Slider(
                    minimum=consts.GE_MIN_GAMMA_OFFSET,
                    maximum=consts.GE_MAX_GAMMA_OFFSET,
                    step=0.05,
                    value=from_setting_or_default(consts.GE_GAMMA_OFFSET, consts.GE_DEFAULT_GAMMA_OFFSET),
                    label="Gamma Offset",
                    info="Offset to add to the calculated gamma when using adaptive steps.",
                    interactive=use_adaptive_steps,
                )
                gamma.change(fn=lambda value: on_change_update_setting(consts.GE_GAMMA, value), inputs=[gamma])
                gamma_offset.change(
                    fn=lambda value: on_change_update_setting(consts.GE_GAMMA_OFFSET, value), inputs=[gamma_offset]
                )

                # Update interactivity when adaptive steps checkbox changes
                adaptive_steps.change(
                    fn=lambda value: (gr.Slider(interactive=not value), gr.Slider(interactive=value)),
                    inputs=[adaptive_steps],
                    outputs=[gamma, gamma_offset],
                    js=None,
                ).then(
                    fn=lambda value: on_change_update_setting(consts.GE_USE_ADAPTIVE_STEPS, value),
                    inputs=[adaptive_steps],
                )

                use_timestep_adaptive_gamma.change(
                    fn=lambda value: on_change_update_setting(consts.GE_USE_TIMESTEP_ADAPTIVE_GAMMA, value),
                    inputs=[use_timestep_adaptive_gamma],
                )

                validate_schedule = gr.Checkbox(
                    label="Validate Schedule",
                    value=from_setting_or_default(consts.GE_VALIDATE_SCHEDULE, False),
                    info="Validate the noise schedule (For debugging purposes).",
                )

            with gr.Accordion(label="SA-Solver", open=False):
                gr.Markdown(
                    "Stochastic strength of SA-Solver and the part of the noise range where it applies. "
                    "Defaults (1.0 inside 0.2-0.8) are the fixed values ComfyUI uses. "
                    "Eta 1.6-1.8 adds texture at some cost to geometry and also changes the composition; "
                    "widening the window does not add texture."
                )
                with gr.Row():
                    sa_eta = gr.Slider(
                        minimum=0.0,
                        maximum=6.0,
                        step=0.05,
                        value=from_setting_or_default(consts.SA_SOLVER_ETA, consts.SA_SOLVER_DEFAULT_ETA),
                        label="Eta",
                        info="0 runs SA-Solver as an ODE.",
                    )
                    sa_start = gr.Slider(
                        minimum=0.0,
                        maximum=1.0,
                        step=0.01,
                        value=from_setting_or_default(
                            consts.SA_SOLVER_STOCHASTIC_START, consts.SA_SOLVER_START_PERCENT
                        ),
                        label="Stochastic Start",
                    )
                    sa_end = gr.Slider(
                        minimum=0.0,
                        maximum=1.0,
                        step=0.01,
                        value=from_setting_or_default(consts.SA_SOLVER_STOCHASTIC_END, consts.SA_SOLVER_END_PERCENT),
                        label="Stochastic End",
                    )

                sa_eta.change(fn=lambda value: on_change_update_setting(consts.SA_SOLVER_ETA, value), inputs=[sa_eta])
                sa_start.change(
                    fn=lambda value: on_change_update_setting(consts.SA_SOLVER_STOCHASTIC_START, value),
                    inputs=[sa_start],
                )
                sa_end.change(
                    fn=lambda value: on_change_update_setting(consts.SA_SOLVER_STOCHASTIC_END, value),
                    inputs=[sa_end],
                )

            with gr.Accordion(label="Adaptive PC", open=False):
                gr.Markdown(
                    "Adams predictor-corrector, one model call per step. "
                    "**Fixed** follows the scheduler. **Budget** (experimental) moves the same number of steps "
                    "along the schedule using the free error estimate; it ignores the scheduler's exact sigmas."
                )
                with gr.Row():
                    apc_order = gr.Slider(
                        minimum=1,
                        maximum=4,
                        step=1,
                        value=from_setting_or_default(consts.APC_ORDER, consts.APC_DEFAULT_ORDER),
                        label="Order",
                    )
                    apc_mode = gr.Radio(
                        choices=["fixed", "budget"],
                        value=from_setting_or_default(consts.APC_MODE, consts.APC_DEFAULT_MODE),
                        label="Step Mode",
                    )
                    apc_use_corrector = gr.Checkbox(
                        value=from_setting_or_default(consts.APC_USE_CORRECTOR, True),
                        label="Use Corrector",
                        info="Write the corrected state back. Off runs the predictor only.",
                    )
                with gr.Accordion(label="Budget Mode", open=False):
                    with gr.Row():
                        apc_rtol = gr.Slider(
                            minimum=1e-5,
                            maximum=1.0,
                            step=0.001,
                            value=from_setting_or_default(consts.APC_RTOL, consts.APC_DEFAULT_RTOL),
                            label="Relative Tolerance",
                        )
                        apc_atol = gr.Slider(
                            minimum=1e-6,
                            maximum=1.0,
                            step=0.0001,
                            value=from_setting_or_default(consts.APC_ATOL, consts.APC_DEFAULT_ATOL),
                            label="Absolute Tolerance",
                        )
                        apc_damping = gr.Slider(
                            minimum=0.1,
                            maximum=2.0,
                            step=0.05,
                            value=from_setting_or_default(consts.APC_DAMPING, consts.APC_DEFAULT_DAMPING),
                            label="Damping",
                        )
                    with gr.Row():
                        apc_min_ratio = gr.Slider(
                            minimum=0.1,
                            maximum=1.0,
                            step=0.05,
                            value=from_setting_or_default(consts.APC_MIN_RATIO, consts.APC_DEFAULT_MIN_RATIO),
                            label="Min Step Ratio",
                        )
                        apc_max_ratio = gr.Slider(
                            minimum=1.0,
                            maximum=8.0,
                            step=0.1,
                            value=from_setting_or_default(consts.APC_MAX_RATIO, consts.APC_DEFAULT_MAX_RATIO),
                            label="Max Step Ratio",
                        )
                        apc_spread = gr.Slider(
                            minimum=1.0,
                            maximum=16.0,
                            step=0.25,
                            value=from_setting_or_default(consts.APC_SPREAD, consts.APC_DEFAULT_SPREAD),
                            label="Spread",
                        )
                        apc_smoothing = gr.Slider(
                            minimum=0.0,
                            maximum=1.0,
                            step=0.05,
                            value=from_setting_or_default(consts.APC_SMOOTHING, consts.APC_DEFAULT_SMOOTHING),
                            label="Smoothing",
                        )

                for key, component in [
                    (consts.APC_ORDER, apc_order),
                    (consts.APC_MODE, apc_mode),
                    (consts.APC_USE_CORRECTOR, apc_use_corrector),
                    (consts.APC_RTOL, apc_rtol),
                    (consts.APC_ATOL, apc_atol),
                    (consts.APC_DAMPING, apc_damping),
                    (consts.APC_MIN_RATIO, apc_min_ratio),
                    (consts.APC_MAX_RATIO, apc_max_ratio),
                    (consts.APC_SPREAD, apc_spread),
                    (consts.APC_SMOOTHING, apc_smoothing),
                ]:
                    component.change(
                        fn=lambda value, key=key: on_change_update_setting(key, value),
                        inputs=[component],
                    )

        return [
            euler_a_end,
            dpm_2m_end,
            ancestral_eta,
            detail_strength,
            langevin_strength,
            adaptive_steps,
            use_timestep_adaptive_gamma,
            gamma,
            gamma_offset,
            validate_schedule,
            sa_eta,
            sa_start,
            sa_end,
            apc_order,
            apc_mode,
            apc_use_corrector,
            apc_rtol,
            apc_atol,
            apc_damping,
            apc_min_ratio,
            apc_max_ratio,
            apc_spread,
            apc_smoothing,
        ]

    def get_values_and_apply(self, p: StableDiffusionProcessing, values: dict):
        for key, value in values.items():
            value = self.xyz_cache.pop(key, value)
            setattr(p, key, value)
            p.extra_generation_params[key] = value

    def process_batch(
        self,
        p: StableDiffusionProcessing,
        euler_a_end: float,
        dpm_2m_end: float,
        ancestral_eta: float,
        detail_strength: float,
        langevin_strength: float,
        use_adaptive_steps: bool,
        use_timestep_adaptive_gamma: bool,
        gamma: float,
        gamma_offset: float,
        validate_schedule: bool,
        sa_eta: float,
        sa_start: float,
        sa_end: float,
        apc_order: int,
        apc_mode: str,
        apc_use_corrector: bool,
        apc_rtol: float,
        apc_atol: float,
        apc_damping: float,
        apc_min_ratio: float,
        apc_max_ratio: float,
        apc_spread: float,
        apc_smoothing: float,
        batch_number: int,
        prompts: list[str],
        seeds: list[int],
        subseeds: list[int],
    ):
        if p.sampler_name == "Adaptive Progressive":
            self.get_values_and_apply(
                p,
                {
                    consts.AP_EULER_A_END: euler_a_end,
                    consts.AP_DPM_2M_END: dpm_2m_end,
                    consts.AP_ANCESTRAL_ETA: ancestral_eta,
                    consts.AP_DETAIL_STRENGTH: detail_strength,
                },
            )
        elif p.sampler_name == "Langevin Euler":
            self.get_values_and_apply(p, {consts.LANGEVIN_STRENGTH: langevin_strength})
        elif p.sampler_name == "Gradient Estimation":
            self.get_values_and_apply(
                p,
                {
                    consts.GE_GAMMA: gamma,
                    consts.GE_GAMMA_OFFSET: gamma_offset,
                    consts.GE_USE_ADAPTIVE_STEPS: use_adaptive_steps,
                    consts.GE_USE_TIMESTEP_ADAPTIVE_GAMMA: use_timestep_adaptive_gamma,
                    consts.GE_VALIDATE_SCHEDULE: validate_schedule,
                },
            )
        elif p.sampler_name == "SA-Solver":
            self.get_values_and_apply(
                p,
                {
                    consts.SA_SOLVER_ETA: sa_eta,
                    consts.SA_SOLVER_STOCHASTIC_START: sa_start,
                    consts.SA_SOLVER_STOCHASTIC_END: sa_end,
                },
            )
        elif p.sampler_name == "Adaptive PC":
            self.get_values_and_apply(
                p,
                {
                    consts.APC_ORDER: int(apc_order),
                    consts.APC_MODE: apc_mode,
                    consts.APC_USE_CORRECTOR: apc_use_corrector,
                },
            )
            budget_values = {
                consts.APC_RTOL: apc_rtol,
                consts.APC_ATOL: apc_atol,
                consts.APC_DAMPING: apc_damping,
                consts.APC_MIN_RATIO: apc_min_ratio,
                consts.APC_MAX_RATIO: apc_max_ratio,
                consts.APC_SPREAD: apc_spread,
                consts.APC_SMOOTHING: apc_smoothing,
            }
            # The budget knobs do nothing in fixed mode; keep them out of the infotext.
            if getattr(p, consts.APC_MODE) == "budget":
                self.get_values_and_apply(p, budget_values)
            else:
                for key in budget_values:
                    self.xyz_cache.pop(key, None)
        elif p.scheduler == "beta_57" or p.scheduler == "Beta 57":
            self.get_values_and_apply(
                p,
                {
                    "Beta schedule alpha": 0.5,
                    "Beta schedule beta": 0.7,
                },
            )


section = ("exs", "Extra Samplers")


def on_settings():
    opts.add_option(
        consts.AP_EULER_A_END,
        OptionInfo(
            0.35,
            "Euler A End",
            component=gr.Slider,
            component_args={"minimum": 0.0, "maximum": 1.0, "step": 0.05},
            section=section,
        ),
    )
    opts.add_option(
        consts.AP_DPM_2M_END,
        OptionInfo(
            0.75,
            "DPM++ 2M End",
            component=gr.Slider,
            component_args={"minimum": 0.0, "maximum": 1.0, "step": 0.05},
            section=section,
        ),
    )
    opts.add_option(
        consts.AP_ANCESTRAL_ETA,
        OptionInfo(
            0.4,
            "Adaptive Progressive Eta",
            component=gr.Slider,
            component_args={"minimum": 0.0, "maximum": 1.0, "step": 0.01},
            section=section,
        ),
    )
    opts.add_option(
        consts.AP_DETAIL_STRENGTH,
        OptionInfo(
            1.5,
            "Adaptive Progressive Detail Strength",
            component=gr.Slider,
            component_args={"minimum": 0.0, "maximum": 3.0, "step": 0.01},
            section=section,
        ),
    )

    opts.add_option(
        consts.LANGEVIN_STRENGTH,
        OptionInfo(
            0.1,
            "Langevin Strength",
            component=gr.Slider,
            component_args={"minimum": 0.0, "maximum": 1.0, "step": 0.01},
            section=section,
        ),
    )

    opts.add_option(
        consts.GE_GAMMA,
        OptionInfo(
            consts.GE_DEFAULT_GAMMA,
            "Gradient Estimation Gamma",
            component=gr.Slider,
            component_args={"minimum": consts.GE_MIN_GAMMA, "maximum": consts.GE_MAX_GAMMA, "step": 0.1},
            section=section,
        ),
    )

    opts.add_option(
        consts.GE_GAMMA_OFFSET,
        OptionInfo(
            consts.GE_DEFAULT_GAMMA_OFFSET,
            "Gradient Estimation Gamma Offset",
            component=gr.Slider,
            component_args={"minimum": consts.GE_MIN_GAMMA_OFFSET, "maximum": consts.GE_MAX_GAMMA_OFFSET, "step": 0.1},
            section=section,
        ),
    )

    opts.add_option(
        consts.GE_USE_ADAPTIVE_STEPS,
        OptionInfo(
            False,
            "Use Adaptive Steps",
            component=gr.Checkbox,
            section=section,
        ),
    )

    opts.add_option(
        consts.GE_USE_TIMESTEP_ADAPTIVE_GAMMA,
        OptionInfo(
            False,
            "Use Timestep Adaptive Gamma",
            component=gr.Checkbox,
            section=section,
        ),
    )

    opts.add_option(
        consts.SA_SOLVER_ETA,
        OptionInfo(
            consts.SA_SOLVER_DEFAULT_ETA,
            "SA-Solver Eta",
            component=gr.Slider,
            component_args={"minimum": 0.0, "maximum": 6.0, "step": 0.05},
            section=section,
        ),
    )

    opts.add_option(
        consts.SA_SOLVER_STOCHASTIC_START,
        OptionInfo(
            consts.SA_SOLVER_START_PERCENT,
            "SA-Solver Stochastic Start",
            component=gr.Slider,
            component_args={"minimum": 0.0, "maximum": 1.0, "step": 0.01},
            section=section,
        ),
    )

    opts.add_option(
        consts.SA_SOLVER_STOCHASTIC_END,
        OptionInfo(
            consts.SA_SOLVER_END_PERCENT,
            "SA-Solver Stochastic End",
            component=gr.Slider,
            component_args={"minimum": 0.0, "maximum": 1.0, "step": 0.01},
            section=section,
        ),
    )

    opts.add_option(
        consts.APC_ORDER,
        OptionInfo(
            consts.APC_DEFAULT_ORDER,
            "Adaptive PC Order",
            component=gr.Slider,
            component_args={"minimum": 1, "maximum": 4, "step": 1},
            section=section,
        ),
    )

    opts.add_option(
        consts.APC_MODE,
        OptionInfo(
            consts.APC_DEFAULT_MODE,
            "Adaptive PC Step Mode",
            component=gr.Radio,
            component_args={"choices": ["fixed", "budget"]},
            section=section,
        ),
    )

    opts.add_option(
        consts.APC_USE_CORRECTOR,
        OptionInfo(
            True,
            "Adaptive PC Use Corrector",
            component=gr.Checkbox,
            section=section,
        ),
    )

    opts.add_option(
        consts.APC_RTOL,
        OptionInfo(
            consts.APC_DEFAULT_RTOL,
            "Adaptive PC Relative Tolerance",
            component=gr.Slider,
            component_args={"minimum": 1e-5, "maximum": 1.0, "step": 0.001},
            section=section,
        ),
    )

    opts.add_option(
        consts.APC_ATOL,
        OptionInfo(
            consts.APC_DEFAULT_ATOL,
            "Adaptive PC Absolute Tolerance",
            component=gr.Slider,
            component_args={"minimum": 1e-6, "maximum": 1.0, "step": 0.0001},
            section=section,
        ),
    )

    opts.add_option(
        consts.APC_DAMPING,
        OptionInfo(
            consts.APC_DEFAULT_DAMPING,
            "Adaptive PC Damping",
            component=gr.Slider,
            component_args={"minimum": 0.1, "maximum": 2.0, "step": 0.05},
            section=section,
        ),
    )

    opts.add_option(
        consts.APC_MIN_RATIO,
        OptionInfo(
            consts.APC_DEFAULT_MIN_RATIO,
            "Adaptive PC Min Step Ratio",
            component=gr.Slider,
            component_args={"minimum": 0.1, "maximum": 1.0, "step": 0.05},
            section=section,
        ),
    )

    opts.add_option(
        consts.APC_MAX_RATIO,
        OptionInfo(
            consts.APC_DEFAULT_MAX_RATIO,
            "Adaptive PC Max Step Ratio",
            component=gr.Slider,
            component_args={"minimum": 1.0, "maximum": 8.0, "step": 0.1},
            section=section,
        ),
    )

    opts.add_option(
        consts.APC_SPREAD,
        OptionInfo(
            consts.APC_DEFAULT_SPREAD,
            "Adaptive PC Spread",
            component=gr.Slider,
            component_args={"minimum": 1.0, "maximum": 16.0, "step": 0.25},
            section=section,
        ),
    )

    opts.add_option(
        consts.APC_SMOOTHING,
        OptionInfo(
            consts.APC_DEFAULT_SMOOTHING,
            "Adaptive PC Smoothing",
            component=gr.Slider,
            component_args={"minimum": 0.0, "maximum": 1.0, "step": 0.05},
            section=section,
        ),
    )


on_ui_settings(on_settings)
