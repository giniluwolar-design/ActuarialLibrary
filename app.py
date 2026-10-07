"""Run with: python -m streamlit run app.py"""

import hashlib
import io
import json
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import polars as pl
import streamlit as st

from actuarial_library import (
    AnalysisConfig,
    build_triangles,
    export_google_sheets_package,
    export_results,
    run_reserving,
    validate_claims,
)
from actuarial_library.agent import AnalystSession, local_models
from actuarial_library.data import GROUP, REQUIRED, dates
from actuarial_library.demo import generate_demo
from actuarial_library.exploration import claim_diagnostics, factor_triangle
from actuarial_library.export import safe_csv
from actuarial_library.models import DevelopmentConfig, FrequencySeverityConfig
from actuarial_library.reserving import METHODS, development
from actuarial_library.review import method_impact, observation_pairs

st.set_page_config(page_title="Actuarial Library · Reserving", page_icon="◩", layout="wide")
st.markdown(
    """<style>
:root{--ink:#142c3b;--accent:#087f8c}
.block-container{max-width:1800px;padding:3.6rem 1.6rem 4rem}
h1{letter-spacing:-.045em!important;font-size:2.8rem!important;color:var(--ink)}
h2,h3{color:var(--ink)}
[data-testid="stAppViewContainer"]{background:linear-gradient(140deg,#f3fafb 0%,#fff 45%,#f6f5ff 100%)}
[data-testid="stSidebar"]{background:#eaf2f5;border-right:1px solid #d3e0e6}
[data-testid="stMetric"]{background:white;border:1px solid #d6e4e9;border-radius:16px;padding:18px;box-shadow:0 4px 18px #17374c06}
[data-testid="stMetricLabel"]{color:#415565}
button[data-baseweb="tab"]{font-size:1rem;padding:14px 18px}
button[data-baseweb="tab"][aria-selected="true"]{color:#087f8c!important;font-weight:700}
[data-testid="stExpander"]{background:#ffffffb8;border-radius:12px}
[data-testid="stBaseButton-primary"]{background:#087f8c;border-color:#087f8c;border-radius:10px;min-height:44px}
button:focus-visible,input:focus-visible{outline:3px solid #8154c9!important;outline-offset:3px}
.hero-note{font-size:1.1rem;color:#415565;max-width:850px;line-height:1.6}
.reserve-hero{background:linear-gradient(115deg,#103a45,#096c72 68%,#148c87);border-radius:24px;padding:30px 34px;margin-bottom:24px;color:white;box-shadow:0 12px 40px #103a4518}
.reserve-hero h1{color:white!important;margin:5px 0!important;font-size:2.7rem!important}
.reserve-hero p{color:#d4eeec;margin:4px 0;font-size:1.05rem}
.reserve-eyebrow{letter-spacing:.15em;font-size:.72rem;font-weight:700;color:#a9eee0}
.assistant-intro{background:#ecf8f3;border:1px solid #b8dfd2;border-radius:18px;padding:20px;margin-bottom:12px}
.assistant-intro h3{margin:0;color:#16564f;font-size:1.35rem}
.assistant-intro p{color:#35564f;font-size:.95rem;margin:8px 0 0}
</style>""",
    unsafe_allow_html=True,
)
st.markdown(
    """<div class="reserve-hero"><div class="reserve-eyebrow">ACTUARIAL LIBRARY · RESERVING WORKSPACE</div>
<h1>Your next reserve starts here.</h1><p>Load claims. Explore development. Calculate ultimate.</p>
<p>Your local AI analyst can guide you, run a scenario and prepare your review.</p></div>""",
    unsafe_allow_html=True,
)


@st.cache_data
def demo_data():
    root = Path(__file__).parent / "data" / "demo"
    if (root / "claims.parquet").exists():
        return pl.read_parquet(root / "claims.parquet"), pl.read_csv(
            root / "coverage.csv", try_parse_dates=True
        )
    d, c, _ = generate_demo()
    return d, c


@st.cache_data
def prepare(d, c, valuation, portfolio, currency, basis, grain):
    return build_triangles(
        d, c, valuation=valuation, portfolio=portfolio, currency=currency, amount_basis=basis, grain=grain
    )


