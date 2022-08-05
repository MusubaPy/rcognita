import os, sys

PARENT_DIR = os.path.abspath(__file__ + "/../../")
sys.path.insert(0, PARENT_DIR)
CUR_DIR = os.path.abspath(__file__ + "/..")
sys.path.insert(0, CUR_DIR)

import pathlib
import warnings
import matplotlib.animation as animation
import matplotlib.pyplot as plt
import csv
import rcognita
import numpy as np
from rcognita.utilities import rep_mat

from config_blueprints import Config3WRobot
from pipeline_blueprints import AbstractPipeline

if os.path.abspath(rcognita.__file__ + "/../..") == PARENT_DIR:
    info = (
        f"this script is being run using "
        f"rcognita ({rcognita.__version__}) "
        f"located in cloned repository at '{PARENT_DIR}'. "
        f"If you are willing to use your locally installed rcognita, "
        f"run this script ('{os.path.basename(__file__)}') outside "
        f"'rcognita/presets'."
    )
else:
    info = (
        f"this script is being run using "
        f"locally installed rcognita ({rcognita.__version__}). "
        f"Make sure the versions match."
    )
print("INFO:", info)

from rcognita import (
    controllers,
    visuals,
    simulator,
    systems,
    loggers,
    state_predictors,
    optimizers,
    objectives,
    models,
)
from datetime import datetime
from rcognita.utilities import on_key_press
from rcognita.rl_tools import Actor, CriticValue, CriticActionValue


