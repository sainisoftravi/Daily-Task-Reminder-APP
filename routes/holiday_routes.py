#!/usr/bin/env python3
"""
Holiday Calendars Management Blueprint
Handles `/holidays` management view, calendar creation, date assignment, and Excel import/export.
"""

import io
import datetime
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, send_file
import database

holiday_bp = Blueprint('holiday_bp', __name__)

def log_event(msg: str, level: str = "INFO"):
    database.log_to_db(msg, level)


@holiday_bp.route("/holidays")
def holidays_page():
    if not session.get("user"):
        return redirect(url_for("auth_bp.login_page"))

    calendars = database.get_all_holiday_calendars()
    return render_template("holidays.html", active_page="holidays", calendars=calendars)


@holiday_bp.route("/api/holiday-calendars", methods=["GET"])
def api_get_holiday_calendars():
    if not session.get("user"):
        return jsonify({"success": False, "error": "Authentication required"}), 401
    calendars = database.get_all_holiday_calendars()
    return jsonify({"success": True, "calendars": calendars})


@holiday_bp.route("/api/holiday-calendars/<cal_id>/download-template", methods=["GET"])
@holiday_bp.route("/api/holiday-calendars/download-template", methods=["GET"])
def api_download_holiday_template(cal_id=None):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Holiday Calendar Syntax"
    ws.views.sheetView[0].showGridLines = True

    # Styling Palettes
    HEADER_FILL = PatternFill(start_color="7E22CE", end_color="7E22CE", fill_type="solid")
    HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    TITLE_FONT = Font(name="Calibri", size=14, bold=True, color="6B21A8")
    SUBTITLE_FONT = Font(name="Calibri", size=10, italic=True, color="6B7280")
    ZEBRA_FILL = PatternFill(start_color="F9FAFB", end_color="F9FAFB", fill_type="solid")
    HOLIDAY_FILL = PatternFill(start_color="F3E8FF", end_color="F3E8FF", fill_type="solid")

    THIN_BORDER = Border(
        left=Side(style='thin', color='E5E7EB'),
        right=Side(style='thin', color='E5E7EB'),
        top=Side(style='thin', color='E5E7EB'),
        bottom=Side(style='thin', color='E5E7EB')
    )

    cal = None
    cal_name = "Holiday Calendar"
    existing_dates = []
    if cal_id and cal_id != "default":
        cal = database.get_holiday_calendar_by_id(cal_id)
        if cal:
            cal_name = cal.get("name", "Holiday Calendar")
            existing_dates = cal.get("dates", [])

    # Header Row (Row 1) - Clean format starting directly at Row 1
    headers = ["Date (YYYY-MM-DD)", "Day of Week", "Festival / Holiday Name"]
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center" if col_num <= 2 else "left", vertical="center")

    # Data Rows (Starting at Row 2)
    start_row = 2
    if existing_dates:
        for idx, d in enumerate(existing_dates):
            r = start_row + idx
            dt_str = d.get("date_str", "")
            weekday_str = ""
            try:
                dt_obj = datetime.datetime.strptime(dt_str, "%Y-%m-%d")
                weekday_str = dt_obj.strftime("%A")
            except Exception:
                weekday_str = ""

            h_name = d.get("holiday_name", "")

            c1 = ws.cell(row=r, column=1, value=dt_str)
            c2 = ws.cell(row=r, column=2, value=weekday_str)
            c3 = ws.cell(row=r, column=3, value=h_name)

            c1.alignment = Alignment(horizontal="center", vertical="center")
            c2.alignment = Alignment(horizontal="center", vertical="center")
            c3.alignment = Alignment(horizontal="left", vertical="center")

            fill = HOLIDAY_FILL if idx % 2 == 0 else ZEBRA_FILL
            for cell in (c1, c2, c3):
                cell.fill = fill
                cell.border = THIN_BORDER
                cell.font = Font(name="Calibri", size=11)
    else:
        sample_rows = [
            ("2026-01-26", "Monday", "Republic Day"),
            ("2026-03-25", "Wednesday", "Holi Festival"),
            ("2026-08-15", "Saturday", "Independence Day"),
            ("2026-10-20", "Tuesday", "Diwali Festival"),
            ("2026-12-25", "Friday", "Christmas Day")
        ]
        for idx, (dt_str, wk, h_name) in enumerate(sample_rows):
            r = start_row + idx
            c1 = ws.cell(row=r, column=1, value=dt_str)
            c2 = ws.cell(row=r, column=2, value=wk)
            c3 = ws.cell(row=r, column=3, value=h_name)

            c1.alignment = Alignment(horizontal="center", vertical="center")
            c2.alignment = Alignment(horizontal="center", vertical="center")
            c3.alignment = Alignment(horizontal="left", vertical="center")

            fill = HOLIDAY_FILL if idx % 2 == 0 else ZEBRA_FILL
            for cell in (c1, c2, c3):
                cell.fill = fill
                cell.border = THIN_BORDER
                cell.font = Font(name="Calibri", size=11)

    # Column Dimensions
    ws.column_dimensions['A'].width = 24
    ws.column_dimensions['B'].width = 20
    ws.column_dimensions['C'].width = 42

    out = io.BytesIO()
    wb.save(out)
    out.seek(0)

    filename_clean = cal_name.replace(" ", "_").lower()
    return send_file(
        out,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"{filename_clean}_syntax.xlsx"
    )