def read_upload(file):
    return (
        pl.read_parquet(io.BytesIO(file.getvalue()))
        if file.name.endswith(".parquet")
        else pl.read_csv(io.BytesIO(file.getvalue()), infer_schema=False)
    )


def nullable_map(frame, key, value):
    return {str(r[key]): float(r[value]) for _, r in frame.iterrows() if pd.notna(r[value])}


with st.sidebar:
    st.header("Analysis")
    source = st.radio("Data source", ["Synthetic portfolios", "Upload snapshots"])
    if source == "Synthetic portfolios":
        claims, coverage = demo_data()
        st.caption("Fictitious claims · 2006–2025 · EUR · after deductible")
    else:
        uploaded = st.file_uploader("Claims snapshots", type=["csv", "parquet"])
        cov_file = st.file_uploader("Coverage declarations", type=["csv", "parquet"])
        if uploaded is None or cov_file is None:
            st.info("Upload both claims and coverage. See docs/data_dictionary.md for the input contract.")
            st.stop()
        try:
            claims, coverage = read_upload(uploaded), read_upload(cov_file)
        except (ValueError, OSError, pl.exceptions.PolarsError) as e:
            st.error(f"Could not read input: {e}")
            st.stop()
        with st.expander("Map claims columns", expanded=not set(REQUIRED).issubset(claims.columns)):
            mapping = {}
            for c in REQUIRED:
                options = ["—"] + claims.columns
                chosen = st.selectbox(
                    c, options, index=options.index(c) if c in options else 0, key="map_" + c
                )
                if chosen != "—":
                    mapping[chosen] = c
            if len(mapping) != len(REQUIRED):
                st.warning("Map every required field to a distinct column.")
                st.stop()
            claims = claims.rename(mapping)
    if not set(GROUP).issubset(coverage.columns):
        st.error("Coverage needs portfolio, currency, amount_basis, valuation_date and complete columns.")
        st.stop()
    groups = coverage.select(GROUP).unique().sort(GROUP).to_dicts()
    group_index = st.selectbox(
        "Portfolio and amount basis",
        range(len(groups)),
        format_func=lambda i: " · ".join(str(groups[i][c]) for c in GROUP),
    )
    group = groups[group_index]
    grain_label = st.radio("Time periods", ["Annual", "Quarterly"], horizontal=True)
    grain = "Y" if grain_label == "Annual" else "Q"
    valuation = st.date_input("Valuation date", date(2025, 12, 31))
    st.caption("Use year-end or quarter-end. Earlier valuations ignore later information.")

analyst_tab = st.container()
workspace = st.container()
with workspace:
    input_tab, triangles_tab, output_tab = st.tabs(
        ["1 · Load data", "2 · Explore triangles", "3 · Calculate ultimate"]
    )
with input_tab:
    controls_tab = st.expander("Data checks & completeness", expanded=False)
with output_tab:
    assumptions_tab = st.expander("Adjust assumptions & select final methods", expanded=False)

with input_tab:
    st.subheader("Meet your portfolio")
    st.write("Paid is cumulative. Case reserve is the remaining amount on the file. Incurred is their sum.")
    st.caption("Deductible is metadata only. No deduction or gross-to-net conversion is performed.")
    st.caption(
        "Choose an example or upload snapshots in the sidebar. Your AI analyst is available alongside every step."
    )

try:
    scoped_filter = pl.all_horizontal([pl.col(k) == v for k, v in group.items()])
    scoped_claims = dates(claims, ["valuation_date"]).filter(
        scoped_filter & ((pl.col("valuation_date") <= valuation) | pl.col("valuation_date").is_null())
    )
    scoped_cov = dates(coverage, ["valuation_date"]).filter(
        scoped_filter & ((pl.col("valuation_date") <= valuation) | pl.col("valuation_date").is_null())
    )
    validation = validate_claims(scoped_claims, scoped_cov)
except (ValueError, OSError, pl.exceptions.PolarsError) as e:
    st.error(f"Input could not be validated: {e}")
    st.stop()
with controls_tab:
    st.subheader("Data quality before modelling")
    if validation.issues.height:
        st.dataframe(validation.issues, hide_index=True, width="stretch")
    else:
        st.success("No issues found in the selected historical snapshots.")
    st.caption(
        "Row references use the filtered data below (header is row 1). Coverage declarations cannot prove completeness of the original source system."
    )
    if not validation.valid:
        st.dataframe(validation.data, hide_index=True, width="stretch")
        st.error("Resolve errors before building triangles. No rows are silently removed.")