class Pipeline3WRobot(AbstractPipeline):
    def system_initialization(self):
        self.my_sys = systems.Sys3WRobot(
            sys_type="diff_eqn",
            dim_state=self.dim_state,
            dim_input=self.dim_input,
            dim_output=self.dim_output,
            dim_disturb=self.dim_disturb,
            pars=[self.m, self.I],
            control_bounds=self.control_bounds,
            is_dyn_ctrl=self.is_dyn_ctrl,
            is_disturb=self.is_disturb,
            pars_disturb=[],
        )

    def state_predictor_initialization(self):
        self.state_predictor = state_predictors.EulerStatePredictor(
            self.pred_step_size,
            self.my_sys._state_dyn,
            self.my_sys.out,
            self.dim_output,
            self.Nactor,
        )

    def objectives_initialization(self):
        self.objectives = objectives.Objectives(
            stage_obj_model=models.ModelQuadForm(R1=self.R1, R2=self.R2)
        )

    def optimizers_initialization(self):

        self.actor_optimizer = optimizers.RcognitaOptimizer.create_scipy_actor_optimizer(
            opt_method="SLSQP", control_bounds=self.control_bounds, Nactor=self.Nactor,
        )
        self.critic_optimizer = optimizers.RcognitaOptimizer.create_scipy_critic_optimizer(
            opt_method="SLSQP",
            critic_struct=self.critic_struct,
            dim_input=self.dim_input,
            dim_output=self.dim_output,
        )

    def rl_components_initialization(self):

        self.q_critic = CriticActionValue(
            Ncritic=self.Ncritic,
            dim_input=self.dim_input,
            dim_output=self.dim_output,
            buffer_size=self.buffer_size,
            stage_obj=self.objectives.stage_obj,
            gamma=self.gamma,
            optimizer=self.critic_optimizer,
            critic_model=models.ModelPolynomial(model_name=self.critic_struct),
        )
        self.v_critic = CriticValue(
            Ncritic=self.Ncritic,
            dim_input=self.dim_input,
            dim_output=self.dim_output,
            buffer_size=self.buffer_size,
            stage_obj=self.objectives.stage_obj,
            gamma=self.gamma,
            optimizer=self.critic_optimizer,
            critic_model=models.ModelPolynomial(model_name=self.critic_struct),
        )

        self.q_actor = Actor(
            self.Nactor,
            self.dim_input,
            self.dim_output,
            self.control_mode,
            state_predictor=self.state_predictor,
            optimizer=self.actor_optimizer,
            critic=self.q_critic,
            stage_obj=self.objectives.stage_obj,
        )

        self.v_actor = Actor(
            self.Nactor,
            self.dim_input,
            self.dim_output,
            self.control_mode,
            state_predictor=self.state_predictor,
            optimizer=self.actor_optimizer,
            critic=self.v_critic,
            stage_obj=self.objectives.stage_obj,
        )

    def controller_initialization(self):
        self.my_ctrl_nominal = controllers.CtrlNominal3WRobot(
            self.m,
            self.I,
            ctrl_gain=5,
            control_bounds=self.control_bounds,
            t0=self.t0,
            sampling_time=self.dt,
        )

        self.my_ctrl_opt_pred = controllers.CtrlOptPred(
            action_init=self.action_init,
            t0=self.t0,
            sampling_time=self.dt,
            pred_step_size=self.pred_step_size,
            state_dyn=self.my_sys._state_dyn,
            sys_out=self.my_sys.out,
            prob_noise_pow=self.prob_noise_pow,
            is_est_model=self.is_est_model,
            model_est_stage=self.model_est_stage,
            model_est_period=self.model_est_period,
            buffer_size=self.buffer_size,
            model_order=self.model_order,
            model_est_checks=self.model_est_checks,
            critic_period=self.critic_period,
            actor=self.q_actor,
            critic=self.q_critic,
            stage_obj_pars=[self.R1],
            observation_target=[],
        )

        self.my_ctrl_RL_stab = controllers.CtrlRLStab(
            action_init=self.action_init,
            t0=self.t0,
            sampling_time=self.dt,
            pred_step_size=self.pred_step_size,
            state_dyn=self.my_sys._state_dyn,
            sys_out=self.my_sys.out,
            prob_noise_pow=self.prob_noise_pow,
            is_est_model=self.is_est_model,
            model_est_stage=self.model_est_stage,
            model_est_period=self.model_est_period,
            buffer_size=self.buffer_size,
            model_order=self.model_order,
            model_est_checks=self.model_est_checks,
            critic_period=self.critic_period,
            actor=self.v_actor,
            critic=self.v_critic,
            stage_obj_pars=[self.R1],
            observation_target=[],
            safe_ctrl=self.my_ctrl_nominal,
            safe_decay_rate=1e-4,
        )

        if self.control_mode == "RLSTAB":
            self.my_ctrl_benchm = self.my_ctrl_RL_stab

        else:
            self.my_ctrl_benchm = self.my_ctrl_opt_pred

    def simulator_initialization(self):
        self.my_simulator = simulator.Simulator(
            sys_type="diff_eqn",
            closed_loop_rhs=self.my_sys.closed_loop_rhs,
            sys_out=self.my_sys.out,
            state_init=self.state_init,
            disturb_init=[],
            action_init=self.action_init,
            t0=self.t0,
            t1=self.t1,
            dt=self.dt,
            max_step=self.dt / 10,
            first_step=1e-6,
            atol=self.atol,
            rtol=self.rtol,
            is_disturb=self.is_disturb,
            is_dyn_ctrl=self.is_dyn_ctrl,
        )

    def logger_initialization(self):
        if (
            os.path.basename(os.path.normpath(os.path.abspath(os.getcwd())))
            == "presets"
        ):
            self.data_folder = "../simdata"
        else:
            self.data_folder = "simdata"

        pathlib.Path(self.data_folder).mkdir(parents=True, exist_ok=True)

        date = datetime.now().strftime("%Y-%m-%d")
        time = datetime.now().strftime("%Hh%Mm%Ss")
        self.datafiles = [None] * self.Nruns

        for k in range(0, self.Nruns):
            self.datafiles[k] = (
                self.data_folder
                + "/"
                + self.my_sys.name
                + "__"
                + self.control_mode
                + "__"
                + date
                + "__"
                + time
                + "__run{run:02d}.csv".format(run=k + 1)
            )

            if self.is_log:
                print("Logging data to:    " + self.datafiles[k])

                with open(self.datafiles[k], "w", newline="") as outfile:
                    writer = csv.writer(outfile)
                    writer.writerow(["System", self.my_sys.name])
                    writer.writerow(["Controller", self.control_mode])
                    writer.writerow(["dt", str(self.dt)])
                    writer.writerow(["state_init", str(self.state_init)])
                    writer.writerow(["is_est_model", str(self.is_est_model)])
                    writer.writerow(["model_est_stage", str(self.model_est_stage)])
                    writer.writerow(
                        [
                            "model_est_period_multiplier",
                            str(self.model_est_period_multiplier),
                        ]
                    )
                    writer.writerow(["model_order", str(self.model_order)])
                    writer.writerow(["prob_noise_pow", str(self.prob_noise_pow)])
                    writer.writerow(["Nactor", str(self.Nactor)])
                    writer.writerow(
                        [
                            "pred_step_size_multiplier",
                            str(self.pred_step_size_multiplier),
                        ]
                    )
                    writer.writerow(["buffer_size", str(self.buffer_size)])
                    writer.writerow(["stage_obj_struct", str(self.stage_obj_struct)])
                    writer.writerow(["R1_diag", str(self.R1_diag)])
                    writer.writerow(["R2_diag", str(self.R2_diag)])
                    writer.writerow(["Ncritic", str(self.Ncritic)])
                    writer.writerow(["gamma", str(self.gamma)])
                    writer.writerow(
                        ["critic_period_multiplier", str(self.critic_period_multiplier)]
                    )
                    writer.writerow(["critic_struct", str(self.critic_struct)])
                    writer.writerow(["actor_struct", str(self.actor_struct)])
                    writer.writerow(
                        [
                            "t [s]",
                            "x [m]",
                            "y [m]",
                            "alpha [rad]",
                            "v [m/s]",
                            "omega [rad/s]",
                            "stage_obj",
                            "accum_obj",
                            "F [N]",
                            "M [N m]",
                        ]
                    )

        # Do not display annoying warnings when print is on
        if not self.no_print:
            warnings.filterwarnings("ignore")

        self.my_logger = loggers.Logger3WRobot()

    def main_loop_visual(self):
        self.state_full_init = self.my_simulator.state_full

        my_animator = visuals.Animator3WRobot(
            objects=(
                self.my_simulator,
                self.my_sys,
                self.my_ctrl_nominal,
                self.my_ctrl_benchm,
                self.datafiles,
                self.my_logger,
                self.actor_optimizer,
                self.critic_optimizer,
            ),
            pars=(
                self.state_init,
                self.action_init,
                self.t0,
                self.t1,
                self.state_full_init,
                self.xMin,
                self.xMax,
                self.yMin,
                self.yMax,
                self.control_mode,
                self.action_manual,
                self.Fmin,
                self.Mmin,
                self.Fmax,
                self.Mmax,
                self.Nruns,
                self.no_print,
                self.is_log,
                0,
                [],
            ),
        )

        anm = animation.FuncAnimation(
            my_animator.fig_sim,
            my_animator.animate,
            init_func=my_animator.init_anim,
            blit=False,
            interval=self.dt / 1e6,
            repeat=False,
        )

        my_animator.get_anm(anm)

        cId = my_animator.fig_sim.canvas.mpl_connect(
            "key_press_event", lambda event: on_key_press(event, anm)
        )

        anm.running = True
        my_animator.fig_sim.tight_layout()

        plt.show()

    def main_loop_raw(self):

        run_curr = 1
        datafile = self.datafiles[0]

        while True:

            self.my_simulator.sim_step()

            (t, _, observation, state_full,) = self.my_simulator.get_sim_step_data()

            if self.save_trajectory:
                self.trajectory.append(np.concatenate((state_full, t), axis=None))
            if self.control_mode == "nominal":
                action = self.my_ctrl_nominal.compute_action_sampled(t, observation)
            else:
                action = self.my_ctrl_benchm.compute_action_sampled(t, observation)

            self.my_sys.receive_action(action)
            self.my_ctrl_benchm.upd_accum_obj(observation, action)

            xCoord = state_full[0]
            yCoord = state_full[1]
            alpha = state_full[2]
            v = state_full[3]
            omega = state_full[4]

            stage_obj = self.my_ctrl_benchm.stage_obj(observation, action)
            accum_obj = self.my_ctrl_benchm.accum_obj_val

            if not self.no_print:
                self.my_logger.print_sim_step(
                    t, xCoord, yCoord, alpha, v, omega, stage_obj, accum_obj, action
                )

            if self.is_log:
                self.my_logger.log_data_row(
                    datafile,
                    t,
                    xCoord,
                    yCoord,
                    alpha,
                    v,
                    omega,
                    stage_obj,
                    accum_obj,
                    action,
                )

            if t >= self.t1:
                if not self.no_print:
                    print(
                        ".....................................Run {run:2d} done.....................................".format(
                            run=run_curr
                        )
                    )

                run_curr += 1

                if run_curr > self.Nruns:
                    break

                if self.is_log:
                    datafile = self.datafiles[run_curr - 1]

                # Reset simulator
                self.my_simulator.status = "running"
                self.my_simulator.t = self.t0
                self.my_simulator.observation = self.state_full_init

                if self.control_mode != "nominal":
                    self.my_ctrl_benchm.reset(self.t0)
                else:
                    self.my_ctrl_nominal.reset(self.t0)

                accum_obj = 0

    def pipeline_execution(self, **kwargs):
        self.load_config(Config3WRobot)
        self.setup_env()
        self.__dict__.update(kwargs)
        self.system_initialization()
        self.state_predictor_initialization()
        self.objectives_initialization()
        self.optimizers_initialization()
        self.rl_components_initialization()
        self.controller_initialization()
        self.simulator_initialization()
        self.logger_initialization()
        if not self.no_visual and not self.save_trajectory:
            self.main_loop_visual()
        else:
            self.main_loop_raw()


def main():
    Pipeline3WRobot().pipeline_execution()


if __name__ == "__main__":
    main()