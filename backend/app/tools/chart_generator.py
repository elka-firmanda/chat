"""
Chart Generator

Generate charts and visualizations using matplotlib or plotly.
Supports bar, line, pie, scatter, and histogram charts.
"""

import base64
import io
import json
import logging
from typing import Any, Dict, List, Optional, Union

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

logger = logging.getLogger(__name__)


class ChartGenerator:
    """Chart generator supporting multiple chart types."""

    def __init__(self, default_width: int = 10, default_height: int = 6):
        """
        Initialize the chart generator.

        Args:
            default_width: Default chart width in inches
            default_height: Default chart height in inches
        """
        self.default_width = default_width
        self.default_height = default_height
        matplotlib.rcParams["figure.figsize"] = (default_width, default_height)

    def generate_chart(
        self,
        chart_type: str,
        data: Dict[str, Any],
        title: Optional[str] = None,
        xlabel: Optional[str] = None,
        ylabel: Optional[str] = None,
        figsize: Optional[tuple] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate a chart of the specified type.

        Args:
            chart_type: Type of chart (bar, line, pie, scatter, histogram)
            data: Chart data dictionary with labels and values
            title: Chart title
            xlabel: X-axis label
            ylabel: Y-axis label
            figsize: Figure size tuple (width, height)
            **kwargs: Additional chart-specific options

        Returns:
            Dictionary with success, image_base64, chart_type, and error info
        """
        try:
            if figsize is None:
                figsize = (self.default_width, self.default_height)

            fig, ax = plt.subplots(figsize=figsize)

            chart_type = chart_type.lower().replace("-", "_")

            if chart_type == "bar":
                self._create_bar_chart(ax, data, **kwargs)
            elif chart_type == "line":
                self._create_line_chart(ax, data, **kwargs)
            elif chart_type == "pie":
                self._create_pie_chart(ax, data, **kwargs)
            elif chart_type == "scatter":
                self._create_scatter_chart(ax, data, **kwargs)
            elif chart_type == "histogram":
                self._create_histogram(ax, data, **kwargs)
            else:
                plt.close(fig)
                return {
                    "success": False,
                    "error": f"Unsupported chart type: {chart_type}",
                }

            if title:
                ax.set_title(title)
            if xlabel:
                ax.set_xlabel(xlabel)
            if ylabel:
                ax.set_ylabel(ylabel)

            ax.grid(True, linestyle="--", alpha=0.7)
            ax.legend() if ax.get_legend() else None

            plt.tight_layout()

            image_base64 = self._fig_to_base64(fig)
            plt.close(fig)

            return {
                "success": True,
                "image_base64": image_base64,
                "chart_type": chart_type,
                "format": "png",
            }

        except Exception as e:
            logger.error(f"Chart generation failed: {e}")
            plt.close("all")
            return {
                "success": False,
                "error": str(e),
            }

    def _create_bar_chart(self, ax, data: Dict[str, Any], **kwargs) -> None:
        """Create a bar chart."""
        labels = data.get("labels", data.get("x", []))
        values = data.get("values", data.get("y", []))

        if isinstance(labels, str):
            labels = json.loads(labels)
        if isinstance(values, str):
            values = json.loads(values)

        colors = kwargs.get("colors", None)
        if colors and isinstance(colors, str):
            colors = json.loads(colors)

        if colors and len(colors) == len(values):
            ax.bar(labels, values, color=colors)
        else:
            ax.bar(labels, values)

        if kwargs.get("horizontal", False):
            ax.barh(labels, values)

    def _create_line_chart(self, ax, data: Dict[str, Any], **kwargs) -> None:
        """Create a line chart."""
        labels = data.get("labels", data.get("x", []))
        values = data.get("values", data.get("y", []))

        if isinstance(labels, str):
            labels = json.loads(labels)
        if isinstance(values, str):
            values = json.loads(values)

        marker = kwargs.get("marker", "o")
        linestyle = kwargs.get("linestyle", "-")
        linewidth = kwargs.get("linewidth", 2)

        ax.plot(labels, values, marker=marker, linestyle=linestyle, linewidth=linewidth)

        if kwargs.get("fill", False):
            ax.fill_between(labels, values, alpha=0.3)

    def _create_pie_chart(self, ax, data: Dict[str, Any], **kwargs) -> None:
        """Create a pie chart."""
        labels = data.get("labels", data.get("x", []))
        values = data.get("values", data.get("y", []))

        if isinstance(labels, str):
            labels = json.loads(labels)
        if isinstance(values, str):
            values = json.loads(values)

        colors = kwargs.get("colors", None)
        if colors and isinstance(colors, str):
            colors = json.loads(colors)

        explode = kwargs.get("explode", [0] * len(values))

        ax.pie(
            values,
            labels=labels,
            autopct=kwargs.get("autopct", "%1.1f%%"),
            colors=colors,
            explode=explode,
            shadow=kwargs.get("shadow", False),
            startangle=kwargs.get("startangle", 0),
        )

    def _create_scatter_chart(self, ax, data: Dict[str, Any], **kwargs) -> None:
        """Create a scatter chart."""
        x_values = data.get("x", [])
        y_values = data.get("y", [])

        if isinstance(x_values, str):
            x_values = json.loads(x_values)
        if isinstance(y_values, str):
            y_values = json.loads(y_values)

        sizes = kwargs.get("sizes", None)
        if sizes and isinstance(sizes, str):
            sizes = json.loads(sizes)

        colors = kwargs.get("colors", None)
        if colors and isinstance(colors, str):
            colors = json.loads(colors)

        ax.scatter(
            x_values,
            y_values,
            s=sizes,
            c=colors,
            alpha=kwargs.get("alpha", 0.7),
            marker=kwargs.get("marker", "o"),
        )

    def _create_histogram(self, ax, data: Dict[str, Any], **kwargs) -> None:
        """Create a histogram."""
        values = data.get("values", data.get("y", []))

        if isinstance(values, str):
            values = json.loads(values)

        bins = kwargs.get("bins", "auto")
        if isinstance(bins, str):
            bins = {"auto": 10, "sqrt": int(np.sqrt(len(values)))}.get(bins, 10)

        ax.hist(
            values,
            bins=bins,
            alpha=kwargs.get("alpha", 0.7),
            edgecolor=kwargs.get("edgecolor", "black"),
        )

    def _fig_to_base64(self, fig) -> str:
        """Convert a matplotlib figure to base64 encoded PNG."""
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100)
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode("utf-8")
        buf.close()
        return image_base64

    def generate_from_json(
        self,
        json_data: str,
        chart_type: str = "bar",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate a chart from JSON string data.

        Args:
            json_data: JSON string containing chart data
            chart_type: Type of chart to generate
            **kwargs: Additional chart options

        Returns:
            Dictionary with success, image_base64, and error info
        """
        try:
            data = json.loads(json_data)
            return self.generate_chart(chart_type=chart_type, data=data, **kwargs)
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Invalid JSON data: {e}",
            }


default_chart_generator = ChartGenerator()


async def generate_chart(
    data: Dict[str, Any],
    chart_type: str = "bar",
    title: Optional[str] = None,
    xlabel: Optional[str] = None,
    ylabel: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Convenience function to generate a chart.

    Args:
        data: Chart data dictionary with labels and values
        chart_type: Type of chart (bar, line, pie, scatter, histogram)
        title: Chart title
        xlabel: X-axis label
        ylabel: Y-axis label
        **kwargs: Additional chart-specific options

    Returns:
        Dictionary with success, image_base64, chart_type, and error info
    """
    return default_chart_generator.generate_chart(
        chart_type=chart_type,
        data=data,
        title=title,
        xlabel=xlabel,
        ylabel=ylabel,
        **kwargs,
    )
