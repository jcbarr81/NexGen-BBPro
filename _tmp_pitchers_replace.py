from pathlib import Path
path = Path('ui/pitchers_dialog.py')
text = path.read_text()
old = "        for r, row in enumerate(rows):\n            # The player ID is stored as a hidden element at the end of the row.\n            *data, pid = row\n\n            for c, val in enumerate(data):\n                if COLUMNS[c] == \"SLOT\":\n                    item = SlotItem(str(val))\n                else:\n                    item = QtWidgets.QTableWidgetItem(str(val))\n                if c == 0:  # store player id in first column\n                    item.setData(QtCore.Qt.ItemDataRole.UserRole, pid)\n                if COLUMNS[c] in {\"NO.\", \"AS\", \"EN\", \"CO\", \"FB\", \"SL\", \"CU\", \"CB\", \"SI\", \"SCB\", \"KN\", \"MO\", \"FA\"}:\n                    if str(val).isdigit():\n                        item.setData(QtCore.Qt.ItemDataRole.DisplayRole, int(val))\n                item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)\n                self.setItem(r, c, item)\n"
new = '''        for r, row in enumerate(rows):
            *data, pid = row

            for c, val in enumerate(data):
                column = COLUMNS[c]
                if column == "SLOT":
                    item = SlotItem(str(val))
                    item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                    item.setTextAlignment(
                        QtCore.Qt.AlignmentFlag.AlignCenter
                        | QtCore.Qt.AlignmentFlag.AlignVCenter
                    )
                else:
                    align_left = column in {"Player Name", "ROLE", "B"}
                    item = NumericItem(val, align_left=align_left)
                if c == 0:
                    item.setData(QtCore.Qt.ItemDataRole.UserRole, pid)
                self.setItem(r, c, item)
'''
if old not in text:
    raise SystemExit('roster population block not found in pitchers dialog')
path.write_text(text.replace(old, new, 1))
