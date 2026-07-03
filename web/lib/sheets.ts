import { GoogleSpreadsheet } from "google-spreadsheet";
import { JWT } from "google-auth-library";
import { Expense } from "@/types/expense";

// Column indices match the bot's append_row order in main.py:
// 0:desc  1:amount  2:currency  3:exchangeRate  4:amountGs  5:date  6:category  7:bank  8:paymentMethod  9:invoiced
const COL = {
  DESC: 0,
  AMOUNT: 1,
  CURRENCY: 2,
  EXCHANGE_RATE: 3,
  AMOUNT_GS: 4,
  DATE: 5,
  CATEGORY: 6,
  BANK: 7,
  PAYMENT_METHOD: 8,
  INVOICED: 9,
} as const;

function getAuth() {
  const email = process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL;
  const key = process.env.GOOGLE_PRIVATE_KEY?.replace(/\\n/g, "\n");

  if (!email || !key) {
    throw new Error(
      "Missing GOOGLE_SERVICE_ACCOUNT_EMAIL or GOOGLE_PRIVATE_KEY env vars"
    );
  }

  return new JWT({
    email,
    key,
    scopes: ["https://www.googleapis.com/auth/spreadsheets.readonly"],
  });
}

function getCurrentSheetName() {
  return process.env.SHEET_NAME ?? new Date().getFullYear().toString();
}

// Parses the Gs amount formatted by the bot as "1.234.567" or "1.234.567,00"
function parseGs(val: unknown): number {
  const s = String(val ?? "0").replace(/\./g, "").replace(",", ".");
  return parseFloat(s) || 0;
}

function parseDate(val: unknown): string {
  if (!val) return "";
  if (val instanceof Date) {
    return val.toISOString().split("T")[0];
  }
  const s = String(val);
  const parts = s.split("/");
  if (parts.length === 3) {
    const [d, m, y] = parts;
    const year = y.length === 2 ? `20${y}` : y;
    return `${year}-${m.padStart(2, "0")}-${d.padStart(2, "0")}`;
  }
  return s;
}

function parseBoolean(val: unknown): boolean {
  const s = String(val ?? "").toUpperCase().trim();
  return s === "SI" || s === "SÍ" || s === "TRUE" || s === "YES" || s === "1";
}

export async function fetchExpenses(): Promise<Expense[]> {
  const spreadsheetId = process.env.GOOGLE_SPREADSHEET_ID;
  if (!spreadsheetId) throw new Error("Missing GOOGLE_SPREADSHEET_ID env var");

  const doc = new GoogleSpreadsheet(spreadsheetId, getAuth());
  await doc.loadInfo();

  const sheetName = getCurrentSheetName();
  const sheet = doc.sheetsByTitle[sheetName];
  if (!sheet) throw new Error(`Sheet "${sheetName}" not found`);

  await sheet.loadCells();
  const rowCount = sheet.rowCount;
  const expenses: Expense[] = [];

  // Start from row 1 (0-indexed) to skip the header row
  for (let r = 1; r < rowCount; r++) {
    const desc = sheet.getCell(r, COL.DESC).value;
    if (!desc) continue; // skip empty rows

    expenses.push({
      description: String(desc),
      amount: parseFloat(String(sheet.getCell(r, COL.AMOUNT).value ?? 0)),
      currency: String(sheet.getCell(r, COL.CURRENCY).value ?? ""),
      exchangeRate: parseFloat(
        String(sheet.getCell(r, COL.EXCHANGE_RATE).value ?? 1)
      ),
      amountGs: parseGs(sheet.getCell(r, COL.AMOUNT_GS).value),
      date: parseDate(sheet.getCell(r, COL.DATE).value),
      category: String(sheet.getCell(r, COL.CATEGORY).value ?? ""),
      bank: String(sheet.getCell(r, COL.BANK).value ?? ""),
      paymentMethod: String(sheet.getCell(r, COL.PAYMENT_METHOD).value ?? ""),
      invoiced: parseBoolean(sheet.getCell(r, COL.INVOICED).value),
    });
  }

  return expenses;
}
