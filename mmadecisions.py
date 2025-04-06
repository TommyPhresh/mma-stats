import requests
import pandas as pd
from bs4 import BeautifulSoup


PREFIX_URL = "https://mmadecisions.com/"
round_abbr_mapping = {
        "ROUND 1": "R1", "ROUND 2": "R2", "ROUND 3": "R3",
        "ROUND 4": "R4", "ROUND 5": "R5"
        }

# all event links in a given year
def get_event_links(year, promotion='ufc'):
    event_links = []
    response = requests.get(PREFIX_URL + "decisions-by-event/" + year + "/")
    soup = BeautifulSoup(response.content, 'html.parser')
    for event in soup.find_all('a', href=True):
        if "UFC" in event.text:
            event_links.append(event['href'])
    return event_links

# all fight links in a given event
def get_fight_links(event_url):
    fight_links = []
    response = requests.get(PREFIX_URL + event_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    table = soup.find_all('td', class_='list2')
    for row in table:
        for fight in row.find_all('a', href=True):
            if 'decision' in fight['href']:
                fight_links.append(fight['href'].strip())
    return fight_links

# get fighter names
def get_fighter_names(soup):
    fighters = [soup.find('tr', class_='top-row'), soup.find('tr', class_='bottom-row')]
    for i in range(len(fighters)):
        fighters[i] = fighters[i].text.strip().replace('\xa0', ' ')
    return fighters

# get fan round-by-round scores, along with total fan scorecard
def get_fan_scores(soup, fighter1, fighter2):    
    # isolates each round's voting results
    search = soup.find('div', id='scorecard_totals').text.splitlines()
    round_data = []
    curr_round = None
    for item in search:
        if not item.strip():
            continue
        if "ROUND" in item.strip():
            curr_round = item.strip()
        elif curr_round:
            if "%" in item.strip():
                round_data[-1][-1] = item.strip()
            else:
                if len(round_data) == 0 or round_data[-1][-1] != "":
                    round_data.append([curr_round, item.strip(), "", ""])
                else:
                    round_data[-1][2] = item.strip()
                    
    # uses the parsed voting results to get weighted fan scorecard for each round
    weighted_pts = {}
    for round_score in round_data:
        round_name, score, fighter, vote = round_score
        weight = float(vote.strip("%")) / 100
        points = list(map(int, score.split('-')))
        winner_pts = points[0]
        loser_pts = points[1]
        if round_name not in weighted_pts:
            weighted_pts[round_name] = {fighter1: 0, fighter2: 0}
        if fighter == "Draw":
            weighted_pts[round_name][fighter1] += weight * winner_pts
            weighted_pts[round_name][fighter2] += weight * loser_pts
        elif fighter in fighter1:
            weighted_pts[round_name][fighter1] += weight * winner_pts
            weighted_pts[round_name][fighter2] += weight * loser_pts
        else:
            weighted_pts[round_name][fighter2] += weight * winner_pts
            weighted_pts[round_name][fighter1] += weight * loser_pts

    # create total fan scorecard
    fan_scorecard = {fighter1: 0, fighter2: 0}
    for rd in weighted_pts:
        fan_scorecard[fighter1] += weighted_pts[rd][fighter1]
        fan_scorecard[fighter2] += weighted_pts[rd][fighter2]
    
    # create dataframe to return
    result = {}
    for rd in weighted_pts:
        round_abbr = round_abbr_mapping[rd]
        result[round_abbr + 'FanScore_F1'] = weighted_pts[rd][fighter1]
        result[round_abbr + 'FanScore_F2'] = weighted_pts[rd][fighter2]
    result["FanScore_F1"] = fan_scorecard[fighter1]
    result["FanScore_F2"] = fan_scorecard[fighter2]
    return result

# get the aggregated media scorecard 
def get_media_scores(soup, fighter1, fighter2):
    # get all media opinions
    page_text = soup.get_text(separator="\n").strip()
    start_marker = "MEDIA SCORES"
    end_marker = "YOUR SCORECARD"
    start_index = page_text.find(start_marker)
    end_index = page_text.find(end_marker)
    media_text = page_text[start_index + len(start_marker) : end_index].strip()
    media_lines =[line.strip() for line in media_text.split("\n") if line.strip()]
    # aggregate all opinions
    num_media = len(media_lines) / 4
    media_scores = {fighter1: 0, fighter2: 0}
    for i in range(0, len(media_lines), 4):
        _,_,score,winner = media_lines[i:i+4]
        scores = list(map(int, score.strip('-')))
        winner_pts, loser_pts = scores
        if winner in fighter1:
            media_scores[fighter1] += winner_pts
            media_scores[fighter2] += loser_pts
        else:
            media_scores[fighter2] += winner_pts
            media_scores[fighter1] += loser_pts
    media_scores[fighter1] /= num_media
    media_scores[fighter2] /= num_media

    return {
        "MediaScore_F1": media_scores[fighter1],
        "MediaScore_F2": media_scores[fighter2]
        }

# get the aggregated and round-byround official scorecards
def get_official_scores(soup, fighter1, fighter2):
    # all text within judge scorecard section
    page_text = soup.get_text(separator="\n").strip()
    start_marker = "ROUND"
    end_marker = "MEDIA SCORES"
    start_index = page_text.find(start_marker)
    end_index = page_text.find(end_marker)
    official_scores = page_text[start_index + len(start_marker) : end_index].strip()

    # grab all numbers only
    official_lines = [line.strip() for line in official_scores.split("\n") if line.strip()]
    new_official_lines = []
    for line in official_lines:
        if not any(char.isalpha() for char in line):
            elem = int(line)
            if elem <= 10:
                new_official_lines.append(elem)

    # create round-by-round official scorecard
    official_data = {"Total": {fighter1: 0, fighter2: 0}}
    for i in range(0, len(new_official_lines), 3):
        rd, score1, score2 = new_official_lines[i : i+3]
        if rd not in official_data:
            official_data[rd] = {fighter1: 0, fighter2: 0}
        official_data[rd][fighter1] += score1 / 3
        official_data[rd][fighter2] += score2 / 3

    # create aggregated scorecard
    official_data["Total"][fighter1] = sum([scores[fighter1] for scores in official_data.values()])
    official_data["Total"][fighter2] = sum([scores[fighter2] for scores in official_data.values()])

    # convert into correctly labeled format
    return official_data

# grab all data from a fight
def mmadec_parse_fight(fight_url):
    response = requests.get(PREFIX_URL + fight_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    fighters = get_fighter_names(soup)
    fighter1, fighter2 = fighters
    fan_scores = get_fan_scores(soup, fighter1, fighter2)
    media_scores = get_media_scores(soup, fighter1, fighter2)
    official_scores = get_official_scores(soup, fighter1, fighter2)
    datasets = [fan_scores, media_scores, official_scores]
    result = {}
    for dataset in datasets:
        result.update(dataset)
    return result
    
# grab all fights from an event
def parse_event_scores(event_url):
    all_fights = []
    fight_links = get_fight_links(event_url)
    for fight_link in fight_links:
        fight_data = mmadec_parse_fight(fight_link)
        all_fights.append(fight_data)
    return all_fights

