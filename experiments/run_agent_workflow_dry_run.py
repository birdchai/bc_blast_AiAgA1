"""Step 10.1 agent workflow dry-run prototype.

This script simulates the agent-orchestrated decision-support architecture on a
small set of province-week records. It is intentionally lightweight:

- no model training,
- no threshold tuning,
- no external downloads,
- no prediction-pipeline modification,
- no test labels used for decisions.

The workflow is deterministic Python. Agent roles are simulated sequentially for
local reproducibility on the current research laptop.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments" / "outputs"

PRED_ANALOG = OUT / "analog_decision_calibrated_predictions.csv"
PRED_FORWARD = OUT / "forward_calibrated_predictions.csv"
PRED_UPDATED = OUT / "updated_2022_test_predictions.csv"
DATASET = OUT / "region_temporal_sequence_dataset_updated_labels_2015_2022.csv"
MODEL_REGISTRY = OUT / "model_registry_current.csv"
FEATURE_REGISTRY = OUT / "feature_registry_current.csv"
REGIONAL_POLICY = OUT / "regional_routing_policy.csv"
DECISION_MODES = OUT / "decision_mode_registry.csv"
ALERT_SCHEMA = OUT / "alert_output_schema.csv"
BACKLOG = OUT / "research_backlog_current.csv"


ALERT_TIERS = [
    (0.40, "high alert"),
    (0.25, "warning"),
    (0.10, "watch"),
    (0.00, "low risk"),
]


@dataclass
class AgentResult:
    agent: str
    status: str
    notes: str


def alert_tier(score: float | None) -> str:
    if score is None or pd.isna(score):
        return "unscored"
    for threshold, tier in ALERT_TIERS:
        if score >= threshold:
            return tier
    return "low risk"


def action_category(tier: str, confidence_flag: str) -> str:
    if "low confidence" in confidence_flag:
        return "diagnostic review"
    if tier == "high alert":
        return "priority field check"
    if tier == "warning":
        return "field monitoring"
    if tier == "watch":
        return "routine monitoring"
    return "routine monitoring"


def model_agreement(primary_score: float | None, secondary_score: float | None) -> str:
    if primary_score is None or secondary_score is None or pd.isna(primary_score) or pd.isna(secondary_score):
        return "single_model_or_missing_secondary"
    primary_tier = alert_tier(primary_score)
    secondary_tier = alert_tier(secondary_score)
    if primary_tier == secondary_tier:
        return "agreement_same_tier"
    if abs(primary_score - secondary_score) >= 0.20:
        return "disagreement_large_score_gap"
    return "partial_disagreement"


def compact_signal(value: Any, label: str, high: float | None = None) -> str:
    if value is None or pd.isna(value):
        return f"{label}: missing"
    try:
        numeric = float(value)
    except Exception:  # noqa: BLE001
        return f"{label}: {value}"
    if high is not None:
        state = "high" if numeric >= high else "modest"
        return f"{label}: {state} ({numeric:.3g})"
    return f"{label}: {numeric:.3g}"


def load_prediction_scores() -> pd.DataFrame:
    """Load available local prediction scores into a wide province-week table."""
    frames: list[pd.DataFrame] = []
    if PRED_ANALOG.exists():
        pred = pd.read_csv(PRED_ANALOG)
        pred = pred[pred["split"].eq("test")].copy()
        pred["score_used"] = pred.get("calibrated_score", pred["y_score"])
        pred["score_key"] = pred["model_feature"].fillna(pred["model"] + "__" + pred["feature_set"])
        frames.append(pred[["province", "region", "datetime", "year", "week", "score_key", "score_used"]])
    elif PRED_UPDATED.exists():
        pred = pd.read_csv(PRED_UPDATED)
        pred = pred[pred["split"].eq("test")].copy()
        pred["score_used"] = pred["y_score"]
        pred["score_key"] = pred["model"] + "__" + pred["feature_set"]
        frames.append(pred[["province", "region", "datetime", "year", "week", "score_key", "score_used"]])

    if PRED_FORWARD.exists():
        pred = pd.read_csv(PRED_FORWARD)
        pred = pred[pred["split"].eq("test")].copy()
        pred["score_used"] = pred.get("calibrated_score", pred["y_score"])
        pred["score_key"] = pred["model"]
        frames.append(pred[["province", "region", "datetime", "year", "week", "score_key", "score_used"]])

    if not frames:
        return pd.DataFrame()

    long = pd.concat(frames, ignore_index=True)
    wide = (
        long.pivot_table(
            index=["province", "region", "datetime", "year", "week"],
            columns="score_key",
            values="score_used",
            aggfunc="first",
        )
        .reset_index()
        .rename_axis(None, axis=1)
    )
    return wide


def create_synthetic_examples() -> pd.DataFrame:
    rows = [
        {"province": "Khon Kaen", "region": "Northeast", "datetime": "2022-08-14", "year": 2022, "week": 32},
        {"province": "Lamphun", "region": "North", "datetime": "2022-12-04", "year": 2022, "week": 48},
        {"province": "Chon Buri", "region": "East", "datetime": "2022-08-14", "year": 2022, "week": 32},
        {"province": "Sing Buri", "region": "Central", "datetime": "2022-08-14", "year": 2022, "week": 32},
        {"province": "Ubon Ratchathani", "region": "Northeast", "datetime": "2022-08-21", "year": 2022, "week": 33},
    ]
    df = pd.DataFrame(rows)
    df["dry_run_source"] = "synthetic_example_no_official_prediction_available"
    return df


def choose_cases(scores: pd.DataFrame) -> pd.DataFrame:
    """Choose 5 dry-run cases from available scores, fallback to synthetic if needed."""
    if scores.empty:
        return create_synthetic_examples()

    cases = []
    desired = [
        ("northeast_analog_active", lambda d: d["region"].eq("Northeast")),
        ("north_low_confidence", lambda d: d["region"].eq("North")),
        ("default_non_north", lambda d: d["region"].isin(["East", "South"])),
        ("sparse_region", lambda d: d["region"].isin(["Central", "West"])),
        ("dashboard_ranking", lambda d: d["region"].eq("Northeast")),
    ]
    used_keys: set[tuple[str, int, int]] = set()
    for case_type, mask_fn in desired:
        subset = scores[mask_fn(scores)].copy()
        if subset.empty:
            continue
        score_cols = [c for c in subset.columns if c not in {"province", "region", "datetime", "year", "week"}]
        if score_cols:
            subset["_max_score"] = subset[score_cols].max(axis=1, skipna=True)
            subset = subset.sort_values("_max_score", ascending=False)
        selected = None
        for _, row in subset.iterrows():
            key = (str(row["province"]), int(row["year"]), int(row["week"]))
            if key not in used_keys:
                selected = row.drop(labels=["_max_score"], errors="ignore").to_dict()
                used_keys.add(key)
                break
        if selected:
            selected["dry_run_case_type"] = case_type
            selected["dry_run_source"] = "local_prediction_outputs_no_label_decision_use"
            cases.append(selected)

    result = pd.DataFrame(cases)
    if len(result) < 5:
        synthetic = create_synthetic_examples()
        for _, row in synthetic.iterrows():
            if len(result) >= 5:
                break
            key = (str(row["province"]), int(row["year"]), int(row["week"]))
            if key not in used_keys:
                result = pd.concat([result, pd.DataFrame([row])], ignore_index=True)
                used_keys.add(key)
    return result.head(5)


def merge_feature_context(cases: pd.DataFrame) -> pd.DataFrame:
    if not DATASET.exists():
        return cases
    usecols = [
        "province",
        "region",
        "datetime",
        "year",
        "week",
        "humidity_mean",
        "leaf_wet_hours",
        "susceptibility_score",
        "neighbor_prevweek_blast",
        "regional_neighbor_pressure_2w",
        "analog_prevweek_blast",
        "bus_feature_available",
        "bus_critical_any",
    ]
    available = pd.read_csv(DATASET, nrows=0).columns.tolist()
    usecols = [c for c in usecols if c in available]
    context = pd.read_csv(DATASET, usecols=usecols)
    context["datetime"] = context["datetime"].astype(str)
    cases["datetime"] = cases["datetime"].astype(str)
    return cases.merge(context, on=["province", "region", "datetime", "year", "week"], how="left")


def get_score(row: pd.Series, candidates: list[str]) -> float | None:
    for col in candidates:
        if col in row.index and pd.notna(row[col]):
            return float(row[col])
    return None


def data_audit_agent(row: pd.Series) -> AgentResult:
    required = ["province", "region", "year", "week"]
    missing = [field for field in required if field not in row.index or pd.isna(row[field])]
    if missing:
        return AgentResult("Data Audit Agent", "flag", f"missing required fields: {', '.join(missing)}")
    if int(row["year"]) < 2017:
        return AgentResult("Data Audit Agent", "flag", "outside corrected-label supervised phase")
    score_missing = pd.isna(row.get("primary_score_internal"))
    note = "required fields present; corrected-label phase record"
    if score_missing:
        note += "; primary score missing"
    return AgentResult("Data Audit Agent", "pass" if not score_missing else "warning", note)


def feature_agent(row: pd.Series) -> AgentResult:
    families = []
    if pd.notna(row.get("humidity_mean")) or pd.notna(row.get("leaf_wet_hours")):
        families.append("weather/leaf wetness")
    if pd.notna(row.get("susceptibility_score")):
        families.append("host susceptibility")
    if pd.notna(row.get("neighbor_prevweek_blast")) or pd.notna(row.get("regional_neighbor_pressure_2w")):
        families.append("spatial/regional pressure")
    if pd.notna(row.get("analog_prevweek_blast")):
        families.append("analog history")
    if pd.notna(row.get("bus_feature_available")):
        families.append("BUS reference")
    missing = [
        name
        for name in ["weather/leaf wetness", "host susceptibility", "spatial/regional pressure"]
        if name not in families
    ]
    status = "pass" if not missing else "warning"
    note = f"available families: {', '.join(families) if families else 'none'}"
    if missing:
        note += f"; missing core families: {', '.join(missing)}"
    return AgentResult("Feature Agent", status, note)


def model_agent(row: pd.Series) -> AgentResult:
    region = row["region"]
    if region == "Northeast":
        note = "route DNN core primary; DNN analog history second opinion; RF all analog ranking comparator"
    elif region == "North":
        note = "route DNN core primary only with low-confidence caveat"
    elif region in {"Central", "West", "South"}:
        note = "route DNN core primary; sparse-region caveat; RF comparator if available"
    else:
        note = "route DNN core primary; RF comparator if available"
    return AgentResult("Model Agent", "pass", note)


def decision_agent(row: pd.Series) -> AgentResult:
    tier = row.get("primary_alert_tier", "unscored")
    policy = row.get("selected_policy", "balanced default")
    note = f"policy={policy}; tier={tier}; no threshold tuning; labels not used"
    return AgentResult("Decision Governance Agent", "pass", note)


def regional_agent(row: pd.Series) -> AgentResult:
    region = row["region"]
    if region == "Northeast":
        return AgentResult("Regional Routing Agent", "pass", "Northeast enhanced monitoring route")
    if region == "North":
        return AgentResult("Regional Routing Agent", "low_confidence", "North diagnostic backlog route")
    if region in {"Central", "West", "South"}:
        return AgentResult("Regional Routing Agent", "warning", f"{region} sparse-positive caveat")
    return AgentResult("Regional Routing Agent", "pass", "default regional route")


def explanation_agent(row: pd.Series) -> AgentResult:
    notes = [
        row.get("key_weather_signal", ""),
        row.get("key_host_signal", ""),
        row.get("key_spatial_signal", ""),
        row.get("key_analog_signal", ""),
        row.get("region_caveat", ""),
    ]
    return AgentResult("Explanation Agent", "pass", " | ".join([n for n in notes if n])[:300])


def build_alert_record(row: pd.Series) -> dict[str, Any]:
    region = str(row["region"])
    case_type = str(row.get("dry_run_case_type", ""))
    primary_model = "DNN no-class-weight core_no_BUS"
    secondary_model = ""
    ranking_model = ""
    selected_policy = "balanced default"

    primary_score = get_score(
        row,
        [
            "dnn_no_class_weight__core_no_BUS",
            "dnn_no_class_weight_core_no_BUS",
            "dnn_no_class_weight__core_no_BUS_calibrated",
        ],
    )
    dnn_analog_score = get_score(row, ["dnn_no_class_weight__core_plus_analog_history"])
    rf_all_analog_score = get_score(row, ["random_forest__core_plus_all_analog"])
    rf_core_score = get_score(row, ["random_forest_core_no_BUS__core_no_BUS", "random_forest_core_no_BUS"])

    secondary_score = None
    if case_type == "dashboard_ranking" and rf_all_analog_score is not None:
        secondary_model = "RF all analog"
        secondary_score = rf_all_analog_score
        selected_policy = "calibrated alert tier dashboard + ranking comparator"
    elif region == "Northeast":
        secondary_model = "DNN no-class-weight analog history"
        secondary_score = dnn_analog_score
        ranking_model = "RF all analog"
        if rf_all_analog_score is not None:
            selected_policy = "balanced default + regional second opinion + ranking comparator"
    elif region == "North":
        secondary_model = ""
        secondary_score = None
        selected_policy = "balanced default + diagnostic backlog"
    elif region in {"Central", "West", "South"}:
        secondary_model = "Random Forest core_no_BUS"
        secondary_score = rf_core_score
        selected_policy = "balanced default + sparse-region caveat"
    else:
        secondary_model = "Random Forest core_no_BUS"
        secondary_score = rf_core_score

    if primary_score is None:
        # Use a dry-run score only when official scores are absent for the selected synthetic record.
        primary_score = 0.0

    primary_tier = alert_tier(primary_score)
    confidence = "normal"
    caveat = "standard national route"
    if region == "Northeast":
        caveat = "Northeast enhanced monitoring; analog is similarity not direct spread"
        confidence = "monitor disagreement"
    elif region == "North":
        caveat = "North low-confidence diagnostic backlog; do not force threshold lowering"
        confidence = "low confidence"
    elif region in {"Central", "West", "South"}:
        caveat = f"{region} sparse-positive caveat"
        confidence = "medium-low confidence" if region in {"Central", "West"} else "medium confidence"

    weather = "; ".join(
        [
            compact_signal(row.get("humidity_mean"), "humidity", 80),
            compact_signal(row.get("leaf_wet_hours"), "leaf wet hours", 40),
        ]
    )
    host = compact_signal(row.get("susceptibility_score"), "susceptibility", 0.55)
    spatial = "; ".join(
        [
            compact_signal(row.get("neighbor_prevweek_blast"), "neighbor blast", 0.1),
            compact_signal(row.get("regional_neighbor_pressure_2w"), "regional pressure", 0.1),
        ]
    )
    if pd.notna(row.get("analog_prevweek_blast")):
        analog = compact_signal(row.get("analog_prevweek_blast"), "analog prevweek blast", 0.1)
    elif dnn_analog_score is not None or rf_all_analog_score is not None:
        analog_parts = []
        if dnn_analog_score is not None:
            analog_parts.append(f"DNN analog score: {dnn_analog_score:.3g}")
        if rf_all_analog_score is not None:
            analog_parts.append(f"RF analog rank score: {rf_all_analog_score:.3g}")
        analog = "; ".join(analog_parts)
    else:
        analog = "analog signal: missing"
    bus = "BUS unavailable"
    if pd.notna(row.get("bus_feature_available")):
        bus = f"BUS available={int(row.get('bus_feature_available'))}; critical={row.get('bus_critical_any')}"

    agreement = model_agreement(primary_score, secondary_score)
    explanation = f"{primary_model} routed by region={region}; {caveat}; labels not used for decision."

    return {
        "province": row["province"],
        "region": region,
        "year": int(row["year"]),
        "week": int(row["week"]),
        "primary_model": primary_model,
        "primary_score": round(float(primary_score), 6),
        "primary_alert_tier": primary_tier,
        "selected_policy": selected_policy,
        "secondary_model": secondary_model or ranking_model,
        "secondary_score": "" if secondary_score is None else round(float(secondary_score), 6),
        "model_agreement_status": agreement,
        "key_weather_signal": weather,
        "key_host_signal": host,
        "key_spatial_signal": spatial,
        "key_analog_signal": analog,
        "BUS_reference_signal_optional": bus,
        "region_caveat": caveat,
        "confidence_flag": confidence,
        "recommended_action_category": action_category(primary_tier, confidence),
        "explanation_notes": explanation,
    }


def trace_for_case(alert: dict[str, Any], agent_results: list[AgentResult], source: str) -> str:
    lines = [
        f"## Dry-Run Case: {alert['province']} {alert['year']}-W{alert['week']}",
        "",
        "### Input Record Summary",
        f"- province: {alert['province']}",
        f"- region: {alert['region']}",
        f"- year/week: {alert['year']} / {alert['week']}",
        f"- source: {source}",
        "",
    ]
    for result in agent_results:
        lines.extend(
            [
                f"### {result.agent}",
                f"- status: {result.status}",
                f"- notes: {result.notes}",
                "",
            ]
        )
    lines.extend(
        [
            "### Final Alert Record",
            f"- primary model: {alert['primary_model']}",
            f"- primary score: {alert['primary_score']}",
            f"- alert tier: {alert['primary_alert_tier']}",
            f"- selected policy: {alert['selected_policy']}",
            f"- confidence: {alert['confidence_flag']}",
            f"- recommended action: {alert['recommended_action_category']}",
            f"- explanation: {alert['explanation_notes']}",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    # Load registries to verify they exist for this architecture dry run.
    for required in [MODEL_REGISTRY, FEATURE_REGISTRY, REGIONAL_POLICY, DECISION_MODES, ALERT_SCHEMA, BACKLOG]:
        if not required.exists():
            raise FileNotFoundError(f"Required governance artifact missing: {required}")

    scores = load_prediction_scores()
    cases = choose_cases(scores)
    cases = merge_feature_context(cases)

    alert_records: list[dict[str, Any]] = []
    example_rows: list[dict[str, Any]] = []
    trace_sections: list[str] = [
        "# Agent Workflow Dry-Run Decision Traces",
        "",
        "Local runtime note:",
        "",
        "- Agent roles are simulated sequentially.",
        "- No concurrent LLM agents are used.",
        "- Deterministic Python handles data transformation.",
        "- LLM use is conceptual / prompt-governed at this stage.",
        "- No model training, threshold tuning, external data download, or prediction-pipeline modification occurred.",
        "",
    ]

    for i, raw_row in cases.reset_index(drop=True).iterrows():
        alert = build_alert_record(raw_row)
        row_for_agents = raw_row.copy()
        row_for_agents["primary_score_internal"] = alert["primary_score"]
        row_for_agents["primary_alert_tier"] = alert["primary_alert_tier"]
        row_for_agents["selected_policy"] = alert["selected_policy"]
        row_for_agents["key_weather_signal"] = alert["key_weather_signal"]
        row_for_agents["key_host_signal"] = alert["key_host_signal"]
        row_for_agents["key_spatial_signal"] = alert["key_spatial_signal"]
        row_for_agents["key_analog_signal"] = alert["key_analog_signal"]
        row_for_agents["region_caveat"] = alert["region_caveat"]

        agent_results = [
            data_audit_agent(row_for_agents),
            feature_agent(row_for_agents),
            model_agent(row_for_agents),
            decision_agent(row_for_agents),
            regional_agent(row_for_agents),
            explanation_agent(row_for_agents),
            AgentResult("Report Writer Agent", "pass", "final dry-run alert record and markdown trace written"),
        ]

        alert_records.append(alert)
        source = str(raw_row.get("dry_run_source", "local_prediction_outputs_no_label_decision_use"))
        trace_sections.append(trace_for_case(alert, agent_results, source))
        example = {
            "case_id": i + 1,
            "dry_run_case_type": raw_row.get("dry_run_case_type", ""),
            "dry_run_source": source,
            "province": alert["province"],
            "region": alert["region"],
            "year": alert["year"],
            "week": alert["week"],
            "primary_model": alert["primary_model"],
            "primary_score": alert["primary_score"],
            "primary_alert_tier": alert["primary_alert_tier"],
            "selected_policy": alert["selected_policy"],
            "confidence_flag": alert["confidence_flag"],
            "agent_status_summary": "; ".join([f"{r.agent}:{r.status}" for r in agent_results]),
        }
        example_rows.append(example)

    alert_columns = pd.read_csv(ALERT_SCHEMA, nrows=0).columns.tolist()
    pd.DataFrame(alert_records, columns=alert_columns).to_csv(OUT / "sample_alert_records.csv", index=False)
    pd.DataFrame(example_rows).to_csv(OUT / "agent_workflow_dry_run_examples.csv", index=False)

    summary = pd.DataFrame(
        [
            {"summary_item": "dry_run_cases", "value": len(alert_records)},
            {"summary_item": "uses_official_prediction_outputs", "value": not scores.empty},
            {"summary_item": "uses_test_labels_for_decision", "value": False},
            {"summary_item": "model_training_performed", "value": False},
            {"summary_item": "threshold_tuning_performed", "value": False},
            {"summary_item": "external_data_downloaded", "value": False},
            {"summary_item": "pipeline_modified", "value": False},
            {"summary_item": "agent_execution_mode", "value": "sequential deterministic Python simulation"},
        ]
    )
    summary.to_csv(OUT / "agent_workflow_dry_run_summary.csv", index=False)
    (OUT / "agent_decision_trace_examples.md").write_text("\n".join(trace_sections), encoding="utf-8")

    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
