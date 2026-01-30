# scripts/run_e01_demo.py
from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys
from datetime import datetime

import pandas as pd

from src.viz import plot_sales_vs_ads_static, plot_sales_vs_ads_interactive


REQUIRED_COLUMNS = ["month", "sales", "ad_spend"]


def build_demo_data() -> pd.DataFrame:
    """构造 E01 教学用样例数据（默认数据源）。"""
    return pd.DataFrame({
        "month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
        "sales": [120, 135, 128, 160, 172, 190],
        "ad_spend": [20, 22, 21, 26, 27, 30],
    })


def load_data(input_path: str | None) -> tuple[pd.DataFrame, str]:
    """
    优先从 --input 读取 CSV；否则使用内置 demo 数据。
    返回：(df, data_source_desc)
    """
    if not input_path:
        return build_demo_data(), "built-in demo data"

    p = Path(input_path).expanduser()
    if not p.exists():
        raise FileNotFoundError(f"--input 文件不存在：{p}")

    if p.suffix.lower() != ".csv":
        raise ValueError(f"--input 目前仅支持 CSV 文件：{p}")

    df = pd.read_csv(p)
    return df, f"csv:{p}"


def validate_dataframe(df: pd.DataFrame) -> dict:
    """
    校验数据是否符合实验预期，返回验收信息（不抛异常，便于生成评分 JSON）。
    """
    info: dict = {
        "required_columns": REQUIRED_COLUMNS,
        "columns_present": list(df.columns),
        "missing_columns": [],
        "dtype_issues": [],
        "row_count": int(len(df)),
    }

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    info["missing_columns"] = missing

    # 基础类型检查（不强制，但给提示）
    if "sales" in df.columns and not pd.api.types.is_numeric_dtype(df["sales"]):
        info["dtype_issues"].append("sales 不是数值型（建议为 int/float）")
    if "ad_spend" in df.columns and not pd.api.types.is_numeric_dtype(df["ad_spend"]):
        info["dtype_issues"].append("ad_spend 不是数值型（建议为 int/float）")

    return info


def write_text_stats(df: pd.DataFrame, stats_path: Path) -> None:
    desc = df.describe(include="all")
    with stats_path.open("w", encoding="utf-8") as f:
        f.write("=== E01 Demo Data ===\n")
        f.write(df.to_string(index=False))
        f.write("\n\n=== Describe ===\n")
        f.write(desc.to_string())


