#!/usr/bin/env python3
"""
Generate Kaplan-Meier Survival Curves for Clinical Decision Support Documents

This script creates publication-quality survival curves with:
- Kaplan-Meier survival estimates
- 95% confidence intervals
- Log-rank test statistics
- Hazard ratios with confidence intervals
- Number at risk tables
- Median survival annotations

Dependencies: lifelines, matplotlib, pandas, numpy
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from lifelines import CoxPHFitter, KaplanMeierFitter
from lifelines.statistics import logrank_test, multivariate_logrank_test


def load_survival_data(filepath, time_col='time', event_col='event', group_col='group'):
    """
    Load survival data from CSV file.

    Expected columns (names configurable via --time-col / --event-col / --group-col):
    - patient_id: Unique patient identifier (optional, not used downstream)
    - time: Survival time (months or days)
    - event: Event indicator (1=event occurred, 0=censored)
    - group: Stratification variable (e.g., 'Biomarker+', 'Biomarker-')
    - Optional: Additional covariates for Cox regression

    Returns:
        pandas.DataFrame
    """
    df = pd.read_csv(filepath)

    # Validate required columns. patient_id is deliberately NOT required: it is
    # never used downstream, yet demanding it rejected otherwise valid CSVs.
    required_cols = [time_col, event_col, group_col]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}. Present columns: {list(df.columns)}")

    # Convert event to boolean if needed
    df[event_col] = df[event_col].astype(bool)

    return df


def calculate_median_survival(kmf):
    """Median survival time with its 95% confidence interval.

    The interval is the Brookmeyer-Crowley one: its limits are the times at
    which the confidence *bands* for S(t) cross 0.5. Those limits carry the
    time unit of the x axis, which is what manuscripts report.

    Two upstream defects are corrected here:
      1. The confidence-interval column names follow the fitted label. Without
         a label they are "KM_estimate_lower_0.95" / "KM_estimate_upper_0.95",
         but passing `label=` makes lifelines rename them to
         "<label>_lower_0.95" / "<label>_upper_0.95". Hard-coding the
         "KM_estimate_*" form raised KeyError on every labelled fit.
      2. The old code read the confidence limits of the survival *probability*
         S(t) at the median (about 0.4-0.6) and reported them as the CI of the
         median *time* ("95% CI 0.4-0.6 months"), which is a different quantity
         and meaningless as a time interval.
    """
    median = kmf.median_survival_time_
    if median is None or not np.isfinite(median):
        return None, None, None

    ci = kmf.confidence_interval_survival_function_
    lower_col = next((c for c in ci.columns if "lower" in str(c)), None)
    upper_col = next((c for c in ci.columns if "upper" in str(c)), None)
    if lower_col is None or upper_col is None:
        return median, None, None

    def crossing_time(band, level=0.5):
        """First time the step band drops to or below `level`, else None."""
        hits = np.where(np.asarray(band, dtype=float) <= level)[0]
        return float(ci.index[hits[0]]) if len(hits) else None

    # The pessimistic (lower) band reaches 0.5 first -> lower time limit;
    # the optimistic (upper) band reaches it last -> upper time limit.
    lower_ci = crossing_time(ci[lower_col])
    upper_ci = crossing_time(ci[upper_col])

    return median, lower_ci, upper_ci


def generate_kaplan_meier_plot(
    data,
    time_col='time',
    event_col='event',
    group_col='group',
    output_path='survival_curve.pdf',
    title='Kaplan-Meier Survival Curve',
    xlabel='Time (months)',
    ylabel='Survival Probability',
):
    """
    Generate Kaplan-Meier survival curve comparing groups.

    Parameters:
        data: DataFrame with survival data
        time_col: Column name for survival time
        event_col: Column name for event indicator
        group_col: Column name for stratification
        output_path: Path to save figure
        title: Plot title
        xlabel: X-axis label (specify units)
        ylabel: Y-axis label
    """

    # Create figure and axis
    fig, ax = plt.subplots(figsize=(10, 6))

    # Get unique groups
    groups = data[group_col].unique()

    # Colors for groups (colorblind-friendly)
    colors = ['#0173B2', '#DE8F05', '#029E73', '#CC78BC', '#CA9161']

    kmf_models = {}
    median_survivals = {}

    # Plot each group
    for i, group in enumerate(groups):
        group_data = data[data[group_col] == group]

        # Fit Kaplan-Meier
        kmf = KaplanMeierFitter()
        kmf.fit(group_data[time_col], group_data[event_col], label=str(group))

        # Plot survival curve
        kmf.plot_survival_function(ax=ax, ci_show=True, color=colors[i % len(colors)], linewidth=2, alpha=0.8)

        # Store model
        kmf_models[group] = kmf

        # Calculate median survival
        median, lower, upper = calculate_median_survival(kmf)
        median_survivals[group] = (median, lower, upper)

    # Log-rank test
    if len(groups) == 2:
        group1_data = data[data[group_col] == groups[0]]
        group2_data = data[data[group_col] == groups[1]]

        results = logrank_test(
            group1_data[time_col], group2_data[time_col], group1_data[event_col], group2_data[event_col]
        )

        p_value = results.p_value
        test_statistic = results.test_statistic

        # Add log-rank test result to plot
        ax.text(
            0.02,
            0.97,
            f'Log-rank test:\np = {p_value:.4f}',
            transform=ax.transAxes,
            fontsize=10,
            verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
        )
    else:
        # Multivariate log-rank for >2 groups
        results = multivariate_logrank_test(data[time_col], data[group_col], data[event_col])
        p_value = results.p_value
        test_statistic = results.test_statistic

        ax.text(
            0.02,
            0.97,
            f'Log-rank test:\np = {p_value:.4f}\n({len(groups)} groups)',
            transform=ax.transAxes,
            fontsize=10,
            verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
        )

    # Add median survival annotations
    y_pos = 0.95
    for group, (median, lower, upper) in median_survivals.items():
        if median is not None and lower is not None and upper is not None:
            ax.text(
                0.98,
                y_pos,
                f'{group}: {median:.1f} months (95% CI {lower:.1f}-{upper:.1f})',
                transform=ax.transAxes,
                fontsize=9,
                ha='right',
                verticalalignment='top',
            )
        else:
            ax.text(
                0.98,
                y_pos,
                f'{group}: Not reached',
                transform=ax.transAxes,
                fontsize=9,
                ha='right',
                verticalalignment='top',
            )
        y_pos -= 0.05

    # Formatting
    ax.set_xlabel(xlabel, fontsize=12, fontweight='bold')
    ax.set_ylabel(ylabel, fontsize=12, fontweight='bold')
    ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
    ax.legend(loc='lower left', frameon=True, fontsize=10)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_ylim([0, 1.05])

    plt.tight_layout()

    # Save figure
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Survival curve saved to: {output_path}")

    # Also save as PNG for easy viewing
    png_path = Path(output_path).with_suffix('.png')
    plt.savefig(png_path, dpi=300, bbox_inches='tight')
    print(f"PNG version saved to: {png_path}")

    plt.close()

    return kmf_models, p_value


def generate_number_at_risk_table(data, time_col='time', event_col='event', group_col='group', time_points=None):
    """
    Generate number at risk table for survival analysis.

    Parameters:
        data: DataFrame with survival data
        time_points: List of time points for risk table (if None, auto-generate)

    Returns:
        DataFrame with number at risk at each time point
    """

    if time_points is None:
        # Auto-generate time points (every 6 months up to max time)
        max_time = data[time_col].max()
        time_points = np.arange(0, max_time + 6, 6)

    groups = data[group_col].unique()
    risk_table = pd.DataFrame(index=time_points, columns=groups)

    for group in groups:
        group_data = data[data[group_col] == group]

        for t in time_points:
            # Number at risk = patients who haven't had event and haven't been censored before time t
            at_risk = len(group_data[group_data[time_col] >= t])
            risk_table.loc[t, group] = at_risk

    return risk_table


def calculate_hazard_ratio(data, time_col='time', event_col='event', group_col='group', reference_group=None):
    """
    Calculate hazard ratio using Cox proportional hazards regression.

    Parameters:
        data: DataFrame
        reference_group: Reference group for comparison (if None, uses first group)

    Returns:
        Hazard ratio, 95% CI, p-value
    """

    # Encode group as binary for Cox regression
    groups = data[group_col].unique()
    if len(groups) != 2:
        print("Warning: Cox HR calculation assumes 2 groups. Using first 2 groups.")
        groups = groups[:2]

    if reference_group is None:
        reference_group = groups[0]

    # Create binary indicator (1 for comparison group, 0 for reference)
    data_cox = data.copy()
    data_cox['group_binary'] = (data_cox[group_col] != reference_group).astype(int)

    # Fit Cox model
    cph = CoxPHFitter()
    cph.fit(data_cox[[time_col, event_col, 'group_binary']], duration_col=time_col, event_col=event_col)

    # Extract results
    hr = np.exp(cph.params_['group_binary'])
    ci = np.exp(cph.confidence_intervals_.loc['group_binary'].values)
    p_value = cph.summary.loc['group_binary', 'p']

    return hr, ci[0], ci[1], p_value


def generate_report(data, output_dir, prefix='survival',
                    title='Survival Analysis by Group',
                    xlabel='Time (months)', ylabel='Survival Probability',
                    time_col='time', event_col='event', group_col='group'):
    """
    Generate comprehensive survival analysis report.

    Creates:
    - Kaplan-Meier curves (PDF and PNG)
    - Number at risk table (CSV)
    - Statistical summary (TXT)
    - LaTeX table code (TEX)

    All plotting labels and column names are forwarded so the CLI flags
    (-t/-x/-y/--time-col/--event-col/--group-col) actually take effect; the
    original version hard-coded them and silently ignored every flag.
    """

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate survival curve
    kmf_models, logrank_p = generate_kaplan_meier_plot(
        data,
        time_col=time_col,
        event_col=event_col,
        group_col=group_col,
        output_path=output_dir / f'{prefix}_kaplan_meier.pdf',
        title=title,
        xlabel=xlabel,
        ylabel=ylabel,
    )

    # Number at risk table
    risk_table = generate_number_at_risk_table(
        data, time_col=time_col, event_col=event_col, group_col=group_col
    )
    risk_table.to_csv(output_dir / f'{prefix}_number_at_risk.csv')

    # Calculate hazard ratio
    hr, ci_lower, ci_upper, hr_p = calculate_hazard_ratio(
        data, time_col=time_col, event_col=event_col, group_col=group_col
    )

    # Generate statistical summary
    with open(output_dir / f'{prefix}_statistics.txt', 'w') as f:
        f.write("SURVIVAL ANALYSIS STATISTICAL SUMMARY\n")
        f.write("=" * 60 + "\n\n")

        groups = data[group_col].unique()
        for group in groups:
            kmf = kmf_models[group]
            median = kmf.median_survival_time_

            # Calculate survival rates at common time points
            try:
                surv_12m = kmf.survival_function_at_times(12).values[0]
                surv_24m = kmf.survival_function_at_times(24).values[0] if data[time_col].max() >= 24 else None
            except:
                surv_12m = None
                surv_24m = None

            f.write(f"Group: {group}\n")
            f.write(f"  N = {len(data[data[group_col] == group])}\n")
            f.write(f"  Events = {data[data[group_col] == group][event_col].sum()}\n")
            f.write(
                f"  Median survival: {median:.1f} months\n" if median != np.inf else "  Median survival: Not reached\n"
            )
            if surv_12m is not None:
                f.write(f"  12-month survival rate: {surv_12m * 100:.1f}%\n")
            if surv_24m is not None:
                f.write(f"  24-month survival rate: {surv_24m * 100:.1f}%\n")
            f.write("\n")

        f.write("Log-Rank Test:\n")
        f.write(f"  p-value = {logrank_p:.4f}\n")
        f.write(
            f"  Interpretation: {'Significant' if logrank_p < 0.05 else 'Not significant'} difference in survival\n\n"
        )

        if len(groups) == 2:
            f.write(f"Hazard Ratio ({groups[1]} vs {groups[0]}):\n")
            f.write(f"  HR = {hr:.2f} (95% CI {ci_lower:.2f}-{ci_upper:.2f})\n")
            f.write(f"  p-value = {hr_p:.4f}\n")
            # Effect size must be signed correctly: HR > 1 means MORE risk,
            # HR < 1 means LESS risk. The previous expression (1 - hr) yielded
            # "-48% increase in risk" for HR = 1.48.
            if hr < 1:
                _effect = f"{(1 - hr) * 100:.0f}% reduction in risk"
            else:
                _effect = f"{(hr - 1) * 100:.0f}% increase in risk"
            f.write(f"  Interpretation: {groups[1]} has {_effect}\n")

    # Generate LaTeX table code
    with open(output_dir / f'{prefix}_latex_table.tex', 'w') as f:
        f.write("% LaTeX table code for survival outcomes\n")
        f.write("\\begin{table}[H]\n")
        f.write("\\centering\n")
        f.write("\\small\n")
        f.write("\\begin{tabular}{lcccc}\n")
        f.write("\\toprule\n")
        f.write(
            "\\textbf{Endpoint} & \\textbf{Group A} & \\textbf{Group B} & \\textbf{HR (95\\% CI)} & \\textbf{p-value} \\\\\n"
        )
        f.write("\\midrule\n")

        # Add median survival row
        for i, group in enumerate(groups):
            kmf = kmf_models[group]
            median = kmf.median_survival_time_
            if i == 0:
                f.write("Median survival, months (95\\% CI) & ")
                if median != np.inf:
                    f.write(f"{median:.1f} & ")
                else:
                    f.write("NR & ")
            else:
                if median != np.inf:
                    f.write(f"{median:.1f} & ")
                else:
                    f.write("NR & ")

        f.write(f"{hr:.2f} ({ci_lower:.2f}-{ci_upper:.2f}) & {hr_p:.3f} \\\\\n")

        # Add 12-month survival rate
        f.write("12-month survival rate (\\%) & ")
        for group in groups:
            kmf = kmf_models[group]
            try:
                surv_12m = kmf.survival_function_at_times(12).values[0]
                f.write(f"{surv_12m * 100:.0f}\\% & ")
            except:
                f.write("-- & ")
        f.write("-- & -- \\\\\n")

        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")
        f.write(f"\\caption{{Survival outcomes by group (log-rank p={logrank_p:.3f})}}\n")
        f.write("\\end{table}\n")

    print(f"\nAnalysis complete! Files saved to {output_dir}/")
    print(f"  - Survival curves: {prefix}_kaplan_meier.pdf/png")
    print(f"  - Statistics: {prefix}_statistics.txt")
    print(f"  - LaTeX table: {prefix}_latex_table.tex")
    print(f"  - Risk table: {prefix}_number_at_risk.csv")


def main():
    parser = argparse.ArgumentParser(description='Generate Kaplan-Meier survival curves')
    parser.add_argument('input_file', type=str, help='CSV file with survival data')
    parser.add_argument(
        '-o', '--output', type=str, default='survival_output', help='Output directory (default: survival_output)'
    )
    parser.add_argument('-t', '--title', type=str, default='Kaplan-Meier Survival Curve', help='Plot title')
    parser.add_argument('-x', '--xlabel', type=str, default='Time (months)', help='X-axis label')
    parser.add_argument('-y', '--ylabel', type=str, default='Survival Probability', help='Y-axis label')
    parser.add_argument('--time-col', type=str, default='time', help='Column name for time variable')
    parser.add_argument('--event-col', type=str, default='event', help='Column name for event indicator')
    parser.add_argument('--group-col', type=str, default='group', help='Column name for grouping variable')

    args = parser.parse_args()

    # Load data
    print(f"Loading data from {args.input_file}...")
    data = load_survival_data(
        args.input_file,
        time_col=args.time_col,
        event_col=args.event_col,
        group_col=args.group_col,
    )
    print(f"Loaded {len(data)} patients")
    print(f"Groups: {data[args.group_col].value_counts().to_dict()}")

    # Generate analysis
    generate_report(
        data,
        output_dir=args.output,
        prefix='survival',
        title=args.title,
        xlabel=args.xlabel,
        ylabel=args.ylabel,
        time_col=args.time_col,
        event_col=args.event_col,
        group_col=args.group_col,
    )


if __name__ == '__main__':
    main()


# Example usage:
# python generate_survival_analysis.py survival_data.csv -o figures/ -t "PFS by PD-L1 Status"
#
# Input CSV format:
# patient_id,time,event,group
# PT001,12.3,1,PD-L1+
# PT002,8.5,1,PD-L1-
# PT003,18.2,0,PD-L1+
# ...
