from stageConstants import *

class Category:

    def __init__(self, ds_id, _name, _columns):
        self.id = ds_id
        self.name = _name
        self.columns = _columns
        self.data_list = list()
        self.error_ix = 0
        self.last_ix = 1

        self.points_columns_changed = False
        self.youth_columns_changed = False
        self.gc_pnt_removed = False
        self.gc_changes = False
        self.team_changed = False

        self.gc_uci_changed = False
        self.row_length = len(self.columns) - 1
        

    def add_row(self, row):
        self.data_list.append(row)

    def remove_columns(self, remove_list):
        for col in remove_list: self.columns.remove(col)
        self.__update_row_length()

    def __update_columns__(self, new_cols):
        self.columns = new_cols
        self.__update_row_length()

    def __update_row_length(self):
        self.row_length = len(self.columns) - 1

class DataRow:

    def __init__(self, _id):
        self.stage_id = _id
        self.row = [self.stage_id]
        self.error_row = False

    def append(self, text):
        self.row.append(text)
        self.length = len(self.row)

    def pos(self, ix):
        return self.row[ix]

    def change_error(self):
        self.error_row = True

    def add_pos(self, ix, text):
        self.row[ix] = text