import uiautomator2 as u2
import time
import pandas as pd
import os
import json
import copy
import re
import pandas as pd
from pathlib import  Path




# Part 2: Remove cyclic, duplicates edges, and convert the edges into ATG

def get_useful_edges(events,atg_data):
    avaliable_ids = [event.widget.resourceId.split('/')[-1] for event in events if event.widget.resourceId is not None]
    useful_atg_data = atg_data[atg_data.widgetname.isin(avaliable_ids)]
    useful_atg_data = useful_atg_data[
        ~atg_data['Source Activity'].str.startswith('android') & ~atg_data['Target Activity'].str.startswith('android')]

    return useful_atg_data
def get_transition_info(visited_activities, transitions):
    transitions_info=set()
    for _, row in transitions.iterrows():
        target_activity = row['Target Activity']
        if target_activity in visited_activities:
            target_activity+='(visited)'
        # else:
        #     target_activity +='(not visited)'
        widget_name = row['widgetname']
        transitions_info.add(f"{target_activity} via widget resourceId={widget_name},\n")
    return list(transitions_info)
def atg2sequence(atg_data,source_activity):
    #here I only implement 1-hop neignbors
    transitions = atg_data[atg_data['Source Activity'] == source_activity]

# Function to construct prompt for a given source activity
def generate_prompt_for_activity(events,contexts, atg_data):
    # Filter the transitions for the given source activity

    source_activity=contexts[-1].activity
    visited_activitys=[context.activity for context in contexts]

    transitions=atg2sequence(atg_data,source_activity)
    #get 1 hop

    useful_transitions=get_useful_edges(events,transitions)
    other_transitions=transitions-useful_transitions

    # Building the transitions info string
    transitions_info_useful = get_transition_info(visited_activitys,useful_transitions)
    transitions_info_others= get_transition_info(visited_activitys,other_transitions)

    # give me the code: keep all transitions_info_useful,
    #   if transitions_info_useful lengtg<20, then add transition_info_others, but the max length should be 20
    #

    prompt = f"""
Based on the activity transition graph, the current activity '{source_activity}' can transfer to the following target activities:
{transitions_info}
"""
    return prompt.strip()


# Example: Generate prompt for a specific source activity

def remove_ad_events(ad_event,events):
    def is_inside(widget1, widget2):
        x1, y1, x2, y2 = widget1
        X1, Y1, X2, Y2 = widget2

        return X1 <= x1 <= X2 and X1 <= x2 <= X2 and Y1 <= y1 <= Y2 and Y1 <= y2 <= Y2
    # if ad_event.widget.resourceId
    ad_pos=ad_event.widget.pos
    for event in copy.deepcopy(events):
        pos=event.widget.pos
        if is_inside(pos,ad_pos):
            events.remove(event)

def map_adwidget_to_event(ad_widget):
    return ad_widget
def remove_false_positives(widget_id):
    banned_str=['rate','about','policy','share','gdpr','privacy']
    if any([i in widget_id for i in banned_str]):
        return False
    return True
def trigger_ad_widgets(events,SA_ad_widgets):
    """
    each turn
    get SA_widgets of this activity
    if all SA_widgets are triggered:
        LLM_guide-next_activity
    if not:
        if for each SA_widget:
            if avaliable_current_context(SA_widget):
                click
            not:
                LLM_guide-SA_widget()
    """
    existing_ad_widget=[]
    for SA_ad_widget in SA_ad_widgets:
        if exists_ad_widgets(SA_ad_widget,events):
            existing_ad_widget.append(SA_ad_widget)
            trigger_ad_widget(SA_ad_widget)
            SA_ad_widgets.remove(SA_ad_widget)
            # continue
    return existing_ad_widget
            # return SA_ad_widget
        # return SA_ad_widgets
    # if current_ad_widgets!=None:
    #     for ad_widget in current_ad_widgets:
    #         trigger_ad_widget(ad_widget)
    # SA_ad_widgets-current_ad_widgets
def extract_SA_ad_widgets(ad_df):
    # Function to extract event handlers from the handlers field
    def extract_event_handlers(handlers_str):
        try:
            handlers = json.loads(handlers_str.replace("'", "\""))
            events = [handler['event'] for handler in handlers]
            return ", ".join(events)
        except (json.JSONDecodeError, KeyError):
            return ""

    # Function to remove duplicate events
    def remove_duplicates(events_str):
        events = events_str.split(", ")
        unique_events = list(dict.fromkeys(events))  # Maintain order and remove duplicates
        return ", ".join(unique_events)
    widgets=ad_df['ad-widget'].str.split('|', expand=True)
    widgets.columns=['className','widget_id','num_id']

    event_handlers = ad_df['handlers'].apply(extract_event_handlers).apply(remove_duplicates)
    ad_df=pd.concat([widgets,event_handlers,ad_df['activity_name']],axis=1)
    ad_df.drop_duplicates(subset='widget_id', inplace=True)

    # ad_df['handlers']=ad_df.handlers.fillna('none')
    ad_df=ad_df[ad_df['widget_id'].apply(remove_false_positives)]
    # def row_to_dict(group):
    #     return group.drop(columns='activity_name').to_dict(orient='records')
    #
    # ad_dict = ad_df.groupby('activity_name').apply(row_to_dict).reset_index(drop=True)
    return ad_df
def trigger_ad_widget(event):
    pass
def exists_ad_widgets(ad_widget,events):
    for event in events:
        if event.widget.resourceId.split('/')[-1]==ad_widget['widget_id']:
            # assert event.widget.clazz==ad_widget['className']
            return event
    # in this case, we encounter diaglog/optionmenu
    return False
def findPackage_u2():
    packageName = False
    d=u2.connect()
    # time.sleep(1)
    if d(text="More info").count > 0:
        d(text='More info').click()
        time.sleep(1)
    # for Android 9, it doesn't always show more info
    # else:
    #     return 0

    d.xpath("//android.widget.TextView").wait(1)

    if d.xpath('//*[@content-desc="More options"]').exists:
        d.xpath('//*[@content-desc="More options"]').click()
        time.sleep(1)

    if d.xpath('//*[@content-desc="More Options"]').exists:
        d.xpath('//*[@content-desc="More Options"]').click()
        time.sleep(1)

    if d(text='Share').count>0:
        # click Share
        d(text='Share')[0].click()
        # click copy to clipboard
        time.sleep(1)

        d(text='Copy URL')[0].click()
        d.app_start('ca.zgrs.clipper')
        time.sleep(1)
        serial_number='R5CT90DQ2ND'
        cmdOutput = os.popen('adb -s {} shell am broadcast -a clipper.get'.format(serial_number))
        intent=cmdOutput.read()
        packageName=intent.split('id=')[-1][:-2]

    return packageName


