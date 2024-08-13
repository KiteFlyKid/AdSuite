import csv, traceback
from pathlib import  Path
import pandas as pd
from guardian import Guardian
from chatgpt import sessions, getTotalTokensUsed
import os
from all_tests import *
from configs import GenerationConf
port = "R5CT90DQ2ND"




def generate_results(tests,GENERATION='',iter=0):
    o = open("output.log", "a")   
    print('generation type',GENERATION)
    outputDir = Path(f"raw_results/{GENERATION}_running{iter}")
    print(str(outputDir))
    for test in tests:
        print(test)
        app = test["apk"]
        pkg = test['pkg']

        target = test["function"]
        outputPath = outputDir / f"{pkg}"
        if not (outputPath/"scores.csv").exists():
            sa_csv_path=f'data/csv/{pkg}.csv'

            if not Path(sa_csv_path).exists():
                print('csv not exists')
                continue
            ad_csv = pd.read_csv(sa_csv_path)
            print(test['apk'])

            setup_app(pkg)

            os.environ['test_case_name'] = test['apk']
            chatDroid: Guardian = Guardian(app, pkg, target, port, ad_csv, GENERATION=GENERATION)
            startTime = time.time()
            testCase: TestCase = chatDroid.genTestCase()
            endTime = time.time()
            del os.environ['test_case_name']
            # dump test case
            outputPath.mkdir(parents=True, exist_ok=True)
            testCase.dump(outputPath)

            # dump test case without compression
            history_dir = outputPath / "history"
            history_dir.mkdir(parents=True, exist_ok=True)
            fullTestCase = TestCase(EventSeq(chatDroid.all_events),[context.hierarchy for context in chatDroid.history])

            fullTestCase.dump(history_dir)

            # dump chatgpt history
            (outputPath / "sessions").mkdir(parents=True, exist_ok=True)
            totalTokensUsed = getTotalTokensUsed()
            for idx, session in enumerate(sessions):
                session.dump(outputPath / "sessions" / f"session{idx}.json")
            sessions.clear()
            print(test['apk'])

            try:
                with open(outputPath / "scores.csv", "w") as output:
                    writer = csv.writer(output)
                    # writer.writerow(["metric", "score"])
                    writer.writerow(["duration", endTime - startTime])
                    writer.writerow(["token_used", totalTokensUsed])

            except Exception as e:
                error_message = traceback.format_exc()
            #     print(test['apk']+ " evaluation failed!")
            #     # o.write(test['apk'] + "evaluation failed")
            #     # o.write(error_message + "\n")


def test_ATG(df,model,iter=0):
    TASK='task1'

    tests=[]
    for idx,row in df.iterrows():
        tests.append({'apk': row.app_name, 'pkg': row.pkg_name, 'function': row[TASK]})
    generate_results(tests, GENERATION=f'{model}_{TASK}', iter=iter)


    tests=[]
    for idx,row in df.iterrows():
        file_path = f"data/dot/{row.pkg_name}.apk.wtg.dot"
        if Path(file_path).exists():
            tests.append({'apk':row.app_name,'pkg':row.pkg_name,'function':row[TASK]})
    generate_results(tests, GENERATION=f'{model}_DijkstraATG_{TASK}', iter=iter)
    generate_results(tests, GENERATION=f'{model}_KHopATG2_{TASK}', iter=iter)
    generate_results(tests, GENERATION=f'{model}_KHopATG1_{TASK}', iter=iter)
    generate_results(tests, GENERATION=f'{model}_DFSATG_{TASK}', iter=iter)

