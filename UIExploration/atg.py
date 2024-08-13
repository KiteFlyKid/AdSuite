

import re
import pandas as pd
import pydot
from pathlib import  Path
import networkx as nx

class ATG:
    def __init__(self, pkg):
        self.pkg = pkg
        # self.widget_id = widget_id
        self.atg_data = self.read_atg(pkg)

    def read_atg(self,pkg_name):
        # Part 1: Find DIALOG/OptionsMenu that belong to each ACT based on "alloc"
        # Load the DOT file
        file_path = f"data/dot/{pkg_name}.apk.wtg.dot"
        if Path(file_path).exists():
            (graph,) = pydot.graph_from_dot_file(file_path)
        else:
            return None

        df = self.filter_edges(graph)
        if len(df)==0:
            return None
        def extract_info_act(text):
            matches = re.findall(r'\[.*?\]', text)
            return matches[0][1:-1]

        df['Source Activity'] = df['Source Activity'].apply(extract_info_act)
        df['Target Activity'] = df['Target Activity'].apply(extract_info_act)

        # atg_df = df.dropna()
        atg_df = df[df.classname.apply(len) > 0]
        return atg_df

    def filter_edges(self,graph):
        edges = set()
        adlibs = ["unityads", "facebook.ads", "gms.ads", "doubleclick", "google.ads", "flurry", "appbrain", "adcolony",
                  "applovin", "inmobi.ads", "mbridge.msdk", "com.vungle", "applovin", "com.facebook", "bytedance.sdk",
                  "com.bytedance.sdk", "com.applovin", "com.unity3d", "com.mbridge", "com.adjust", "easybrain", "mopub",
                  "hyprmx", "verizon", "yandex", "smaato", "ironsource", "unity3d", "fyber", "net.pubnative.lite",
                  "io.bidmachine", "inmobi", "bytedance", "io.presage", "com.baidu.mobads", "com.qq.e.ads", "com.kwad",
                  "com.ss.android.downloadlib", "com.zero.flutter_gromore_ads", "com.cssq.ad",
                  "com.youdao.sdk.extra.common"]
        android_lib = '"android'
        for edge in graph.get_edges():
            src = edge.get_source()
            tgt = edge.get_destination()
            src_label = graph.get_node(src)[0].get_label()
            tgt_label = graph.get_node(tgt)[0].get_label()
            if src != tgt:  # Remove cyclic edges
                # if pkg_name not in src_label or pkg_name not in tgt_label:
                #     continue
                if src_label.startswith(android_lib) or tgt_label.startswith(android_lib):
                    continue
                if any([adlib in src_label for adlib in adlibs]) or any([adlib in tgt_label for adlib in adlibs]):
                    continue
                edge_label = edge.get_label()
                evt_match = re.search(r'evt: ([^\n]+)', edge_label)
                widget_match = re.search(r'widget: ([^\n]+)', edge_label)
                if evt_match and widget_match:
                    evt = evt_match.group(1)
                    widget = widget_match.group(1)
                    edges.add((src_label, tgt_label, evt, widget))

        # activity_dialog_df = pd.DataFrame(list(activity_dialog_map), columns=['Activity', 'Dialog', 'Handler'])
        filtered_edges_df = pd.DataFrame(list(edges), columns=['Source Activity', 'Target Activity', 'Event', 'Widget'])
        if len(filtered_edges_df)==0:
            return filtered_edges_df
        filtered_edges_df['Event'] = filtered_edges_df['Event'].apply(lambda x: x.split('\\n')[0])

        # Redefine the regex pattern to strictly end at the first closing bracket after widget name
        refined_pattern = r'\[(.*?),WID\[.*?\|(.*?)\]'

        # Reapply the extraction with the refined regex pattern
        def refined_extract_info(text):
            matches = re.findall(refined_pattern, text)
            return matches

        filtered_edges_df['refined_extracted_info'] = filtered_edges_df['Widget'].apply(refined_extract_info)

        # Display the refined results
        # df=filtered_edges_df[['Widget', 'refined_extracted_info']]

        # Function to split the extracted info into classname and widgetname
        def split_info(extracted_list):
            if extracted_list:
                return extracted_list[0]
            return "", ""

        # Split the refined_extracted_info into two new columns: classname and widgetname
        filtered_edges_df['classname'], filtered_edges_df['widgetname'] = zip(
            *filtered_edges_df['refined_extracted_info'].apply(split_info))

        # Display the updated DataFrame
        df = filtered_edges_df[['Source Activity', 'Target Activity', 'classname', 'widgetname']]
        return df

    def get_useful_edges(self, events,transitions):
        available_ids = [event.widget.resourceId.split('/')[-1] for event in events if event.widget.resourceId is not None]

        useful_transitions = transitions[transitions.widgetname.isin(available_ids)]
        # useful_atg_data = useful_atg_data[~self.atg_data['Source Activity'].str.startswith('android') & ~self.atg_data['Target Activity'].str.startswith('android')]
        useful_transitions=useful_transitions[~useful_transitions['Source Activity'].str.startswith('android')]

        return useful_transitions

    def get_transition_info(self, visited_activities, transitions):
        transitions_info = set()
        for _, row in transitions.iterrows():
            target_activities = row['Target Activity']
            targets=[]
            for target_activity in target_activities:
                if target_activity in visited_activities:
                    targets.append(f'{target_activity}(visited)')
                else:
                    targets.append(f'{target_activity}(unvisited)')
            widget_name = row['widgetname']
            transitions_info.add(f"{', '.join(targets)} via widget resourceId={widget_name}")
        return list(transitions_info)
    def remove_system_activities(self,transitions):
        transitions['Target Activity']=transitions['Target Activity'].apply(lambda x:[i for i in x if not i.startswith('android') ])

    def generate_prompt(self,transitions,events,contexts):
        #remove cycle
        transitions=transitions[transitions['Source Activity']!=transitions['Target Activity']]
        #remove duplicates
        transitions=transitions.drop_duplicates(subset=['Source Activity','Target Activity','widgetname'])

        #get the reachable neibors from each widgets
        transitions = transitions.groupby(['widgetname', 'Source Activity'])['Target Activity'].agg(list).reset_index()

        if len(transitions)==0:
            return ''

        visited_activities = [context.activity for context in contexts]
        useful_transitions = self.get_useful_edges(events, transitions)
        other_transitions = transitions[~transitions.index.isin(useful_transitions.index)]



        # Building the transitions info string
        transitions_info_useful = self.get_transition_info(visited_activities, useful_transitions)
        transitions_info_others = self.get_transition_info(visited_activities, other_transitions)

        transitions_info = transitions_info_useful
        # if len(transitions_info) < 20:
        #     transitions_info = transitions_info_useful + transitions_info_others
        if len(transitions_info)>20:
            transitions_info = transitions_info[:20]

        if len(transitions_info)==0:
            return ''
        transitions_info='\n'.join(transitions_info)
        source_activity=contexts[-1].activity
        prompt = f"""Based on the activity transition graph, the current activity '{source_activity}' can transfer to the following target activities:\n{transitions_info} """
        return prompt.strip()

    def atg2sequence(self):
        # Base method should be overridden
        raise NotImplementedError("This method should be implemented by subclasses.")

