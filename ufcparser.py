import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd


# Base URL for UFC events - FightMetric
BASE_URL = "http://ufcstats.com/statistics/events/completed?page=all"

# get all event HTML files on FightMetric
def get_event_links(base_url):
    top_level_response = requests.get(base_url)
    top_level_soup = BeautifulSoup(top_level_response.content, 'html.parser')

    # Extract event links
    event_links = []
    for event_link in top_level_soup.find_all('a', href=True):
        if "/event-details/" in event_link['href']:
            event_links.append(event_link['href'])
    
    return list(set(event_links))

# list all fight HTML files in an event
def get_fight_links(event_url):
    event_response = requests.get(event_url)
    event_soup = BeautifulSoup(event_response.content, 'html.parser')

    # Extract fight links
    fight_links = []
    for fight_link in event_soup.find_all('a', href=True):
        if "/fight-details" in fight_link['href']:
            fight_links.append(fight_link['href'])

    return list(set(fight_links))

# parses columns with stat as int
def extract_int_stat(col):
    return [int(stat.strip()) for stat in col.text.strip().split('\n') if stat.strip()]

# parses columns with stat in form of "x of y"
def extract_of_stat(col):
    L = [stat.strip() for stat in col.text.strip().split('\n') if stat.strip()]
    return [int(num) for stat in L for num in stat.split(' of ')]

# get entire fight totals for stats
def get_totals_data(columns):
    # parse col 0 into list of two names
    fighters = [name.strip() for name in columns[0].text.strip().split('\n') if name.strip()]
    # parse col 1 into list of total knockdowns
    tot_kds = extract_int_stat(columns[1])
    # parse col 2 into list of total significant strikes landed/attempted
    tot_sigs = extract_of_stat(columns[2])
    # col 3 = sig. strike % (calculated col)
    # parse col 4 into list of total strikes landed/attempted
    tot_strs = extract_of_stat(columns[4])
    # parse col 5 into list of takedowns landed/attempted
    tot_tds = extract_of_stat(columns[5])
    # col 6 = takedown % (calculated col)
    # parse col 7 into list of total submission attempts
    tot_subs = extract_int_stat(columns[7])
    # parse col 8 into list of reversals
    tot_revs = extract_int_stat(columns[8])
    # parse col 9 into list of seconds of control time
    tot_control = [stat.strip() for stat in columns[9].text.strip().split('\n') if stat.strip()]
    tot_control = [int(minutes) * 60 + int(seconds) for time in tot_control
                   for minutes, seconds in [time.split(":")]]
    totals_data = {
        "Fighter1": fighters[0], "Fighter2": fighters[1],
        "TotKD_F1": tot_kds[0], "TotKD_F2": tot_kds[1],
        "TotSigStrLand_F1": tot_sigs[0], "TotSigStrLand_F2": tot_sigs[2],
        "TotSigStrAtt_F1": tot_sigs[1], "TotSigStrAtt_F2": tot_sigs[3],
        "TotStrLand_F1": tot_strs[0], "TotStrLand_F2": tot_strs[2],
        "TotStrAtt_F1": tot_strs[1], "TotStrAtt_F2": tot_strs[3],
        "TotTDLand_F1": tot_tds[0], "TotTDLand_F2": tot_tds[2],
        "TotTDAtt_F1": tot_tds[1], "TotTDAtt_F2": tot_tds[3],
        "TotSubAtts_F1": tot_subs[0], "TotSubAtts_F2": tot_subs[1],
        "TotRevs_F1": tot_revs[0], "TotRevs_F2": tot_revs[1],
        "TotCtrl_F1": tot_control[0], "TotCtrl_F2": tot_control[1],
        }
    return totals_data

def get_header_data(fight_soup):
    # method of victory
    method = fight_soup.find('i', class_='b-fight-details__text-item_first')
    method = method.find('i', {'style': 'font-style: normal'}).text.strip()
    columns = fight_soup.find_all('i', class_='b-fight-details__text-item')
    # num of rounds in the fight
    rounds = int(columns[0].text.split("Round:")[-1].strip())
    # total fight time
    time_format = columns[2].text.strip()
    time_format = time_format.split("(")[-1].strip(")").split("-")
    time_format = [int(length) for length in time_format]
    tot_time = 0
    for i in range(rounds-1):
        tot_time += 60*time_format[i]
    finish_time = columns[1].text.split("Time:")[-1].strip()
    minutes, seconds = map(int, finish_time.split(":"))
    tot_time += 60*minutes + seconds
    # scorecards (if decision)
    if ("Decision" in method):
        try:
            scores = columns[4].text.strip()
            L_score, W_score = int(scores.split()[2]), int(scores.split()[4].strip('.'))
            scores = columns[5].text.strip()
            L_score += int(scores.split()[2])
            W_score += int(scores.split()[4].strip('.'))
            scores = columns[6].text.strip()
            L_score += int(scores.split()[2])
            W_score += int(scores.split()[4].strip('.'))
        except:
            L_score, W_score = None, None
    else:
        L_score, W_score = None, None
    # weight class
    weight = fight_soup.find('i', class_='b-fight-details__fight-title').text.strip().split(" ")
    for word in weight:
        if "weight" in word:
            weight = word
            break
        
    # compile into dict
    header_data = {
        "Method": method, "Rounds": rounds, "FightTime": tot_time,
        "JudgesScore_F1": W_score, "JudgesScore_F2": L_score, "Weight": weight
        }
    return header_data

