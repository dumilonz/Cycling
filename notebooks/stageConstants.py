import re

# constants for stage scraping
ONE_DAY_RACE = 0
FIRST_STAGE_IN_TOUR = 1
OTHER_TOUR_STAGE = 2
ITT = 3
PROLOGUE = 4
TTT = 5
ITT_CC = 6

def get_stage_columns(stage, all_df_cols=False):
    stage_columns = [None] * 7
    stage_columns[ONE_DAY_RACE] = {'stage': ['stageID', 'stagePos', 'bib', 'createBib', 'url', 'name', 'age', 'teamName', 'uciStage', 'pnt', 'stageTime', 'DNF']}
    stage_columns[ITT_CC] = {'stage': ['stageID', 'stagePos', 'bib', 'createBib', 'url', 'name', 'age', 'countryTeam', 'uciStage', 'pnt', 'stgAvgPace', 'stageTime', 'DNF']}
    stage_columns[ITT] = {'stage': ['stageID', 'stagePos', 'gc', 'gc-time', 'bib', 'url', 'name', 'age', 'team', 'uciStage', 'pnt', 'stgAvgPace', 'stageTime', 'DNF'], \
                                        'gc': ['stageID', 'gcPos', 'prevGcPos', 'gcChng', 'bib', 'url', 'name', 'age', 'team', 'uciGc', 'gcPnt', 'gcTime', 'more', 'DNF'], \
                                        'points': ['stageID', 'greenPos', 'prevGreenPos', 'greenChng', 'bib', 'url', 'name', 'age', 'team', 'greenPnts', 'greenPntsChng', 'DNF'], \
                                        'youth': ['stageID', 'youthPos', 'prevYouthPos', 'youthChng', 'gcPos', 'gcTime', 'bib', 'url', 'name', 'age', 'team', 'youthTime', 'DNF'], \
                                        'kom': ['stageID', 'komPos', 'prevKomPos', 'komChng', 'bib', 'url', 'name', 'age', 'team', 'komPnts',  'komPntsChng', 'DNF'], \
                                        'teams': ['stageID', 'teamPos', 'prevTeamPos', 'teamChng', 'empty', 'teamName', 'teamTime', 'DNF'] \
                                        }
    stage_columns[FIRST_STAGE_IN_TOUR] = {'stage': ['stageID', 'stagePos', 'gcPos', 'timeAdd', 'bib', 'url', 'name', 'age', 'teamName', 'uciStage','pnt', 'stageTime', 'DNF'],
                                        'gc': ['stageID', 'gcPos', 'bib', 'url', 'name', 'age', 'team', 'uciGc', 'gcTime', 'more', 'DNF'], \
                                        'points': ['stageID', 'greenPos', 'bib', 'url', 'name', 'age', 'team', 'greenPnts', 'greenPntsChng', 'DNF'], \
                                        'youth': ['stageID', 'youthPos', 'gcPos', 'timeAdd', 'bib', 'url', 'name', 'age', 'team', 'youthTime', 'DNF'], \
                                        'kom': ['stageID', 'komPos', 'bib', 'url', 'name', 'age', 'team', 'komPnts',  'komPntsChng', 'DNF'], \
                                        'teams': ['stageID', 'teamPos', 'empty', 'teamName', 'teamTime', 'DNF'] \
                                        }
    stage_columns[OTHER_TOUR_STAGE] = {'stage': ['stageID', 'stagePos', 'gcPos', 'gcTime', 'bib', 'url', 'name', 'age', 'teamName', 'uciStage','pnt', 'stageTime', 'DNF'], \
                                        'gc': ['stageID', 'gcPos', 'prevGcPos', 'gcChng', 'bib', 'url', 'name', 'age', 'team', 'uciGc', 'gcPnt', 'gcTime', 'more', 'DNF'], \
                                        'points': ['stageID', 'greenPos', 'prevGreenPos', 'greenChng', 'bib', 'url', 'name', 'age', 'team', 'greenPnts', 'greenPntsChng', 'DNF'], \
                                        'youth': ['stageID', 'youthPos', 'prevYouthPos', 'youthChng', 'gcPos', 'gcTime', 'bib', 'url', 'name', 'age', 'team', 'youthTime', 'DNF'], \
                                        'kom': ['stageID', 'komPos', 'prevKomPos', 'komChng', 'bib', 'url', 'name', 'age', 'team', 'komPnts',  'komPntsChng', 'DNF'], \
                                        'teams': ['stageID', 'teamPos', 'prevTeamPos', 'teamChng', 'empty', 'teamName', 'teamTime', 'DNF'] \
                                        }
    stage_columns[PROLOGUE] = {'stage': ['stageID', 'stagePos', 'gcPos', 'gcTime', 'bib', 'url', 'name', 'age', 'teamName', 'uciStage','pnt', 'avgTime', 'stageTime', 'DNF'], \
                                        'gc': ['stageID', 'gcPos', 'bib', 'url', 'name', 'age', 'teamName', 'uciGc', 'stageTime', 'more', 'DNF'], \
                                        'points': ['stageID', 'greenPos', 'bib', 'url', 'name', 'age', 'team', 'greenPnts', 'greenPntsChng', 'DNF'], \
                                        'youth': ['stageID', 'youthPos', 'gcPos', 'timeAdd', 'bib', 'url', 'name', 'age', 'team', 'youthTime', 'DNF'], \
                                        'kom': ['stageID', 'komPos', 'bib', 'url', 'name', 'age', 'team', 'komPnts',  'komPntsChng', 'DNF'], \
                                        'teams': ['stageID', 'teamPos', 'empty', 'teamName', 'teamTime', 'DNF']
                                        }
    stage_columns[TTT] =  {'stage': ['stageID', 'stagePos', 'gcPos', 'gcTime', 'bib', 'url', 'name', 'age', 'teamName', 'uciStage','pnt', 'avgTime', 'stageTime', 'DNF'], \
                                        'gc': ['stageID', 'gcPos', 'bib', 'url', 'name', 'age', 'teamName', 'stageTime', 'timeWonLost', 'DNF'], \
                                        'points': ['stageID', 'greenPos', 'bib', 'url', 'name', 'age', 'team', 'greenPnts', 'greenPntsChng', 'DNF'], \
                                        'youth': ['stageID', 'youthPos', 'gcPos', 'timeAdd', 'bib', 'url', 'name', 'age', 'team', 'youthTime', 'DNF'], \
                                        'kom': ['stageID', 'komPos', 'bib', 'url', 'name', 'age', 'team', 'komPnts',  'komPntsChng', 'DNF'], \
                                        'teams': ['stageID', 'teamPos', 'empty', 'teamName', 'teamTime', 'DNF']
                                        }
    if not all_df_cols:
        return stage_columns[stage]
    else:
        return stage_columns
    
def get_all_df_columns():
    stage_columns = get_stage_columns('', all_df_cols=True)
    al = []
    for stage_dss in stage_columns:
        stage_keys = stage_dss.keys()
        for key in stage_keys:
            if key != 'teams':
                al = al + stage_dss[key]

    al = list(set(al))
    al_sm = list()
    for el in al:
        cb = re.match('[\w]*Chng', el)
        lb = el in ['empty', 'more', 'bib']
        pb = re.match('prev[\w]*', el)
        if not(cb or lb or pb):
            al_sm.append(el)
    try:
        al.remove('prevGreenPos')
        al.remove('greenPntsChng')
    except:
        pass
    all_labels = sorted(al_sm)
    return all_labels