def test_customprompt(df,model,iter=0):
    custom_apps=['com.dicionario_bibico_free.dicionario_bibico_free',
     'com.teachersparadise.fingertracing001',
     'com.xphotokit.app',
     'com.app2game.aquarium.live.wallpaper.free',
     'com.gkinhindiofflince.a30000gkquestion',
     'com.meberty.selfievideorecorder',
     'com.zavariseapps.mulherdeoracao',
     'com.purpleberry.staticwall.cnygreeting.g01',
     'com.tabexam.imo1',
     'com.sanaedutech.chemistry_quiz',
     'com.song_om_mantra_adv',
     'godbless.deliverance.prayer',
     'ru.androidtools.countries_of_the_world',
     'com.wolf.woringtones',
     'com.purpleberry.staticwall.cnygreeting.g01',
     'godbless.deliverance.prayer',
     'conversor.conversaotaxasbasico.cnyshp',
     'com.dicionario_bibico_free.dicionario_bibico_free',
     'com.afghan.af.amir.ahmadi',
     'com.circledev.nirvana',
     'com.rr.lordshivawallpapers',
     'com.circledev.yasin_dan_tahlil',
     'ru.androidtools.countries_of_the_world',
     'com.kitegames.baby.spans.photo.editor',
     'godbless.orthodox.prayers',
     'com.ikeyboard.theme.led.pastel',
     'conversor.conversaotaxasbasico.gbpmad',
     'com.Catholic.Zone.Divine.Mercy.Novena.Chaplet.Litany.Song.Audio.offline.Text']

    TASK = 'custom ads'
    tests = []
    for idx, row in df.iterrows():
        pkg_name=row.pkg_name
        if pkg_name in custom_apps:
            tests.append({'apk': row.app_name, 'pkg': pkg_name, 'function': row[TASK]})
    generate_results(tests, GENERATION=f'{model}_rag_{TASK}', iter=iter)
    generate_results(tests, GENERATION=f'{model}_{TASK}', iter=iter)


def test_guidedGPT(df,model,iter=0):

    TASK = 'task1'
    tests = []
    for idx, row in df.iterrows():
        tests.append({'apk': row.app_name, 'pkg': row.pkg_name, 'function': row[TASK]})

# compare to DFS, whether GPT-guide makes improvements
    generate_results(tests, GENERATION=f'{model}_{TASK}', iter=iter)
    generate_results(tests, GENERATION=f'DFS', iter=iter)



    TASK = 'notask'
    tests = []
    for idx, row in df.iterrows():
        tests.append({'apk': row.app_name, 'pkg': row.pkg_name, 'function': 'Explore the app'})

    #whether the Navigation guide makes improvements
    generate_results(tests, GENERATION=f'{model}_{TASK}', iter=0)
    generate_results(tests, GENERATION=f'{model}_{TASK}', iter=1)

def test_guidedStaticAnalysis(df, model,iter=0):
    TASK = 'task1'
    tests = []
    for idx, row in df.iterrows():
        tests.append({'apk': row.app_name, 'pkg': row.pkg_name, 'function': row[TASK]})
    generate_results(tests, GENERATION=f'{model}_noSA_{TASK}', iter=iter)

    generate_results(tests, GENERATION=f'DFS_noSA', iter=iter)
    generate_results(tests, GENERATION=f'DFS', iter=iter)

    generate_results(tests, GENERATION=f'DFS_noSA_MADDROID', iter=iter)
    generate_results(tests, GENERATION=f'DFS_MADDROID', iter=iter)

    generate_results(tests, GENERATION=f'{model}_noSA_notask', iter=0)
    generate_results(tests, GENERATION=f'{model}_noSA_notask', iter=1)

    TASK = 'custom ads'
    tests = []
    for idx, row in df.iterrows():
        tests.append({'apk': row.app_name, 'pkg': row.pkg_name, 'function': row[TASK]})
    generate_results(tests, GENERATION=f'{model}_rag_noSA_{TASK}', iter=iter)



if __name__=="__main__":


    df=pd.read_csv('data/task_df.csv')
    labeled_pkgs =df.pkg_name.tolist()


    test_guidedGPT(df,'GPT4omini')
    test_guidedStaticAnalysis(df,'GPT4omini')
    test_ATG(df, 'GPT4omini',iter=1)

