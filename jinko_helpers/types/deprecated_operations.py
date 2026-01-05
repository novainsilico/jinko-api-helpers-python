# generated from: https://api.jinko.ai/openapi.json
# timestamp: 2025-12-23T09:05:51.131341+00:00

DEPRECATED_OPERATIONS = [
    {'http_method': 'POST', 'path': '/core/v2/result_manager/calibration/iteration_summary', 'migration': 'Given a calibration project item id, retrieve a summary of each iteration, that contains the number of errors, time to completion, and scoring metrics.Deprecated: Use /v2/result_manager/calibration/{coreItemId}/snapshot/{snapshotId}/iteration_summary.\n\n'},
    {'http_method': 'POST', 'path': '/core/v2/result_manager/calibration/sorted_patients', 'migration': 'Given a calibration project item id, retrieve the best n patients sorted by the value of a score.Deprecated: Use /v2/result_manager/calibration/{coreItemId}/snapshot/{snapshotId}/sorted_patients.\n\n'},
    {'http_method': 'POST', 'path': '/core/v2/result_manager/scalars_summary', 'migration': 'Deprecated: Use /v2/result_manager/trial/{coreItemId}/snapshot/{snapshotId}/scalars/download.\n\n'},
    {'http_method': 'POST', 'path': '/core/v2/result_manager/timeseries_summary', 'migration': 'Deprecated: Use /v2/result_manager/trial/{coreItemId}/snapshot/{snapshotId}/timeseries/download.\n\n'},
    {'http_method': 'POST', 'path': '/core/v2/trial_manager/import', 'migration': 'Private: Internal use as it is WIP..\n\n'},
]

__all__ = ["DEPRECATED_OPERATIONS"]