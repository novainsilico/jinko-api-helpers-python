"""Module containing the "vpop runner/optimizer" utilities of crabbit."""

__all__ = ["CrabbitVpopRunner", "CrabbitVpopOptimizer"]

import os
import json
import requests
import datetime
import uuid
import yaml
import numpy as np
import pandas as pd
import cma
import matplotlib.pyplot as plt
import seaborn as sns
import shutil

import jinko_helpers as jinko
from crabbit.merge import merge_vpop_designs, merge_vpops
from crabbit.utils import bold_text, check_project_item_url, clear_directory
import crabbit.download as download


class CrabbitVpopRunner:
    def __init__(self, config_path, local_parent_folder):
        self.config_path = os.path.abspath(os.path.expanduser(config_path))
        self.local_parent_folder = os.path.abspath(
            os.path.expanduser(local_parent_folder)
        )
        self.is_prepared = self._prepare()

    def _prepare(self):
        with open(self.config_path, "r", encoding="utf-8") as config:
            try:
                config_dic = yaml.safe_load(config)
            except yaml.YAMLError:
                print(bold_text("Error:"), "invalid yaml")
                return False

        if config_dic is None or "data" not in config_dic:
            print(bold_text("Error:"), "invalid yaml")
            return False
        try:
            self.parent_folder = config_dic["data"]["parent_folder"]
            self.trial_configs = {}
            for item_type, item_url in config_dic["data"]["trial"].items():
                item = check_project_item_url(item_url)
                if item is not None:
                    self.trial_configs[item_type] = item["coreId"]
            if "computational_model" not in self.trial_configs:
                print(bold_text("Error:"), "invalid yaml (missing computational_model)")
                return False
            self.vpop_size = int(config_dic["data"]["vpop_size"])
            self.vpop_seed = (
                int(config_dic["data"]["vpop_seed"])
                if "vpop_seed" in config_dic["data"]
                else 42
            )
            self.design_parts = list(map(str, config_dic["data"]["vpop_design_parts"]))
            default_name_prefix = (
                datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
                + "_"
                + str(uuid.uuid4())
            )
            self.name_prefix = (
                str(config_dic["data"]["vpop_name"])
                if "vpop_name" in config_dic["data"]
                else default_name_prefix
            )
            self.qoi_path = (
                os.path.abspath(os.path.expanduser(config_dic["data"]["qoi_list"]))
                if "qoi_list" in config_dic["data"]
                else ""
            )
        except (KeyError, ValueError, TypeError, AttributeError):
            print(bold_text("Error:"), "invalid yaml")
            return False
        base_design = merge_vpop_designs(self.design_parts)
        if base_design is None:
            print(bold_text("Error:"), "failed to build the vpop design")
            return False
        self.designs = {self.name_prefix: base_design}
        self.vpop_names = []
        return True

    def _refresh_vpops(self, iteration_index=-1):
        self.design_ids = {}
        self.vpop_ids = {}
        self.patient_ids = {}
        self.local_folders = {}
        if iteration_index >= 0:
            special_name = f"{self.name_prefix}_Iteration_{iteration_index}"
            local_folder = os.path.join(self.local_parent_folder, special_name)
            self.local_folders[special_name] = local_folder
            clear_directory(local_folder, force=True)
        for vpop_name in self.vpop_names:
            if iteration_index < 0:
                local_folder = os.path.join(self.local_parent_folder, vpop_name)
            else:
                local_folder = os.path.join(
                    self.local_parent_folder,
                    f"{self.name_prefix}_Iteration_{iteration_index}",
                    vpop_name,
                )
            self.local_folders[vpop_name] = local_folder
            clear_directory(local_folder, force=True)

    def _post_designs(self):
        for vpop_name, vpop_design in self.designs.items():
            json.dump(
                vpop_design,
                open(
                    os.path.join(self.local_folders[vpop_name], "VpopDesign.json"), "w"
                ),
                indent=4,
            )
            try:
                response = jinko.make_request(
                    method="POST",
                    path=f"/core/v2/vpop_manager/vpop_generator",
                    json={"contents": vpop_design, "tag": "VpopGeneratorFromDesign"},
                    options={
                        "folder_id": self.parent_folder,
                        "name": f"{vpop_name} - vpop design",
                    },
                )
                design_id = jinko.get_project_item_info_from_response(response)[
                    "coreItemId"
                ]
                self.design_ids[vpop_name] = design_id
            except requests.exceptions.HTTPError:
                self.design_ids[vpop_name] = {}

    def _generate_vpops(self):
        for k, (vpop_name, design_id) in enumerate(self.design_ids.items()):
            if not design_id:
                continue
            payload = {
                "contents": {
                    "seed": self.vpop_seed + k,
                    "size": self.vpop_size,
                },
                "tag": "VpopGeneratorOptionsForVpopDesign",
            }
            try:
                response = jinko.make_request(
                    method="POST",
                    path=f"/core/v2/vpop_manager/vpop_generator/{design_id['id']}/snapshots/{design_id['snapshotId']}/vpop",
                    json=payload,
                    options={
                        "folder_id": self.parent_folder,
                        "name": f"{vpop_name} - vpop",
                    },
                )
                vpop_id = jinko.get_project_item_info_from_response(response)[
                    "coreItemId"
                ]
                vpop_url = jinko.get_project_item_url_by_core_item_id(vpop_id["id"])
                vpop_id["URL"] = vpop_url
                patients = jinko.make_request(
                    method="GET", path=f"/core/v2/vpop_manager/vpop/{vpop_id['id']}"
                ).json()["patients"]
                json.dump(
                    {"patients": patients},
                    open(
                        os.path.join(self.local_folders[vpop_name], "Patients.json"),
                        "w",
                    ),
                )
                self.vpop_ids[vpop_name] = vpop_id
                self.patient_ids[vpop_name] = [p["patientIndex"] for p in patients]
            except requests.exceptions.HTTPError:
                self.vpop_ids[vpop_name] = {}

    def _post_merged_vpop(self):
        merged_patients = merge_vpops(
            [vpop_id["URL"] for vpop_id in self.vpop_ids.values()]
        )
        response = jinko.make_request(
            method="POST",
            path="/core/v2/vpop_manager/vpop",
            json=merged_patients,
            options={
                "folder_id": self.parent_folder,
                "name": f"{self.name_prefix} - merged vpop",
            },
        )
        vpop_id = jinko.get_project_item_info_from_response(response)["coreItemId"]
        return vpop_id

    def _post_one_vpop_trial(self, vpop_name, vpop_id):
        if not vpop_id:
            return {}
        payload = {
            "computationalModelId": {
                "coreItemId": self.trial_configs["computational_model"]["id"],
                "snapshotId": self.trial_configs["computational_model"]["snapshotId"],
            },
            "vpopId": {
                "coreItemId": vpop_id["id"],
                "snapshotId": vpop_id["snapshotId"],
            },
        }
        if "protocol" in self.trial_configs:
            payload["protocolDesignId"] = {
                "coreItemId": self.trial_configs["protocol"]["id"],
                "snapshotId": self.trial_configs["protocol"]["snapshotId"],
            }
        if "output_set" in self.trial_configs:
            payload["measureDesignId"] = {
                "coreItemId": self.trial_configs["output_set"]["id"],
                "snapshotId": self.trial_configs["output_set"]["snapshotId"],
            }
        if "advanced_output_set" in self.trial_configs:
            payload["scoringDesignId"] = {
                "coreItemId": self.trial_configs["advanced_output_set"]["id"],
                "snapshotId": self.trial_configs["advanced_output_set"]["snapshotId"],
            }
        try:
            response = jinko.make_request(
                method="POST",
                path="/core/v2/trial_manager/trial",
                json=payload,
                options={
                    "folder_id": self.parent_folder,
                    "name": f"{vpop_name} - trial",
                },
            )
            trial_id = jinko.get_project_item_info_from_response(response)["coreItemId"]
            trial_url = jinko.get_project_item_url_by_core_item_id(trial_id["id"])
            trial_id["URL"] = trial_url
        except requests.exceptions.HTTPError:
            trial_id = {}
        payload["trial_id"] = trial_id
        json.dump(
            payload,
            open(
                os.path.join(self.local_folders[vpop_name], "saved_trial_info.json"),
                "w",
            ),
            indent=4,
        )
        return trial_id

    def _run_one_vpop(self, vpop_name, vpop_id):
        trial_id = self._post_one_vpop_trial(vpop_name, vpop_id)
        if trial_id:
            print("Trial started:", trial_id["URL"])
            try:
                jinko.make_request(
                    path=f"/core/v2/trial_manager/trial/{trial_id['id']}/snapshots/{trial_id['snapshotId']}/run",
                    method="POST",
                )
                jinko.monitor_trial_until_completion(
                    trial_id["id"], trial_id["snapshotId"]
                )
            except (requests.exceptions.ConnectionError, requests.exceptions.HTTPErro):
                print(bold_text("Error:"), "connection lost")
        return trial_id

    def download_trial_results(self, vpop_folder, trial_id):
        if not self.qoi_path or not trial_id:
            return
        item = {"coreId": trial_id, "type": "Trial"}
        retries = 0
        downloader = download.CrabbitDownloader(item, vpop_folder, self.qoi_path, False)
        while retries < 5:
            try:
                downloader.run()
                return
            except (requests.exceptions.ConnectionError, requests.exceptions.ChunkedEncodingError):
                retries += 1

    def _split_merged_results(self, merged_vpop_name):
        results = pd.read_csv(
            os.path.join(self.local_folders[merged_vpop_name], "scalars.csv")
        )
        for vpop_name, vpop_patients in self.patient_ids.items():
            sub_results = results.loc[results["patientId"].isin(vpop_patients)]
            sub_results.to_csv(
                os.path.join(self.local_folders[vpop_name], "scalars.csv"), index=False
            )
        print(bold_text("Done!"), "Finished splitting trial results to each vpop")

    def run(self):
        """Run one single vpop"""
        if not self.is_prepared:
            return
        self.vpop_names = [self.name_prefix]
        self._refresh_vpops()
        self._post_designs()
        self._generate_vpops()

        saves = list(map(str, self.local_folders.values()))
        json.dump(
            saves,
            open(os.path.join(self.local_parent_folder, ".SAVE.json"), "w"),
            indent=4,
        )

        vpop_name, vpop_id = list(self.vpop_ids.items()).pop()
        trial_id = self._run_one_vpop(vpop_name, vpop_id)

        self.download_trial_results(self.local_folders[vpop_name], trial_id)
        return saves

    def run_one_iteration(self, iteration_index, calib_func, calib_param_values):
        """Run several vpops as a part of the iterative optimization"""
        self.vpop_names = []
        self.designs = {}
        nb_vpops = len(calib_param_values)
        for i in range(nb_vpops):
            vpop_name = f"{self.name_prefix}_Iteration_{iteration_index}_Vpop_{i+1}"
            self.vpop_names.append(vpop_name)
        self._refresh_vpops(iteration_index)

        for vpop_name, vpop_calib_values in zip(self.vpop_names, calib_param_values):
            try:
                design, design_name = calib_func(vpop_calib_values)
            except ValueError:
                print(bold_text("Error:"), "calib_func not valid")
                return
            calib_design_path = os.path.join(self.local_folders[vpop_name], design_name)
            json.dump(design, open(calib_design_path, "w"), indent=4)

            merged_calib_design = merge_vpop_designs(
                self.design_parts + [calib_design_path]
            )
            if merged_calib_design is None:
                print(bold_text("Error:"), "failed to build the vpop design")
                return
            self.designs[vpop_name] = merged_calib_design

        self._post_designs()
        self._generate_vpops()
        vpop_id = self._post_merged_vpop()
        special_name = f"{self.name_prefix}_Iteration_{iteration_index}"

        saves = list(
            map(str, [self.local_folders[vpop_name] for vpop_name in self.vpop_names])
        )
        json.dump(
            saves,
            open(os.path.join(self.local_parent_folder, ".SAVE.json"), "w"),
            indent=4,
        )

        trial_id = self._run_one_vpop(special_name, vpop_id)
        self.download_trial_results(self.local_folders[special_name], trial_id)
        self._split_merged_results(special_name)

        return saves