if not validation.valid:
    st.stop()
try:
    triangle = prepare(
        claims, coverage, valuation, group["portfolio"], group["currency"], group["amount_basis"], grain
    )
except ValueError as e:
    st.error(str(e))
    st.stop()

with input_tab:
    a, b, c = st.columns(3)
    a.metric("Portfolio", group["portfolio"])
    b.metric("Accident periods", len(triangle.origins))
    c.metric("Reported claims", f"{sum(triangle.latest('count')):,.0f}")
    st.caption(f"{valuation} · {group['currency']} · {group['amount_basis']} · selected historical cutoff")
    current, diagnostics = claim_diagnostics(validation.data, valuation)
    if current.height:
        annual = (
            current.with_columns(pl.col("accident_date").dt.year().alias("Accident year"))
            .group_by("Accident year")
            .agg(
                pl.col("paid").sum().alias("Paid"),
                pl.col("case_reserve").sum().alias("Case reserve"),
                pl.len().alias("Claims"),
            )
            .sort("Accident year")
        )
        chart = px.bar(
            annual.to_pandas(),
            x="Accident year",
            y=["Paid", "Case reserve"],
            title="Where is the observed claim cost?",
            color_discrete_sequence=["#087f8c", "#9bd9c4"],
            labels={"value": group["currency"], "variable": ""},
        )
        chart.update_layout(
            template="plotly_white", height=300, margin={"t": 45, "b": 20}, legend_orientation="h"
        )
        st.plotly_chart(chart, width="stretch")
        st.caption(
            "Latest snapshot by accident year; recent years are less developed. These are observed amounts, not ultimate estimates."
        )
        with st.expander("Claim size & unusual observations"):
            distribution = px.histogram(
                current.to_pandas(),
                x="incurred",
                nbins=35,
                color_discrete_sequence=["#087f8c"],
                title="Claim size at this valuation",
                labels={"incurred": f"Incurred ({group['currency']})"},
            )
            distribution.update_layout(template="plotly_white", height=260)
            st.plotly_chart(distribution, width="stretch")
            flagged = current.filter(pl.col("review_flag"))
            st.write(f"**{flagged.height} claims flagged for review** out of {current.height:,}.")
            st.caption(
                diagnostics["rule"]
                + " A flag is not an error or an exclusion; legitimate large claims can be important."
            )
            st.dataframe(
                current.sort("incurred", descending=True)
                .select(
                    "claim_id", "accident_date", "status", "paid", "case_reserve", "incurred", "review_flag"
                )
                .head(25),
                hide_index=True,
                width="stretch",
            )
            st.caption("Largest 25 claims, with flag status. No historical snapshots are counted twice.")
    else:
        st.info("No claim snapshots at this exact valuation. Review coverage before interpreting charts.")
    with st.expander("Source snapshots and coverage"):
        st.dataframe(scoped_claims.head(200), hide_index=True, width="stretch")
        st.caption(
            f"First 200 of {scoped_claims.height:,} filtered snapshots. Closed claims remain in the history."
        )
        st.dataframe(scoped_cov, hide_index=True, width="stretch")