# get information from each round
def get_rounds_data(columns, rounds):
    start_col = 10
    curr_round = 0
    curr_round_str = "R1"
    rounds_data = {}
    # get stats from current round
    while (curr_round < rounds):
        round_kds = extract_int_stat(columns[start_col + 1])
        round_sigs = extract_of_stat(columns[start_col + 2])
        round_stks = extract_of_stat(columns[start_col + 4])
        round_tds = extract_of_stat(columns[start_col + 5])
        round_subs = extract_int_stat(columns[start_col + 7])
        round_revs = extract_int_stat(columns[start_col + 8])
        round_ctrl = [stat.strip() for stat in columns[start_col + 9].text.strip().split('\n') if stat.strip()]
        round_ctrl = [int(minutes) * 60 + int(seconds) for time in round_ctrl
                   for minutes, seconds in [time.split(":")]]
        rounds_data.update({
            curr_round_str + "KD_F1": round_kds[0], curr_round_str + "KD_F2": round_kds[1],
            curr_round_str + "SigStrLand_F1": round_sigs[0], curr_round_str + "SigStrLand_F2": round_sigs[2],
            curr_round_str + "SigStrAtt_F1": round_sigs[1], curr_round_str + "SigStrAtt_F2": round_sigs[3],
            curr_round_str + "StrLand_F1": round_stks[0], curr_round_str + "StrLand_F2": round_stks[2],
            curr_round_str + "StrAtt_F1": round_stks[1], curr_round_str + "StrAtt_F2": round_stks[3],
            curr_round_str + "TDLand_F1": round_tds[0], curr_round_str + "TDLand_F2": round_tds[2],
            curr_round_str + "TDAtt_F1": round_tds[1], curr_round_str + "TDAtt_F2": round_tds[3],
            curr_round_str + "SubAtts_F1": round_subs[0], curr_round_str + "SubAtts_F2": round_subs[1],
            curr_round_str + "Revs_F1": round_revs[0], curr_round_str + "Revs_F2": round_revs[1],
            curr_round_str + "Ctrl_F1": round_ctrl[0], curr_round_str + "Ctrl_F2": round_ctrl[1]
            })
        start_col += 10
        curr_round += 1
        curr_round_str = "R" + str(int(curr_round_str[1]) + 1)
    return rounds_data, start_col

# extract total significant strike information
def get_total_stks_data(columns, start_col):
    # start_col + [0,1,2] are unneeded (names, Total Sigs, %)
    total_heads = extract_of_stat(columns[start_col + 3])
    total_bodys = extract_of_stat(columns[start_col + 4])
    total_legs = extract_of_stat(columns[start_col + 5])
    total_dist = extract_of_stat(columns[start_col + 6])
    total_clinch = extract_of_stat(columns[start_col + 7])
    total_ground = extract_of_stat(columns[start_col + 8])
    data ={
        "TotSigStkHeadLand_F1": total_heads[0], "TotSigStkHeadLand_F2": total_heads[2],
        "TotSigStkHeadAtt_F1": total_heads[1], "TotSigStkHeadAtt_F2": total_heads[3],
        "TotSigStkBodyLand_F1": total_bodys[0], "TotSigStkBodyLand_F2": total_bodys[2],
        "TotSigStkBodyAtt_F1": total_bodys[1], "TotSigStkBodyAtt_F2": total_bodys[3],
        "TotSigStkLegsLand_F1": total_legs[0], "TotSigStkLegsLand_F2": total_legs[2],
        "TotSigStkLegsAtt_F1": total_legs[1], "TotSigStkLegsAtt_F2": total_legs[3],
        "TotSigStkDistLand_F1": total_dist[0], "TotSigStkDistLand_F2": total_dist[2],
        "TotSigStkDistAtt_F1": total_dist[1], "TotSigStkDistAtt_F2": total_dist[3],
        "TotSigStkClinchLand_F1": total_clinch[0], "TotSigStkClinchLand_F2": total_clinch[2],
        "TotSigStkClinchAtt_F1": total_clinch[1], "TotSigStkClinchAtt_F2": total_clinch[3],
        "TotSigStkGroundLand_F1": total_ground[0], "TotSigStkGroundLand_F2": total_ground[2],
        "TotSigStkGroundAtt_F1": total_ground[1], "TotSigStkGroundAtt_F2": total_ground[3]
        }
    start_col += 9
    return data, start_col

