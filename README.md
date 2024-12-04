# AdSuite
Mobile advertisements (in short as mobile ads) are frequently placed in mobile apps by developers to make profit.
It is crucial to collect and analyze mobile ads as their prevalence without proper regulation can compromise user experiences and promote malware.  
However, ads are embedded in different user interfaces (UIs), require non-trivial efforts to navigate to these UIs.
Existing approaches rely on general-purpose UI navigation, wasting resources on non-ad related UIs, and base detection on runtime features, which become ineffective as ad content changes over time.


To address these issues, in this paper, we propose a novel approach named AdSuite that synergistically combines static analysis, dynamic UI navigation, and large language model (LLM) to effectively and efficiently detect mobile ads, assisting ad regulation.
Specifically, AdSuite first conducts static analysis to detect widgets used to place mobile ads, referred to as _ad widgets_, based on their widget attributes and code behaviors. 
Second, AdSuite instructs an LLM with contextual information to find out the feasible paths leading to the UIs containing ad widgets and triggers the ads widgets based on static analysis's output.

![AdSuite.png](AdSuite.png)
## 1.Dataset and Groundtruth

We have released our full dataset in [google drive](https://drive.google.com/drive/folders/1dTLBSfQLyrNx1qM72OStax8T5H1eYT7_?usp=sharing
)

You can use [the notebook](Groundtruth/readGroundtruth.ipynb) to read our labeled ad widgets. 

The APK files are too large. You can download them using AndroZoo
```bash
curl -o filename.apk "https://androzoo.uni.lu/api/download?apikey=YOUR_API_KEY&sha256=SHA256_HASH_OF_APK"
```

We have put 3 APK files [here](Groundtruth/apks), the rest of the repo will analyze these APKs.

## 2.Static Analysis
The static ad analysis is built in Java 8 (we use jdk corretto 1.8) Android 22

The deployment of android environment of our static ad analysis requires non-trivial effort.
Therefore, we have constructed a docker image of the project and published in
`maishang9/adsuite`


Command to run static ad analysis

```bash
docker pull maishang9/adsuite
   
docker run -dit -v project_dir/Groundtruth/:/data -v project_dir/StaticAnalysis/staticAdAnalysis:/gator maishang9/adsuite /bin/bash
```
The static analysis may take quite long time (depending on your setting). Therefore, you'd better detach the container.

```bash
docker exec -it {container_id} /bin/bash

conda activate myenv && cd gator/

python run_gator.py --apk_dir /data/apks --adk_dir /usr/local/android-sdk-linux

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



## 3.UI Exploration


The LLM-based UI Exploration is built upon Guardian [ISSTA 2024] framework. Our modification and enhancement of Guardian is mainly in \
- [atg.py](UIExploration/atg.py): The code to process WTG dot file, make prompts
- [rag.py](UIExploration/rag.py): The RAG code
- [guardian.py](UIExploration/guardian.py): The main UI Exploration framework


Below are the steps to reproduce our evaluation
1. configure Openai api key as `UIExploration/api.key`
2. Run rag.py to create rag embedding
2. Run [test_adsuite.py](UIExploration/test_adsuite.py)