with triangles_tab:
    st.subheader("See the development pattern")
    basis_view = st.selectbox("Measure", ["paid", "incurred", "count"])
    view = st.radio(
        "Triangle view",
        ["Development factors", "Cumulative amounts", "Incremental movement"],
        horizontal=True,
    )
    incremental = view == "Incremental movement"
    frame = triangle.frame(basis_view, incremental)
    if view == "Development factors":
        ratios = factor_triangle(triangle, basis_view)
        factor_frame = pd.DataFrame(
            ratios,
            index=triangle.origins,
            columns=[f"{i} → {i + 1}" for i in range(1, len(triangle.origins))],
        )
        st.caption(
            "Each cell = cumulative amount at the next development age ÷ current age. Blank means unavailable or an invalid denominator; no factor is inferred."
        )
        if ratios.shape[1]:
            st.dataframe(
                factor_frame.style.format("{:.3f}", na_rep="—").map(
                    lambda x: (
                        ""
                        if pd.isna(x)
                        else (
                            "background-color:#c6e7df;color:#123e38"
                            if x <= 1.2
                            else "background-color:#78bbb8;color:#102e35"
                            if x <= 2
                            else "background-color:#245b70;color:white"
                        )
                    )
                ),
                width="stretch",
                height=470,
            )
            st.caption(
                "Colour bands: ≤1.2 · 1.2–2 · >2. Colour shows factor size, not statistical significance."
            )
        else:
            st.info("At least two development periods are needed for link ratios.")
    else:
        st.dataframe(frame, hide_index=True, width="stretch")
    with st.expander("Coverage states: observed / missing / future"):
        st.dataframe(
            pd.DataFrame(triangle.states, index=triangle.origins, columns=range(1, len(triangle.origins) + 1))
        )
    st.caption(
        "Incremental incurred is the change in paid plus case reserves; it is not a payment cash flow."
    )
    st.caption(
        "Inspect a cell below to see its contributing claims. For a factor, inspect both adjacent ages."
    )
    with st.expander("Inspect underlying claims", expanded=False):
        a, b = st.columns(2)
        origin_trace = a.selectbox("Inspect origin", triangle.origins, index=len(triangle.origins) - 1)
        max_age = len(triangle.origins) - triangle.origins.index(origin_trace)
        age_trace = b.number_input("Development period", min_value=1, max_value=max_age, value=1)
        try:
            traced = triangle.trace(origin_trace, age_trace)
            st.dataframe(traced, hide_index=True, width="stretch")
            st.caption(f"{traced.height:,} contributing claim snapshots.")
        except ValueError as e:
            st.info(str(e))

