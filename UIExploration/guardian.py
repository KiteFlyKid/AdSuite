import gc
import time

import chatgpt
import copy
from configs import *
import util
from hierarchy import SemanticHierarchy, TotalVisibleHierarchy, VisibleHierarchy, Hierarchy
from screen_control import AndroidController
from typing import List, Tuple, Callable
from infra import TestCase,AdTestCase, EventSeq, Oracle, Event, Widget
from context import Context
from random import shuffle
from util import start_app
from adsuite import *
import re
import  pandas as pd
from atg import *
from rag import  RAG
from os.path import join as pjoin
ATTEMPT_LIMIT = 18


class Guardian:
    target_context: Context
    target: str
    contexts: List[Context]
    history: List[Context]
    all_contexts: List[Context]
    controller: AndroidController
    session: chatgpt.Session
    app: str
    pkg: str
    generation_limit: int = ATTEMPT_LIMIT
    attempt_cnt: int
    fin_event: Event
    def __init__(self, _app, _pkg,_target: str, _port: str, ad_csv=None,_target_hierarchy=None, _target_len=0,GENERATION = None,rel_text = [],rel_content_desc = [],fin_event=None):
        self.app = _app
        self.pkg = _pkg
        self.target = _target
        self.target_context = None if _target_hierarchy is None else \
            Context(None, None, SemanticHierarchy(self.pkg, self.app, _target_hierarchy, _target_hierarchy))
        self.last_context = None if _target_hierarchy is None else \
            TotalVisibleHierarchy(_pkg, _target_hierarchy, _target_hierarchy)
        self.target_len = _target_len
        self.controller = AndroidController(port=_port)
        self.last_event = None
        self.all_events = []
        self.session_history=[]
        self.ad_events=[]
        self.adlibs=["unityads", "facebook.ads", "gms.ads", "doubleclick", "google.ads", "flurry", "appbrain", "adcolony", "applovin", "inmobi.ads", "mbridge.msdk", "com.vungle", "applovin", "com.facebook", "bytedance.sdk", "com.bytedance.sdk", "com.applovin", "com.unity3d", "com.mbridge", "com.adjust", "easybrain", "mopub", "hyprmx", "verizon", "yandex", "smaato", "ironsource", "unity3d", "fyber", "net.pubnative.lite", "io.bidmachine", "inmobi", "bytedance", "io.presage", "com.baidu.mobads", "com.qq.e.ads", "com.kwad", "com.ss.android.downloadlib", "com.zero.flutter_gromore_ads", "com.cssq.ad", "com.youdao.sdk.extra.common"]
        if 'noSA' in GENERATION:
            self.SA_ad_widgets=None
            # self.atg_df=get_atg(_pkg)
        else:
            self.SA_ad_widgets=extract_SA_ad_widgets(ad_csv)
            # self.atg_df=get_atg(_pkg)
        if 'ATG' in GENERATION:
            if 'KHopATG2' in GENERATION:
                self.atg=KHopATG(self.pkg,k=2)
            if 'KHopATG1' in GENERATION:
                self.atg=KHopATG(self.pkg,k=1)
            elif 'DFSATG' in GENERATION:
                self.atg=DFSATG(self.pkg)
            elif 'DijkstraATG' in GENERATION:
                self.atg=DijkstraATG(self.pkg)
            # if self.atg is not None:
            #     ad_ids=self.SA_ad_widgets.widget_id.tolist()
            #     self.atg=self.atg[~self.atg.widgetname.isin(ad_ids)]

        global rel_text_global,rel_content_desc_global
        rel_text_global = rel_text
        rel_content_desc_global = rel_content_desc
        
        if GENERATION == GenerationConf.ONEHOP:
            self.initial_prompt = "Suppose you are an Android UI testing expert helping me write a UI test case.\n" \
                                    " In each step, you task is to tell me the exact widget and how to interact" \
                                    " with it to reach the test target step by step.\n"
        elif GENERATION == GenerationConf.SELFPLANNING:
            self.initial_prompt = "Suppose you are an Android UI testing expert helping me write a UI test case. Make "\
                                  "a plan on how to test the app."

        else:
            self.initial_prompt = "Suppose you are an Android UI testing expert helping me write a UI test case. In our " \
                                "conversation, each round I will provide you with a list of UI elements on the screen, " \
                                "and your task is to select one and only one UI element with its index that is the most likely to reach " \
                                "the test target.\n"
        self.generation_type = GENERATION
        self.first_prompt = self.initial_prompt + \
                            f"We are testing the {self.app} app . " + \
                            f"Our testing target is to {self.target}ff."

        self.targetPrompt = f"Remember our test target is to {self.target} on {self.app}."
        chatgpt.setupChatGPT(self.first_prompt)
        self.attempt_cnt = 0
        self.session = None
        self.fin_event = fin_event
        # self.session = chatgpt.Session()

    def getCurHistory(self) -> List[Event]:
        return [context.event for context in self.contexts[:-1]]

    def getAllHistory(self) -> List[Event]:
        return [context.event for context in self.all_contexts[:-1]]

    def obtain_event_to_execute(self,events: List[Event]):
        
        # filteredEvents = list(filter(lambda x: x[1].strip() != "a View () to click", [(i, e.dump()) for i, e in enumerate(events)]))
        # if len(filteredEvents)==0:
        #     print('error')
        if len(events)>30:
            events=events[:30]
        filteredEvents = [(i, e.dump()) for i, e in enumerate(events)]

        elemDesc = [f"index-{i}: {x[1]}" for i, x in enumerate(filteredEvents)]
        event_map = {i:e[0] for i,e in enumerate(filteredEvents)}
        if len(filteredEvents)==0:
            return Event.back()
        description = f"Currently we have {len(elemDesc)} widgets, namely:\n" + '\n'.join(elemDesc)
        # if self.last_event is not None:
        #     if self.last_event==Event.back():
        #         description += f'The users has previously preformed back'
        #     else:
        #         description+=f'The users has previously preformed {self.last_event.widget.dump()}'
        if 'ATG' in self.generation_type:
            if self.atg.atg_data is not None:
                transitions=self.atg.atg2sequence(self.contexts[-1].activity)
                atg_prompt=self.atg.generate_prompt(transitions=transitions,events=events,contexts=self.all_contexts)
                description=atg_prompt+'\n'+description




        if 'rag' in self.generation_type:
            if not hasattr(self,'rag'):
                self.rag=RAG()
            search_results=self.rag.query_string(self.pkg,self.controller.device.dump_hierarchy())
            rag_prompt=self.rag.read_payload(search_results)
            description = '\n'.join([rag_prompt,description])  # put few shots at beginning


        task = self.targetPrompt
        prompt = '\n'.join([description, task])

        if len(self.session_history)>3:
            self.session_history=self.session_history[-3:]
        self.session=chatgpt.Session(init_history=self.session_history)
        idx = self.session.queryIndex(prompt, lambda x: x in range(len(events)))
        self.session_history.append(self.session.history[-1])

        if idx == -1:
            return Event.back()
        return  events[event_map[idx]]
        
    def deltaValueFun(self, target: str, events: List[Event]):
        """
            Previous UI event execution is correct, start to generate the next UI event with possible failed attempts.
        """
        # get desc for each event. We want to filter out the useless ones
        print('events',events)
        filteredEvents = list(filter(lambda x: x[1].strip() != "a View () to click", [(i, e.dump()) for i, e in enumerate(events)]))
        print('filtered events',filteredEvents)
        idx_mapping = list(map(lambda x: x[0], filteredEvents))

        elemDesc = [f"index-{i}: {x[1]}" for i, x in enumerate(filteredEvents)]
        description = f"Currently we have {len(elemDesc)} widgets, namely:\n" + '\n'.join(elemDesc)
        task = self.targetPrompt
        if HISTORY == HistoryConf.ALL:
            historyDesc = [f"- {e.dump()}" for e in self.getAllHistory()]
            history = f"The user has performed {len(historyDesc)} actions:\n" + '\n'.join(historyDesc)
            description += '\n\n' + history
        elif HISTORY == HistoryConf.PROCESSED:
            historyDesc = [f"- {e.dump()}" for e in self.getCurHistory()]
            history = f"The user has performed {len(historyDesc)} actions:\n" + '\n'.join(historyDesc)
            description += '\n\n' + history
        prompt = '\n'.join([description, task])

        self.session = chatgpt.Session()
        idx = self.session.queryIndex(prompt, lambda x: x in range(len(events)))
        if idx is None:
            raise ValueError("ChatGPT failed to select a UI event")
        if idx == -1:
            # no progress, replan by triggering back for now
            idx = events.index(Event.back())
            return [(i == idx, e) for i, e in enumerate(events)]
        # output the value mapping for the selected event
        return [(i == idx_mapping[idx], e) for i, e in enumerate(events)]
    
    def obtain_ui_desc(self,events: List[Event],blocker:List[str] = []):
        all_block = [x for x in blocker]
        all_block.append("a View () to click")
        filteredEvents = list(filter(lambda x: x[1].strip() not in all_block, [(i, e.dump()) for i, e in enumerate(events)]))
        # print('filtered events',filteredEvents)
        event_map = {i:e[0] for i,e in enumerate(filteredEvents)}

        elemDesc = [f"index-{i}: {x[1]}" for i, x in enumerate(filteredEvents)]
        description = f"Currently we have {len(elemDesc)} UI elements on the screen, namely:\n" + '\n'.join(elemDesc)
        return description,event_map

    def naiveStrategy(self, values: List[Tuple[float, Event]]):
        """
            values of the form (1, Event)
        """
        return max(values, key=lambda x: x[0])[1]

    def naiveTerminate(self, target: str) -> bool:
        if self.attempt_cnt >= self.generation_limit:
            return True
        #if len(self.contexts) == 1:
        #    return False
        filteredEvents = list(
            filter(lambda x: x[1].strip() != "a View () to click",
                   [(i, e.dump()) for i, e in enumerate(self.contexts[-1].getEvents())]))

        elemDesc = [f"- index-{i} {e[1]}" for i, e in enumerate(filteredEvents)]
        #elemDesc = [f"- {e.dump()}" for e in self.contexts[-1].getEvents()]
        description = f"Currently we have {len(elemDesc)} widgets, namely:\n" + '\n'.join(elemDesc)

        historyDesc = [f"- {e.dump()}" for e in self.getCurHistory()]
        history = f"The user has performed {len(historyDesc)} actions:\n" + '\n'.join(historyDesc)
        task = self.targetPrompt + " Do you think that we have successfully reached our goal?"
        prompt = '\n'.join([description, '', history, '', task])

        if self.session == None:
            self.session = chatgpt.Session()
        return self.session.queryOpinion(prompt)

    def aidedTerminate(self, target: str) -> bool:
        if self.attempt_cnt >= self.generation_limit:
            return True
        print([w.__dict__ for w in self.target_context.hierarchy._widgets])
        print(self.target_len)
        if len(self.contexts) >= self.target_len and self.target_context == self.contexts[-1]:
            return True
        return False
        # return self.naiveTerminate(target)
    def oracleTerminate(self,last_event:Event)->bool:
        if self.fin_event is not None and last_event is not None:
            if self.fin_event == last_event:
                return True
        if self.attempt_cnt >= max(min(2.5*self.target_len,self.generation_limit),30):
        # if self.attempt_cnt >= 3:
            return True   
        return False 
    def getInput(self, target) -> str:
        # ask chatGPT what text to input
        task = "You have selected a TextEdit view, which requires a text input." \
               f"Remember that your task is to {target}"
        requirement = "Please insert the text that you want to input." \
                      "Please only respond with the text input and nothing else."
        return self.session.queryString(f"{task}\n{requirement}")

    def getCurrentContext(self, target: str) -> Context:
        if INFODISTILL == InformationDistillationConf.NONE:
            return Context(self.controller.app_info()[1], target,
                           VisibleHierarchy(self.controller.device.dump_hierarchy(),
                                            self.controller.device.dump_hierarchy()))
        return Context(self.controller.app_info()[1], target,
                       SemanticHierarchy(self.pkg, self.app, self.controller.device.dump_hierarchy(),
                                         self.controller.device.dump_hierarchy()))

    def check_interstitial_ads(self,activity:str):
        # print('chec')
        if any(adlib in activity for adlib in self.adlibs) or 'android.vending' in activity:
            # if self.last_event is not None:
                # self.ad_events.append(self.last_event)
            # while any(adlib in self.contexts[-1].activity for adlib in self.adlibs):
            # self.controller.click(360,800,wait_time=1)
            print('Ad activity')
            # time.sleep(15)
            util.restart_app(pkg=self.pkg)
            time.sleep(3)
            # self.controller.back()
    def checkBackLoop(self):
        if len(self.all_events)>3:
            if self.all_events[-1]==self.all_events[-2]==Event.back():
                util.restart_app(pkg=self.pkg)
    def updateContext(self, target: str):
        # TODO: use history context here

        currentContext = self.getCurrentContext(target)



        self.check_interstitial_ads(activity=currentContext.activity)
        self.checkBackLoop()
        # check if still in app
        if self.pkg not in self.controller.app_info():
            # start app again
            # event = Event.back()
            # self.act_back(event)
            # self.controller.click(360,800,wait_time=1)

            util.start_app(pkg=self.pkg)

            time.sleep(3)
            # self.controller.back()
            if self.pkg not in self.controller.app_info():
                self.controller.back()
                self.check_interstitial_ads(activity=currentContext.activity)
                raise ValueError("Something Failed!")
            self.contexts[-1].ban_current()
            self.check_interstitial_ads(activity=currentContext.activity)
            # return
            # currentContext = self.getCurrentContext(target)



        currentContext = self.getCurrentContext(target)
        self.all_contexts.append(self.getCurrentContext(target))
        self.history.append(self.getCurrentContext(target))
        # check loop
        try:
            contextIdx = self.contexts.index(currentContext)
            self.contexts = self.contexts[:contextIdx + 1]
            if self.contexts[-1].event is not None:
                self.contexts[-1].ban_current()
            return
        except ValueError as e:
            print(str(e))

        print("new screen!")
        # currentContext.setRelevant()
        event: Event = self.contexts[-1].event
        if event is not None and event.action == "text":
            currentContext.ban(event)
        self.contexts.append(currentContext)


    def skipSplashAds(self,raw_events):
        for raw_event in raw_events:
            try:
                if raw_event.widget.text in ['Continue to app','Continue']:
                    # pos = raw_event.widget.pos
                    # click_pos = ((pos[2] + pos[0]) / 2, (pos[1] + pos[3]) / 2)
                    # self.controller.click(*click_pos)
                    return raw_event
            except Exception as e:
                print(str(e))
                return None
        return None

    def mainLoop(self, target: str,
                 termination: Callable[['Guardian', Event], bool] = oracleTerminate) -> EventSeq:
        
        #  valueFun: Callable[['Guardian', str, List[Event]], List[Tuple[float, Event]]] = deltaValueFun,
        #  strategy: Callable[['Guardian', List[Tuple[float, Event]]], Event] = naiveStrategy,
        # init context
        initContext: Context = self.getCurrentContext(target)
        if len(self.history) == 0:
            self.history.append(initContext)
        self.all_contexts = [initContext]
        self.contexts = [initContext]
        # self.contexts[-1].setRelevant()



        while not termination(self, self.last_event):
            #wait ad to load
            time.sleep(3)
            # get potential events

            events = self.contexts[-1].getEvents()
            raw_events=self.contexts[-1].getRawEvents()


            skipped_splashads=self.skipSplashAds(raw_events)
            if skipped_splashads is not None:
                self.act_event(skipped_splashads)
                continue

            SA_ad_widgets=self.SA_ad_widgets#.get(act_name)
            if SA_ad_widgets is not None:
                for idx,ad_widget in copy.deepcopy(SA_ad_widgets).iterrows():
                    event=exists_ad_widgets(ad_widget, raw_events)
                    if event:
                        self.all_events.append(event)
                        if event not in self.ad_events:
                            print(f'act ad event: {event.widget.resourceId}')
                            self.ad_events.append(event)
                        # SA_ad_widgets.drop(index=idx,axis=0,inplace=True)
            # if SA_ad_widgets is not None and len(SA_ad_widgets) > 0:
                # we ask LLM to: go optionmenu, open dialog
                # event = self.obtain_ad_event_to_execute(SA_ad_widgets[0],events)
                # pass

            if len(events)==0:
                    event=Event.back()
            else:
                if len([e for e in events if e.dump().strip() != "a View () to click"]) < 2:
                    self.contexts[-1].bannedEvents.clear()
                    events = self.contexts[-1].getEvents()

                for ad_event in self.ad_events:
                    # if ad_event in events:
                    if ad_event==Event.back():
                        continue
                    remove_ad_events(ad_event,events)

                event = self.obtain_event_to_execute(events)
            # decide for ev
            # values = valueFun(self, target, events)
            # event: Event = strategy(self, values)

            if event.action == "text":
                event.input = self.getInput(target)

            self.act_event(event)


            # dump history for debugging
            #for context in self.contexts[:-1]:
            #    print(context.event.dump(True))
            #ChatDroid.debug()
            #input()
        if hasattr(self, 'rag'):
            del self.rag
            gc.collect()
        self.controller.stop_app(self.pkg)
        return EventSeq(self.getCurHistory())
    def mainLoopRandom(self, target: str,
                 termination: Callable[['Guardian', Event], bool] = oracleTerminate) -> EventSeq:

        #  valueFun: Callable[['Guardian', str, List[Event]], List[Tuple[float, Event]]] = deltaValueFun,
        #  strategy: Callable[['Guardian', List[Tuple[float, Event]]], Event] = naiveStrategy,
        # init context
        initContext: Context = self.getCurrentContext(target)
        if len(self.history) == 0:
            self.history.append(initContext)
        self.all_contexts = [initContext]
        self.contexts = [initContext]
        # self.contexts[-1].setRelevant()

        while not termination(self, self.last_event):
            # wait ad to load
            time.sleep(3)
            # get potential events


            events = self.contexts[-1].getEvents()

            raw_events = self.contexts[-1].getRawEvents()
            # act_name=self.contexts[-1].activity
            # if act_name[0]=='.':
            #     act_name=self.pkg+act_name

            SA_ad_widgets = self.SA_ad_widgets  # .get(act_name)
            if SA_ad_widgets is not None:
                for idx, ad_widget in copy.deepcopy(SA_ad_widgets).iterrows():
                    event = exists_ad_widgets(ad_widget, raw_events)
                    if event:
                        self.all_events.append(event)
                        if event not in self.ad_events:
                            print(f'act ad event: {event.widget.resourceId}')
                            self.ad_events.append(event)
                        # SA_ad_widgets.drop(index=idx,axis=0,inplace=True)
            # if SA_ad_widgets is not None and len(SA_ad_widgets) > 0:
            # we ask LLM to: go optionmenu, open dialog
            # event = self.obtain_ad_event_to_execute(SA_ad_widgets[0],events)
            # pass

            if len(events) == 0:
                event = Event.back()
            else:
                if len([e for e in events if e.dump().strip() != "a View () to click"]) < 2:
                    self.contexts[-1].bannedEvents.clear()
                    events = self.contexts[-1].getEvents()

                for ad_event in self.ad_events:
                    # if ad_event in events:
                    if ad_event==Event.back():
                        continue
                    remove_ad_events(ad_event, events)

            if 'DFS' in self.generation_type:
                events.append(Event.back())
            if 'MADDROID' in self.generation_type:
                for event in events:
                    widget=event.widget
                    if widget is not None:
                        if any([ c in event.widget.clazz for c in ['ImageView','WebView','ViewFlipper']]):
                            events.remove(event)
                            events.insert(0,event)

            events=list(filter(lambda x: x not in self.contexts[-1].bannedEvents, events))
            event=events[0]
            if event.action == "text":
                # event.input = self.getInput(target)
                event.input='hello world'

            self.act_event(event)



        return EventSeq(self.getCurHistory())

    def act_event(self,event):
        # perform action
        event.act(self.controller)
        self.last_event = event
        self.all_events.append(event)
        time.sleep(1)

        # check context and remove loop
        self.contexts[-1].setEvent(event)
        self.all_contexts[-1].setEvent(event)
        self.history[-1].setEvent(event)
        try:
            self.updateContext(self.target)
        except ValueError:
            print("Something Wrong!!!!")
            util.start_app(pkg=self.pkg)
            time.sleep(3)
            # break
        self.attempt_cnt += 1
    def act_back(self,event):
        # perform action
        event.act(self.controller)
        # self.last_event = event
        self.all_events.append(event)
        time.sleep(1)

        # check context and remove loop
        self.contexts[-1].setEvent(event)
        self.all_contexts[-1].setEvent(event)
        self.history[-1].setEvent(event)
        try:
            self.updateContext(self.target)
        except ValueError:
            print("Something Wrong!!!!")
            util.start_app(pkg=self.pkg)
            time.sleep(3)
            # break
        # self.attempt_cnt += 1
    def mainLoopNoPrune(self, target: str,
                 valueFun: Callable[['Guardian', str, List[Event]], List[Tuple[float, Event]]] = deltaValueFun,
                 strategy: Callable[['Guardian', List[Tuple[float, Event]]], Event] = naiveStrategy,
                 termination: Callable[['Guardian', Event], bool] = oracleTerminate) -> EventSeq:
        # init context
        initContext: Context = self.getCurrentContext(target)
        if len(self.history) == 0:
            self.history.append(initContext)
        self.all_contexts = [initContext]
        self.contexts = [initContext]
        self.contexts[-1].setRelevant()

        while not termination(self, self.last_event):
            # get potential events
            self.contexts[-1].bannedEvents.clear()
            events = self.contexts[-1].getEvents()

            # decide for event
            event = self.obtain_event_to_execute(events)
            if event.action == "text":
                event.input = self.getInput(target)

            # perform action
            event.act(self.controller)
            self.last_event = event
            self.all_events.append(event)
            time.sleep(1)
            print(event.dumpAsDict())

            # check context and remove loop
            self.contexts[-1].setEvent(event)
            self.all_contexts[-1].setEvent(event)
            self.history[-1].setEvent(event)
            try:
                self.updateContext(target)
            except ValueError:
                print("Something Wrong!!!!")
                break
            self.attempt_cnt += 1

            # dump history for debugging
            #for context in self.contexts[:-1]:
            #    print(context.event.dump(True))
            #ChatDroid.debug()
            #input()

        return EventSeq(self.getCurHistory())

    
    def nobacktrack(self,target)->EventSeq:
        # init context
        initContext: Context = self.getCurrentContext(target)
        if len(self.history) == 0:
            self.history.append(initContext)
        self.all_contexts = [initContext]
        self.contexts = [initContext]
        self.contexts[-1].setRelevant()
        last_event = None
        while not self.oracleTerminate(target,last_event):
            # get potential events
            events = self.contexts[-1].getEvents()

            # decide for event
            values = self.deltaValueFun(target, events)
            event: Event = self.naiveStrategy(values)
            if event.action == "text":
                event.input = self.getInput(target)
            if event.action == "back":
                break
            # perform action
            event.act(self.controller)
            self.all_events.append(event)
            last_event = event
            time.sleep(1)

            self.contexts[-1].setEvent(event)
            self.all_contexts[-1].setEvent(event)
            self.history[-1].setEvent(event)
            self.attempt_cnt += 1

            # dump history for debugging
            #for context in self.contexts[:-1]:
            #    print(context.event.dump(True))
            #ChatDroid.debug()
            #input()

        return EventSeq(self.getCurHistory())

    def naiveCodeStrategy(self, events, instruction):
        '''
        find the first widget whose name appears in the action given by gpt
        '''
        for i in range(len(events)):
            try:
                if(events[i].widget.contentDesc.split()[0].lower() in instruction.lower() and\
                    events[i].action in instruction.lower()):
                    return events[i]
            except:
                ...
        return None


    def tranformScriptToEvents(self, instructions, strategy = naiveCodeStrategy):
        if(INFODISTILL != InformationDistillationConf.NONE):
            raise ValueError("OneHot and Selfplanning generation needs INFODISTILL be NONE.")
        
        initContext: Context = self.getCurrentContext(self.target)

        self.all_contexts = [initContext]
        self.contexts = [initContext]
        self.contexts[-1].setRelevant()

        for instruction in instructions:
            # get potential events
            events = self.contexts[-1].hierarchy.getEvents()

            event = strategy(self, events, instruction)
            if event is None:
                continue
            elif event.action == "text":
                name = event.widget.contentDesc.split()[0].lower()
                i = instruction.lower()
                start = i.find(name)
                s = i[start:].find("\"")
                e = i[e:].find("\"")
                if (s==-1 or e==-1):
                    continue
                event.input = instruction[s,e]
            print(event.dumpAsDict())
            print(self.contexts)

            # perform action
            event.act(self.controller)
            self.all_events.append(event)

            # check context and remove loop
            self.contexts[-1].setEvent(event)

            currentContext = self.getCurrentContext(self.target)
            
            self.all_contexts.append(currentContext)
            self.history.append(currentContext)


            # dump history for debugging
            for context in self.contexts[:]:
                print(context.event.dump(True))
        
        return [context.event for context in self.contexts[:]]

    # both one hop and self planning need trimming
    def oneHop(self) -> EventSeq:
        chatsession = chatgpt.Session()
        all_test_steps = chatsession.spawn_tests(self.target,self.app,spawn_num=1)
        test_steps = all_test_steps[0]
        test_steps = {int(k):v for k,v in test_steps.items()}
        max_step = max([k for k in test_steps.keys()])
        
        initContext: Context = self.getCurrentContext(self.target)
        if len(self.history) == 0:
            self.history.append(initContext)
        self.all_contexts = [initContext]
        self.contexts = [initContext]
        self.contexts[-1].setRelevant()
        
        for i in range(1,max_step+1):
            current_step = test_steps[i]
            if current_step.lower().startswith('launch'):
                continue
            events = self.contexts[-1].getEvents()
            ui_desc,index_mapping = self.obtain_ui_desc(events)
            grounded_id = chatsession.grounding_single(self.target,self.app,current_step,ui_desc)
            event = None
            print(self.target,self.app,current_step,ui_desc)
            try:
                idx = int(grounded_id[6:])
            except:
                break
            if idx >= 0 and idx < len(events):
                event = events[index_mapping[idx]]
            if event is None:
                break
            if event.action =='back':
                break
            try:
                event.act(self.controller)
                self.all_events.append(event)
            except:
                break
            time.sleep(1)

            # check context and remove loop
            self.contexts[-1].setEvent(event)
            self.all_contexts[-1].setEvent(event)
            self.history[-1].setEvent(event)
            try:
                self.updateContext(self.target)
            except ValueError:
                print("Something Wrong!!!!")
                break
            self.attempt_cnt += 1
        return EventSeq(self.getCurHistory())
        
    def selfPlanning(self) -> EventSeq:
        chatsession = chatgpt.Session()
        initContext: Context = self.getCurrentContext(self.target)
        if len(self.history) == 0:
            self.history.append(initContext)
        self.all_contexts = [initContext]
        self.contexts = [initContext]
        self.contexts[-1].setRelevant()
        last_event = None
        while self.attempt_cnt < self.generation_limit and not self.oracleTerminate(last_event):
            events = self.contexts[-1].getEvents()
            ui_desc,index_mapping = self.obtain_ui_desc(events)
            grounded_id = chatsession.targeting(self.target,self.app,ui_desc)
            event = None
            print(self.target,self.app,ui_desc)
            limit = lambda x: x in range(len(events))
            idx = -1
            try:
                for m in re.finditer('index-', grounded_id):
                    local = grounded_id[m.start():m.start()+12]
                    if 'index-none' not in local and limit(chatsession.findFirstInteger(local[5:])):
                        idx = chatsession.findFirstInteger(local[5:])
                        break
            except:
                idx = -1
            if idx >= 0 and idx < len(events):
                event = events[index_mapping[idx]]
            if event is None:
                event = Event.back()
            if event.action == 'back':
                break
            last_event = event
            event.act(self.controller)
            self.all_events.append(event)
            time.sleep(1)

            # check context and remove loop
            self.contexts[-1].setEvent(event)
            self.all_contexts[-1].setEvent(event)
            self.history[-1].setEvent(event)
            try:
                self.updateContext(self.target)
            except ValueError:
                print("Something Wrong!!!!")
                break
            self.attempt_cnt += 1
        return EventSeq(self.getCurHistory())
    def BACKTRACK(self) -> EventSeq:
        self.blocked_elems = []
        self.last_elem = None
        chatsession = chatgpt.Session()
        initContext: Context = self.getCurrentContext(self.target)
        if len(self.history) == 0:
            self.history.append(initContext)
        self.all_contexts = [initContext]
        self.contexts = [initContext]
        self.contexts[-1].setRelevant()
        last_event = None
        while self.attempt_cnt < self.generation_limit and not self.oracleTerminate(last_event):
            events = self.contexts[-1].getEvents()
            ui_desc,index_mapping = self.obtain_ui_desc(events,blocker = [e.dump() for e in self.blocked_elems])
            grounded_id = chatsession.targeting(self.target,self.app,ui_desc)
            event = None
            print(self.target,self.app,ui_desc)
            limit = lambda x: x in range(len(events))
            idx = -1
            try:
                for m in re.finditer('index-', grounded_id):
                    local = grounded_id[m.start():m.start()+12]
                    if 'index-none' not in local and limit(chatsession.findFirstInteger(local[5:])):
                        idx = chatsession.findFirstInteger(local[5:])
                        break
            except:
                idx = -1
            if idx >= 0 and idx < len(events):
                event = events[index_mapping[idx]]
            if event is None:
                event = Event.back()
            if event.action == 'back' and isinstance(self.last_elem,Event) and self.last_elem.action != 'back':
                self.blocked_elems.append(self.last_elem)
            try:
                last_event = event
                event.act(self.controller)
                self.all_events.append(event)
            except:
                break
            time.sleep(1)
            self.last_elem = event
            # check context and remove loop
            self.contexts[-1].setEvent(event)
            self.all_contexts[-1].setEvent(event)
            self.history[-1].setEvent(event)
            try:
                self.updateContext(self.target)
            except ValueError:
                print("Something Wrong!!!!")
                break
            self.attempt_cnt += 1
        return EventSeq(self.getCurHistory()) 

    def genTestCase(self) -> TestCase:
        self.history = []
        if self.generation_type == GenerationConf.NOBACKTRACK:
            return TestCase(self.nobacktrack(self.target),[context.hierarchy for context in  self.contexts])
        if self.generation_type == GenerationConf.BACKTRACK:
            return TestCase(self.BACKTRACK(),[context.hierarchy for context in  self.contexts])
        if self.generation_type == GenerationConf.ONEHOP:
            return TestCase(self.oneHop(), [context.hierarchy for context in  self.contexts])
        if self.generation_type == GenerationConf.SELFPLANNING:
            return TestCase(self.selfPlanning(), [context.hierarchy for context in  self.contexts])
        # if self.generation_type == GenerationConf.STATICFDTREE:
        #     return TestCase(self.STATICFDTREE(), [context.hierarchy for context in  self.contexts])
        if self.generation_type == GenerationConf.NOPRUNE:
            return TestCase(self.mainLoopNoPrune(self.target), [context.hierarchy for context in  self.contexts])

        if 'DFS' in self.generation_type or 'BFS' in self.generation_type:
            return AdTestCase(self.mainLoopRandom(self.target), self.ad_events, self.all_events,
                              [context.hierarchy for context in self.contexts])

        if self.generation_type=='DFS_noSA' or self.generation_type=='BFS_noSA':
            return AdTestCase(self.mainLoopRandom(self.target), self.ad_events, self.all_events,
                              [context.hierarchy for context in self.contexts])
        self.generation_limit = 50
        if HISTORY != HistoryConf.SPLIT:
            # return TestCase(self.mainLoopAds(self.target), [context.hierarchy for context in self.contexts])
            return AdTestCase(self.mainLoop(self.target), self.ad_events, self.all_events,[context.hierarchy for context in  self.contexts])
        raise NotImplementedError()