class CrabbitVpopOptimizer:
    def __init__(
        self,
        config_path,
        local_parent_folder,
        init_mean,
        scaling_stds,
        init_step_size,
        seed,
        popsize,
        maxiter,
        calib_func,
        scoring_func,
    ):
        self.runner = CrabbitVpopRunner(config_path, local_parent_folder)
        self.calib_func = calib_func
        self.scoring_func = scoring_func
        self.es = cma.CMAEvolutionStrategy(
            init_mean,
            init_step_size,
            {
                "CMA_stds": scaling_stds,
                "seed": seed,
                "popsize": popsize,
                "maxiter": maxiter,
            },
        )
        self.simple_log = []
        self.log_path = os.path.join(self.runner.local_parent_folder, "log.json")

    def run(self):
        if not self.runner.is_prepared:
            return
        iteration = 0
        best_score = float("Inf")
        best_vpop = ""
        all_iteration_scores = []
        while not self.es.stop():
            candidates = self.es.ask()
            vpops = self.runner.run_one_iteration(
                iteration, self.calib_func, candidates
            )
            scores = self.scoring_func(vpops)
            self.es.tell(candidates, scores)

            scores = list(map(float, scores))
            self.simple_log.append(
                {
                    "iteration": iteration,
                    "vpops": list(map(str, vpops)),
                    "params": [list(map(float, values)) for values in candidates],
                    "scores": scores,
                }
            )
            current_best_score = np.nanmin(scores)
            if current_best_score < best_score:
                best_score = current_best_score
                best_vpop = vpops[scores.index(best_score)]
            all_iteration_scores.append([iteration, best_score])

            iteration += 1
            json.dump(self.simple_log, open(self.log_path, "w"), indent=4)

        best_folder = os.path.join(
            self.runner.local_parent_folder, f"{self.runner.name_prefix}_BEST"
        )
        shutil.copytree(best_vpop, best_folder, dirs_exist_ok=True)
        json.dump(
            self.simple_log, open(os.path.join(best_folder, "log.json"), "w"), indent=4
        )

        all_iteration_scores = pd.DataFrame(
            all_iteration_scores, columns=["Iteration", "Score"]
        )
        fig = plt.figure(figsize=(9, 6), layout="tight")
        ax = fig.add_subplot()
        sns.lineplot(
            ax=ax,
            data=all_iteration_scores,
            x="Iteration",
            y="Score",
            errorbar=None,
            estimator=None,
            n_boot=0,
        )
        plt.savefig(os.path.join(best_folder, "score-evolution.png"))
        print(bold_text("Done!"), "Results saved to:", best_folder)