with assumptions_tab:
    st.subheader("Challenge the development pattern")
    st.write(
        "Inspect individual link ratios, compare averaging periods and tick observations to exclude. Your changes affect fitted factors; the source triangle stays intact."
    )
    development_settings = {}
    for basis in ("paid", "incurred", "count"):
        with st.expander(basis.title() + " development", expanded=False):
            left, mid, right = st.columns(3)
            average = left.selectbox("Average", ["volume", "simple"], key=basis + "avg")
            window = mid.number_input(
                "Latest eligible pairs (0 = all)", min_value=0, value=0, key=basis + "window"
            )
            tail = right.number_input(
                "Tail factor", min_value=1.0, value=1.0, step=0.01, format="%.4f", key=basis + "tail"
            )
            st.caption("A tail of 1.0000 assumes no development beyond the final observed age.")
            comparisons = pd.DataFrame(development(triangle, basis, DevelopmentConfig())[2][:-1])
            for years in (3, 5):
                comparisons[f"volume_{years}"] = [
                    r["volume"] for r in development(triangle, basis, DevelopmentConfig(window=years))[2][:-1]
                ]
            comparisons = comparisons[["development", "volume", "simple", "volume_3", "volume_5", "pairs"]]
            comparisons["override"] = None
            st.markdown("**Factor selection bench**")
            st.caption(
                "Reference averages below use all valid observations before your exclusions. The live fitted pattern appears below the observation review."
            )
            overrides = st.data_editor(
                comparisons,
                column_config={
                    "override": st.column_config.NumberColumn(
                        "Your factor", min_value=0.000001, format="%.6f"
                    ),
                    **{
                        k: st.column_config.NumberColumn(k.replace("_", " ").title(), format="%.4f")
                        for k in ["volume", "simple", "volume_3", "volume_5"]
                    },
                },
                disabled=[c for c in comparisons.columns if c != "override"],
                hide_index=True,
                key=basis + "overrides_" + grain,
                width="stretch",
                height=240,
            )
            observations = observation_pairs(triangle, basis, DevelopmentConfig()).to_pandas()
            observations = observations[["origin", "development", "from_amount", "to_amount", "link_ratio"]]
            observations.insert(0, "exclude", False)
            st.markdown("**Observation review · tick to exclude**")
            exclusions = st.data_editor(
                observations,
                disabled=[c for c in observations.columns if c != "exclude"],
                column_config={
                    "exclude": st.column_config.CheckboxColumn(
                        "Exclude", help="Remove this adjacent pair from fitting; retain the claim data."
                    ),
                    "link_ratio": st.column_config.NumberColumn("Link ratio", format="%.4f"),
                    "from_amount": st.column_config.NumberColumn("From", format="%.2f"),
                    "to_amount": st.column_config.NumberColumn("To", format="%.2f"),
                },
                key=basis + "exclude_" + grain,
                hide_index=True,
                height=270,
                width="stretch",
            )
            accessible_exclusions = st.multiselect(
                "Additional exclusions (keyboard-friendly)",
                [(r.origin, int(r.development)) for r in observations.itertuples()],
                format_func=lambda pair: f"{pair[0]} · development {pair[1]} → {pair[1] + 1}",
                key=basis + "accessible_exclusions_" + grain,
                help="Alternative to ticking the table. Combined with any exclusions ticked above.",
            )
            note = st.text_input("Reason for exclusions / overrides / tail", key=basis + "note")
            development_settings[basis] = {
                "average": average,
                "window": window or None,
                "tail": tail,
                "overrides": {
                    int(k): v for k, v in nullable_map(overrides, "development", "override").items()
                },
                "excluded": accessible_exclusions
                + [
                    (str(r.origin), int(r.development))
                    for _, r in exclusions[exclusions["exclude"]].iterrows()
                ],
                "rationale": note,
            }
            # Preview is allowed before a rationale is typed; final calculation still requires it.
            preview_settings = dict(development_settings[basis])
            preview_settings["rationale"] = note or "Uncommitted diagnostic preview"
            preview_config = DevelopmentConfig(**preview_settings)
            inspected = observation_pairs(triangle, basis, preview_config)
            fitted = pd.DataFrame(development(triangle, basis, preview_config)[2])
            st.markdown("**Live development pattern**")
            chart = px.line(
                fitted,
                x="development",
                y=["volume", "simple", "selected"],
                markers=True,
                labels={
                    "value": "Age-to-age factor",
                    "development": "Development period",
                    "variable": "Pattern",
                },
                color_discrete_sequence=["#087f8c", "#8154c9", "#d16b20"],
            )
            chart.update_layout(
                template="plotly_white", height=300, legend_title_text="", margin={"t": 20, "b": 20}
            )
            st.plotly_chart(chart, width="stretch", key=basis + "pattern")
            age = (
                st.selectbox(
                    "Inspect age-to-age observation",
                    list(range(1, len(triangle.origins))),
                    key=basis + "inspect_age",
                )
                if len(triangle.origins) > 1
                else None
            )
            if age is not None:
                age_pairs = inspected.filter(pl.col("development") == age)
                scatter = px.scatter(
                    age_pairs.to_pandas(),
                    x="origin",
                    y="link_ratio",
                    color="status",
                    symbol="status",
                    hover_data=["from_amount", "to_amount", "volume_weight"],
                    color_discrete_map={
                        "Used": "#087f8c",
                        "Excluded": "#ba3e3e",
                        "Outside window": "#8154c9",
                        "Invalid / missing": "#667684",
                    },
                    labels={
                        "origin": "Accident period",
                        "link_ratio": "Link ratio",
                        "status": "Fitting status",
                    },
                )
                chosen = fitted.loc[fitted.development == age, "selected"].iloc[0]
                if pd.notna(chosen):
                    scatter.add_hline(y=chosen, line_dash="dash", annotation_text=f"Selected {chosen:.4f}")
                scatter.update_layout(template="plotly_white", height=290, margin={"t": 25, "b": 20})
                st.plotly_chart(scatter, width="stretch", key=basis + "observations")
                st.dataframe(age_pairs, hide_index=True, width="stretch")
                st.caption(
                    "Volume weight shows each used pair's contribution to the volume-weighted fit. It does not apply to simple averaging or a manual factor."
                )
            with st.expander("Fitted factors, CDFs and exact observations used"):
                st.dataframe(fitted, hide_index=True, width="stretch")
    st.markdown("**Frequency × severity**")
    a, b, c = st.columns(3)
    fs_average = a.selectbox("Historical severity average", ["weighted", "simple"])
    trend = b.number_input("Annual severity trend (%)", min_value=-99.0, value=0.0, step=0.5) / 100
    lookback = c.number_input("Prior years", min_value=1, max_value=50, value=10)
    hist_years = st.multiselect(
        "Eligible historical years",
        sorted(set(triangle.origin_years)),
        default=sorted(set(triangle.origin_years)),
    )
    mode = st.selectbox("Target claim count", ["developed", "manual", "exposure", "reported"])
    confirm = st.checkbox("I assume no further claim reporting") if mode == "reported" else False
    target = st.data_editor(
        pd.DataFrame(
            {
                "origin": triangle.origins,
                "expected_count": [None] * len(triangle.origins),
                "exposure": [None] * len(triangle.origins),
                "frequency": [None] * len(triangle.origins),
                "bf_prior": [None] * len(triangle.origins),
            }
        ),
        disabled=["origin"],
        column_config={
            k: st.column_config.NumberColumn(min_value=0.0)
            for k in ["expected_count", "exposure", "frequency", "bf_prior"]
        },
        hide_index=True,
        key="targets_" + grain,
        width="stretch",
    )
    st.caption(
        "Blank BF prior uses frequency × severity. Zero is a real override. Exposure × frequency requires both fields."
    )
    with st.expander("Historical ultimate and count selections"):
        hist = st.data_editor(
            pd.DataFrame(
                {
                    "origin": triangle.origins,
                    "ultimate_override": [None] * len(triangle.origins),
                    "count_override": [None] * len(triangle.origins),
                }
            ),
            disabled=["origin"],
            column_config={"count_override": st.column_config.NumberColumn(min_value=0.0)},
            hide_index=True,
            key="hist_" + grain,
            width="stretch",
        )
        hist_note = st.text_input("Reason for historical selections")
    st.markdown("**Final selection by origin**")
    selections = st.data_editor(
        pd.DataFrame(
            {
                "origin": triangle.origins,
                "method": [""] * len(triangle.origins),
                "manual_ultimate": [None] * len(triangle.origins),
                "note": [""] * len(triangle.origins),
            }
        ),
        disabled=["origin"],
        column_config={
            "method": st.column_config.SelectboxColumn(options=["", *METHODS, "manual"]),
            "manual_ultimate": st.column_config.NumberColumn(),
        },
        hide_index=True,
        key="selections_" + grain,
        width="stretch",
    )
    st.caption(
        "No final method is preselected. Calibration uses independent historical CL estimates, never the final selections."
    )

