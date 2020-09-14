import requests
from stageConstants import *
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup

def fix_time(data, time_col):
    tdf = data[data[time_col] == ',,'][[time_col]]
    to_change_ix = list(tdf.index)
    data.loc[data.index.isin(to_change_ix), time_col] = None
    data[time_col] = data[time_col].fillna(method='ffill')
    return data

def is_not_int(value):
    ''' Assesses whether value is an int or not'''
    try:
        int(value)
        return False
    except ValueError:
        return True

def get_text(cell):
    ''' Return the text from the html cell. '''
    # some cells have a span or hyperlink element with text in it
    if cell.a != None:
        url = cell.a.get('href')
        if url.startswith('rider/') or url.startswith('race/'):
            return url, cell.a.get_text()
        return cell.a.get_text()
    elif cell.span != None:
        return cell.span.get_text()
    else:
        return cell.get_text()

def is_rider_url(text):
    result = re.search(r'rider\/([\w-])*', text)
    if result is None: return False
    else: return True

def is_change(text):
    # options are ▲x, ▼y, - 
    result = re.search(r'((▲\d)|(▼\d))', text)
    if result is None and text != '-': return False
    else: return True

class Stage():
    def __init__(self, stage_ID, stage_url):
        self.ID = stage_ID
        self.stage_url = stage_url
        self.__read_html__()

        self.stage_data = None
        self.team_df = None
        self.all_df = None
        self.__init_datasets__()
        self.column_subsets = {
            'gc': ['bib', 'uciGc'],
            'points': ['bib', 'greenPos', 'greenPnts'], \
            'youth': ['bib', 'youthPos', 'youthTime'], \
            'kom': ['bib', 'komPos', 'komPnts'], \
            'teams': ['teamPos', 'empty', 'teamName', 'teamTime', 'DNF']
        }
        self.all_labels = get_all_df_columns()
        
    def __read_html__(self):
        page = requests.get(self.stage_url)
        self.stage_html = BeautifulSoup(page.content, 'html.parser')
        h1 = str(self.stage_html.h1)
        h2 = str(self.stage_html.h2)
        if 'One day race' in h2:
            print('ONE DAY RACE')
            self.stage_type = ONE_DAY_RACE
        elif 'ITT (CC)' in h1 or 'ITT (NC)' in h1:
            print('ITT (CC)/ (NC)')
            self.stage_type = ITT_CC
        elif '(ITT)' in h2 or 'Time trial' in h2:
            print('(ITT)')
            self.stage_type = ITT
        elif 'Prev' in str(self.stage_html):
            print('OTHER TOUR STAGE')
            self.stage_type = OTHER_TOUR_STAGE
        elif 'Prologue' in h2:
            print('PROLOGUE')
            self.stage_type = PROLOGUE
        elif 'TTT' in h2:
            print('TTT')
            self.stage_type = TTT
        else:
            print('FIRST_STAGE_IN_TOUR')
            self.stage_type = FIRST_STAGE_IN_TOUR
        
    def __init_datasets__(self):
        stage_columns = get_stage_columns(self.stage_type)
        self.__update_datasets__(stage_columns)
        
    def __update_datasets__(self, new_ds):
        self.stage_datasets = new_ds
        self.__init_row_lengths()
        
    def __init_row_lengths(self):
        self.row_lengths = list()
        for dataset_name in self.stage_datasets.keys():
            self.row_lengths.append(len(self.stage_datasets[dataset_name]) - 1)
    
    def verify_datasets(self):
        div_res_left = self.stage_html.find_all('div', class_="res-left")
        li_list = div_res_left[0].find_all('li')
        html_datasets_list = [get_text(li)[1].lower() for li in li_list]
        print('HTML datasets list: {}'.format(html_datasets_list))
        if len(html_datasets_list) > 0:
            new_stage_datasets = {}
            for key in html_datasets_list:
                if key == 'prol.':
                    key = 'stage'
                elif self.stage_type != TTT and key == '':
                    key = 'stage'
                if key not in self.stage_datasets.keys() and key != '':
                    print('KEY PROBLEM!!! Want ', key)
                    raise ValueError
                if key != '':
                    # time trial positions
                    new_stage_datasets[key] = self.stage_datasets[key]
            print('Old stage datasets: ', self.stage_datasets.keys())
            print('New stage datasets: ', new_stage_datasets.keys())
            self.__update_datasets__(new_stage_datasets)
        
    def scrape_stage_data(self, print_row=False):
        html = self.stage_html
        self.row_lengths
        # all the racers are in a table data cell ('td')
        # intialise variables
        td_cells = html.find_all('td')
        # there can be up to 6 data tables on an html page
        self.stage_data = {}
        print('DRL@@:', self.row_lengths)
        
        ds_names = list(self.stage_datasets.keys())
        data_id = 0
        ds_name = ds_names[data_id]
        ds_columns_changed = False
        row_length = self.row_lengths[data_id]

        old_length = row_length
        last_list_length = 0
        data_list = list()
        error_list = list()
        error_row = False

        row = [self.ID]
        last_ix = 1
        error_ix = 0

        # itterate through all data cells and append their text values to a row
        print('TD: number of cells {}'.format(len(td_cells)))
        for td_ix, cell in enumerate(td_cells):
            text = get_text(cell)
            if type(text) is type('str'):
                #print(row)
                row.append(text)
            else:
                row.append(text[0])
                row.append(text[1])

            if len(row) == 2:
                # the second element in the row is the position the rider finished
                # if the rider did not finish, the position will not be an int
                # it will be: DNF, DNS, OTL
                not_int = is_not_int(row[1])

                if not_int:
                    error_row = True

                if not not_int and int(row[1]) == 1 and len(data_list) != 0:
                    # a new table begins with a rider being placed 1st
                    # save the complete previous table to the data map
                    self.__add_data_list__(data_id, data_list)
                    old_length = row_length

                    #reinitialise variables
                    data_id += 1
                    ds_name = ds_names[data_id]
                    points_columns_changed = False
                    youth_columns_changed = False
                    gc_pnt_removed = False
                    gc_changes = False
                    data_list = list()
                    last_ix = 1
                    error_row = False
                
                    row_length = self.row_lengths[data_id]
                    print('OLD ROW: {}, NEW ROW: {}'.format(old_length, row_length))

            #if ds_name == 'gc':
            #   print(row)
            
            if self.stage_type in [ITT_CC, ONE_DAY_RACE] and len(row) in [3, 4]:
                # some ITTs have no bib numbers for the riders
                # we make it the postition number
                row = self.__check_bib__(row, last_ix + error_ix)

            if self.stage_type == OTHER_TOUR_STAGE:
                if ds_name in ['points', 'kom'] and not points_columns_changed and len(row) in [4, 5]:
                    # in the Other stages, kom or green points may be awarded only in later stages
                    # for the first time. Until that point there wil be no changes in the points 
                    # classifications. Bu default change columns are included in the dataset
                    print('ROW LENGTH IS: {} and this is the row so far {}'.format(row_length, row))
                    self.__check_change__(data_id, ds_name, row)
                    points_columns_changed = True
                
                if ds_name == 'youth' and not youth_columns_changed and len(row) == 4:
                    # for some reason some races don't have the youth change columns for their races
                    text = row[3]

                    if not is_change(text):
                        # there are no change columns
                        self.__remove_change_columns__(data_id, ds_name)
                        youth_columns_changed = True
                
                if ds_name == 'gc':
                    if not gc_pnt_removed and len(row) == 12:
                        # repeated
                        text = row[11]
                        print('gc is col text change (should be true)', text, text == '..')
                        if text == '..':
                            self.__remove_change_columns__(data_id, ds_name)
                            gc_pnt_removed = True

                    if not gc_changes and len(row) in [4, 5]:
                        text = row[3]
                        print('gc is col text change (should be true)', text, not is_change(text), len(row))
                        if not is_change(text):
                            self.__remove_change_columns__(data_id, ds_name, 1)
                            gc_changes = True

                row_length = self.row_lengths[data_id]
                #print('ROW LENGTH IS: aim for {}, current {}'.format(row_length, len(row)))
                
                
            if ds_name == 'gc':
                # there are uci gc points awarded to high category races/ stages
                # not all stages have them. the position in the row varies for stage types
                if self.stage_type in [PROLOGUE, FIRST_STAGE_IN_TOUR] and len(row) == 8:
                    row = self.__check_uciGc__(row)
                elif self.stage_type in [OTHER_TOUR_STAGE] and len(row) == 10:
                    row = self.__check_uciGc__(row)
            
            if error_row and len(row) == old_length:
                # a row with a DNS, DNF, OTL rider
                # put the DNF reason in last position or the row list
                # put the rider in the last position
                row.append(row[1])
                row[1] = last_ix
                print('ERROR: {}'.format(row))
                data_list.append(row)
                row = [self.ID]
                error_ix += 1

            elif not error_row and len(row) == row_length:
                # 'row_length' data cells make an entire row
                if print_row:
                    print(row)
                # data list gets saved in data subset
                pos = int(row[1])
                # DQ/ DNF/ OL column
                row.append(np.nan)
                data_list.append(row)
                last_ix = pos + 1
                row = [self.ID]
            
            #if len(row) > 20:
            #    break

        self.__add_data_list__(data_id, data_list)
        
    def __check_bib__(self, row, row_id):
        #print('Checking bib row:', row, row_id)
        r3t = row[2]
        #print('WHAT is this (Should D bib): ', r3t)
        not_int = is_not_int(r3t)
        if not_int:
            rank = row[1]
            if is_not_int(rank):
                rank = 1000 + row_id
            url_or_space = r3t
            before = row[:2]
            #print('BEFORE:', before)

            #print('URL OR SPACE (IF SPACE False) ', url_or_space != '')
            if url_or_space != '':
                after = row[2:]
        #        print('AFTER:', after)
                row = before + [rank, True] + after
            else:
                row[2] = rank
                row.append(True)
        else:
            row.append(False)
        #print('AFTER ROW', row)
        return row
    
    def __check_change__(self, ds_id, ds_name, row):
        print('CHECKING CHANGE COLUMNS FOR {}'.format(ds_name))
        text = row[3]
        print('This is the text (should be true): {} {}'.format(text, is_rider_url(text)))
        if is_rider_url(text):
            self.__remove_change_columns__(ds_id, ds_name)
        return self.row_lengths[ds_id]

    def __remove_change_columns__(self, _id, _name, gc_count=0):
        old_columns = self.stage_datasets[_name]
        if _name == 'kom':
            old_columns.remove('prevKomPos')
            old_columns.remove('komChng')
        elif _name == 'points':
            old_columns.remove('prevGreenPos')
            old_columns.remove('greenChng')
        elif _name == 'youth':
            old_columns.remove('youthChng')
            old_columns.remove('prevYouthPos')
        elif _name == 'gc' and gc_count == 0:
            old_columns.remove('gcPnt')
        elif _name == 'gc' and gc_count == 1:
            old_columns.remove('prevGcPos')
            old_columns.remove('gcChng')
        self.stage_datasets[_name] = old_columns
        self.row_lengths[_id] = len(old_columns) - 1

    def __check_uciGc__(self, row):
        # there is no uciGC points
        uciGc = row[-1]
        if uciGc != '' and is_not_int(uciGc):
            time = uciGc
            row[-1] = ''
            row.append(time)
        return row
        
    def __add_data_list__(self, key_id, data_list):
        dataset_keys = list(self.stage_datasets.keys())
        ds_key = dataset_keys[key_id]
        print('UPDATING: {} has {} participants'.format(ds_key, len(data_list)))
        if len(data_list) <= 1:
            print('ERROR WITH NUMBER OF PARTICIPANTS')
            #print(self.stage_datasets[ds_key], data_list[0])
            raise ValueError
        self.stage_data[ds_key] = data_list

    def build_df(self):
        if self.stage_data is None:
            self.scrape_stage_data()

        dfs = list()
        dfs_to_decrease = self.column_subsets.keys()
        for dataset_name in self.stage_datasets.keys():
            print('{} in {}'.format(dataset_name, self.stage_data.keys()))
            ds = self.stage_data[dataset_name]
            df_cols = self.stage_datasets[dataset_name]
            print('"{}" with columns: {}'.format(dataset_name, df_cols))
            print(ds[0])
            df = pd.DataFrame(ds, columns=df_cols)
            
            # fix times
            if dataset_name == 'stage':
                df = fix_time(df, 'stageTime')
            if dataset_name == 'youth':
                df = fix_time(df, 'youthTime')
            
            # select necessary 
            if dataset_name in dfs_to_decrease:
                if 'stage' in self.stage_datasets.keys() or dataset_name != 'gc':
                    df = df[self.column_subsets[dataset_name]]
                
            if dataset_name != 'teams':
                print("BIBS UNIQUE LENGTH: {} of full length {} and {}".format(len(df.index), df.shape[0], df.index))
                print('CHANGING index from {}'.format(df.index.name))
                df = df.set_index('bib')
                print('to {}'.format(df.index.name))
                lid = list(df.index)
                for l in lid:
                    if is_not_int(l):
                        print(lid, l)
                        raise ValueError
                if len(df.index) != df.shape[0]:
                    print("NON UNIQUE INDICES!!!!!!")
                    raise ValueError
                dfs.append(df)
            else:
                self.team_df = df

        for df in dfs:
            print('INDEX: ', df.index.name, len(df.index.unique()) == df.shape[0])
        self.all_df = pd.concat(dfs, axis=1, sort=False)
        print('ALL TOGETHER INDEX: {}'.format(self.all_df.index.name))
        print('CHECK UNIQUE BIB values : {} == {}'.format(len(self.all_df.index.unique()), self.all_df.shape[0]))
        print('BIB in columns:', 'bib' in self.all_df.columns)
        self.__create_all_columns__()
        return dfs
        
    def __create_all_columns__(self):
        # TODO: include this in the file
        current_columns = self.all_df.columns
        for label in self.all_labels:
            if label not in current_columns:
                self.all_df[label] = ''
        self.all_df = self.all_df[self.all_labels]
        self.all_df.index.name = 'bib'
        
    def get_all_df(self):
        print('all df columns: {}\nand index: {}'.format(self.all_df.columns, self.all_df.index.name))
        return self.all_df