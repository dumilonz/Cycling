import requests
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
from datetime import datetime

from stageConstants import *
from categories import Category, DataRow

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

def is_not_pnt(text):
    # it is a time or a '..' string
    try:
        text = text.replace(' ', '')
        datetime.strptime(text, '%H:%M:%S')
        return True
    except:
        # gc can have total hours greater than 24
        # this throws an error for datetime
        result = re.search(r'[\d]{1,}:[\d]{2}:[\d]{2}', text)
        if result is not None or text == '..': return True
        else: return False

def not_empty_text(text):
    t = text.replace(' ', '')
    if len(t) == 0:
        return False
    else:
        return True

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
        if len(html_datasets_list) > 0:
            new_stage_datasets = {}
            for key in html_datasets_list:
                if key == 'prol.':
                    key = 'stage'
                elif self.stage_type != TTT and key == '':
                    key = 'stage'
                if key not in self.stage_datasets.keys() and key != '':
                    print('KEY PROBLEM:  ', key)
                    raise ValueError
                if key != '':
                    # time trial positions
                    new_stage_datasets[key] = self.stage_datasets[key]
            self.__update_datasets__(new_stage_datasets)
        
    def scrape_stage_data(self, print_=False):
        html = self.stage_html
        # all the racers are in a table data cell ('td')
        # intialise variables
        td_cells = html.find_all('td')
        # there can be up to 6 data tables on an html page
        self.stage_data = {}
        
        ds_names = list(self.stage_datasets.keys())
        data_id = 0
        ds_name = ds_names[data_id]
        ds_columns = self.stage_datasets[ds_name]
        ds = Category(data_id, ds_name, ds_columns)

        old_length = ds.row_length

        data_row = DataRow(self.ID)
        if print_:
            print('BEGINS COLS:', self.stage_datasets[ds_name])
            print('TD: number of cells {}'.format(len(td_cells)))

        # itterate through all data cells and append their text values to a row
        for cell in td_cells:
            data_row = self._add_text_to_row(data_row, cell)
            if print_ and ds.name == 'gc':
                print(data_row.row)

            column_name = ds.columns[data_row.length - 1]
            if data_row.length == 2:
                # the second element in the row is the position the rider finished
                # if the rider did not finish, the position will not be an int
                # it will be: DNF, DNS, OTL
                not_int = is_not_int(data_row.pos(1))

                if not_int:
                    data_row.error_row = True

                if not not_int and int(data_row.pos(1)) == 1 and len(ds.data_list) != 0:
                    old_length = ds.row_length
                    ds = self._end_ds(ds, ds_names)
                    
            ds, row, column_name = self._column_checks(ds, data_row, column_name, print_)

            if data_row.length == old_length and data_row.error_row:
                ds = self._append_error_row(ds, data_row)
                data_row = DataRow(self.ID)
            elif data_row.length == ds.row_length and not data_row.error_row:
                ds = self._append_row(ds, row)
                data_row = DataRow(self.ID)
            
            #if len(row) > 20:
            #    break
        self.__add_data_list__(ds)

    def _add_text_to_row(self, data_row, cell):
        text = get_text(cell)
        if type(text) is type('str'):
            data_row.append(text)
        else:
            data_row.append(text[0])
            data_row.append(text[1])
        return data_row

    def _end_ds(self, ds, ds_names):
        # a new table begins with a rider being placed 1st
        # save the complete previous table to the data map
        data_id = ds.id + 1
        self.__add_data_list__(ds)

        #reinitialise variables
        ds_name = ds_names[data_id]
        ds_columns = self.stage_datasets[ds_name]
        ds = Category(data_id, ds_name, ds_columns)
        return ds

    def _column_checks(self, ds, data_row, column_name, print_):
        if self.stage_type in [ITT_CC, ONE_DAY_RACE] and data_row.length in [3, 4]:
            # some ITTs have no bib numbers for the riders
            # we make it the postition number
            data_row = self.__check_bib__(data_row, ds.last_ix + ds.error_ix)

        if self.stage_type == OTHER_TOUR_STAGE:
            if ds.name in ['points', 'kom'] and not ds.points_columns_changed and data_row.length in [4, 5]:
                # in the Other stages, kom or green points may be awarded only in later stages
                # for the first time. Until that point there wil be no changes in the points 
                # classifications. Bu default change columns are included in the dataset
                print('ROW LENGTH IS: {} and this is the row so far {}'.format(ds.row_length, data_row.row))
                ds = self.__points_cat_change__(ds, text=data_row.pos(3))
            
            if ds.name == 'youth' and not ds.youth_columns_changed and column_name == 'youthChng':
                # for some reason some races don't have the youth change columns for their races
                ds = self.__youth_change__(ds, text=data_row.pos(-1))

            if ds.name == 'teams' and not ds.team_changed and column_name == 'teamChng':
                ds = self.__team_changes__(ds, text=data_row.pos(-1))
            
        if self.stage_type in [OTHER_TOUR_STAGE, ITT, FIRST_STAGE_IN_TOUR] and ds.name == 'gc':
            # there are uci gc points awarded to high category races/ stages
            # not all stages have them. the position in the row varies for stage types
            if self.stage_type is not FIRST_STAGE_IN_TOUR and not ds.gc_changes and data_row.length in [4, 5]:
                # gcChanges
                ds = self.__gc_change__(ds, text=data_row.pos(3))
                column_name = ds.columns[data_row.length - 1]    
            
            if print_:
                print('UCISGC (should be true)', column_name, column_name == 'uciGc', )

            if not ds.gc_uci_changed and column_name == 'uciGc':
                # uciGc
                ds = self.__check_uciGc__(ds, text=data_row.pos(-1))
                column_name = ds.columns[data_row.length - 1]
                
            if print_:
                print('All should be true', self.stage_type is not FIRST_STAGE_IN_TOUR, not ds.gc_pnt_removed, column_name == 'gcPnt', column_name)
            if self.stage_type is not FIRST_STAGE_IN_TOUR and not ds.gc_pnt_removed and column_name == 'gcPnt':
                # gc Points
                ds = self.__gc_pnt__(ds, text=data_row.pos(-1))

        column_name = ds.columns[data_row.length - 1]
        return ds, data_row, column_name
        
    def __check_bib__(self, data_row, row_id):
        #print('Checking bib row:', row, row_id)
        r3t = data_row.pos(2)
        not_int = is_not_int(r3t)
        if not_int:
            rank = data_row.pos(1)
            if is_not_int(rank):
                rank = 1000 + row_id
            url_or_space = r3t
            before = data_row.row[:2]

            if url_or_space != '':
                after = data_row.row[2:]
                data_row.row = before + [rank, True] + after
            else:
                data_row.add_pos(2, rank)
                data_row.append(True)
        else:
            data_row.append(False)
        return data_row
    
    def __points_cat_change__(self, ds, text):
        print('CHECKING CHANGE COLUMNS FOR {}'.format(ds.name))
        print('This is the text (should be true): {} {}'.format(text, is_rider_url(text)))
        if is_rider_url(text):
            if ds.name == 'kom': ds.remove_columns(['prevKomPos', 'komChng'])
            else: ds.remove_columns(['prevGreenPos', 'greenChng'])
        ds.points_columns_changed = True
        return ds

    def __youth_change__(self, ds, text):
        if not is_change(text):
            # there are no change columns
            ds.remove_columns(['youthChng', 'prevYouthPos'])
        ds.youth_columns_changed = True
        return ds

    def __gc_change__(self, ds, text):
        print('gc (looking for prevGcPos, gcChng) text change (should be false)', text, is_change(text))
        if not is_change(text):
            ds.remove_columns(['prevGcPos', 'gcChng'])
        ds.gc_changes = True
        return ds

    def __gc_pnt__(self, ds, text):
        print('gc (looking for gcPnt) text change (should be true) {} {}'.format(text, is_not_pnt(text)))
        if is_not_pnt(text):
            ds.remove_columns(['gcPnt'])
        ds.gc_pnt_removed = True
        return ds

    def __team_changes__(self, ds, text):
        if not is_change(text):
            ds.remove_columns(['prevTeamPos', 'teamChng'])
        ds.team_changed  = True
        return ds

    def _append_error_row(self, ds, data_row):
        # a row with a DNS, DNF, OTL rider
        # put the DNF reason in last position or the row list
        # put the rider in the last position
        data_row.append(data_row.pos(1))
        data_row.add_pos(1, ds.last_ix)
        if not data_row.pos(-1) in ['DNF', 'DNS', 'OTL', 'DSQ', '\xa0\xa0']:
            print('ERROR: {}'.format(data_row.row))
            print('COLS: {}'.format(self.stage_datasets[ds.name]))
            raise ValueError
        ds.error_ix = ds.error_ix + 1
        ds.add_row(data_row.row)
        return ds
    
    def _append_row(self, ds, data_row):
        # 'row_length' data cells make an entire row
        #if ds.name == 'gc':
        #    print('Appending to datalist:', data_row.row)
        # data list gets saved in data subset
        pos = int(data_row.pos(1))
        # DQ/ DNF/ OL column
        data_row.append(np.nan)
        ds.add_row(data_row.row)
        ds.last_ix = pos + 1
        return ds

    def __check_uciGc__(self, ds, text):
        # there is no uciGC points
        print('checking uciGC: ', text)
        if text != '' and is_not_int(text):
            ds.remove_columns(['uciGc'])
        ds.gc_uci_changed = True
        return ds
        
    def __add_data_list__(self, ds):
        print('\tUPDATING: {} has {} participants\n'.format(ds.name, len(ds.data_list)))
        if len(ds.data_list) <= 1 and ds.name not in ["kom", "points"]:
            print('ERROR WITH NUMBER OF PARTICIPANTS')
            #print(self.stage_datasets[ds_key], data_list[0])
            raise ValueError
        self.stage_data[ds.name] = ds.data_list

    def build_df(self):
        if self.stage_data is None:
            self.scrape_stage_data()

        dfs = list()
        dfs_to_decrease = self.column_subsets.keys()
        for dataset_name in self.stage_datasets.keys():
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
                    df_cols = self.column_subsets[dataset_name]
                    try:
                        df = df[df_cols]
                    except KeyError:
                        for column in df_cols:
                            if column not in df.columns:
                                df[column] = ''
                        df = df[df_cols]
                
            if dataset_name != 'teams':
                print("BIBS UNIQUE LENGTH: {} of full length {} and {}".format(len(df.index), df.shape[0], df.index))
                df = df.set_index('bib')
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

        self.all_df = pd.concat(dfs, axis=1, sort=False)
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
        return self.all_df
    
    def find_stage_info(self):
        '''
            Each stage has more information about its profile. Itterate 
            through each stage and extract the profile information. 
        '''
        res_ = self.stage_html.find_all("div", class_="res-right")
        
        res_text = res_[0].find_all(text=True)
        
        self.stage_info = list()
        mountains = list()
        found_race_rank = False
        
        for text in res_text:
            web_regex = re.search('(www.(.)+\.(.)+)+', text) \
                            or re.search('((.)+\.com(.)*)+', text) \
                            or re.search('((.)+\.org(.)*)+', text) \
                            or re.search('((.)+\.(\w)*(\d)*/)', text) \
                            or 'googletag.cmd.push(' in text
            repetitive_text = text in ['Race information', 'Date: ', 'Avg. speed winner:', 'rd', \
                            'Race category: ', 'Parcours type:', 'PCS point scale:', \
                            ' ', 'Start/finish:', ' › ', 'Climbs: ', ', ', 'Race profile', \
                            'Finish photo', 'Finish photo', 'LiveStats', 'Websites:', \
                            'Race ranking position', 'ranking', 'th', 'nd', 'st', '\n', \
                            'breakdown', 'Position and points as on startdate of race.']
            if not repetitive_text and not web_regex:
                if len(self.stage_info) <= 6 or found_race_rank:
                    # the first 6 cells of interest
                    # or if the race rank has been found
                    if '›' in text:
                        start_ix = text.find('›')
                        start = text[:start_ix]
                        if not_empty_text(start):
                            self.stage_info.append(start)
                        text = text[start_ix + 1:]
                    if not_empty_text(text):
                        self.stage_info.append(text)
                    if re.search('(\d)* pnt', text):
                        # after this string regex there is only adds and redundant information
                        break
                else:
                    # there is a variable number of mountains 
                    if is_not_int(text):
                        mountains.append(text)
                    else:
                        # race rank (int value) comes right after mountains 
                        # have been listed
                        self.stage_info.append(mountains)
                        self.stage_info.append(len(mountains))
                        self.stage_info.append(text)
                        found_race_rank = True
                        
                        mountains = list()
            
            if text is 'ranking':
                break

        if len(mountains) != 0:
            self.stage_info.append(mountains)
            self.stage_info.append(len(mountains))