try:
    config = AnalysisConfig(
        **{b: DevelopmentConfig(**d) for b, d in development_settings.items()},
        frequency_severity=FrequencySeverityConfig(
            average=fs_average,
            trend=trend,
            lookback_years=lookback,
            historical_years=hist_years,
            count_mode=mode,
            no_further_reporting=confirm,
            expected_counts=nullable_map(target, "origin", "expected_count"),
            exposures=nullable_map(target, "origin", "exposure"),
            frequencies=nullable_map(target, "origin", "frequency"),
            historical_ultimates=nullable_map(hist, "origin", "ultimate_override"),
            historical_counts=nullable_map(hist, "origin", "count_override"),
            rationale=hist_note,
        ),
        priors=nullable_map(target, "origin", "bf_prior"),
        selections={r.origin: r.method for _, r in selections.iterrows() if r.method},
        manual_ultimates=nullable_map(selections, "origin", "manual_ultimate"),
        selection_notes={r.origin: r.note for _, r in selections.iterrows() if r.note},
    )
except ValueError as e:
    with output_tab:
        st.warning(f"Complete assumptions before calculating: {e}")
    st.stop()

signature = hashlib.sha256(
    (config.model_dump_json() + json.dumps(triangle.metadata, sort_keys=True)).encode()
).hexdigest()
with output_tab:
    st.subheader("Compare, select and explain")
    if st.button("Calculate analysis", type="primary"):
        try:
            with st.spinner("Calculating development and reserving methods…"):
                st.session_state["calculated"] = (signature, run_reserving(triangle, config))
        except ValueError as e:
            st.error(str(e))
    saved = st.session_state.get("calculated")
    if saved is None:
        st.info("Review the assumptions, then calculate the analysis.")
    elif saved[0] != signature:
        st.warning("Inputs or assumptions changed. Calculate again to refresh results and enable export.")
    else:
        result = saved[1]
        latest = result.results.filter(pl.col("origin") == triangle.origins[-1])
        st.caption(
            f"Valuation {valuation} · {group['portfolio']} · {group['currency']} · {group['amount_basis']}"
        )
        selected = result.results.filter(pl.col("selected"))
        complete_selection = selected.height == len(triangle.origins)
        a, b, c = st.columns(3)
        a.metric("Origins selected", f"{selected.height} / {len(triangle.origins)}")
        a.caption("Select a method in Assumptions.")
        b.metric(
            "Selected ultimate", f"{selected['ultimate'].sum():,.0f}" if complete_selection else "Incomplete"
        )
        c.metric(
            "Selected outstanding",
            f"{selected['outstanding'].sum():,.0f}"
            if complete_selection and selected["outstanding"].null_count() == 0
            else "Incomplete",
        )
        st.plotly_chart(
            px.bar(
                latest.to_pandas(),
                x="method",
                y="ultimate",
                title=f"Latest origin · {triangle.origins[-1]}",
                color_discrete_sequence=["#087f8c"],
            ),
            width="stretch",
        )
        st.subheader("What changed when you changed assumptions?")
        st.caption(
            "Like-for-like comparison against default assumptions on the same data and valuation. This is not a prior-period reserve movement."
        )
        baseline = run_reserving(triangle)
        impact = method_impact(baseline, result)
        available = impact.filter(pl.col("ultimate_change").is_not_null())
        if available.height:
            largest = available.sort(pl.col("ultimate_change").abs(), descending=True).row(0, named=True)
            st.info(
                f"Largest absolute assumption effect: {largest['origin']} · {largest['method']} · {largest['ultimate_change']:+,.2f} {group['currency']} in ultimate. This identifies a change, not its business cause."
            )
        with st.expander("Review every assumption effect"):
            st.dataframe(impact, hide_index=True, width="stretch")
        st.subheader("Method comparison and reserve components")
        st.dataframe(result.results, hide_index=True, width="stretch")
        with st.expander("Factors and exact calibration years"):
            st.dataframe(result.factors, hide_index=True, width="stretch")
            st.dataframe(result.history, hide_index=True, width="stretch")
        if result.warnings:
            with st.expander(f"{len(result.warnings)} model diagnostics"):
                st.write("\n\n".join(result.warnings))
        st.download_button(
            "Download analysis package",
            export_results(result),
            file_name="reserving-analysis.zip",
            mime="application/zip",
        )
        st.download_button(
            "Download for Google Sheets (CSV package)",
            export_google_sheets_package(result),
            file_name="reserving-google-sheets-package.zip",
            mime="application/zip",
            help="Unzip and import results.csv, development_factors.csv and historical_calibration.csv into separate Google Sheets tabs.",
        )
        st.markdown("**Or download a single table directly**")
        csv_cols = st.columns(3)
        for col, label, frame, filename in zip(
            csv_cols,
            ["Results CSV", "Development factors CSV", "Calibration CSV"],
            [result.results, result.factors, result.history],
            ["results.csv", "development_factors.csv", "historical_calibration.csv"],
        ):
            col.download_button(
                label, safe_csv(frame).encode(), file_name=filename, mime="text/csv", key="direct_" + filename
            )
        st.caption(
            "Google Sheets imports CSV directly: File → Import → Upload → Replace current sheet or Insert new sheet. The ZIP is only a convenience bundle and must be unzipped first."
        )
        st.caption(
            "Includes CSV tables and JSON assumptions, hashes and version. No raw claim records are included."
        )
    workbook = Path(__file__).parent / "examples" / "reserving_worked_example.xlsx"
    if workbook.exists():
        st.download_button(
            "Download the worked spreadsheet example (XLSX)", workbook.read_bytes(), file_name=workbook.name
        )
        st.caption(
            "You do not need Excel for the analysis. Use the Google Sheets package above for current results; the XLSX is the worked formula example."
        )
    st.caption(
        "Deterministic estimates only. No Mack error estimates, bootstrap distributions or discounting in v0.1."
    )