class KHopATG(ATG):
    def __init__(self, pkg, k=1):
        super().__init__(pkg)
        self.k = k

    def atg2sequence(self, source_activity, depth=1):
        if source_activity[0]=='.':
            source_activity=self.pkg+source_activity
        if depth > self.k:
            return pd.DataFrame()
        transitions = self.atg_data[self.atg_data['Source Activity'] == source_activity]
        if depth < self.k:
            results = [transitions]
            for activity in transitions['Target Activity'].unique():
                sub_transitions = self.atg2sequence(activity, depth + 1)
                results.append(sub_transitions)
            transitions = pd.concat(results, ignore_index=True)
        return transitions

class DFSATG(ATG):
    def __init__(self, pkg):
        super().__init__(pkg)

    def atg2sequence(self, source_activity, visited=None):
        if source_activity[0]=='.':
            source_activity=self.pkg+source_activity
        if visited is None:
            visited = set()
        visited.add(source_activity)
        transitions = self.atg_data[self.atg_data['Source Activity'] == source_activity]
        results = [transitions]
        for activity in transitions['Target Activity'].unique():
            if activity not in visited:
                sub_transitions = self.atg2sequence(activity, visited)
                results.append(sub_transitions)
        transitions = pd.concat(results, ignore_index=True)
        return transitions