@holiday_bp.route("/api/holiday-calendars", methods=["POST"])
def api_save_holiday_calendar():
    if not session.get("user"):
        return jsonify({"success": False, "error": "Authentication required"}), 401
    user_role = session["user"].get("role", "employee")
    if user_role not in ["admin", "manager"]:
        return jsonify({"success": False, "error": "Forbidden: Only Admin or Manager can manage holiday calendars."}), 403

    data = request.json or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"success": False, "error": "Calendar Name is required."}), 400

    cal_id = database.save_holiday_calendar(data)
    log_event(f"Admin/Manager saved Holiday Calendar '{name}' (ID: {cal_id}).")
    return jsonify({"success": True, "calendar_id": cal_id, "message": f"Successfully saved Holiday Calendar '{name}'."})


@holiday_bp.route("/api/holiday-calendars/<cal_id>", methods=["DELETE"])
def api_delete_holiday_calendar(cal_id):
    if not session.get("user"):
        return jsonify({"success": False, "error": "Authentication required"}), 401
    user_role = session["user"].get("role", "employee")
    if user_role not in ["admin", "manager"]:
        return jsonify({"success": False, "error": "Forbidden: Only Admin or Manager can delete holiday calendars."}), 403

    database.delete_holiday_calendar(cal_id)
    log_event(f"Admin/Manager deleted Holiday Calendar ID '{cal_id}'.")
    return jsonify({"success": True, "message": f"Successfully deleted Holiday Calendar."})


@holiday_bp.route("/api/holiday-calendars/<cal_id>/dates", methods=["GET"])
def api_get_holiday_dates(cal_id):
    if not session.get("user"):
        return jsonify({"success": False, "error": "Authentication required"}), 401
    cal = database.get_holiday_calendar_by_id(cal_id)
    if not cal:
        return jsonify({"success": False, "error": "Holiday Calendar not found."}), 404
    return jsonify({"success": True, "calendar": cal, "dates": cal.get("dates", [])})


@holiday_bp.route("/api/holiday-calendars/<cal_id>/dates", methods=["POST"])
def api_save_holiday_dates(cal_id):
    if not session.get("user"):
        return jsonify({"success": False, "error": "Authentication required"}), 401
    user_role = session["user"].get("role", "employee")
    if user_role not in ["admin", "manager"]:
        return jsonify({"success": False, "error": "Forbidden: Only Admin or Manager can edit holiday dates."}), 403

    cal = database.get_holiday_calendar_by_id(cal_id)
    if not cal:
        return jsonify({"success": False, "error": "Holiday Calendar not found."}), 404

    data = request.json or {}
    dates_input = data.get("dates")
    if not dates_input and (data.get("date_str") or data.get("date")):
        dates_input = [data]

    if not isinstance(dates_input, list) or not dates_input:
        return jsonify({"success": False, "error": "No holiday date records provided."}), 400

    saved_count = database.save_holiday_dates_batch(cal_id, dates_input)
    log_event(f"Saved {saved_count} holiday dates for Calendar '{cal.get('name')}' (ID: {cal_id}).")
    return jsonify({"success": True, "saved_count": saved_count, "message": f"Successfully saved {saved_count} holiday date(s)."})


