"""Flask web portal for the Construction Cost Estimator."""

import sys
from pathlib import Path

from flask import Flask, render_template, request, send_file

from construction_estimator.database import HistoricalDatabase
from construction_estimator.estimator import EstimatorEngine
from construction_estimator.export_xlsx import generate_gmp_xlsx


def _parse_float(val, default=0.0):
    """Safely parse a form value to float, handling empty strings."""
    val = (val or "").replace(",", "").strip()
    return float(val) if val else default


def _parse_int(val, default=0):
    """Safely parse a form value to int, handling empty strings."""
    val = (val or "").replace(",", "").strip()
    return int(float(val)) if val else default

app = Flask(__name__)
app.jinja_env.globals.update(zip=zip)

DB_PATH = Path(__file__).parent / "historical_data.json"
db = HistoricalDatabase()
db.load(str(DB_PATH))
engine = EstimatorEngine(db)


@app.template_filter("currency")
def currency_filter(value):
    try:
        return f"${value:,.0f}"
    except (TypeError, ValueError):
        return "$0"


@app.template_filter("currency2")
def currency2_filter(value):
    try:
        return f"${value:,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


@app.template_filter("pct")
def pct_filter(value):
    try:
        return f"{value:.0%}"
    except (TypeError, ValueError):
        return "0%"


@app.route("/")
def index():
    return render_template(
        "index.html",
        projects=db.projects,
        estimate=None,
        db_cost_codes=len(db.get_all_cost_codes()),
    )


@app.route("/estimate", methods=["POST"])
def estimate():
    try:
        p = _build_estimate_params(request.form)
        cost_codes = len(db.get_all_cost_codes())

        if p["total_gba"] <= 0 or p["units"] <= 0:
            return render_template(
                "index.html",
                projects=db.projects,
                estimate=None,
                error="Total GBA and total units must be greater than zero.",
                form=request.form,
                db_cost_codes=cost_codes,
            )

        result = engine.estimate(
            gba_concrete=p["gba_concrete"],
            gba_wood=p["gba_wood"],
            units=p["units"],
            unit_mix=p["unit_mix"],
            num_floors=p["podium_levels"] + p["wood_levels"],
            gc_fee_pct=p["gc_fee"],
            bonding_pct=p["bonding"],
            admin_pct=p["admin"],
            podium_levels=p["podium_levels"],
            wood_levels=p["wood_levels"],
            elevator_count=p["elevator_count"],
            elevator_stops=p["elevator_stops"],
            lot_size=p["lot_size"],
            shored_area=p["shored_area"],
        )

        return render_template(
            "index.html",
            projects=db.projects,
            estimate=result,
            form=request.form,
            db_cost_codes=cost_codes,
            gba_concrete=p["gba_concrete"],
            gba_wood=p["gba_wood"],
        )

    except (ValueError, TypeError) as e:
        return render_template(
            "index.html",
            projects=db.projects,
            estimate=None,
            error=f"Invalid input: {e}",
            form=request.form,
            db_cost_codes=len(db.get_all_cost_codes()),
        )


def _build_estimate_params(form):
    """Extract estimate parameters from form data."""
    gba_concrete = _parse_float(form.get("gba_concrete"))
    gba_wood = _parse_float(form.get("gba_wood"))
    podium_levels = _parse_int(form.get("podium_levels"), 1)
    wood_levels = _parse_int(form.get("wood_levels"), 4)
    lot_size = _parse_float(form.get("lot_size"))
    shored_area = _parse_float(form.get("shored_area"))
    parking_spaces = _parse_int(form.get("parking_spaces"))

    units_0br = _parse_int(form.get("units_0br"))
    units_1br = _parse_int(form.get("units_1br"))
    units_2br = _parse_int(form.get("units_2br"))
    units_3br = _parse_int(form.get("units_3br"))

    unit_mix = {"0BR": units_0br, "1BR": units_1br, "2BR": units_2br, "3BR": units_3br}
    units = units_0br + units_1br + units_2br + units_3br

    elevator_count = _parse_int(form.get("elevator_count"), 2)
    elevator_stops = _parse_int(form.get("elevator_stops"), 7)

    gc_fee = _parse_float(form.get("gc_fee"), 6.0)
    bonding = _parse_float(form.get("bonding"), 1.0)
    admin = _parse_float(form.get("admin"), 2.0)

    total_gba = gba_concrete + gba_wood
    project_name = form.get("project_name", "").strip() or "New Project"

    return {
        "gba_concrete": gba_concrete,
        "gba_wood": gba_wood,
        "total_gba": total_gba,
        "podium_levels": podium_levels,
        "wood_levels": wood_levels,
        "lot_size": lot_size,
        "shored_area": shored_area,
        "parking_spaces": parking_spaces,
        "unit_mix": unit_mix,
        "units": units,
        "elevator_count": elevator_count,
        "elevator_stops": elevator_stops,
        "gc_fee": gc_fee,
        "bonding": bonding,
        "admin": admin,
        "project_name": project_name,
    }


@app.route("/download", methods=["POST"])
def download_xlsx():
    """Generate and download GMP Hard Cost Budget XLSX."""
    try:
        p = _build_estimate_params(request.form)

        if p["total_gba"] <= 0 or p["units"] <= 0:
            return "GBA and units must be > 0", 400

        result = engine.estimate(
            gba_concrete=p["gba_concrete"],
            gba_wood=p["gba_wood"],
            units=p["units"],
            unit_mix=p["unit_mix"],
            num_floors=p["podium_levels"] + p["wood_levels"],
            gc_fee_pct=p["gc_fee"],
            bonding_pct=p["bonding"],
            admin_pct=p["admin"],
            podium_levels=p["podium_levels"],
            wood_levels=p["wood_levels"],
            elevator_count=p["elevator_count"],
            elevator_stops=p["elevator_stops"],
            lot_size=p["lot_size"],
            shored_area=p["shored_area"],
        )

        buf = generate_gmp_xlsx(result, p)
        fname = f"{p['project_name'].replace(' ', '_')}_GMP_Budget.xlsx"

        return send_file(
            buf,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=fname,
        )
    except Exception as e:
        return f"Error generating XLSX: {e}", 500


if __name__ == "__main__":
    print(f"Loaded {db.project_count} historical projects from {DB_PATH}")
    app.run(debug=True, port=5000)
