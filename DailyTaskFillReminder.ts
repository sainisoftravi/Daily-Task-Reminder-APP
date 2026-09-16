/**
 * Office Script: Daily Task Fill Reminder
 * 
 * Description: Checks the Daily Task worksheet for missing employee submissions
 * for a specific date.
 * 
 * Parameters:
 *  - sheetName: Name of the target worksheet (e.g. "Techincal Infra Team-Aug-2026")
 *  - targetDateStr: Date string to check (e.g. "15-Sep-26", "2026-09-15", or empty for today)
 */

interface ScriptResult {
  success: boolean;
  message: string;
  sheetName: string;
  targetDate: string;
  excelDate: string;
  totalEmployees: number;
  completedCount: number;
  missingCount: number;
  completedEmployees: string[];
  missingEmployees: string[];
}

function main(workbook: ExcelScript.Workbook, sheetName?: string, targetDateStr?: string): ScriptResult {
  // Default sheet name if not specified
  const targetSheetName = sheetName || "Techincal Infra Team-Aug-2026";
  const worksheet = workbook.getWorksheet(targetSheetName);

  if (!worksheet) {
    return {
      success: false,
      message: `Worksheet '${targetSheetName}' not found in workbook.`,
      sheetName: targetSheetName,
      targetDate: targetDateStr || "",
      excelDate: "",
      totalEmployees: 0,
      completedCount: 0,
      missingCount: 0,
      completedEmployees: [],
      missingEmployees: []
    };
  }

  const usedRange = worksheet.getUsedRange();
  if (!usedRange) {
    return {
      success: false,
      message: `Worksheet '${targetSheetName}' is empty.`,
      sheetName: targetSheetName,
      targetDate: targetDateStr || "",
      excelDate: "",
      totalEmployees: 0,
      completedCount: 0,
      missingCount: 0,
      completedEmployees: [],
      missingEmployees: []
    };
  }

  const texts = usedRange.getTexts();
  const values = usedRange.getValues();
  const rowCount = texts.length;
  const colCount = texts[0].length;

  if (rowCount < 2 || colCount < 2) {
    return {
      success: false,
      message: "Worksheet does not have sufficient rows or columns (Row 2 must contain employee names).",
      sheetName: targetSheetName,
      targetDate: targetDateStr || "",
      excelDate: "",
      totalEmployees: 0,
      completedCount: 0,
      missingCount: 0,
      completedEmployees: [],
      missingEmployees: []
    };
  }

  // Row index 1 corresponds to Row 2 in Excel (0-indexed array)
  const employeeNames: { name: string; colIndex: number }[] = [];
  for (let c = 1; c < colCount; c++) {
    const name = texts[1][c] ? texts[1][c].trim() : "";
    if (name.length > 0) {
      employeeNames.push({ name: name, colIndex: c });
    }
  }

  // Prepare target date matching formats
  let searchDateFormatted = "";
  if (targetDateStr && targetDateStr.trim().length > 0) {
    searchDateFormatted = targetDateStr.trim().toLowerCase();
  } else {
    // Default to today's date formatted as DD-MMM-YY e.g. 16-Sep-26
    const today = new Date();
    const day = String(today.getDate()).padStart(2, '0');
    const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const month = monthNames[today.getMonth()];
    const year = String(today.getFullYear()).slice(-2);
    searchDateFormatted = `${day}-${month}-${year}`.toLowerCase();
  }

  // Find target date row in Column A (Column index 0)
  let targetRowIndex = -1;
  let actualExcelDateCellText = "";

  for (let r = 2; r < rowCount; r++) {
    const cellText = texts[r][0] ? texts[r][0].trim() : "";
    const cellValue = values[r][0];

    // Normalize date strings for comparison
    const normText = cellText.toLowerCase();

    // Check direct string match or date component match
    if (
      normText === searchDateFormatted ||
      isDateMatch(normText, cellValue, searchDateFormatted)
    ) {
      targetRowIndex = r;
      actualExcelDateCellText = cellText;
      break;
    }
  }

  if (targetRowIndex === -1) {
    return {
      success: false,
      message: `Date '${targetDateStr}' not found in Column A of '${targetSheetName}'.`,
      sheetName: targetSheetName,
      targetDate: targetDateStr || searchDateFormatted,
      excelDate: "",
      totalEmployees: employeeNames.length,
      completedCount: 0,
      missingCount: employeeNames.length,
      completedEmployees: [],
      missingEmployees: employeeNames.map(e => e.name)
    };
  }

  // Check task completion for each employee on the found date row
  const completedEmployees: string[] = [];
  const missingEmployees: string[] = [];

  for (const emp of employeeNames) {
    const cellContent = texts[targetRowIndex][emp.colIndex] ? texts[targetRowIndex][emp.colIndex].trim() : "";
    if (cellContent.length > 0) {
      completedEmployees.push(emp.name);
    } else {
      missingEmployees.push(emp.name);
    }
  }

  return {
    success: true,
    message: "Daily task check completed.",
    sheetName: targetSheetName,
    targetDate: targetDateStr || searchDateFormatted,
    excelDate: actualExcelDateCellText || searchDateFormatted,
    totalEmployees: employeeNames.length,
    completedCount: completedEmployees.length,
    missingCount: missingEmployees.length,
    completedEmployees: completedEmployees,
    missingEmployees: missingEmployees
  };
}

/**
 * Helper function to match various date formats (e.g. 15-Sep-26, 2026-09-15, Excel serial dates)
 */
function isDateMatch(cellTextNorm: string, cellValue: any, targetStrNorm: string): boolean {
  if (cellTextNorm === targetStrNorm) return true;
  
  // Try comparing formatted dates (e.g. 15-Sep-2026 vs 15-Sep-26)
  const cleanCell = cellTextNorm.replace(/[^a-z0-9]/g, '');
  const cleanTarget = targetStrNorm.replace(/[^a-z0-9]/g, '');
  if (cleanCell.length > 0 && cleanTarget.length > 0 && (cleanCell.includes(cleanTarget) || cleanTarget.includes(cleanCell))) {
    return true;
  }

  return false;
}
