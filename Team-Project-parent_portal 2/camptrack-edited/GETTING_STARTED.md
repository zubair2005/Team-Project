# CampTrack - Quick Start Guide

## Installation (3 steps)

1. **Navigate to the camptrack directory**:

   ```bash
   cd camptrack
   ```

2. **Install dependencies**:

   ```bash
   python3 -m pip install --user -r requirements.txt
   ```

3. **Launch the application**:
   ```bash
   python3 camptrack.py
   ```

## First Login

The login screen will appear. Use these test accounts (all passwords are **blank** - just press Enter):

- **admin** - Administrator account
- **coordinator** - Logistics coordinator account
- **leader1** / **leader2** / **leader3** - Scout leader accounts

## Quick Feature Tour

### As Admin:

1. Go to **User Management** tab
2. Click on a user row to select it
3. Try buttons: "Edit name", "Enable", "Disable", "Delete"
4. Create a new leader: enter username, select "leader" role, click "Create User"
5. Switch to **Chat** tab to send messages

### As Coordinator:

1. **Camps** tab:

   - Set daily pay rate to 50
   - Create a camp (fill all fields, use dates like 2025-07-01 to 2025-07-05)
   - Select the camp row, click "Select" to edit it

2. **Stock Management** tab:

   - Select a camp from Camps tab first
   - Enter a top-up delta (e.g., +10)
   - Click "Apply"
   - View top-up history

3. **Analytics** tab:

   - View 5 auto-generated charts
   - Check shortage alerts panel

4. **Chat** tab:
   - Send/receive messages

### As Leader:

1. **Camps & Pay** tab:

   - Select an available camp
   - Click "Assign selected camp"
   - View pay summary at top

2. **Campers** tab:

   - Make sure a camp is assigned first (go back to Camps & Pay tab and select an assignment)
   - Click "Import campers from CSV"
   - Choose `sample_data/campers_sample.csv`
   - Click "Adjust food units" to customize per-camper food

3. **Activities** tab:

   - Click "Create activity"
   - Enter name and date
   - Select the activity, click "Bulk assign campers"
   - Multi-select campers (Ctrl/Cmd + click)

4. **Daily Reports** tab:

   - Click "Add/Edit report"
   - Enter date and notes

5. **Statistics** tab:

   - Click "Refresh Statistics" to view all camps you've led
   - See participation rates, food usage, and incident reports
   - Per-camp breakdown and overall summary

6. **Chat** tab:
   - Communicate with all users

## Tips

- **Window sizing**: Windows auto-resize when you login (Admin: 900×700, Coordinator: 1200×800, Leader: 1000×750)
- **Table selection**: Click directly on a row to select it before using action buttons
- **Tab navigation**: Click tab names at the top to switch views - no scrolling needed!
- **Multi-select**: Hold Ctrl (Windows/Linux) or Cmd (Mac) while clicking to select multiple items
- **Date format**: Always use YYYY-MM-DD (e.g., 2025-07-15)
- **Field requirements**:
  - Location, area, and type are required per the brief
  - Area is used for geographical grouping in analytics
- **Data persistence**: All changes are saved automatically to `data/camptrack.db`

## Common Workflows

### Import campers to a camp:

1. Login as coordinator, create a camp
2. Login as leader, assign to the camp (Camps & Pay tab)
3. Go to Campers tab
4. Click "Import campers from CSV"
5. Campers appear in table with default food units from camp

### Schedule an activity:

1. Login as leader with an assigned camp
2. Import some campers first (Campers tab)
3. Go to Activities tab
4. Click "Create activity", enter name/date
5. Select the activity row
6. Click "Bulk assign campers"
7. Select multiple campers, click "Assign"

### Check for food shortages:

1. Login as coordinator
2. Go to Analytics tab
3. Look at "Food shortage alerts" panel
4. Any camps with insufficient food will be listed

## Need Help?

See `README.md` for full documentation and `VIDEO_DEMO_OUTLINE.md` for a complete demonstration script.
