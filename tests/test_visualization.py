"""Figuren: Risikopfad, Politik-Schwellwertband, Kostenvergleich - alle Achsen fest (fixedrange)."""
import rrs_evaluation as E
import rrs_visualization as V


def _scenario():
    params = E.params_from_controls("mittel", "normal", 2, 40, 10)
    result = E.evaluate(params)
    shown = E.evaluate_shown_path(params, 5, result)
    return params, result, shown


def test_risk_path_figure_has_fixed_axes():
    params, result, shown = _scenario()
    fig = V.risk_path_figure(shown, params.n_risk_levels)
    assert fig.layout.xaxis.fixedrange is True
    assert fig.layout.yaxis.fixedrange is True


def test_risk_path_figure_plots_the_full_path():
    params, result, shown = _scenario()
    fig = V.risk_path_figure(shown, params.n_risk_levels)
    path_trace = fig.data[0]
    assert list(path_trace.y) == shown.path


def test_policy_grid_figure_has_fixed_axes_and_covers_all_periods_and_levels():
    params, result, shown = _scenario()
    fig = V.policy_grid_figure(result.policy, params.n_periods, params.n_risk_levels)
    assert fig.layout.xaxis.fixedrange is True
    assert fig.layout.yaxis.fixedrange is True
    heatmap = fig.data[0]
    assert len(heatmap.x) == params.n_periods + 1
    assert len(heatmap.y) == params.n_risk_levels


def test_policy_grid_figure_encodes_every_action_as_a_distinct_code():
    params, result, shown = _scenario()
    fig = V.policy_grid_figure(result.policy, params.n_periods, params.n_risk_levels)
    heatmap = fig.data[0]
    codes = {z for row in heatmap.z for z in row}
    assert codes.issubset({0, 1, 2})


def test_cost_comparison_figure_has_fixed_axes():
    params, result, shown = _scenario()
    fig = V.cost_comparison_figure(result, show_hindsight=True)
    assert fig.layout.xaxis.fixedrange is True
    assert fig.layout.yaxis.fixedrange is True


def test_cost_comparison_figure_includes_hindsight_bar_only_when_requested():
    params, result, shown = _scenario()
    with_hs = V.cost_comparison_figure(result, show_hindsight=True)
    without_hs = V.cost_comparison_figure(result, show_hindsight=False)
    assert len(with_hs.data[0].x) == 4
    assert len(without_hs.data[0].x) == 3
