/*
 * GUIHierarchyPrinterClient.java - part of the GATOR project
 *
 * Copyright (c) 2014, 2015 The Ohio State University
 *
 * This file is distributed under the terms described in LICENSE in the
 * root directory.
 */
package presto.android.gui.clients;
import java.util.Date;
import com.google.common.collect.Multimap;
import org.json.simple.JSONArray;
import org.json.simple.JSONObject;
import presto.android.Configs;
import presto.android.Debug;
import presto.android.Logger;
import presto.android.gui.GUIAnalysisClient;
import presto.android.gui.GUIAnalysisOutput;
import presto.android.gui.clients.energy.VarUtil;
import presto.android.gui.graph.NNode;
import presto.android.gui.graph.NObjectNode;
import presto.android.gui.rep.GUIHierarchy;
import presto.android.gui.rep.GUIHierarchy.Activity;
import presto.android.gui.rep.GUIHierarchy.Dialog;
import presto.android.gui.rep.GUIHierarchy.EventAndHandler;
import presto.android.gui.rep.GUIHierarchy.View;
import presto.android.gui.rep.StaticGUIHierarchy;
import presto.android.gui.wtg.WTGAnalysisOutput;
import presto.android.gui.wtg.WTGBuilder;
import presto.android.gui.wtg.ds.HandlerBean;
import presto.android.gui.wtg.ds.WTG;
import presto.android.gui.wtg.ds.WTGEdge;
import presto.android.gui.wtg.ds.WTGNode;
import soot.Scene;
import soot.SootMethod;
import presto.android.gui.IDNameExtractor;
import java.io.File;
import java.io.PrintStream;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Set;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.Arrays;
public class AdWidgetIDPrinterClient implements GUIAnalysisClient {
    GUIAnalysisOutput output;
    GUIHierarchy guiHier;
    List<String> adLibs;
    private PrintStream out;
    private int indent;
    public void AdLibChecker(String filePath) {
        try {
            // Read all lines from the file as a single String
            String content = new String(Files.readAllBytes(Paths.get(filePath)));
            // Assuming the file content is single-line and parse it into a List
            // Removing single quotes and splitting by comma
//            adLibs = Arrays.asList(content.replace("'", "").split(",\\s*"));
            adLibs = Arrays.asList(content.split("\\r?\\n"));
        } catch (IOException e) {
            e.printStackTrace();
            adLibs = null;
        }
    }
    void printf(String format, Object... args) {
        for (int i = 0; i < indent; i++) {
            out.print(' ');
        }
        out.printf(format, args);
    }

    void log(String s) {
        System.out.println(
                "\033[1;31m[GUIHierarchyPrinterClient] " + s + "\033[0m");
    }

