import scipy.stats as st
import math


def sample_size_continuous_outcome(
        alpha,
        beta,
        diff_btw_groups,
        sd_outcome,
        dropout = 0):  
    """
    Calculates the sample size needed to detect a difference of diff_btw_groups in a
    continuous outcome with a given standard deviation sd_outcome, with a type I error
    rate of alpha and a type II error rate of beta. The dropout rate is assumed to be
    0 by default (in silico context).

    Parameters
    ----------
    alpha : float
        Type I error rate
    beta : float
        Type II error rate
    diff_btw_groups : float
        Difference between groups to be detected
    sd_outcome : float
        Standard deviation of the outcome
    dropout : float, optional
        Dropout rate, default is 0

    Returns
    ----------
    sample_size : float
        Required sample size for each study arm
    """
    z_alpha = st.norm.ppf(1 - (alpha / 2))
    z_beta = st.norm.ppf(1 - beta)

    return math.ceil((2 * ((z_alpha + z_beta) / (abs(diff_btw_groups) / sd_outcome)) ** 2) / (
        1 - dropout
    ))


def sample_size_binary_outcome(alpha,
                               beta,
                               prop_grp1,
                               prop_grp2,
                               dropout = 0):
    """
    Calculates the sample size needed to detect a given difference in terms of proportion
    between two groups in a binary outcome setting, with a type I error rate of alpha a
    type II error rate of beta, and expected proportions of group 1 and group 2.
    The dropout rate is assumed to be 0 by default (in silico context).
    
    Parameters
    ----------
    alpha : float
        Type I error rate
    beta : float
        Type II error rate
    prop_grp1 : float
        Proportion of events in group 1
    prop_grp2 : float
        Proportion of events in group 2

    Returns
    ----------
    sample_size : float
        Required sample size for each study arm
    """
    z_alpha = st.norm.ppf(1 - (alpha / 2))
    z_beta = st.norm.ppf(1 - beta)
    return (
        ((z_alpha + z_beta) ** 2)
        * (prop_grp1 * (1 - prop_grp1) + prop_grp2 * (1 - prop_grp2))
        / ((prop_grp1 - prop_grp2) ** 2)
    ) / (1 - dropout)

def sample_size_tte_outcome(
    alpha,
    beta,
    follow_up_duration,
    hazard_ratio,
    med_surv_time_ctrl,
    recruitment_duration=0,
    censored_proportion=0):
    """
    
    Parameters
    ----------
    alpha : float
        Type I error rate
    beta : float
        Type II error rate
    follow_up_duration : float
        Trial duration (must be in the same unit as med_surv_time_ctrl)
    hazard_ratio : float
        Expected Hazard ratio
    med_surv_time_ctrl : float
        Median survival time in the control group (must be in the same unit as follow_up_duration)
    allocation_ratio : float, optional
        Allocation ratio, default is 1:1 (same number of patients in both groups)
    recruitment_duration : float, optional
        Recruitment duration, default is 0 (in silico context)
    censored_proportion : float, optional
        Censored proportion, default is 0 (in silico context)

    Returns
    ----------
    sample_size : float
        Required sample size for each study armm
    """

    allocation_ratio = 1

    z_alpha = st.norm.ppf(1 - (alpha / 2))
    z_beta = st.norm.ppf(1 - beta)

    # HR in the control group
    lambda_control = math.log(2) / med_surv_time_ctrl

    # HR in the treatment group
    lambda_treatment = lambda_control / hazard_ratio

    # Overall event rate
    event_rate = lambda_control + allocation_ratio * lambda_treatment
    event_rate /= 1 + allocation_ratio  # Weighted average

    # Effective observation time (considering accrual and follow-up)
    total_time = recruitment_duration + follow_up_duration
    prob_event = (
        (1 - math.exp(-event_rate * follow_up_duration)) * follow_up_duration / total_time
    ) * (1 - censored_proportion)

    # Required number of events
    num_events = ((z_alpha + z_beta) ** 2 * (1 + allocation_ratio) ** 2) / (
        allocation_ratio * (math.log(hazard_ratio)) ** 2
    )

    # Sample size
    sample_size = (num_events / prob_event)/2
    return sample_size