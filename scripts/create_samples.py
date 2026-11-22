from pathlib import Path
from textwrap import wrap
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
REPORTS = {
    "library_report": """Library Loan Tracker
Problem: A college library records loans on paper and struggles to identify overdue books.
Objective: Build a Python desktop application for librarians to register books, issue loans and record returns.
Implementation: Tkinter provides forms. SQLite stores books, borrowers and loans. Each loan has a due date.
Workflow: The librarian searches a book identifier, selects a borrower and confirms the loan. Returning a book closes the loan and makes the book available again.
Validation: The application rejects missing borrower identifiers and prevents issuing a book that already has an active loan.
Evaluation: Manual tests covered issuing, returning and duplicate loan rejection. No numerical performance measurements are specified.
Limitations: This prototype supports a single librarian on one computer and has no online reservations.
Future work: Add barcode scanning and a browser interface. These features have not been implemented.""",
    "irrigation_report": """Soil Moisture Irrigation Monitor
Problem: Watering plants at fixed times can waste water when soil is already moist.
Objective: Build a sensor-based prototype that activates a water pump only when soil moisture falls below a configured threshold.
Architecture: An Arduino Uno reads a capacitive soil moisture sensor through an analog pin. A relay controls a low-voltage pump. Serial output displays readings and pump state.
Method: The prototype compares the current reading against a threshold calibrated using dry and wet soil samples. Hysteresis uses separate start and stop thresholds to avoid rapid switching.
Evaluation: Bench tests verified that dry soil starts the pump and wet soil stops it. The report provides no measured water savings or field trial results.
Limitations: Calibration depends on soil type. The prototype has no internet connectivity or weather forecast integration.
Future work: A reservoir level sensor could prevent running the pump dry. This is proposed, not implemented.""",
    "expense_report": """Personal Expense Dashboard
Problem: Students find it difficult to track spending across daily purchases.
Objective: Build a local dashboard that summarizes expenses by category and month.
Technology: Python, Streamlit and pandas. Input is a CSV file containing date, category and amount. The app does not connect to bank accounts.
Workflow: The user uploads CSV data. pandas validates required columns, converts dates and amounts, groups expenses, and computes monthly totals. Streamlit renders tables and bar charts.
Validation: Missing columns, invalid dates and negative amounts produce validation errors. Category names are stripped of surrounding spaces before aggregation.
Evaluation: Hand-calculated totals for a small example CSV were compared with dashboard output. The report does not specify dataset size or processing speed.
Limitations: Files are processed in memory and data is not persisted. There is no login or shared account feature.
Future improvements: Budget alerts and recurring payment detection are proposals only.""",
    "attendance_report": """QR Classroom Attendance Prototype
Problem: Calling student names consumes class time and leads to transcription mistakes.
Objective: Record attendance by scanning student QR identifiers.
Architecture: A Flask server accepts identifiers from a browser scanner. SQLite stores students, class sessions and attendance records. A unique constraint on student and session prevents duplicate entries.
Workflow: The teacher opens a session. The browser reads a QR identifier, submits it to the server and displays whether attendance was recorded or already exists.
Validation: Unknown student identifiers and inactive sessions are rejected. The teacher can export a session as CSV.
Evaluation: Manual tests checked valid identifiers, unknown identifiers, duplicate scans and closed sessions. No accuracy percentage or timing results are reported.
Limitations: Static QR codes can be shared between students. The prototype does not verify physical presence or use facial recognition.
Future improvements: Expiring session codes are proposed to reduce misuse. Deployment scalability has not been evaluated.""",
}


def main():
    for name, text in REPORTS.items():
        path = ROOT / "samples" / f"{name}.pdf"
        doc = canvas.Canvas(str(path))
        doc.setTitle(text.splitlines()[0])
        y = 790
        for paragraph in text.splitlines():
            for line in wrap(paragraph, 88):
                doc.drawString(40, y, line)
                y -= 16
            y -= 10
        doc.save()
    doc = canvas.Canvas(str(ROOT / "samples" / "blank_report.pdf"))
    doc.showPage()
    doc.save()
    (ROOT / "samples" / "invalid_report.pdf").write_text("This deliberately invalid PDF tests error handling.\n")


if __name__ == "__main__":
    main()
