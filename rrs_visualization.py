"""Plotly-Figuren der Routenresilienz-Demo: Risikopfad mit DP-/Schwellwert-Entscheidungspunkten,
Politik-Schwellwertband (Periode x Risikostufe), Kostenvergleich ueber die Bausteine.

Konventionen des Portfolios: Achsen `fixedrange` (Touch-Scrollen), Vorlage plotly_white, Farbcodierung
Direktroute/Abwarten/Ausweichroute konsistent (blau/gelb/gruen, wie im Plan). Plotly wird erst in den
Funktionen importiert, damit die reine Rechnung ohne Plotly testbar bleibt."""
import rrs_constants as C

LEGEND_BOTTOM = dict(orientation="h", yref="container", yanchor="bottom", y=0.0, x=0)


def _lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


# ---------------------------------------------------------------------------------------------------
# Risikopfad mit DP- gegen Schwellwert-Entscheidungspunkt (Plan Abschnitt 1/6, live fuer den Seed)
# ---------------------------------------------------------------------------------------------------
def risk_path_figure(shown, n_risk_levels):
    import plotly.graph_objects as go

    fig = go.Figure()
    xs = list(range(len(shown.path)))
    fig.add_trace(go.Scatter(
        x=xs, y=shown.path, mode="lines+markers", line=dict(color="#1c2430", width=2),
        marker=dict(size=7, color="#1c2430"), name="Risikopfad", showlegend=False,
        hovertemplate="Periode %{x}<br>Risikostufe %{y}<extra></extra>",
    ))
    dp_color = C.ACTION_COLORS[shown.dp_action]
    fig.add_trace(go.Scatter(
        x=[shown.dp_commit_n], y=[shown.k_at_commit], mode="markers",
        marker=dict(size=17, symbol="circle-open", color=dp_color, line=dict(width=3, color=dp_color)),
        name=f"DP: {C.ACTION_LABELS[shown.dp_action]}",
        hovertemplate=f"DP entscheidet in Periode {shown.dp_commit_n}: {C.ACTION_LABELS[shown.dp_action]}<extra></extra>",
    ))
    sw_color = C.ACTION_COLORS[shown.schwelle_action]
    n_last = len(shown.path) - 1
    fig.add_trace(go.Scatter(
        x=[n_last], y=[shown.k_at_n], mode="markers",
        marker=dict(size=17, symbol="diamond-open", color=sw_color, line=dict(width=3, color=sw_color)),
        name=f"Schwellwert: {C.ACTION_LABELS[shown.schwelle_action]} (immer hier)",
        hovertemplate=f"Schwellwert entscheidet immer am Ende: {C.ACTION_LABELS[shown.schwelle_action]}<extra></extra>",
    ))
    fig.update_layout(template="plotly_white", height=C.CHART_HEIGHT, margin=dict(t=30, b=45), legend=LEGEND_BOTTOM,
                      xaxis_title="Periode (Tage bis zur Weggabelung)", yaxis_title="Risikostufe")
    fig.update_yaxes(tickmode="array", tickvals=list(range(n_risk_levels)), ticktext=list(C.RISK_LABELS[:n_risk_levels]))
    fig.update_xaxes(range=[-0.4, n_last + 0.4])
    return _lock_axes(fig)


# ---------------------------------------------------------------------------------------------------
# Politik-Schwellwertband: Periode x Risikostufe, farbcodiert nach Aktion (Plan Abschnitt 6 Kernabschnitt)
# ---------------------------------------------------------------------------------------------------
def policy_grid_figure(policy, n_periods, n_risk_levels):
    import plotly.graph_objects as go

    action_order = [C.ACTION_DIRECT, C.ACTION_WAIT, C.ACTION_DETOUR]
    code = {a: i for i, a in enumerate(action_order)}
    ns = list(range(n_periods + 1))
    ks = list(range(n_risk_levels))
    z = [[code[policy[n][k]] for n in ns] for k in ks]
    text = [[C.ACTION_LABELS[policy[n][k]] for n in ns] for k in ks]
    n_cat = len(action_order)
    colorscale = []
    for i, a in enumerate(action_order):
        lo, hi = i / n_cat, (i + 1) / n_cat
        colorscale.append([lo, C.ACTION_COLORS[a]])
        colorscale.append([hi, C.ACTION_COLORS[a]])
    fig = go.Figure(go.Heatmap(
        z=z, x=ns, y=ks, text=text, colorscale=colorscale, zmin=-0.5, zmax=n_cat - 0.5, showscale=False,
        xgap=2, ygap=2, hovertemplate="Periode %{x}<br>Risikostufe %{y}<br>%{text}<extra></extra>",
    ))
    for a in action_order:
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers",
                                 marker=dict(size=11, symbol="square", color=C.ACTION_COLORS[a]),
                                 name=C.ACTION_LABELS[a]))
    fig.update_yaxes(tickmode="array", tickvals=ks, ticktext=list(C.RISK_LABELS[:n_risk_levels]))
    fig.update_layout(template="plotly_white", height=C.CHART_HEIGHT, margin=dict(t=30, b=45), legend=LEGEND_BOTTOM,
                      xaxis_title="Periode (Tage bis zur Weggabelung)", yaxis_title="Risikostufe")
    return _lock_axes(fig)


# ---------------------------------------------------------------------------------------------------
# Kostenvergleich der Bausteine, optional mit Hindsight als vierter, sekundaerer Kurve (Plan Abschnitt 8)
# ---------------------------------------------------------------------------------------------------
def cost_comparison_figure(result, show_hindsight=True):
    import plotly.graph_objects as go

    labels = [C.POLICY_LABELS[C.POLICY_DETOUR], C.POLICY_LABELS[C.POLICY_THRESHOLD], C.POLICY_LABELS[C.POLICY_DP]]
    values = [result.detour_cost, result.threshold_cost, result.dp_cost]
    colors = [C.POLICY_COLORS[C.POLICY_DETOUR], C.POLICY_COLORS[C.POLICY_THRESHOLD], C.POLICY_COLORS[C.POLICY_DP]]
    if show_hindsight:
        labels.append("🔮 Hindsight (Referenz)")
        values.append(result.hindsight_cost)
        colors.append(C.HINDSIGHT_COLOR)
    fig = go.Figure(go.Bar(
        x=labels, y=values, marker_color=colors,
        hovertemplate="%{x}<br>Kosten: %{y:.3f}<extra></extra>",
    ))
    fig.add_hline(y=result.dp_cost, line=dict(color=C.POLICY_COLORS[C.POLICY_DP], width=2, dash="dot"),
                 annotation_text="DP-Optimum", annotation_position="top left", annotation_font=dict(size=11))
    fig.update_layout(template="plotly_white", height=C.CHART_HEIGHT, margin=dict(t=30, b=45),
                      yaxis_title="Erwartete Kosten (normiert)")
    return _lock_axes(fig)
