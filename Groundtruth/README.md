To manually label the ad widget

1. Start your device and run tool.py in command line
2. Open UIauto.dev
3. Manually navigate (i.e., you tap the phone)to the ad UI of the current app
4. Input the widget type in the command line: 'i' for adview, 'c' for cutom-made, 'p' for popup (tool.py Line 60 - Line 74)
5. Copy the bound of the widget in UIauto.dev to command line
6. Repeat 3-5 until all the ad widget of that app are recorded, input 'stop' in command line (tool.py Line 97)