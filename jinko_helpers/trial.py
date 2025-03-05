import jinko_helpers as jinko
from math import ceil
import requests
import time
import pandas as pd
from tqdm import tqdm


def is_trial_completed(trial_core_id) -> bool | None:
    """
    Checks if the trial is running.

    Args:
        trial_core_id (CoreItemId): The CoreItemId of the trial.

    Returns:
        bool: True if the trial is running, False otherwise.
        None: If an HTTP error occurs during the request.
    """
    try:
        response = jinko.makeRequest(
            path=f"/core/v2/trial_manager/trial/{trial_core_id['id']}/snapshots/{trial_core_id['snapshotId']}/status",
            method="GET",
        )
        response_json = response.json()
        return response_json["status"] == "completed"
    except requests.exceptions.HTTPError:
        return None


def is_trial_running(trial_core_item_id, trial_snapshot_id):
    """
    Checks if the trial is running.

    Args:
        trial_core_item_id (str): The CoreItemId of the trial.
        trial_snapshot_id (str): The snapshot ID of the trial.

    Returns:
        bool: True if the trial is running, False otherwise.
    """
    response = jinko.makeRequest(
        path=f"/core/v2/trial_manager/trial/{trial_core_item_id}/snapshots/{trial_snapshot_id}/status"
    )
    response_json = response.json()
    return response_json["isRunning"]


def monitor_trial_until_completion(
    trial_core_item_id, trial_snapshot_id, time_to_completion=None, retry_interval=5
):
    """
    Polls the Jinko API for the status of a trial and prints a progress view with completed task counts.

    Args:
        trial_core_item_id (str): The CoreItemId of the trial.
        trial_snapshot_id (str): The snapshot ID of the trial.
        time_to_completion (int, optional): Maximum time to monitor the trial in seconds. If not provided, monitors indefinitely.
        retry_interval (int, optional): Interval in seconds between retries. Default is 5 seconds.

    Returns:
        pd.DataFrame: A DataFrame summarizing the perArm data.

    Raises:
        RuntimeError: If no 'perArmSummary' data is found in the response or if the trial does not complete in the specified time.
    """
    pbar = tqdm(total=0, desc="Trial Progress", unit="tasks")  # Initialize with 0 total

    if time_to_completion is not None:
        max_retries = ceil(time_to_completion / retry_interval)
    else:
        max_retries = None  # Loop indefinitely

    retries = 0

    while max_retries is None or retries < max_retries:
        response = jinko.makeRequest(
            path=f"/core/v2/trial_manager/trial/{trial_core_item_id}/snapshots/{trial_snapshot_id}/status"
        )
        response_json = response.json()
        per_arm_data = response_json.get("perArmSummary", {})

        # Check if the job is still running
        if response_json.get("isRunning", False):
            tasks_count = get_task_count(per_arm_data)

            # Set the progress bar's total to the latest total task count
            pbar.total = tasks_count["total_tasks"]
            pbar.n = tasks_count["completed_tasks"]
            pbar.refresh()

            time.sleep(retry_interval)  # Wait before checking again
            retries += 1
        else:
            print("Job succeeded.")
            pbar.total = get_task_count(per_arm_data)["total_tasks"]
            pbar.n = pbar.total
            pbar.refresh()
            pbar.close()
            break
    else:
        raise RuntimeError(
            "Trial did not complete within the specified time. Please rerun to continue monitoring the job."
        )

    try:
        per_arm_summary = pd.DataFrame.from_dict(per_arm_data, orient="index")
        per_arm_summary.reset_index(inplace=True)
        per_arm_summary.rename(columns={"index": "Arm"}, inplace=True)
        return per_arm_summary
    except (ValueError, KeyError) as e:
        raise RuntimeError("No 'perArmSummary' data found in the response.") from e


def get_task_count(per_arm_data: dict):
    """
    Calculates the total and completed task counts from the given per-arm data.

    Args:
        per_arm_data (dict): A dictionary where each key is an arm identifier, and
                             its value is another dictionary containing counts of tasks
                             with keys 'countPending', 'countError', and 'countSuccess'.

    Returns:
        dict: A dictionary containing 'total_tasks' which is the sum of pending, error,
              and success counts, and 'completed_tasks' which is the sum of error and success counts.
    """
    total_pending = 0
    total_error = 0
    total_success = 0

    # Loop through all arms in perArmData
    for _, arm_data in per_arm_data.items():
        total_pending += arm_data.get("countPending", 0)
        total_error += arm_data.get("countError", 0)
        total_success += arm_data.get("countSuccess", 0)

    total_tasks = total_pending + total_error + total_success
    completed_tasks = total_success + total_error

    return {"total_tasks": total_tasks, "completed_tasks": completed_tasks}