    @Override
    public void run(GUIAnalysisOutput output) {
        long startTime = System.currentTimeMillis();
        log("Start Time: " + new Date(startTime));
        this.output = output;
        guiHier = new StaticGUIHierarchy(output);
        long staticGUIEndTime = System.currentTimeMillis();
        long staticGUITime = staticGUIEndTime - startTime; // Time used in milliseconds
        log("static GUI Hierarchy Time: " + staticGUITime + " ms");
        // Init the file io
        try {
            File file = File.createTempFile(Configs.benchmarkName + "-", ".xml");
            log("XML file: " + file.getAbsolutePath());
            out = new PrintStream(file);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
        AdLibChecker("adlibs");
        // Start printing
        printf("<GUIHierarchy app=\"%s\">\n", guiHier.app);
        printActivities();
        printDialogs();
        printf("</GUIHierarchy>\n");

        // Finish
        out.flush();
        out.close();

        VarUtil.v().guiOutput = output;
        Configs.debugCodes.add(Debug.DUMP_CCFX_DEBUG);
        String[] split = Configs.benchmarkName.split("/");
        String apkname = split[split.length - 1];
//        WTGBuilder wtgBuilder = new WTGBuilder(apkname);


        ArrayList <Activity> activities= (ArrayList) guiHier.activities;
        ArrayList <Dialog> dialogs= (ArrayList) guiHier.dialogs;


        PrintWriter out1 = null;

        try {
            out1 = new PrintWriter("json_output/" + apkname + ".json");
            JSONArray wins = new JSONArray();
            for (Activity n : activities) {
                JSONObject win = new JSONObject();
                wins.add(win);
                win.put("name", n.getName());
                JSONArray jsonviews = new JSONArray();
                win.put("views", jsonviews);
                ArrayList<View> allViews = DFSGetAllViews(n.views);
                for (View view : allViews) processView(view,jsonviews,apkname);

            }
            for (Dialog n : dialogs) {
                JSONObject win = new JSONObject();
                wins.add(win);
                win.put("name", n.getName());
                JSONArray jsonviews = new JSONArray();
                win.put("views", jsonviews);
                ArrayList<View> allViews = DFSGetAllViews(n.views);
                for (View view : allViews) processView(view,jsonviews,apkname);

            }

            out1.println(wins.toJSONString());
            out1.close();
        } catch (Exception e) {
            // TODO Auto-generated catch block
            e.printStackTrace();
        }
        long endTime = System.currentTimeMillis();
        log("End Time: " + new Date(endTime));

        // Calculate and log the used time
        long usedTime = endTime - startTime; // Time used in milliseconds
        log("Used Time: " + usedTime + " ms");
        Logger.verb(this.getClass().getSimpleName(),
                "WTG building starts");
        WTGBuilder wtgBuilder = new WTGBuilder(apkname);
        wtgBuilder.build(output);
        WTGAnalysisOutput wtgAO = new WTGAnalysisOutput(output, wtgBuilder);
        WTG wtg = wtgAO.getWTG();

//        Collection<WTGEdge> edges = wtg.getEdges();
//        Collection<WTGNode> nodes = wtg.getNodes();
//
//        Multimap<NObjectNode, NObjectNode> guiHierarchy = wtgBuilder.guiHierarchy;
//        Multimap<NObjectNode, HandlerBean> widgetToHandlers = wtgBuilder.widgetToHandlers;

        Logger.verb("DEMO", "Application: " + Configs.benchmarkName);
        Logger.verb("DEMO", "Launcher Node: " + wtg.getLauncherNode());


    }

    void printRootViewAndHierarchy(ArrayList<View> roots) {
        indent += 2;
        for (View rootView : roots) {
            printView(rootView);
        }
        indent -= 2;
    }
    void processView(View view,JSONArray jsonviews, String apkname) {
//                    for each view in this window(activity,dialog,...)
            JSONObject viewjson = new JSONObject();
            jsonviews.add(viewjson);
            viewjson.put("name", view.toString());

            StringBuilder adsInfo = new StringBuilder();
            String label = "none";
            if (view.toString().contains("toolbar")) {
                Logger.verb("ADS", view.toString());
            }

            if ( isAdView(view)) {

                adsInfo.append(view.getParentWithIdName().getIdName());
                label = "static"+'|'+view.toParentString();
            }

            SootMethod method = hasAdHandler(view.eventAndHandlers,apkname);
            if (method != null) {
                if (adsInfo.length() > 0) adsInfo.append(" + ");
                adsInfo.append(method.getActiveBody().toString());
                label = "dynamic"+'|'+view.toParentString();;
            }

            if (adsInfo.length() == 0) {
                adsInfo.append("none");
            } else {
                // If adsInfo is not empty but label hasn't been updated (in case isAdView didn't catch anything)
                if (label.equals("none")) label = "detected";
            }
            viewjson.put("label", label);
            viewjson.put("ads", adsInfo.toString());

            JSONArray jsonhandlers = new JSONArray();
            viewjson.put("handlers", jsonhandlers);
            for (EventAndHandler handler : view.eventAndHandlers) {
//                        for each handler
                JSONObject handlerjson = new JSONObject();
                jsonhandlers.add(handlerjson);
                handlerjson.put("event", handler.getEvent());
                JSONArray eventhandlers = new JSONArray();
                handlerjson.put("handlers", eventhandlers);
                SootMethod m =handler.getEventHandlerMethod();
                eventhandlers.add(m.toString());

            }

        }
//jsonviews-->viewjson-->label, ads, handlers

     ArrayList<View> DFSGetAllViews(ArrayList<View> views) {
        ArrayList<View> result = new ArrayList<>();
        for (View v : views) {
            result.add(v); // Add the current view
            if (!v.views.isEmpty()) {
                // If the current view has subviews, recursively find and add them
                result.addAll(DFSGetAllViews(v.views));
            }
        }
        return result;
    }
    public Boolean containAdLibs(String type) {
        for (String adLib : adLibs) {
            if (type.contains(adLib)) {
                return true; // Found an adlib in 'type'
            }
        }
        return false; // No adlibs found in 'type'
    }
    Boolean isAdView(View view){
        // Assuming adLib is defined elsewhere
        if (containAdLibs(view.getType())){
            return true;
        }
        return false;
    }
    View parentAd(View view) {
        // view self is a class of ad, but no id, then find it parent until have id
        List<View> children = view.getChildren();
        for (View child : children) {
            if (child instanceof View && isAdView((View) child)) {
                return (View) child;
            }
        }
        return null;
    }
    SootMethod hasAdHandler(ArrayList<EventAndHandler> handlers, String apkname) {
        for (EventAndHandler handler : handlers) {
            SootMethod method = handler.getEventHandlerMethod(); // Assuming getHandlers returns a Set of SootMethods
                if (method != null) {
                    String methodBody = method.getActiveBody().toString();
                    if (containAdLibs(methodBody) ||(
//                            methodBody.contains("market://details?id=") ||
//                            methodBody.contains("play.google.com/store/apps/")&&
//                            some times the link is like market://search?q=, play.google.com/search?q=
                            methodBody.contains("market://") ||
                                    methodBody.contains("http")&& !methodBody.contains("id="+apkname) ||
                            methodBody.contains("play.google.com/")&&!methodBody.contains("id="+apkname)
                    )
                    )
                    {
                        return method;
                }
            }
        }
        return null;
    }


    void printActivities() {
        for (Activity act : guiHier.activities) {
            indent += 2;
            printf("<Activity name=\"%s\">\n", act.name);

            // Roots & view hierarchy (including OptionsMenu)
            printRootViewAndHierarchy(act.views);

            printf("</Activity>\n");
            indent -= 2;
        }
    }

    void printDialogs() {
        for (Dialog dialog : guiHier.dialogs) {
            indent += 2;
            printf("<Dialog name=\"%s\" allocLineNumber=\"%d\" allocStmt=\"%s\" allocMethod=\"%s\">\n",
                    dialog.name, dialog.allocLineNumber,
                    xmlSafe(dialog.allocStmt), xmlSafe(dialog.allocMethod));
            printRootViewAndHierarchy(dialog.views);
            printf("</Dialog>\n");
            indent -= 2;
        }
    }

    public String xmlSafe(String s) {
        return s
                .replaceAll("&", "&amp;")
                .replaceAll("\"", "&quot;")
                .replaceAll("'", "&apos;")
                .replaceAll("<", "&lt;")
                .replaceAll(">", "&gt;");

    }

    // WARNING: remember to remove the node before exit. Very prone to error!!!
    void printView(View view) {
        // <View type=... id=... idName=... text=... title=...>
        //   <View ...>
        //     ...
        //   </View>
        //   <EventAndHandler event=... handler=... />
        // </View>

        String type = String.format(" type=\"%s\"", view.type);
        String id = String.format(" id=\"%d\"", view.id);
        String idName = String.format(" idName=\"%s\"", view.idName);
        // TODO(tony): add the text attribute for TextView and so on
        String text = "";
        // title for MenuItem
        String title = "";
        if (view.title != null) {
            if (!type.contains("MenuItem")) {
//                throw new RuntimeException(type + " has a title field!");
            }
            for (String title_item: view.title){
                title = String.format(" title=\"%s\"", xmlSafe(title_item));
            }
//            title = String.format(" title=\"%s\"", xmlSafe(view.title));
        }
        String head =
                String.format("<View%s%s%s%s%s>\n", type, id, idName, text, title);
        printf(head);

        {
            // This includes both children and context menus
            for (View child : view.views) {
                indent += 2;
                printView(child);
                indent -= 2;
            }
            // Events and handlers
            for (EventAndHandler eventAndHandler : view.eventAndHandlers) {
                indent += 2;
                String handler = eventAndHandler.handler;
                String safeRealHandler = "";
                if (handler.startsWith("<FakeName_")) {
                    SootMethod fake = Scene.v().getMethod(handler);
                    SootMethod real = output.getRealHandler(fake);
                    safeRealHandler = String.format(
                            " realHandler=\"%s\"", xmlSafe(real.getSignature()));
                }
                printf("<EventAndHandler event=\"%s\" handler=\"%s\"%s />\n",
                        eventAndHandler.event, xmlSafe(eventAndHandler.handler), safeRealHandler);
                indent -= 2;
            }
        }

        String tail = "</View>\n";
        printf(tail);
    }
}
