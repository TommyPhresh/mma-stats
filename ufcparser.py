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

# extract information from fight HTML file
def parse_fight(fight_url):
    fight_response = requests.get(fight_url)
    fight_soup = BeautifulSoup(fight_response.content, 'html.parser')
    columns = fight_soup.find_all('td', class_='b-fight-details__table-col')
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
    fight_data = {
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
    return fight_data
    
# Logic: grab all fights into a multi-dimensional pandas file 
all_fights = []
event_links = get_event_links(BASE_URL)
for event_link in event_links:
    fight_links = get_fight_links(event_link)
    for fight_link in fight_links:
        fight_data = parse_fight(fight_link)
        all_fights.append(fight_data)

df = pd.DataFrame(all_fights)
df.to_csv('ufc_fight_data.csv', index=False)