class DijkstraATG(ATG):
    def __init__(self, pkg):
        super().__init__(pkg)
        if self.atg_data is not None:
            self.graph = self.build_graph()
        else:
            self.graph=nx.DiGraph()

    def build_graph(self):
        G = nx.DiGraph()
        for _, row in self.atg_data.iterrows():
            # Add edges with weight. If specific weights are available, they can be used instead of a constant.
            G.add_edge(row['Source Activity'], row['Target Activity'], weight=1)
        return G

    def atg2sequence(self, source_activity):
        if source_activity[0]=='.':
            source_activity=self.pkg+source_activity
        # Use NetworkX to find the shortest path from source to all other nodes
        if source_activity not in list(self.graph.nodes):
            return pd.DataFrame()
        lengths = nx.single_source_dijkstra_path_length(self.graph, source_activity)
        paths = nx.single_source_dijkstra_path(self.graph, source_activity)
        result = []
        for target_activity, path in paths.items():
            cost = lengths[target_activity]
            if cost==0:
                continue
            if len(path) > 1:
                # Find widgetname for the transition from source to first activity in path
                first_transition = self.atg_data[
                    (self.atg_data['Source Activity'] == path[0]) &
                    (self.atg_data['Target Activity'] == path[1])
                    ]['widgetname'].tolist()
                first_transition=list(set(first_transition))# Get the first matching widgetname
            else:
                first_transition = None  # No transition if path length is 1 (same node)

            result.append({
                'Source Activity': source_activity,
                'Target Activity': target_activity,
                'Path': path,
                'Cost': cost,
                'widgetname': first_transition
            })

        return pd.DataFrame(result)
    def get_transition_info(self, visited_activities, transitions):
        transitions_info = set()
        for _, row in transitions.iterrows():
            target_activity = row['Target Activity']
            if target_activity in visited_activities:
                target = f'{target_activity}(visited) '
            else:
                target = target_activity
            widgets=', '.join(row.widgetname)
            # widget_name = row['widgetname']
            transitions_info.add(f"{target} with cost {row.Cost} via widgets resourceId={widgets}")
        return list(transitions_info)

    def generate_prompt(self,transitions,events,contexts):
        # transitions=transitions.drop_duplicates(subset=['Source Activity','Target Activity','widgetname'])
        # transitions = transitions.groupby(['widgetname', 'Source Activity'])['Target Activity'].agg(list).reset_index()

        # transitions = transitions.groupby(['widgetname', 'Source Activity'])['Target Activity'].agg(list).reset_index()

        if len(transitions)==0:
            return ''
        visited_activities = [context.activity for context in contexts]
        useful_transitions = self.get_useful_edges(events, transitions)
        other_transitions = transitions[~transitions.index.isin(useful_transitions.index)]



        # Building the transitions info string
        transitions_info_useful = self.get_transition_info(visited_activities, useful_transitions)
        transitions_info_others = self.get_transition_info(visited_activities, other_transitions)

        transitions_info = transitions_info_useful
        if len(transitions_info) < 20:
            transitions_info = transitions_info_useful + transitions_info_others
        if len(transitions_info)>20:
            transitions_info = transitions_info[:20]

        if len(transitions_info)==0:
            return ''
        source_activity = contexts[-1].activity
        transitions_info='\n'.join(transitions_info)
        prompt = f"""Based on the activity transition graph, the current activity '{source_activity}' can transfer to the following target activities:\n{transitions_info}"""
        return prompt.strip()


if __name__=='__main__':
    # Load the DOT file
    # atg=KHopATG(pkg='com.afghan.af.amir.ahmadi')
    atg = DijkstraATG(pkg='com.afghan.af.amir.ahmadi')
    atg=DijkstraATG(pkg='com.purpleberry.staticwall.cnygreeting.g01')
    # atg = DFSATG(pkg='com.afghan.af.amir.ahmadi')
    transitions = atg.atg2sequence('com.purpleberry.staticwall.cnygreeting.g01.MainCategory')
    transition_info=atg.get_transition_info([],transitions)
    # transitions = transitions.drop_duplicates(subset=['Source Activity', 'Target Activity', 'widgetname'])
    transitions_info=atg.remove_system_activities(transitions)
    # print(grouped)
    # atg_prompt = atg.generate_prompt(transitions=transitions, events=events, contexts=self.contexts)
    # grouped = transitions.groupby(['widgetname', 'Source Activity'])['Target Activity'].agg(list).reset_index()

    # prompt=KHopATG.generate_prompt(contexts='com.purpleberry.staticwall.cnygreeting.g01.MainCategory',atg_data=atg)
    # print(prompt)