@holiday_bp.route("/api/holiday-calendars/dates/<date_id>", methods=["DELETE"])
def api_delete_holiday_date(date_id):
    if not session.get("user"):
        return jsonify({"success": False, "error": "Authentication required"}), 401
    user_role = session["user"].get("role", "employee")
    if user_role not in ["admin", "manager"]:
        return jsonify({"success": False, "error": "Forbidden: Only Admin or Manager can delete holiday dates."}), 403

    database.delete_holiday_date(date_id)
    return jsonify({"success": True, "message": "Deleted holiday date."})


@holiday_bp.route("/api/holiday-calendars/<cal_id>/import-excel", methods=["POST"])
def api_import_holiday_excel(cal_id):
    if not session.get("user"):
        return jsonify({"success": False, "error": "Authentication required"}), 401
    user_role = session["user"].get("role", "employee")
    if user_role not in ["admin", "manager"]:
        return jsonify({"success": False, "error": "Forbidden: Only Admin or Manager can import Excel files."}), 403

    cal = database.get_holiday_calendar_by_id(cal_id)
    if not cal:
        return jsonify({"success": False, "error": "Holiday Calendar not found."}), 404

    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No Excel file uploaded."}), 400

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({"success": False, "error": "No file selected."}), 400

    import openpyxl

    try:
        wb = openpyxl.load_workbook(file, data_only=True)
        ws = wb.active
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to parse Excel workbook: {str(e)}"}), 400

    rows = list(ws.iter_rows(values_only=True))
    if not rows or len(rows) < 2:
        return jsonify({"success": False, "error": "The uploaded Excel file contains no holiday date rows."}), 400

    header_row_idx = 3 # Default to row 4 (0-indexed 3)
    found_header = False
    for idx, r in enumerate(rows[:10]):
        if not any(r):
            continue
        row_strs = [str(c or "").strip().lower() for c in r if c is not None]
        # Skip merged title/instruction rows with only 1 filled cell
        if len(row_strs) < 2:
            continue

        has_date_hdr = any(s.startswith("date") or "date (" in s or s == "date" for s in row_strs) or any("date" in s for s in row_strs)
        has_name_hdr = any(any(k in s for k in ["festival", "holiday name", "holiday", "event", "name"]) for s in row_strs)

        if has_date_hdr and has_name_hdr:
            header_row_idx = idx
            found_header = True
            break

    header = [str(c or "").strip().lower() for c in rows[header_row_idx]]
    date_col = next((i for i, h in enumerate(header) if "date" in h), 0)
    
    # Ensure name_col is distinct from date_col
    name_col = next((i for i, h in enumerate(header) if i != date_col and any(x in h for x in ["festival", "holiday", "name", "event", "description"])), -1)
    if name_col == -1 or name_col == date_col:
        name_col = 2 if len(header) > 2 else 1

    dates_list = []
    for r in rows[header_row_idx + 1:]:
        if not any(r):
            continue

        raw_date = str(r[date_col]).strip() if len(r) > date_col and r[date_col] is not None else ""
        raw_name = str(r[name_col]).strip() if len(r) > name_col and r[name_col] is not None else ""

        if not raw_date:
            continue

        clean_date = ""
        if isinstance(r[date_col], (datetime.datetime, datetime.date)):
            clean_date = r[date_col].strftime("%Y-%m-%d")
        else:
            for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%b-%Y"):
                try:
                    dt = datetime.datetime.strptime(raw_date.split(" ")[0], fmt)
                    clean_date = dt.strftime("%Y-%m-%d")
                    break
                except Exception:
                    continue

        if not clean_date:
            continue

        # Fallback if raw_name accidentally matches clean_date or is empty
        if not raw_name or raw_name == clean_date or raw_name == raw_date:
            # Check if there is another column with a string
            other_name = next((str(r[i]).strip() for i in range(len(r)) if i != date_col and r[i] and str(r[i]).strip() != clean_date and str(r[i]).strip() != raw_date), "")
            if other_name:
                raw_name = other_name
            else:
                raw_name = "Festival Holiday"

        dates_list.append({
            "date_str": clean_date,
            "holiday_name": raw_name
        })

    if not dates_list:
        return jsonify({"success": False, "error": "No valid holiday dates could be extracted from the uploaded Excel file."}), 400

    imported_count = database.save_holiday_dates_batch(cal_id, dates_list)
    log_event(f"Imported {imported_count} holiday dates from Excel into Calendar '{cal.get('name')}'.")
    return jsonify({"success": True, "imported_count": imported_count, "message": f"Successfully imported {imported_count} holiday date(s)." if imported_count else "No new dates imported."})