with analyst_tab:
    st.markdown(
        """<div class="assistant-intro"><h3>Your AI analyst</h3>
<p><strong>Ask. Analyse. Create.</strong><br>Understand a method, run a scenario, or make a report and test data — just ask.</p></div>""",
        unsafe_allow_html=True,
    )
    st.caption("Gemma runs on your computer. Calculations come from the actuarial library.")
    connection, reset = st.container(), st.container()
    if connection.button("Connect to local Gemma"):
        try:
            st.session_state["local_models"] = local_models()
            if not st.session_state["local_models"]:
                st.warning("No local models found. Open Ollama and install a local Gemma model.")
        except ValueError as exc:
            st.error(str(exc))
    models = st.session_state.get("local_models", [])
    if models:
        preferred = next((i for i, name in enumerate(models) if "gemma" in name.lower()), 0)
        model = st.selectbox("Local model", models, index=preferred)
        chat_key = signature + model
        if reset.button("Start new chat"):
            st.session_state.pop("analyst", None)
        stored = st.session_state.get("analyst")
        if stored is None or stored[0] != chat_key:
            if stored is not None:
                st.info("The data, assumptions or model changed. A fresh chat now uses the current analysis.")
            try:
                st.session_state["analyst"] = (chat_key, AnalystSession(triangle, config))
            except ValueError as exc:
                st.error(f"Complete the current analysis before chatting: {exc}")
                st.stop()
        analyst = st.session_state["analyst"][1]
        st.success(f"Using {model} on this computer · {group['portfolio']} · {valuation}")
        starters = [
            "Review the latest accident period. Compare the available methods and highlight limitations.",
            "Explain how run_reserving works using the documented signature: what goes in, how it calculates, and what comes out.",
            "Create a downloadable review report from the current analysis. Briefly explain what is in it.",
            "Create a small synthetic test dataset I can upload into this tool. Briefly explain how to use it.",
        ]
        prompt = None
        buttons = st.columns(2)
        for index, (label, question) in enumerate(
            zip(
                ["Analyse", "Explain", "Report", "Test data"],
                starters,
            )
        ):
            col = buttons[index % 2]
            if col.button(label, width="stretch"):
                prompt = question
        st.caption(
            "Try: ‘Flag unusual claims’ or ‘Test a paid tail of 1.05’. Scenarios stay separate from your selections."
        )
        for turn in analyst.transcript:
            with st.chat_message(turn["role"]):
                st.markdown(turn["content"])
        typed = st.chat_input("Ask about methods, observations or a what-if scenario…", max_chars=6000)
        prompt = typed or prompt
        if prompt:
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.status("Asking the local model…", expanded=True) as status:
                try:
                    answer = analyst.ask(prompt, model, progress=lambda text: status.update(label=text))
                    status.update(
                        label="Analysis paused"
                        if answer.startswith("Analysis paused:")
                        else "Finished — inspect the evidence below",
                        state="error" if answer.startswith("Analysis paused:") else "complete",
                        expanded=False,
                    )
                except ValueError as exc:
                    answer = str(exc)
                    status.update(label=answer, state="error")
            with st.chat_message("assistant"):
                st.markdown(answer)
        if analyst.evidence:
            with st.expander(f"Evidence trail · {len(analyst.evidence)} tool calls"):
                for evidence in analyst.evidence:
                    st.markdown(f"**[{evidence['id']}] {evidence['tool']}**")
                    st.json(evidence, expanded=False)
        if analyst.artifacts:
            st.markdown("**Files created**")
            st.caption(
                "Reports: calculated estimates, reserve components, assumptions and diagnostics in Markdown. Test data: synthetic claims + coverage CSVs in a ZIP."
            )
            for identifier, artifact in analyst.artifacts.items():
                st.download_button(
                    "Download " + artifact["filename"],
                    artifact["content"],
                    file_name=artifact["filename"],
                    mime=artifact["mime"],
                    key="file_" + identifier,
                )
        if analyst.transcript:
            st.download_button(
                "Download conversation and evidence (JSON)",
                json.dumps(analyst.record(), indent=2, default=str),
                file_name="local-analyst-review.json",
                mime="application/json",
            )
        for name, scenario in analyst.scenarios.items():
            st.download_button(
                f"Download {name} calculations and assumptions",
                export_results(scenario),
                file_name=f"{name}.zip",
                mime="application/zip",
                key="agent_download_" + name,
            )
        st.caption(
            "Exploratory AI draft: check numerical claims against the evidence. No bootstrap or Word/PowerPoint generation yet. The existing Excel download remains the worked example."
        )
    else:
        st.info(
            "Open Ollama, then choose Connect to local Gemma. The first answer can take longer while the model loads."
        )
