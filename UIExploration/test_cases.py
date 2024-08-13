import inspect
import re
import configs
import time
import sys
import json
import os
from setup import setup_app
from util import *
from hierarchy import parseUIHierarchy

def save_json(path, js):
    with open(path, "w") as f:
        json.dump(js, f)

def save_current_json(path):
    save_json(path, parseUIHierarchy(get_current_ui()))
    
def save_ui(path):
    os.system("cp hierarchy.xml " + path)    

class Test:
    def _pre_oracle(self):
        pass
    def _oracle(self):
        pass
    def _body(self):
        pass
    def _cleanup(self):
        pass
    def gotest(self, sstr:str):
        tree = get_current_ui()
        intlst = parseUIHierarchy(tree)
        save_ui(self.path + "/testui" + str(len(self.testjson)) + ".xml")
        save_current_screen(self.path + "/testfig" + str(len(self.testjson)) + ".png")
        save_json(self.path + "/testjson" + str(len(self.testjson)) + ".json", intlst)
        
        match = re.fullmatch(r"tap (\d+) (\d+)", sstr)
        if match:
            point = [int(i) for i in match.group(1, 2)]
            nodes = list(filter(lambda x: in_bounds(x["pos"], point), intlst))
            assert(len(nodes) != 0)
            if len(nodes) != 1:
                for (i, x) in enumerate(nodes):
                    print()
                    print("index = ", i)
                    print(x)
                k = int(input())
                node = nodes[k]
            else:
                node = nodes[0]
            dict = {"type": "click", "data": node}
            self.testjson.append(dict)
            print(dict)
            return 
        
        match = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", sstr)
        if match:
            tmp = [int(i) for i in match.group(1, 2, 3, 4)]
            point = [(tmp[0] + tmp[2]) // 2, (tmp[1] + tmp[3]) // 2]    
            nodes = list(filter(lambda x: in_bounds(x["pos"], point), intlst))
            assert(len(nodes) != 0)
            if len(nodes) != 1:
                for (i, x) in enumerate(nodes):
                    print()
                    print("index = ", i)
                    print(x)
                k = int(input())
                node = nodes[k]
            else:
                node = nodes[0]
            dict = {"type": "click", "data": node}
            self.testjson.append(dict)
            print(dict)
            return 
        
        match = re.fullmatch(r"text (\S+)", sstr)
        if match:
            text = match.group(1)
            dict = {"type": "text", "data": text}
            self.testjson.append(dict)
            print(dict)
            return 
        
        match = re.fullmatch(r"keyevent (\S+)", sstr)
        if match:
            text = match.group(1)
            dict = {"type": "keyevent", "data": text}
            self.testjson.append(dict)
            print(dict)
            return 
        
        match = re.fullmatch(r"swipe (\d+) (\d+) (\d+) (\d+) (\d+)", sstr)
        if match:
            swipe = [int(i) for i in match.group(1, 2, 3, 4, 5)]
            dict = {"type": "swipe", "data": swipe}
            self.testjson.append(dict)
            print(dict)
            return 
        
        assert(1)
        
    def gooracle(self, sstr:str):
        tree = get_current_ui()
        intlst = parseUIHierarchy(tree)
        save_ui(self.path + "/oracleui" + str(len(self.oraclejson)) + ".xml")
        save_current_screen(self.path + "/oraclefig" + str(len(self.oraclejson)) + ".png")
        save_json(self.path + "/oraclejson" + str(len(self.oraclejson)) + ".json", intlst)
        
        match = re.fullmatch(r"tap (\d+) (\d+)", sstr)
        if match:
            point = [int(i) for i in match.group(1, 2)]
            nodes = list(filter(lambda x: in_bounds(x["pos"], point), intlst))
            assert(len(nodes) != 0)
            if len(nodes) != 1:
                for (i, x) in enumerate(nodes):
                    print()
                    print("index = ", i)
                    print(x)
                k = int(input())
                node = nodes[k]
            else:
                node = nodes[0]
            dict = {"type": "click", "data": node}
            self.oraclejson.append(dict)
            print(dict)
            return 
        
        match = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", sstr)
        if match:
            tmp = [int(i) for i in match.group(1, 2, 3, 4)]
            point = [(tmp[0] + tmp[2]) // 2, (tmp[1] + tmp[3]) // 2]    
            nodes = list(filter(lambda x: in_bounds(x["pos"], point), intlst))
            assert(len(nodes) != 0)
            if len(nodes) != 1:
                for (i, x) in enumerate(nodes):
                    print()
                    print("index = ", i)
                    print(x)
                k = int(input())
                node = nodes[k]
            else:
                node = nodes[0]
            dict = {"type": "click", "data": node}
            self.oraclejson.append(dict)
            print(dict)
            return 
        
        match = re.fullmatch(r"text (\S+)", sstr)
        if match:
            text = match.group(1)
            dict = {"type": "text", "data": text}
            self.oraclejson.append(dict)
            print(dict)
            return 
        
        match = re.fullmatch(r"keyevent (\S+)", sstr)
        if match:
            text = match.group(1)
            dict = {"type": "keyevent", "data": text}
            self.oraclejson.append(dict)
            print(dict)
            return 
        
        match = re.fullmatch(r"swipe (\d+) (\d+) (\d+) (\d+) (\d+)", sstr)
        if match:
            swipe = [int(i) for i in match.group(1, 2, 3, 4, 5)]
            dict = {"type": "swipe", "data": swipe}
            self.oraclejson.append(dict)
            print(dict)
            return 
        
        assert(1)
        pass

    def __call__(self):
        print(self.__class__.__name__)
        if not self.__class__.__name__.endswith("Test"):
            raise Exception("Test class name must end with 'Test'")
        apk = re.findall('[A-Z][^A-Z]*', self.__class__.__name__)[0].lower()
        if apk not in configs.apk_info:
            raise Exception("Test class name must start with a valid apk name")
        self.path = "./testcases/" + self.__class__.__name__
        if not os.path.isdir(self.path):
            os.makedirs(self.path)
        self.testjson = []
        self.oraclejson = []
        setup_app(apk)
        self._body()
        
        tree = get_current_ui()
        save_ui(self.path + "/testui" + str(len(self.testjson)) + ".xml")
        save_current_screen(self.path + "/testfig" + str(len(self.testjson)) + ".png")
        save_json(self.path + "/testjson" + str(len(self.testjson)) + ".json", parseUIHierarchy(tree))
        
        self._pre_oracle()
        result = self._oracle()
        
        tree = get_current_ui()
        save_ui(self.path + "/oracleui" + str(len(self.oraclejson)) + ".xml")
        save_current_screen(self.path + "/oraclefig" + str(len(self.oraclejson)) + ".png")
        save_json(self.path + "/oraclejson" + str(len(self.oraclejson)) + ".json", parseUIHierarchy(tree))
        
        with open(self.path + "/test.json", "w") as f:
            json.dump(self.testjson, f)
        with open(self.path + "/oracle.json", "w") as f:
            json.dump(self.oraclejson, f)
        if result:
            self._cleanup()
        return result

# test for merriamwebster starts here
class MerriamwebsterTest(Test):

    def search_for_word(self, word):
        print('tap search')
        self.gotest('tap 377 104')
        adb_input('tap 377 104', 2) # tap search
        print('input word')
        self.gotest(f'text {word}')
        adb_input(f'text {word}', 2) # input word
        print('tap the first result')
        self.gotest('tap 56 305')
        adb_input('tap 56 305', 2) # tap the first result

    def tap_favorite(self):
        self.gotest("tap 655 1147")
        adb_input('tap 655 1147') # tap the heart

    def is_favorite():
        # check screenshot?
        raise NotImplementedError()

    def get_word(self, tree):
        node = tree.findall(".//node[@resource-id='com.merriamwebster:id/search_src_text']")[0]
        #node = next(filter(lambda x: x.attrib['resource-id'] == 'com.merriamwebster:id/search_src_text',
        #                   tree.findall('node')))
        return node.attrib['text']

class MerriamwebsterSearchForWordTest(MerriamwebsterTest):
    def __init__(self, word = "hello"):
        self.word = word

    def get_doc(self):
        return f"search for word '{self.word}'"

    def _body(self):
        self.search_for_word(self.word)

    def _oracle(self):
        tree = get_current_ui()
        return self.get_word(tree) == self.word

class MerriamwebsterSetFavoriteWordTest(MerriamwebsterTest):
    def __init__(self, word = "hello"):
        self.word = word

    def get_doc(self):
        return f"set '{self.word}' as favorite word"

    def _body(self):
        MerriamwebsterTest.search_for_word(self, self.word)
        MerriamwebsterTest.tap_favorite(self)

    def _pre_oracle(self):
        self.gooracle("tap 56 104")
        adb_input('tap 56 104') # tap menu
        self.gooracle("tap 300 727") 
        adb_input('tap 300 727')     
        self.gooracle("tap 360 208")                                                              # g bo to favorite
        adb_input('tap 360 208') # tap the first word

    def _oracle(self):
        tree = get_current_ui()
        return self.get_word(tree) == self.word

    def _cleanup(self):
        pass
        # self.tap_favorite()

class MerriamwebsterRecentWordTest(MerriamwebsterTest):
    def __init__(self, word="hello"):
        self.word = word

    def get_doc(self):
        return f"search for word '{self.word}' and check if it is in recent words"

    def _body(self):
        self.search_for_word(self.word)

    def _pre_oracle(self):
        self.gooracle("tap 56 104")
        adb_input('tap 56 104') # tap menu
        self.gooracle("tap 300 533")
        adb_input('tap 300 533') # go to recent
        self.gooracle("tap 360 208")
        adb_input('tap 360 208') # tap the first word

    def _oracle(self):
        tree = get_current_ui()
        return self.get_word(tree) == self.word

class MerriamwebsterPauseGameTest(MerriamwebsterTest):
    """ pause a game """
    def get_doc(self):
        return f"pause a game"
    def _body(self):
        self.gotest('tap 56 104')
        adb_input('tap 56 104') # tap menu
        self.gotest('tap 300 824')
        adb_input('tap 300 824') # go to game
        self.gotest('tap 531 238')
        adb_input('tap 531 238') # tap the first game
        self.gotest('tap 360 814')
        # save_current_screen("fig1.png")
        adb_input('tap 360 814') # tap play
        self.gotest('tap 50 110')
        # save_current_screen("fig2.png")
        adb_input('tap 50 110') # ...
        self.gotest('tap 50 110')
        adb_input('tap 50 110') # tap pause

    def _oracle(self):
        tree = get_current_ui()
        node = tree.findall(".//node[@bounds='[212,383][556,459]']")[0]
        return node.attrib['text'] == 'Quiz paused'

# test for webtoon starts here

class LinewebtoonTest(Test):
    def __init__(self):
        self.apk = 'linewebtoon'

    def open_settings():
        adb_input("tap 694 1132")
        adb_input("tap 388 247")
        # adb_tap_center('[668,256][692,280]') # tap more
        # adb_tap_center('[241,160][480,358]') # tap settings

class LinewebtoonAppVersionTest(LinewebtoonTest):

    def get_doc(self):
        return "check if app version is 2.4.3"

    def _body(self):
        # LinewebtoonTest.open_settings()
        self.gotest("tap 694 1132")
        adb_input("tap 694 1132")
        self.gotest("tap 388 247")
        adb_input("tap 388 247")
        self.gotest('swipe 360 1000 360 500 100')
        adb_input('swipe 360 1000 360 500 100') # scroll down
        self.gotest('[44,951][238,1000]')
        adb_tap_center('[44,951][238,1000]') # tap app version

    def _oracle(self):
        tree = get_current_ui()
        node = tree.findall(".//node[@resource-id='com.naver.linewebtoon:id/current_version']")[0]
        return node.attrib['text'].endswith('2.4.3')

class LinewebtoonOpenSleepModeTest(LinewebtoonTest):

    def get_doc(self):
        return "open sleep mode"

    def _body(self):
        
        self.gotest("tap 694 1132")
        adb_input("tap 694 1132")
        self.gotest("tap 388 247")
        adb_input("tap 388 247")
        self.gotest("swipe 360 1000 360 500 150")
        adb_input('swipe 360 1000 360 500 150') # scroll down
        # save_current_screen("screen.png")
        time.sleep(1)
        self.gotest("tap 680 620")
        adb_input("tap 680 620")
        # adb_tap_center('[582,864][720,918]') # tap sleep mode switch

    def _oracle(self):
        tree = get_current_ui()
        return len(tree.findall(".//node[@resource-id='android:id/summary']")) == 1

    def _cleanup(self):
        adb_input("tap 680 620")
        
# test for tripadvisor starts here

class TripadvisorTest(Test):
    pass

class TripadvisorAddTripWithNameTest(TripadvisorTest):
    def __init__(self, name = 'foobar'):
        self.name = name

    def get_doc(self):
        return f"add a trip with name '{self.name}'"

    def _body(self):
        # print("testesdtetstast")
        self.gotest('tap 384 1070')
        adb_input('tap 384 1070') # no thanks
        self.gotest('[180,1072][360,1172]')
        adb_tap_center('[180,1072][360,1172]') # go to my trip
        self.gotest('[574,56][670,152]')
        adb_tap_center('[574,56][670,152]') # tap the '+' sign
        self.gotest(f'text {self.name}')
        adb_input(f'text {self.name}') # input word
        self.gotest("keyevent KEYCODE_TAB")
        adb_input("keyevent KEYCODE_TAB")
        self.gotest("keyevent KEYCODE_TAB")
        adb_input("keyevent KEYCODE_TAB")
        self.gotest("keyevent KEYCODE_ENTER")
        adb_input("keyevent KEYCODE_ENTER", 3) # tap done

    def _pre_oracle(self):
        self.gooracle('[32,288][167,331]')
        adb_tap_center('[32,288][167,331]') # tap the first trip

    def _oracle(self):
        tree = get_current_ui()
        node = tree.findall('.//node[@bounds="[144,77][263,131]"]')[0]
        return node.attrib['text'] == self.name

    def _cleanup(self):
        adb_tap_center('[640,56][720,152]') # tap the '...' sign
        adb_tap_center('[352,181][680,219]') # delete trip
        adb_tap_center('[500,682][646,778]') # delete

# test for spotify starts here

class SpotifyTest(Test):

    def delete_first_list():
        adb_tap_center('[64,1072][262,1184]') # tap your playlists
        adb_tap_center('[216,468][336,509]') # tap the list
        adb_tap_center('[640,64][720,144]') # tap the '...' sign
        adb_tap_center('[32,816][390,928]') # delete list
        adb_tap_center('[361,670][702,766]') # delete

class SpotifySearchSingerTest(SpotifyTest):
    def __init__(self, singer:str = "Lady Gaga"):
        self.singer = singer

    def get_doc(self):
        return f"search for singer '{self.singer}'"

    def _body(self):
        self.gotest('[459,1072][656,1184]')
        adb_tap_center('[459,1072][656,1184]') # tap search
        time.sleep(0.5)
        self.gotest('[161,331][558,372]')
        adb_tap_center('[161,331][558,372]') # tap text box
        self.gotest('text ' + self.singer.split(' ')[0])
        adb_input('text ' + self.singer.split(' ')[0]) # input word
        self.gotest('[152,184][396,225]')
        adb_tap_center('[152,184][396,225]') # tap the first singer

    def _oracle(self):
        tree = get_current_ui()
        node = tree.findall('.//node[@resource-id="com.spotify.music:id/title"]')[0]
        return node.attrib['text'] == self.singer

class SpotifyCreateListWithGivenNameTest(SpotifyTest):
    def __init__(self, name:str = "Test"):
        self.name = name

    def get_doc(self):
        return f"create a list with name '{self.name}'"

    def _body(self):
        self.gotest('[64,1072][262,1184]')
        adb_tap_center('[64,1072][262,1184]', 25) # tap your playlists
        self.gotest('[202,274][517,370]')
        adb_tap_center('[202,274][517,370]') # tap create
        self.gotest(f'text {self.name}')
        adb_input(f'text {self.name}') # input word
        self.gotest('[360,747][624,857]')
        adb_tap_center('[360,747][624,857]') # tap create

    def _pre_oracle(self):
        self.gooracle('[0,64][80,144]')
        adb_tap_center('[0,64][80,144]') # tap back

    def _oracle(self):
        tree = get_current_ui()
        node = tree.findall('.//node[@bounds="[216,470][276,511]"]')[0]
        return node.attrib['text'] == self.name

    def _cleanup(self):
        SpotifyTest.delete_first_list()

class SpotifyCreateListAndAddSongTest(SpotifyTest):
    def __init__(self, name:str = "FEARLESS"):
        self.name = name

    def get_doc(self):
        return f"create a list and add song '{self.name}' to it"

    def _body(self):
        self.gotest('[64,1072][262,1184]')
        adb_tap_center('[64,1072][262,1184]', 25) # tap your playlists
        self.gotest('[202,274][517,370]')
        adb_tap_center('[202,274][517,370]', 1) # tap create
        self.gotest('[360,747][624,857]')
        adb_tap_center('[360,747][624,857]', 5) # tap skip
        self.gotest('[160,896][559,992]')
        adb_tap_center('[160,896][559,992]', 1) # tap add song
        self.gotest('[280,168][440,264]')
        adb_tap_center('[280,168][440,264]', 1) # tap search
        self.gotest(f'text {self.name}')
        adb_input(f'text {self.name}', 1) # input name
        self.gotest('[624,288][688,384]')
        adb_tap_center('[624,288][688,384]') # tap add song

    def _pre_oracle(self):
        self.gooracle('[0,64][80,144]')
        adb_tap_center('[0,64][80,144]') # tap back
        self.gooracle('swipe 360 700 360 500 400')
        adb_input('swipe 360 700 360 500 400') # scroll down
        self.gooracle('[149,922][571,1018]')
        adb_tap_center('[149,922][571,1018]') # tap edit

    def _oracle(self):
        tree = get_current_ui()
        node = tree.findall('.//node[@bounds="[184,537][339,578]"]')[0]
        return node.attrib['text'] == self.name

    def _cleanup(self):
        adb_tap_center('[0,64][80,144]') # tap back
        SpotifyTest.delete_first_list()

# test for goodrx starts here
class GoodrxTest(Test):
    pass

class GoodrxAppVersionTest(GoodrxTest):
    def get_doc(self):
        return f"check if app version is 5.3.6"

    def _body(self):
        self.gotest('[504,1137][696,1170]')
        adb_tap_center('[504,1137][696,1170]') # settings
        self.gotest('swipe 360 1000 360 500 100')
        adb_input('swipe 360 1000 360 500 100') # scroll down

    def _oracle(self):
        tree = get_current_ui()
        node = tree.findall(".//node[@resource-id='com.goodrx:id/textview_version']")[0]
        return node.attrib['text'] == "v5.3.6"

class GoodrxAddPrescriptionTest(GoodrxTest):
    def __init__(self, med = 'aspirin'):
        self.med = med

    def get_doc(self):
        return f"add a prescription for {self.med}"

    def _body(self):
        self.gotest('[24,1137][216,1170]')
        adb_tap_center('[24,1137][216,1170]') # my rx
        self.gotest('[576,928][688,1040]')
        adb_tap_center('[576,928][688,1040]') # add prescription
        self.gotest(f"text {self.med}")
        adb_input(f"text {self.med}", 2)
        self.gotest('[32,190][672,233]')
        adb_tap_center('[32,190][672,233]') # press the first entry
        self.gotest('[384,1100][386,1105]')
        adb_tap_center('[384,1100][386,1105]') # add to my rx

    def _oracle(self):
        tree = get_current_ui()
        node = tree.findall(".//node[@resource-id='com.goodrx:id/textview_myrx_name']")[0]
        return node.attrib['text'] == self.med

    def _cleanup(self):
        adb_tap_center('[144,282][241,325]') # click the med
        adb_tap_center('[528,56][624,152]') # click edit
        adb_tap_center('[256,1092][527,1135]') # delete prescription
        adb_tap_center('[518,666][646,762]', 3) # tap ok

# test for quizlet starts here
class QuizletTest(Test):
    pass

class QuizletTurnOnNightModeTest(QuizletTest):

    def get_doc(self):
        return f"turn on night mode"

    def _body(self):
        self.gotest('[540,1088][720,1184]')
        adb_tap_center('[540,1088][720,1184]') # press account
        self.gotest('swipe 360 1000 360 500 100')
        adb_input('swipe 360 1000 360 500 100') # scroll down
        self.gotest('[32,195][616,237]')
        adb_tap_center('[32,195][616,237]') # press night theme
        self.gotest('[634,205][728,259]')
        adb_tap_center('[634,205][728,259]') # press switch

    def _pre_oracle(self):
        self.gooracle('[0,48][112,160]')
        adb_tap_center('[0,48][112,160]') # go back

    def _oracle(self):
        tree = get_current_ui()
        node = tree.findall(".//node[@resource-id='com.quizlet.quizletandroid:id/user_settings_nightmode_text_indicator']")[0]
        # raise NotImplementedError()
        return node.attrib['text'] == "On" and True # we need to check here also the color of the screen

    def _cleanup(self):
        adb_tap_center('[32,195][616,237]') # press night theme
        adb_tap_center('[634,205][728,259]') # press switch

class QuizletSearchTest(QuizletTest):
    def __init__(self, name = 'test'):
        self.name = name

    def get_doc(self):
        return f"search for '{self.name}'"

    def _body(self):
        self.gotest('[180,1088][360,1184]')
        adb_tap_center('[180,1088][360,1184]') # press search
        self.gotest('[136,60][600,172]')
        adb_tap_center('[136,60][600,172]') # press search box
        self.gotest(f'text {self.name}')
        adb_input(f'text {self.name}')
        # adb_tap_center('[634,205][728,259]') # press switch
        self.gotest("keyevent KEYCODE_ENTER")
        adb_input("keyevent KEYCODE_ENTER", 2) # press enter

    def _oracle(self):
        tree = get_current_ui()
        node = tree.findall(".//node[@resource-id='com.quizlet.quizletandroid:id/setSearchTitle']")[0]
        # only assumes that the input is in the title
        return self.name in node.attrib['text'].lower()

# test for googletranslate starts here
class GoogletranslateTest(Test):
    pass

class GoogletranslateHelloTest(GoogletranslateTest):

    def get_doc(self):
        return f"translate 'hello' to spanish"

    def _body(self):
        self.gotest('[33,298][350,357]')
        adb_tap_center('[33,298][350,357]') # tap to enter text
        self.gotest("text hello")
        adb_input("text hello")
        self.gotest("keyevent KEYCODE_ENTER")
        adb_input("keyevent KEYCODE_ENTER", 2) # press enter

    def _oracle(self):
        tree = get_current_ui()
        node = tree.findall(".//node[@bounds='[16,768][752,827]']")[0]
        return node.attrib['text'] == "Hola"

class GoogletranslateHelloToFrenchTest(GoogletranslateTest):

    def get_doc(self):
        return f"translate 'hello' to french"

    def _body(self):
        self.gotest('[532,160][696,256]')
        adb_tap_center('[532,160][696,256]') # change language
        self.gotest('swipe 360 1000 360 500 90')
        adb_input('swipe 360 1000 360 500 90', 2) # scroll down
        self.gotest('tap 215 959')
        adb_input('tap 215 959') # choose french
        self.gotest('[33,298][350,357]')
        adb_tap_center('[33,298][350,357]') # tap to enter text
        self.gotest("text hello")
        adb_input("text hello")
        self.gotest("keyevent KEYCODE_ENTER")
        adb_input("keyevent KEYCODE_ENTER", 2) # press enter

    def _oracle(self):
        tree = get_current_ui()
        node = tree.findall(".//node[@bounds='[16,768][752,827]']")[0]
        return node.attrib['text'] == "Bonjour"

# test for googlechrome starts here
class GooglechromeTest(Test):

    def go_to(prompt):
        adb_tap_center('[40,58][516,148]')
        adb_input(f"text {prompt}")
        adb_input("keyevent KEYCODE_ENTER", 5) # press enter

    def get_url():
        tree = get_current_ui()
        full_url = tree.findall(".//node[@resource-id='com.android.chrome:id/url_bar']")[0].attrib['text']
        seps = full_url.split('/')
        if len(seps) > 1:
            return seps[2]
        return seps[0]        


class GooglechromeOpenIncognitoTest(GooglechromeTest):
    """open an incognito tab"""
    def get_doc(self):
        return f"open an incognito tab"
    def _body(self):
        self.gotest("[720,48][768,160]")
        adb_tap_center("[720,48][768,160]") # open menu
        self.gotest("[228,302][680,358]")
        adb_tap_center("[228,302][680,358]", 3) # open incognito tab
    def _pre_oracle(self):
        GooglechromeTest.go_to("www.baidu.com")

        self.url = GooglechromeTest.get_url()

        adb_tap_center("[720,48][768,160]") # open menu
        adb_tap_center("[228,460][680,600]") # open history
    def _oracle(self):
        tree = get_current_ui()
        nodes = tree.findall(".//node[@resource-id='com.android.chrome:id/description']")
        return len(nodes) == 0 or nodes[0].attrib['text'] != self.url

class GooglechromeChangeToBingTest(GooglechromeTest):
    """change default search engine to bing"""
    def get_doc(self):
        return f"change default search engine to bing"
    def _body(self):
        self.gotest("[720,48][768,160]")
        adb_tap_center("[720,48][768,160]", 1) # open menu
        self.gotest("[228,800][680,964]")
        adb_tap_center("[228,800][680,964]", 1) # open settings
        self.gotest("[32,652][235,695]")
        adb_tap_center("[32,652][235,695]", 1) # open search engine
        self.gotest("[118,483][185,529]")
        adb_tap_center("[118,483][185,529]", 1) # tap bing
    def _pre_oracle(self):
        adb_input("keyevent 4")
        adb_input("keyevent 4")
        GooglechromeTest.go_to("test")
    def _oracle(self):
        return GooglechromeTest.get_url() == "www.bing.com"

class AccuweatherTest(Test):
    pass

class AccuweatherLondonTest(AccuweatherTest):
    def get_doc(self):
        return "Search for the weather in London, GB"
    def _body(self):
        self.gotest("tap 400 115")
        adb_input("tap 400 115")
        self.gotest("tap 335 200")
        adb_input("tap 335 200")
        self.gotest("text London")
        adb_input("text London")
        self.gotest("tap 160 400")
        adb_input("tap 160 400")
        pass
    def _pre_oracle(self):
        pass
    def _oracle(self):
        tree = get_current_ui()
        nodes = tree.findall(".//node[@resource-id='com.accuweather.android:id/location_button']")
        return nodes[0].attrib['text'] == "London, GB"

class AccuweatherLocationSetTest(AccuweatherTest):
    def get_doc(self):
        return "Set London for favourites and set default location to London"
    def _body(self):
        self.gotest("tap 400 115")
        adb_input("tap 400 115")
        self.gotest("tap 335 200")
        adb_input("tap 335 200")
        self.gotest("text London")
        adb_input("text London")
        self.gotest("tap 680 385")
        adb_input("tap 680 385")
        self.gotest("tap 600 750")
        adb_input("tap 600 750")
        self.gotest("tap 680 180")
        adb_input("tap 680 180")
        self.gotest("tap 60 100")
        adb_input("tap 60 100")
        self.gotest("tap 60 110")
        adb_input("tap 60 110")
        self.gotest("tap 150 330")
        adb_input("tap 150 330")
        self.gotest('swipe 360 1000 360 500 90')
        adb_input('swipe 360 1000 360 500 90', 2)
        self.gotest("tap 150 330")
        adb_input("tap 150 330")
        self.gotest("tap 240 830")
        adb_input("tap 240 830")
        self.gotest("tap 120 650")
        adb_input("tap 120 650")
    def _pre_oracle(self):
        self.gooracle("tap 50 100")
        adb_input("tap 50 100")
        self.gooracle('swipe 360 1000 360 500 90')
        adb_input('swipe 360 1000 360 500 90', 2)
    def _oracle(self):
        tree = get_current_ui()
        nodes = tree.findall(".//node[@text='London']")
        return len(nodes) > 0

class AccuweatherDisplayModeTest(AccuweatherTest):
    def get_doc(self):
        return "Set Display Mode to Dark"
    def _body(self):
        self.gotest("tap 60 110")
        adb_input("tap 60 110")
        self.gotest("tap 150 330")
        adb_input("tap 150 330")
        self.gotest("tap 380 1000")
        adb_input("tap 380 1000")
    def _pre_oracle(self):
        pass
    def _oracle(self):
        # same hierarchy
        pass

class Autoscout24Test(Test):
    pass

class Autoscout24SearchTest(Autoscout24Test):
    def get_doc(self):
        return "Search for BMW X7"
    def _body(self):
        self.gotest("tap 400 220")
        adb_input("tap 400 220") # Search
        self.gotest("tap 180 400")
        adb_input("tap 180 400") # Make
        self.gotest("tap 300 300")
        adb_input("tap 300 300")
        self.gotest("text BMW")
        adb_input("text BMW")
        self.gotest("tap 340 380")
        adb_input("tap 340 380") # Model
        self.gotest("tap 250 530")
        adb_input("tap 250 530")
        self.gotest("tap 300 300")
        adb_input("tap 300 300")
        self.gotest("text X7")
        adb_input("text X7")
        self.gotest("tap 240 620")
        adb_input("tap 240 620")
        self.gotest("tap 560 870")
        adb_input("tap 560 870")
        self.gotest("tap 430 1000")
        adb_input("tap 430 1000") # Click Done
    def _pre_oracle(self):
        pass
    def _oracle(self):
        tree = get_current_ui()
        nodes = tree.findall(".//node[@text='BMW X7']")
        return len(nodes) > 0

class Autoscout24FavouriteTest(Autoscout24Test):
    def get_doc(self):
        return "Search for BMW X7 and add it to my favourites"
    def _body(self):
        self.gotest("tap 400 220")
        adb_input("tap 400 220") # Search
        self.gotest("tap 180 400")
        adb_input("tap 180 400") # Make
        self.gotest("tap 300 300")
        adb_input("tap 300 300")
        self.gotest("text BMW")
        adb_input("text BMW")
        self.gotest("tap 340 380")
        adb_input("tap 340 380") # Model
        self.gotest("tap 250 530")
        adb_input("tap 250 530")
        self.gotest("tap 300 300")
        adb_input("tap 300 300")
        self.gotest("text X7")
        adb_input("text X7")
        self.gotest("tap 240 620")
        adb_input("tap 240 620")
        self.gotest("tap 560 870")
        adb_input("tap 560 870")
        self.gotest("tap 430 1000")
        adb_input("tap 430 1000", 5) # Click Done
        self.gotest("tap 570 870")
        adb_input("tap 570 870")
    def _pre_oracle(self):
        self.gooracle("tap 384 1100")
        adb_input("tap 384 1100")
        self.gooracle("tap 384 825")
        adb_input("tap 384 825")
        pass
    def _oracle(self):
        tree = get_current_ui()
        nodes = tree.findall(".//node[@text='BMW X7']")
        return len(nodes) > 0
    
class Autoscout24DarkThemeTest(Autoscout24Test):
    def get_doc(self):
        return "Set Dark Theme"
    def _body(self):
        self.gotest("tap 50 115")
        adb_input("tap 50 115") # Click menu
        self.gotest("tap 180 450")
        adb_input("tap 180 450") # Click settings
        self.gotest("tap 130 580")
        adb_input("tap 130 580") # Appearance
        self.gotest("tap 612 753")
        adb_input("tap 612 753") # Dark theme
    def _pre_oracle(self):
        self.gooracle("tap 130 580")
        adb_input("tap 130 580") # Appearance
    def _oracle(self):
        tree = get_current_ui()
        nodes = tree.findall(".//node[@checked='true']")
        return nodes[0].attrib["text"] == "Dark theme"

class DuolingoTest(Test):
    pass

class DuolingoUsernameTest(DuolingoTest):
    def get_doc(self):
        return "check my username"
    def _body(self):
        self.gotest("tap 370 1100")
        adb_input("tap 370 1100") # Profile
    def _pre_oracle(self):
        pass
    def _oracle(self):
        tree = get_current_ui()
        nodes = tree.findall(".//node[@text='FWSdoVwd']")
        return len(nodes) > 0
    
class DuolingoAchievementsTest(DuolingoTest):
    def get_doc(self):
        return "check my Achievements"
    def _body(self):
        self.gotest("tap 370 1100")
        adb_input("tap 370 1100") # Profile
        self.gotest("tap 690 400")
        adb_input("tap 690 400") # View Achievements
    def _pre_oracle(self):
        pass
    def _oracle(self):
        tree = get_current_ui()
        nodes = tree.findall(".//node[@text='Achievements']")
        return nodes[0].attrib["bounds"] == "[144,83][378,125]"

class DuolingoGoalTest(DuolingoTest):
    def get_doc(self):
        return "set my daily goal to insane mode"
    def _body(self):
        self.gotest("tap 720 110")
        adb_input("tap 720 110")
        self.gotest("tap 490 110")
        adb_input("tap 490 110") # Settings
        self.gotest("tap 200 1050")
        adb_input("tap 200 1050")
        self.gotest("tap 200 1050")
        adb_input("tap 200 1050")
        
    def _pre_oracle(self):
        pass
    def _oracle(self):
        tree = get_current_ui()
        nodes = tree.findall(".//node[@text='Insane (50 XP per day)']")
        return len(nodes) > 0
    
class DuolingoLearnTest(DuolingoTest):
    def get_doc(self):
        return "start to learn"
    def _body(self):
        self.gotest("tap 386 277")
        adb_input("tap 386 277")
        self.gotest("tap 394 726")
        adb_input("tap 394 726")
        
    def _pre_oracle(self):
        pass
    def _oracle(self):
        tree = get_current_ui()
        nodes = tree.findall(".//node[@text='CHECK']")
        return len(nodes) > 0

class EvernoteTest(Test):
    pass

class EvernoteCreateTextNoteTest(EvernoteTest):
    def get_doc(self):
        return "Create a text note named ASE"
    def _body(self):
        self.gotest("tap 670 1080")
        adb_input("tap 670 1080")
        self.gotest("tap 670 1080")
        adb_input("tap 670 1080")
        # self.gotest("tap 576 710")
        # adb_input("tap 576 710") # allow access location
        self.gotest("tap 100 200")
        adb_input("tap 100 200") # title
        self.gotest("text ASE")
        adb_input("text ASE")
        self.gotest("tap 50 105")
        adb_input("tap 50 105", 5)
        
    def _pre_oracle(self):
        self.gooracle("tap 50 105")
        adb_input("tap 50 105")
    
    def _oracle(self):
        tree = get_current_ui()
        nodes = tree.findall(".//node[@text='ASE']")
        return len(nodes) > 0
    
    def _cleanup(self):
        adb_input("tap 450 400")
        adb_input("tap 720 100")
        tree = get_current_ui()
        nodes = tree.findall(".//node[@text='Delete note']")
        adb_tap_center(nodes[0].attrib["bounds"])
        adb_input("tap 630 720")
        
class EvernoteCreateNotebookTest(EvernoteTest):
    def get_doc(self):
        return "Create a notebook named ASEBOOK"
    def _body(self):
        self.gotest("tap 50 100")
        adb_input("tap 50 100")
        self.gotest("tap 200 520")
        adb_input("tap 200 520")
        self.gotest("tap 540 110")
        adb_input("tap 540 110")
        self.gotest("text ASEBOOK")
        adb_input("text ASEBOOK")
        self.gotest("tap 620 730")
        adb_input("tap 620 730", 20)
        
        
    def _pre_oracle(self):
        self.gooracle("tap 440 735")
        adb_input("tap 440 735")
        self.gooracle("tap 50 105")
        adb_input("tap 50 105")
    
    def _oracle(self):
        tree = get_current_ui()
        nodes = tree.findall(".//node[@text='ASEBOOK']")
        return len(nodes) > 0
    
    def _cleanup(self):
        adb_input("tap 720 440")
        adb_input("tap 150 900")
        adb_input("text Delete")
        adb_input("tap 550 840")
        
class EvernoteCountryTest(EvernoteTest):
    def get_doc(self):
        return "find my account's country"
    def _body(self):
        self.gotest("tap 726 113")
        adb_input("tap 726 113")
        self.gotest("tap 480 590")
        adb_input("tap 480 590")
        self.gotest("tap 250 750")
        adb_input("tap 250 750")
        self.gotest('swipe 360 1000 360 500 90')
        adb_input('swipe 360 1000 360 500 90', 2)
        
    def _pre_oracle(self):
        pass
    
    def _oracle(self):
        tree = get_current_ui()
        nodes = tree.findall(".//node[@text='Country']")
        return len(nodes) > 0

class MarvelcomicsTest(Test):
    pass

class MarvelcomicsLocationTest(MarvelcomicsTest):
    
    def get_doc(self):
        return "Change download location to SD card"
    def _body(self):
        self.gotest("tap 50 100")
        adb_input("tap 50 100")
        self.gotest("tap 100 1130")
        adb_input("tap 100 1130")
        self.gotest('swipe 360 1000 360 500 90')
        adb_input('swipe 360 1000 360 500 90', 2)
        self.gotest("tap 230 1100")
        adb_input("tap 230 1100")
        self.gotest("tap 180 705")
        adb_input("tap 180 705")
        self.gotest("tap 550 975")
        adb_input("tap 550 975")
        
    def _pre_oracle(self):
        pass
    
    def _oracle(self):
        tree = get_current_ui()
        nodes = tree.findall(".//node[@text='SD card']")
        return len(nodes) > 0
    
class MarvelcomicsVersionTest(MarvelcomicsTest):
    
    def get_doc(self):
        return "check if app version is 3.10.20.310432"
    def _body(self):
        self.gotest("tap 50 100")
        adb_input("tap 50 100")
        self.gotest('swipe 160 1000 160 500 90')
        adb_input('swipe 160 1000 160 500 90', 2)
        self.gotest("tap 100 1130")
        adb_input("tap 100 1130")
        
    def _pre_oracle(self):
        pass
    
    def _oracle(self):
        tree = get_current_ui()
        nodes = tree.findall(".//node[@text='Version 3.10.20.310432']")
        return len(nodes) > 0
    
class ZedgeTest(Test):
    pass

class ZedgeClearCacheTest(ZedgeTest):
    
    def get_doc(self):
        return "clear cache"
    def _body(self):
        self.gotest('swipe 160 1000 160 500 90')
        adb_input('swipe 160 1000 160 500 90', 2)
        self.gotest("tap 100 950")
        adb_input("tap 100 950")
        self.gotest("tap 300 230")
        adb_input("tap 300 230")
        self.gotest("tap 200 510")
        adb_input("tap 200 510")
        self.gotest("tap 600 715")
        adb_input("tap 600 715")
        
    def _pre_oracle(self):
        pass
    
    def _oracle(self):
        tree = get_current_ui()
        nodes = tree.findall(".//node[@text='Cache size: 0 kB']")
        return len(nodes) > 0


def get_coarse_description(cls):
    parsed_name = re.findall('[A-Z][^A-Z]*', cls[0])
    return (' ').join(parsed_name[1:-1])

def get_detailed_description(cls):
    return cls[1].__doc__;

def get_test_list():
    clsmembers = inspect.getmembers(sys.modules[__name__], inspect.isclass)
    test_list = []
    for cls in clsmembers:
        if sum([ch.isupper() for ch in cls[0]]) <= 2:
            continue
        apk_info = re.findall('[A-Z][^A-Z]*',cls[1].__base__.__name__)
        # parsed_name = re.findall('[A-Z][^A-Z]*', cls[0])
        test_instance = cls[1]()
        # print(test_instance)
        test_list.append({
            'test': cls[1],
            'apk': apk_info[0],
            # 'function': (' '.join(parsed_name[1:-1])).lower(),
            'function': test_instance.get_doc()
            })

    return test_list
