import json
import logging
import os
import uuid
from dataclasses import dataclass
from typing import Optional

import matplotlib.pyplot as plt
import pandas as pd

from app.agent.domain import ChartSpec, ExecutionResult, Step
from app.agent.llm.client import LLMClient
from app.agent.prompts import CHART_JSON_GENERATOR_PROMPT
from app.models.db_models import ChatSettings

logger = logging.getLogger(__name__)

_CHART_RENDERERS = {
    "bar":     lambda ax, x, y, df: ax.bar(df[x], df[y], color="#4FC3F7"),
    "line":    lambda ax, x, y, df: ax.plot(df[x], df[y], color="#4FC3F7", marker="o"),
    "scatter": lambda ax, x, y, df: ax.scatter(df[x], df[y], color="#4FC3F7"),
    "pie":     lambda ax, x, y, df: ax.pie(df[y], labels=df[x], autopct="%1.1f%%"),
}


@dataclass
class ValidationResult:
    is_valid: bool
    reason: str = ""


class ChartRenderer:
    def __init__(self, llm_client: LLMClient, settings: ChatSettings, plots_dir: str):
        self.llm = llm_client
        self.settings = settings
        self.plots_dir = plots_dir

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_spec(self, step: Step, df: pd.DataFrame, user_query: str) -> Optional[ChartSpec]:
        """
        Build a ChartSpec grounded in an *already computed* DataFrame.
        X and Y are chosen deterministically from the schema; the LLM is
        only allowed to polish titles/labels and cannot override columns.
        """
        chart_type = step.chart_type or "bar"
        if chart_type not in _CHART_RENDERERS:
            chart_type = "bar"

        df = self._recover_dtypes(df)   

        forced_x = self._select_x_column(df)
        forced_y = self._select_y_column(df)

        if not forced_x or not forced_y:
            logger.error("ChartRenderer: no valid x/y columns found in DataFrame")
            return None

        # Feed the LLM the pre-selected columns so it knows it is constrained.
        data_info = {
            "forced_x": forced_x,
            "forced_y": forced_y,
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "shape": df.shape,
            "sample": (
                "(hidden for privacy)"
                if self.settings.zero_leaks_mode
                else df.head(3).to_dict(orient="records")
            ),
        }

        messages = [{
            "role": "system",
            "content": CHART_JSON_GENERATOR_PROMPT.format(
                step_description=step.title,
                chart_type=chart_type,
                data_info=json.dumps(data_info, indent=2, default=str),
                user_query=user_query,
            ),
        }]

        try:
            response = self.llm.complete(messages, temperature=0.0, timeout=30)
            spec = self._parse_spec(response)
        except Exception as e:
            logger.error(f"Chart spec LLM call failed: {e}")
            spec = None

        # If the LLM hallucinated or returned garbage, fall back to a
        # fully deterministic spec.
        if spec is None:
            spec = ChartSpec(
                type=chart_type,
                x=forced_x,
                y=forced_y,
                title=step.title or "Chart",
                xlabel=forced_x,
                ylabel=forced_y,
            )

        # HARD OVERRIDE — the LLM is never allowed to pick columns freely.
        spec.x = forced_x
        spec.y = forced_y
        spec.type = chart_type

        # Enforce sorting / limits by chart type
        if chart_type in ("bar", "pie"):
            spec.sort = "desc"
        if chart_type == "bar":
            spec.limit = 10
        elif chart_type == "pie":
            spec.limit = 8

        return spec

    def validate_spec(self, spec: ChartSpec, df: pd.DataFrame) -> ValidationResult:
        """
        Guard against semantically inconsistent x/y mappings.
        """
        if spec.x not in df.columns:
            return ValidationResult(False, f"X column '{spec.x}' not found in data")
        if spec.y not in df.columns:
            return ValidationResult(False, f"Y column '{spec.y}' not found in data")

        x_series = df[spec.x]
        y_series = df[spec.y]

        # --- X must be categorical or grouped (low cardinality) ---
        x_dtype = x_series.dtype
        x_distinct = x_series.nunique(dropna=True)

        x_is_categorical = (
            pd.api.types.is_string_dtype(x_dtype)
            or pd.api.types.is_categorical_dtype(x_dtype)
            or pd.api.types.is_object_dtype(x_dtype)
        )
        x_is_low_cardinality_numeric = (
            pd.api.types.is_numeric_dtype(x_dtype) and x_distinct <= 20
        )

        if not (x_is_categorical or x_is_low_cardinality_numeric):
            return ValidationResult(
                False,
                f"X column '{spec.x}' has {x_distinct} distinct values and dtype {x_dtype}; "
                "it must be categorical or low-cardinality numeric (≤20) to serve as a label axis.",
            )

        # Reject raw unprocessed text (e.g. free descriptions) masquerading as a dimension
        if pd.api.types.is_object_dtype(x_dtype):
            non_null = x_series.notna().sum()
            if non_null > 0 and x_distinct / non_null > 0.8:
                return ValidationResult(
                    False,
                    f"X column '{spec.x}' appears to contain raw unprocessed text "
                    f"({x_distinct} unique / {non_null} non-null). "
                    "It must be grouped or categorical.",
                )

        # --- Y must be numeric and aggregated (not an ID) ---
        if not pd.api.types.is_numeric_dtype(y_series.dtype):
            return ValidationResult(
                False,
                f"Y column '{spec.y}' has non-numeric dtype {y_series.dtype}; "
                "it must be a numeric aggregated measure.",
            )

        y_distinct = y_series.nunique(dropna=True)
        non_null_y = y_series.notna().sum()

        # If >20 rows and every value is unique, it's likely an ID, not an aggregate.
        if non_null_y > 20 and y_distinct == non_null_y:
            return ValidationResult(
                False,
                f"Y column '{spec.y}' appears to be an identifier "
                f"({y_distinct} unique values). "
                "It must be an aggregated numeric measure (SUM, AVG, COUNT, etc.).",
            )

        return ValidationResult(True, "")

    def render(self, spec: ChartSpec, df: pd.DataFrame, step: Step) -> ExecutionResult:
        """Render a matplotlib chart from a validated spec."""
        step_number = step.number

        if not spec or not spec.type:
            return ExecutionResult(
                step_number=step_number, type="error", data="No valid chart spec"
            )

        renderer = _CHART_RENDERERS.get(spec.type, _CHART_RENDERERS["bar"])

        # Apply limits and sorting before plotting so the visual matches the spec.
        plot_df = df.copy()
        if spec.sort == "desc":
            plot_df = plot_df.sort_values(by=spec.y, ascending=False)
        if spec.limit and spec.limit > 0:
            plot_df = plot_df.head(spec.limit)

        try:
            plt.style.use("dark_background")
            fig, ax = plt.subplots(figsize=(10, 6))

            renderer(ax, spec.x, spec.y, plot_df)

            ax.set_title(spec.title or "Chart")
            if spec.type != "pie":
                ax.set_xlabel(spec.xlabel or spec.x)
                ax.set_ylabel(spec.ylabel or spec.y)
                plt.xticks(rotation=45, ha="right")

            plt.tight_layout()

            os.makedirs(self.plots_dir, exist_ok=True)
            file_name = f"plot_{uuid.uuid4()}.png"
            file_path = os.path.join(self.plots_dir, file_name)
            fig.savefig(file_path, bbox_inches="tight", dpi=100)
            plt.close(fig)

            return ExecutionResult(
                step_number=step_number,
                step_description=step.title,
                step_type="chart",
                type="image",
                data=f"/static/plots/{file_name}",
                mime="image/png",
                description=spec.title or "Chart",
                chart_json=spec.to_dict(),
            )

        except Exception as e:
            logger.error(f"Chart rendering failed: {e}")
            plt.close("all")
            return ExecutionResult(
                step_number=step_number,
                type="error",
                data=f"Chart rendering failed: {e}",
            )

    # ------------------------------------------------------------------
    # Column selection (deterministic, schema-driven)
    # ------------------------------------------------------------------

    @staticmethod
    def _select_x_column(df: pd.DataFrame) -> Optional[str]:
        """Best X = categorical / string / low-cardinality numeric."""
        best_col: Optional[str] = None
        best_score = -1

        for col in df.columns:
            series = df[col]
            non_null = series.notna().sum()
            if non_null == 0:
                continue

            distinct = series.nunique(dropna=True)
            dtype = series.dtype
            lower = col.lower()

            # Reject obvious ID columns as labels
            if any(h in lower for h in ("id", "uuid", "pk", "serial")) and distinct > 10:
                continue

            if (
                pd.api.types.is_string_dtype(dtype)
                or pd.api.types.is_categorical_dtype(dtype)
                or pd.api.types.is_object_dtype(dtype)
            ):
                score = 1000 - min(distinct, 999)   # lower cardinality = better
                if score > best_score:
                    best_score = score
                    best_col = col
                continue

            if pd.api.types.is_numeric_dtype(dtype) and distinct <= 20:
                score = 500 - distinct
                if score > best_score:
                    best_score = score
                    best_col = col

        return best_col

    @staticmethod
    def _select_y_column(df: pd.DataFrame) -> Optional[str]:
        """Best Y = numeric, aggregated (not an ID), and actually varies."""
        best_col: Optional[str] = None
        best_score = -1

        for col in df.columns:
            series = df[col]
            
            # If object, try to see if it's actually numeric underneath
            if series.dtype == object:
                coerced = pd.to_numeric(series, errors="coerce")
                if coerced.notna().sum() >= series.notna().sum() * 0.8:
                    series = coerced
                else:
                    continue  # truly categorical/text, skip for Y
            
            if not pd.api.types.is_numeric_dtype(series.dtype):
                continue

            non_null = series.notna().sum()
            if non_null == 0:
                continue

            distinct = series.nunique(dropna=True)
            lower = col.lower()

            # Heavy penalty for ID-like numeric columns
            id_penalty = 0
            if any(h in lower for h in ("id", "uuid", "pk", "serial", "row", "key")):
                id_penalty = 800

            # Reward names that smell like aggregates
            agg_bonus = 0
            if any(h in lower for h in ("sum", "total", "avg", "mean", "count",
                                        "revenue", "amount", "sales", "profit",
                                        "cost", "price", "value", "quantity", "score",
                                        "rate", "survived")):
                agg_bonus = 300

            cardinality_ratio = distinct / non_null if non_null > 0 else 1.0
            aggregation_score = (1.0 - cardinality_ratio) * 400

            # ---- NEW: variance scoring ----
            # Constant columns (e.g. total_survivors = 342, 342) are useless for charts
            try:
                variance = series.var()
                mean = series.mean()
            except Exception:
                variance = 0
                mean = 0

            variance_score = 0
            if variance == 0 or distinct <= 1:
                variance_score = -1500  # DEAD WEIGHT — kill it
            else:
                # Prefer columns with meaningful spread relative to their scale
                cv = variance / (abs(mean) + 1e-9)
                variance_score = min(cv * 50, 300)

            score = agg_bonus + aggregation_score + variance_score - id_penalty

            if score > best_score:
                best_score = score
                best_col = col

        return best_col
    @staticmethod
    def _parse_spec(response: str) -> Optional[ChartSpec]:
        try:
            cleaned = response.replace("```json", "").replace("```", "").strip()
            return ChartSpec.from_dict(json.loads(cleaned))
        except Exception as e:
            logger.error(f"Failed to parse chart JSON: {e}")
            return None
        
    @staticmethod
    def _recover_dtypes(df: pd.DataFrame) -> pd.DataFrame:
        """Try to coerce object columns back to numeric without destroying categoricals."""
        df = df.copy()
        for col in df.columns:
            if df[col].dtype == object:
                coerced = pd.to_numeric(df[col], errors="coerce")
                # Only adopt coercion if ≥80 % of non-null values survived
                if coerced.notna().sum() >= df[col].notna().sum() * 0.8:
                    df[col] = coerced
        return df