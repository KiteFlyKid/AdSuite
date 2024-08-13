# AdSuite

## Dataset and Groundtruth

We have released our full dataset in [google drive](https://drive.google.com/drive/folders/1dTLBSfQLyrNx1qM72OStax8T5H1eYT7_?usp=sharing
)

You can use [the notebook](Groundtruth/readGroundtruth.ipynb) to read our labeled ad widgets. 

## Static Analysis
The static ad analysis is built in Java 8 (we use jdk corretto 1.8) Android 22

The deployment of android environment of our static ad analysis requires non-trivial effort.
Therefore, we have constructed a docker image of the project and published in
`maishang9/adsuite`


Command to run static ad analysis

```bash
docker run -dit -v {Your APK Directory}:/data -v {Static Ad Analysis Directory}:/gator maishang9/adsuite /bin/bash

docker exec -it {container_id} /bin/bash

conda activate myenv && cd gator/

python run_gator.py --apk_dir /data/{Your APK Directory} --adk_dir /usr/local/android-sdk-linux

```

If you have successfully run the code, you will have three output directory under the `{Static Ad Analysis Directory}` : 
- `json_output/` : the ad widgets. Each apk outputs a json, the json include all widgets/view id/event handler of the apk. 
To help visualize the data, we put the code that extracts ad widgets in a jupyter notebook. 
Please run [the notebook](StaticAnalysis/static2dynamic.ipynb), which will generate a directory `csv/` to store the ad widgets in csv format.
- `dot_output`: the WTGs. They are already in good dot format, you can visualize them using graphiz.
- `log_output`: the logs, which you can view the static process.

and a `result.txt` used to resume the static ad analysis (please see `run_gator.py` for how to rerun, redo failed apk)




Then, move the `csv/` to `UIExploration/data/csv/`, and `dot_output` to `UIExploration/data/dot/`.
We have put 3 examples `.csv` and `.dot` file there. 



## UI Exploration


The LLM-based UI Exploration is built upon Guardian [ISSTA 2024] framework. Our modification and enhancement of Guardian is mainly in \
- [atg.py](UIExploration/atg.py): The code to process WTG dot file, make prompts
- [rag.py](UIExploration/rag.py): The RAG code
- [guardian.py](UIExploration/guardian.py): The main UI Exploration framework


Below are the steps to reproduce our evaluation
1. configure Openai api key as `UIExploration/api.key`
2. Run rag.py to create rag embedding
2. Run [test_adsuite.py](UIExploration/test_adsuite.py)