def main() -> int:
    parser = argparse.ArgumentParser(description="E01 一键复现：数据 + 静态图 + 交互图输出 + 验收JSON")
    parser.add_argument(
        "--outdir",
        default="outputs/e01",
        help="输出目录（默认：outputs/e01）"
    )
    parser.add_argument(
        "--input",
        default=None,
        help="可选：输入 CSV 路径，例如 data/sample/e01.csv；不提供则使用内置 demo 数据"
    )
    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="只输出数据与描述统计，不生成图"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="严格模式：缺失必需字段或图输出失败时返回非0退出码（适合CI/自动验收）"
    )
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # 输出文件路径
    df_path = outdir / "e01_demo_data.csv"
    stats_path = outdir / "e01_demo_stats.txt"
    png_path = outdir / "sales_vs_ads_static.png"
    html_path = outdir / "sales_vs_ads_interactive.html"
    report_path = outdir / "e01_check_report.json"

    # 验收报告骨架
    report: dict = {
        "experiment": "E01",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "outdir": str(outdir),
        "input": args.input,
        "data_source": None,
        "checks": {},
        "artifacts": {
            "csv": str(df_path),
            "stats": str(stats_path),
            "static_png": str(png_path),
            "interactive_html": str(html_path),
        },
        "pass": False,
        "score": 0,
        "messages": [],
    }

    # 1) 读取数据（或内置）
    try:
        df, source_desc = load_data(args.input)
        report["data_source"] = source_desc
    except Exception as e:
        report["messages"].append(f"[ERROR] 数据读取失败：{e}")
        report["checks"]["data_load_ok"] = False
        _write_report(report_path, report)
        return 2

    report["checks"]["data_load_ok"] = True

    # 2) 数据校验
    vinfo = validate_dataframe(df)
    report["checks"]["data_validation"] = vinfo
    data_ok = (len(vinfo["missing_columns"]) == 0) and (vinfo["row_count"] > 0)

    # 尝试把关键列转数值（尽量容错，便于教学）
    if "sales" in df.columns:
        df["sales"] = pd.to_numeric(df["sales"], errors="coerce")
    if "ad_spend" in df.columns:
        df["ad_spend"] = pd.to_numeric(df["ad_spend"], errors="coerce")

    if not data_ok:
        report["messages"].append(
            f"[WARN] 数据不满足最小要求：缺失字段={vinfo['missing_columns']}，行数={vinfo['row_count']}"
        )

    # 3) 输出数据与统计（用于验收/检查环境）
    try:
        df.to_csv(df_path, index=False)
        write_text_stats(df, stats_path)
        report["checks"]["artifacts_csv_ok"] = df_path.exists()
        report["checks"]["artifacts_stats_ok"] = stats_path.exists()
    except Exception as e:
        report["messages"].append(f"[ERROR] 输出 csv/txt 失败：{e}")
        report["checks"]["artifacts_csv_ok"] = False
        report["checks"]["artifacts_stats_ok"] = False

    print(f"[OK] 数据已输出：{df_path}")
    print(f"[OK] 统计已输出：{stats_path}")

    # 4) 图输出（可选）
    plots_ok = True
    if args.no_plots:
        print("[SKIP] 已选择不生成图 (--no-plots)")
        report["checks"]["plots_skipped"] = True
        report["checks"]["static_png_ok"] = None
        report["checks"]["interactive_html_ok"] = None
        plots_ok = True
    else:
        report["checks"]["plots_skipped"] = False

        # 4.1 静态图 PNG
        try:
            fig = plot_sales_vs_ads_static(df)
            fig.savefig(png_path, dpi=160, bbox_inches="tight")
            report["checks"]["static_png_ok"] = png_path.exists()
            print(f"[OK] 静态图已输出：{png_path}")
        except Exception as e:
            plots_ok = False
            report["checks"]["static_png_ok"] = False
            report["messages"].append(f"[ERROR] 生成静态图失败：{e}")

        # 4.2 交互图 HTML
        try:
            fig_i = plot_sales_vs_ads_interactive(df)
            fig_i.write_html(str(html_path), include_plotlyjs="cdn")
            report["checks"]["interactive_html_ok"] = html_path.exists()
            print(f"[OK] 交互图已输出：{html_path}")
        except Exception as e:
            plots_ok = False
            report["checks"]["interactive_html_ok"] = False
            report["messages"].append(f"[ERROR] 生成交互图失败：{e}")

    # 5) 评分逻辑（简单、清晰、可解释）
    # 你可以把这套分值映射到课堂验收规则
    score = 0
    # 数据能读
    if report["checks"].get("data_load_ok"):
        score += 20
    # 字段齐全 + 有数据
    if data_ok:
        score += 30
    # 输出 csv/txt
    if report["checks"].get("artifacts_csv_ok"):
        score += 10
    if report["checks"].get("artifacts_stats_ok"):
        score += 10
    # 图输出（如果未跳过）
    if not args.no_plots:
        if report["checks"].get("static_png_ok"):
            score += 15
        if report["checks"].get("interactive_html_ok"):
            score += 15
    else:
        # 跳过图时，按“环境检查”给一个保底加分
        score += 10

    report["score"] = score

    # 通过判定：数据ok + 基础产物 ok +（若不跳过图则图也 ok）
    artifacts_ok = report["checks"].get("artifacts_csv_ok") and report["checks"].get("artifacts_stats_ok")
    plots_pass = True if args.no_plots else (report["checks"].get("static_png_ok") and report["checks"].get("interactive_html_ok"))

    passed = bool(data_ok and artifacts_ok and plots_pass and plots_ok)
    report["pass"] = passed

    # 输出验收 JSON
    _write_report(report_path, report)
    print(f"[OK] 验收报告已输出：{report_path}")

    print("\n=== 验收建议 ===")
    print(f"1) 检查 {outdir}/ 目录下是否生成 csv/txt/png/html/json 文件")
    print("2) 用浏览器打开 html，确认可 hover/zoom")
    print("3) 需要用真实数据时：加参数 --input data/sample/e01.csv")
    print("4) 若用于自动验收/CI：加参数 --strict（失败返回非0）")

    if args.strict and not passed:
        return 1
    return 0


def _write_report(report_path: Path, report: dict) -> None:
    """写入验收 JSON（独立封装，便于异常路径也能输出报告）。"""
    try:
        with report_path.open("w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    except Exception as e:
        # 最后兜底：写不了 JSON 就打印到 stderr
        print(f"[ERROR] 无法写入验收报告 {report_path}: {e}", file=sys.stderr)
        print(report, file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())