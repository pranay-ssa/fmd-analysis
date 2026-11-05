---
title: Timesheet folder
date: 2026-11-05
type: reference
status: active
where: timesheets/README.md
---

# Timesheets

This folder holds the blank timesheet template and one filled timesheet for each week.

## The standing rule

- Submit a timesheet every Monday by 4:00 PM, covering the week just ended. Send it to the requester and to every project lead for the work listed in the sheet.
- A timesheet must show 40 working hours for the week. A sheet with fewer hours, or with incomplete task details, is not approved.
- Tasks go in the Task column. Hours go in the date columns.
- The first submission is a one-off exception: it covers the week of 26 October 2026 and is due on Thursday 5 November 2026 by 4:00 PM, because the requirement arrived that morning. The Monday cycle starts with the submission on Monday 9 November 2026, covering the week of 2 to 6 November.

## Folder contents

| File | What it is | Rule |
|---|---|---|
| `Timesheet_TEMPLATE.xlsx` | Blank master with the agreed look | Never write into it. Never send it. |
| `Timesheet_<name>_<DDMon>_.xlsx` | One filled sheet per week | Create from the template every Monday. |
| `README.md` | This file | Update it when the process changes. |

- One file per week. The name carries the person and the Monday date: `Timesheet_pranay_pudota_26Oct_.xlsx` is the week that starts on 26 October.
- Keep the folder flat. No drafts, no old copies, no reports belong here.
- The workbook files stay local. They are not committed to the repository (`timesheets/*.xlsx` is in `.gitignore`). Only this README is version controlled.

## The sheet layout

| Region | Rows | Content |
|---|---|---|
| Header | 1-2 | Row 1 holds the dates in `d-mmm-yy` format. Row 2 holds the day names, Monday to Sunday. Columns A and B are merged across both rows. |
| Task block | 3 to the row above Total | Column A is the Sr. No. Column B is the task text, width 90. Columns C to I hold the hours for Monday to Sunday. |
| Total | last row | Cell A holds "Total". Cell B sums the seven day totals. Each day column sums its own task rows. |

- The Total row holds formulas. Never type a number into it.
- Excel recalculates the formulas each time the file opens.

## How to present the data

- Source: the current week's session doc in `docs/sessions/`. Tasks come from the dated entries, which record work that was done, not the plan.
- One row per piece of work. Write what was done and to what: "Train/test split rebuild on the merged record".
- No internal names. No file paths, script names, run-folder names, ticket ids, branch names or version tags. The reader cannot resolve them, and they make the sheet look unfinished.
- Every count names its population: "24 new and revised annotation files", not a bare number.
- Use the field's standard terms: train/test split, threshold, AUPRC, macro average precision, exact match. Define a genuinely new term in the same cell, in a few words.
- Whole hours only. Leave Saturday and Sunday blank. Never write 0 in a day column.
- Target 8 hours a day, Monday to Friday: 5 days x 8 hours = 40 hours.
- A blank day column means no work was logged on that day.

## Weekly procedure (Monday, before 4:00 PM)

1. Copy `Timesheet_TEMPLATE.xlsx`. Rename the copy to `Timesheet_<name>_<DDMon>_.xlsx` with that week's Monday date.
2. Set the dates. Type the Monday date in C1 (for example `9-Nov-26`) and fill C1 to I1 with the seven consecutive dates. Check that row 2 reads Monday to Sunday in order.
3. Open the week's session doc. Turn the dated entries into task rows, starting at row 3.
4. Put the hours in the day columns. Keep each weekday column at 8 hours.
5. Size the task block so the Total row sits directly under the last task:
   - To add a row: right-click a row inside the task block and choose Insert. Excel extends the sum formulas.
   - To remove a row: right-click the whole row and choose Delete.
   - Never insert or delete the Total row itself.
6. Renumber column A from 1 after any insert or delete.
7. Run the verification checklist below.
8. Send the file to the requester and to every project lead for the work listed.

## Verification checklist

- [ ] Header dates are that week's Monday to Sunday.
- [ ] Row 2 day names match the dates.
- [ ] Every weekday column totals 8 hours, and the grand total in cell B of the Total row shows 40.
- [ ] Saturday and Sunday columns are blank.
- [ ] Every task row has task text and at least one hour.
- [ ] Every hour is a whole number.
- [ ] Each cell of the Total row holds a formula, not a typed number.
- [ ] Column A runs 1, 2, 3 ... with no gaps.
- [ ] No path, script name, ticket id or version tag appears in any task.
- [ ] Font is Aptos Narrow, column B is 90 wide, all cells have thin borders.

## Editing rules (keep the agreed look)

- Font Aptos Narrow everywhere. Bold on the header row and on the Total row.
- Thin borders on every cell of the used range. Dates and hours centered.
- Column B is 90 wide. The date columns are 10 to 12 wide.
- No wrap text and no fixed row heights.
- If a task does not fit, shorten the task text. Do not widen column B and do not wrap it.

## Daily work tracking (why Monday is quick)

- Every working day, append a dated entry to the current week's session doc: `docs/sessions/<year>-W<week>.md`, where week is the ISO week number of those dates. Create the file with the standard five-line header if it does not exist yet.
- Write the entry the same day. A day with no entry is a day that cannot be logged on Monday.
- Entry format:

```
## 2026-11-05
- <what was done, in the wording you would use in the timesheet>: <result, one line>
- <second item>
```

- The session doc is the record of the week, and Monday's timesheet is built from it. `HANDOFF.md` stays state only: do not log daily work there.

## What never goes here

- Raw data, reports, decks or drafts.
- Any file meant for the repository other than this README.
