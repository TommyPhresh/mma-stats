import requests
from bs4 import BeautifulSoup
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
        "TotStrAtt_F1": tot_str[1], "TotStrAtt_F2": tot_strs[3],
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
        scores = columns[4].text.strip()
        L_score, W_score = int(scores.split()[2]), int(scores.split[4].strip('.'))
        scores = columns[5].text.strip()
        L_score += int(scores.split()[2])
        W_score += int(scores.split()[4].strip('.'))
        scores = columns[6].text.strip()
        L_score += int(scores.split()[2])
        W_score += int(scores.split()[4].strip('.'))
    else:
        L_score, W_score = None, None
    # weight class
    weight = fight_soup.find('i', class_='b-fight-details__fight-title').text.strip().split(" ")[0]
    # compile into dict
    header_data = {
        "Method": method, "Rounds": rounds, "FightTime": tot_time,
        "Score_F2": L_score, "Score_F1": W_score, "Weight": weight
        }
    return header_data

# extract information from fight HTML file
def parse_fight(fight_url):
    fight_response = requests.get(fight_url)
    fight_soup = BeautifulSoup(fight_response.content, 'html.parser')
    columns = fight_soup.find_all('td', class_='b-fight-details__table-col')
    header_data = get_header_data(fight_soup)
    # fight summary statistics
    totals_data = get_totals_data(columns)
    # get number of rounds and round-by-round data
    
    
# Logic: grab all fights into a multi-dimensional pandas file 
all_fights = []
event_links = get_event_links(BASE_URL)
# have to start at 1 because top event is always upcoming
for event_link in event_links[1:]:
    fight_links = get_fight_links(event_link)
    for fight_link in fight_links:
        fight_data = parse_fight(fight_link)
        all_fights.append(fight_data)

df = pd.DataFrame(all_fights)
df.to_csv('ufc_fight_data.csv', index=False)