# extract round-by-round significant strikes data
def get_rounds_stks_data(columns, start_col, rounds):
    curr_round = 0
    curr_round_str = "R1"
    rounds_stks_data = {}
    # get stats from current round
    while (curr_round < rounds):
        round_heads = extract_of_stat(columns[start_col + 3])
        round_bodys = extract_of_stat(columns[start_col + 4])
        round_legs = extract_of_stat(columns[start_col + 5])
        round_dist = extract_of_stat(columns[start_col + 6])
        round_clinch = extract_of_stat(columns[start_col + 7])
        round_ground = extract_of_stat(columns[start_col + 8])
        rounds_stks_data.update({
            curr_round_str + "SigStkHeadLand_F1": round_heads[0], curr_round_str + "SigStkHeadLand_F2": round_heads[2],
            curr_round_str + "SigStkHeadAtt_F1": round_heads[1], curr_round_str + "SigStkHeadAtt_F2": round_heads[3],
            curr_round_str + "SigStkBodyLand_F1": round_bodys[0], curr_round_str + "SigStkBodyLand_F2": round_bodys[2],
            curr_round_str + "SigStkBodyAtt_F1": round_bodys[1], curr_round_str + "SigStkBodyAtt_F2": round_bodys[3],
            curr_round_str + "SigStkLegsLand_F1": round_legs[0], curr_round_str + "SigStkLegsLand_F2": round_legs[2],
            curr_round_str + "SigStkLegsAtt_F1": round_legs[1], curr_round_str + "SigStkLegsAtt_F2": round_legs[3],
            curr_round_str + "SigStkDistLand_F1": round_dist[0], curr_round_str + "SigStkDistLand_F2": round_dist[2],
            curr_round_str + "SigStkDistAtt_F1": round_dist[1], curr_round_str + "SigStkDistAtt_F2": round_dist[3],
            curr_round_str + "SigStkClinchLand_F1": round_clinch[0], curr_round_str + "SigStkClinchLand_F2": round_clinch[2],
            curr_round_str + "SigStkClinchAtt_F1": round_clinch[1], curr_round_str + "SigStkClinchAtt_F2": round_clinch[3],
            curr_round_str + "SigStkGroundLand_F1": round_ground[0], curr_round_str + "SigStkGroundLand_F2": round_ground[2],
            curr_round_str + "SigStkGroundAtt_F1": round_ground[1], curr_round_str + "SigStkGroundAtt_F2": round_ground[3]
            })
        start_col += 9
        curr_round += 1
        curr_round_str = "R" + str(int(curr_round_str[1]) + 1)
    return rounds_stks_data

# extract information from fight HTML file
def parse_fight(fight_url):
    fight_response = requests.get(fight_url)
    fight_soup = BeautifulSoup(fight_response.content, 'html.parser')
    columns = fight_soup.find_all('td', class_='b-fight-details__table-col')
    # fight metadata
    header_data = get_header_data(fight_soup)
    # fight summary statistics
    totals_data = get_totals_data(columns)
    # get number of rounds and round-by-round data
    rounds = header_data["Rounds"]
    rounds_data, start_col = get_rounds_data(columns, rounds)
    # total significant strikes data
    total_stks_data, start_col = get_total_stks_data(columns, start_col)
    # round-by-round significant strikes data
    rounds_stks_data = get_rounds_stks_data(columns, start_col, rounds)
    # merge into one 'row'
    datasets = [header_data, totals_data, rounds_data, total_stks_data, rounds_stks_data]
    fight_data = {}
    for dataset in datasets:
        fight_data.update(dataset)
    return fight_data
    
# Logic: grab all fights into a multi-dimensional pandas file 
all_fights = []
event_links = get_event_links(BASE_URL)
# have to start at 1 because first event is always next event (not completed)
for i in range(1, len(event_links)):
    fight_links = get_fight_links(event_links[i])
    event_response = requests.get(event_links[i])
    event_soup = BeautifulSoup(event_response.content, 'html.parser')
    event_date = event_soup.find('li', class_='b-list__box-list-item')
    event_date = event_date.text.split("Date:")[-1].strip()
    print(event_date)
    event_date = datetime.strptime(event_date, "%B %d, %Y")
    for fight_link in fight_links:
        fight_data = parse_fight(fight_link)
        fight_data["Date"] =  event_date
        all_fights.append(fight_data)
        

df = pd.DataFrame(all_fights)
df.to_csv('ufc_fight_data.csv', index=False)

